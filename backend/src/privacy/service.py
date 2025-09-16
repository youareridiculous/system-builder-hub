"""
Privacy Settings Service
Manages privacy settings and provides privacy-aware operations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import PrivacySettings, PrivacyAuditLog, DataRetentionJob, PrivacyTransparencyLog
from .modes import PrivacyMode, privacy_resolver
from .redaction import redaction_engine, retention_policy
from ..crypto.keys import get_key_manager

logger = logging.getLogger(__name__)


class PrivacyService:
    """Service for managing privacy settings and operations."""
    
    def __init__(self):
        self.key_manager = get_key_manager()
    
    def get_privacy_settings(self, tenant_id: str, db: Session) -> Optional[PrivacySettings]:
        """Get privacy settings for a tenant."""
        return db.query(PrivacySettings).filter(PrivacySettings.tenant_id == tenant_id).first()
    
    def create_privacy_settings(self, tenant_id: str, user_id: str, db: Session, **kwargs) -> PrivacySettings:
        """Create privacy settings for a tenant."""
        settings = PrivacySettings(
            tenant_id=tenant_id,
            created_by=user_id,
            **kwargs
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    
    def update_privacy_settings(self, tenant_id: str, user_id: str, db: Session, **kwargs) -> PrivacySettings:
        """Update privacy settings for a tenant."""
        settings = self.get_privacy_settings(tenant_id, db)
        if not settings:
            return self.create_privacy_settings(tenant_id, user_id, db, **kwargs)
        
        # Track changes for audit
        changes = {}
        for key, value in kwargs.items():
            if hasattr(settings, key) and getattr(settings, key) != value:
                changes[key] = {
                    'old': getattr(settings, key),
                    'new': value
                }
                setattr(settings, key, value)
        
        settings.updated_by = user_id
        db.commit()
        db.refresh(settings)
        
        # Log changes
        if changes:
            self._log_privacy_change(tenant_id, user_id, db, "settings_updated", changes)
        
        return settings
    
    def get_privacy_mode(self, tenant_id: str, db: Session) -> PrivacyMode:
        """Get privacy mode for a tenant."""
        settings = self.get_privacy_settings(tenant_id, db)
        if not settings:
            return PrivacyMode.PRIVATE_CLOUD  # Default
        
        return PrivacyMode(settings.privacy_mode)
    
    def set_privacy_mode(self, tenant_id: str, user_id: str, mode: PrivacyMode, db: Session) -> PrivacySettings:
        """Set privacy mode for a tenant."""
        settings = self.get_privacy_settings(tenant_id, db)
        if not settings:
            return self.create_privacy_settings(tenant_id, user_id, db, privacy_mode=mode.value)
        
        old_mode = PrivacyMode(settings.privacy_mode)
        settings.privacy_mode = mode.value
        settings.updated_by = user_id
        db.commit()
        db.refresh(settings)
        
        # Log mode change
        self._log_privacy_change(tenant_id, user_id, db, "mode_changed", {
            'privacy_mode': {
                'old': old_mode.value,
                'new': mode.value
            }
        })
        
        return settings
    
    def store_byo_key(self, tenant_id: str, key_name: str, key_value: str, db: Session) -> bool:
        """Store a BYO key for a tenant."""
        try:
            # Encrypt the key
            encrypted_key = self.key_manager.encrypt_data(key_value.encode('utf-8'))
            
            # Update settings
            settings = self.get_privacy_settings(tenant_id, db)
            if not settings:
                return False
            
            setattr(settings, f"byo_{key_name}_key", encrypted_key.hex())
            db.commit()
            
            logger.info(f"Stored BYO key {key_name} for tenant {tenant_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store BYO key {key_name} for tenant {tenant_id}: {e}")
            return False
    
    def get_byo_key(self, tenant_id: str, key_name: str, db: Session) -> Optional[str]:
        """Get a BYO key for a tenant."""
        try:
            settings = self.get_privacy_settings(tenant_id, db)
            if not settings:
                return None
            
            encrypted_hex = getattr(settings, f"byo_{key_name}_key", None)
            if not encrypted_hex:
                return None
            
            encrypted_data = bytes.fromhex(encrypted_hex)
            decrypted_data = self.key_manager.decrypt_data(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to get BYO key {key_name} for tenant {tenant_id}: {e}")
            return None
    
    def redact_data(self, data: str, tenant_id: str, db: Session) -> str:
        """Redact sensitive data based on tenant privacy settings."""
        mode = self.get_privacy_mode(tenant_id, db)
        config = privacy_resolver.get_config(mode)
        
        if not config.log_redaction_enabled:
            return data
        
        redacted_data, redaction_log = redaction_engine.redact_text(data)
        
        if redaction_log:
            logger.info(f"Applied {len(redaction_log)} redactions for tenant {tenant_id}")
        
        return redacted_data
    
    def should_retain_data(self, tenant_id: str, data_type: str, db: Session) -> bool:
        """Check if data should be retained based on tenant settings."""
        settings = self.get_privacy_settings(tenant_id, db)
        if not settings:
            return True  # Default to retaining
        
        if data_type == "prompt" and settings.do_not_retain_prompts:
            return False
        elif data_type == "response" and settings.do_not_retain_model_outputs:
            return False
        
        return True
    
    def get_data_hash(self, data: str) -> str:
        """Get hash of data for retention tracking."""
        return redaction_engine.get_redaction_hash(data)
    
    def schedule_retention_cleanup(self, tenant_id: str, job_type: str, target_table: str, 
                                 retention_policy_name: str, db: Session) -> DataRetentionJob:
        """Schedule a data retention cleanup job."""
        retention_seconds = retention_policy.get_retention_seconds(retention_policy_name)
        scheduled_at = datetime.utcnow() + timedelta(seconds=retention_seconds)
        
        job = DataRetentionJob(
            tenant_id=tenant_id,
            job_type=job_type,
            retention_policy=retention_policy_name,
            target_table=target_table,
            scheduled_at=scheduled_at
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Scheduled retention cleanup job {job.id} for tenant {tenant_id}")
        return job
    
    def log_transparency_event(self, tenant_id: str, event_type: str, data_category: str, 
                              data_volume: int, db: Session, **kwargs) -> PrivacyTransparencyLog:
        """Log a transparency event."""
        mode = self.get_privacy_mode(tenant_id, db)
        settings = self.get_privacy_settings(tenant_id, db)
        
        log_entry = PrivacyTransparencyLog(
            tenant_id=tenant_id,
            event_type=event_type,
            data_category=data_category,
            data_volume=data_volume,
            privacy_mode=mode.value,
            retention_applied=self.should_retain_data(tenant_id, data_category, db),
            redaction_applied=privacy_resolver.get_config(mode).log_redaction_enabled,
            details=str(kwargs) if kwargs else None
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        return log_entry
    
    def _log_privacy_change(self, tenant_id: str, user_id: str, db: Session, action: str, details: Dict[str, Any]):
        """Log a privacy-related change."""
        mode = self.get_privacy_mode(tenant_id, db)
        
        log_entry = PrivacyAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type="privacy_settings",
            privacy_mode=mode.value,
            redactions_applied=0,  # Will be calculated if needed
            details=str(details)
        )
        
        db.add(log_entry)
        db.commit()
    
    def export_privacy_data(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Export privacy-related data for a tenant."""
        settings = self.get_privacy_settings(tenant_id, db)
        if not settings:
            return {}
        
        # Get audit logs
        audit_logs = db.query(PrivacyAuditLog).filter(
            PrivacyAuditLog.tenant_id == tenant_id
        ).all()
        
        # Get transparency logs
        transparency_logs = db.query(PrivacyTransparencyLog).filter(
            PrivacyTransparencyLog.tenant_id == tenant_id
        ).all()
        
        return {
            "settings": {
                "privacy_mode": settings.privacy_mode,
                "prompt_retention_seconds": settings.prompt_retention_seconds,
                "response_retention_seconds": settings.response_retention_seconds,
                "do_not_retain_prompts": settings.do_not_retain_prompts,
                "do_not_retain_model_outputs": settings.do_not_retain_model_outputs,
                "strip_attachments_from_logs": settings.strip_attachments_from_logs,
                "disable_third_party_calls": settings.disable_third_party_calls,
                "created_at": settings.created_at.isoformat() if settings.created_at else None,
                "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
            },
            "audit_logs": [
                {
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "privacy_mode": log.privacy_mode,
                    "redactions_applied": log.redactions_applied,
                    "details": log.details,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in audit_logs
            ],
            "transparency_logs": [
                {
                    "event_type": log.event_type,
                    "data_category": log.data_category,
                    "data_volume": log.data_volume,
                    "privacy_mode": log.privacy_mode,
                    "retention_applied": log.retention_applied,
                    "redaction_applied": log.redaction_applied,
                    "details": log.details,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in transparency_logs
            ]
        }
    
    def erase_privacy_data(self, tenant_id: str, db: Session) -> bool:
        """Erase all privacy-related data for a tenant."""
        try:
            # Delete settings
            db.query(PrivacySettings).filter(PrivacySettings.tenant_id == tenant_id).delete()
            
            # Delete audit logs
            db.query(PrivacyAuditLog).filter(PrivacyAuditLog.tenant_id == tenant_id).delete()
            
            # Delete transparency logs
            db.query(PrivacyTransparencyLog).filter(PrivacyTransparencyLog.tenant_id == tenant_id).delete()
            
            # Delete retention jobs
            db.query(DataRetentionJob).filter(DataRetentionJob.tenant_id == tenant_id).delete()
            
            db.commit()
            
            logger.info(f"Erased all privacy data for tenant {tenant_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to erase privacy data for tenant {tenant_id}: {e}")
            db.rollback()
            return False


# Global service instance
privacy_service = PrivacyService()
