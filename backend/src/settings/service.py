"""
Settings Hub Service
Business logic for user and tenant settings management.
"""

import logging
import secrets
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import (
    UserSettings, UserSession, TenantSettings, TenantApiToken, 
    OutboundWebhook, AuditSecurityEvent
)
from ..crypto.keys import get_key_manager
from ..privacy.service import privacy_service

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing user and tenant settings."""
    
    def __init__(self):
        self.key_manager = get_key_manager()
    
    # User Settings Methods
    
    def get_user_settings(self, user_id: str, db: Session) -> Optional[UserSettings]:
        """Get user settings."""
        return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    def create_user_settings(self, user_id: str, db: Session, **kwargs) -> UserSettings:
        """Create user settings."""
        settings = UserSettings(user_id=user_id, **kwargs)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    
    def update_user_settings(self, user_id: str, db: Session, **kwargs) -> UserSettings:
        """Update user settings."""
        settings = self.get_user_settings(user_id, db)
        if not settings:
            return self.create_user_settings(user_id, db, **kwargs)
        
        # Track changes for audit
        changes = {}
        for key, value in kwargs.items():
            if hasattr(settings, key) and getattr(settings, key) != value:
                changes[key] = {
                    'old': getattr(settings, key),
                    'new': value
                }
                setattr(settings, key, value)
        
        db.commit()
        db.refresh(settings)
        
        # Log changes
        if changes:
            self._log_security_event(
                tenant_id=None, user_id=user_id, db=db,
                event_type="settings_changed",
                resource_type="user_settings",
                resource_id=settings.id,
                before_values=changes,
                after_values={k: v['new'] for k, v in changes.items()}
            )
        
        return settings
    
    # User Sessions Methods
    
    def get_user_sessions(self, user_id: str, db: Session) -> List[UserSession]:
        """Get user sessions."""
        return db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).order_by(UserSession.created_at.desc()).all()
    
    def revoke_user_session(self, session_id: str, user_id: str, db: Session) -> bool:
        """Revoke a user session."""
        session = db.query(UserSession).filter(
            UserSession.id == session_id,
            UserSession.user_id == user_id
        ).first()
        
        if not session:
            return False
        
        session.revoked_at = datetime.utcnow()
        db.commit()
        
        # Log security event
        self._log_security_event(
            tenant_id=None, user_id=user_id, db=db,
            event_type="session_revoked",
            resource_type="user_session",
            resource_id=session_id
        )
        
        return True
    
    def revoke_all_user_sessions(self, user_id: str, db: Session) -> int:
        """Revoke all user sessions except current."""
        count = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None)
        ).update({
            UserSession.revoked_at: datetime.utcnow()
        })
        
        db.commit()
        
        # Log security event
        self._log_security_event(
            tenant_id=None, user_id=user_id, db=db,
            event_type="all_sessions_revoked",
            resource_type="user_session",
            metadata={"sessions_revoked": count}
        )
        
        return count
    
    # Tenant Settings Methods
    
    def get_tenant_settings(self, tenant_id: str, db: Session) -> Optional[TenantSettings]:
        """Get tenant settings."""
        return db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
    
    def create_tenant_settings(self, tenant_id: str, db: Session, **kwargs) -> TenantSettings:
        """Create tenant settings."""
        settings = TenantSettings(tenant_id=tenant_id, **kwargs)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    
    def update_tenant_settings(self, tenant_id: str, user_id: str, db: Session, **kwargs) -> TenantSettings:
        """Update tenant settings."""
        settings = self.get_tenant_settings(tenant_id, db)
        if not settings:
            return self.create_tenant_settings(tenant_id, db, **kwargs)
        
        # Track changes for audit
        changes = {}
        for key, value in kwargs.items():
            if hasattr(settings, key) and getattr(settings, key) != value:
                changes[key] = {
                    'old': getattr(settings, key),
                    'new': value
                }
                setattr(settings, key, value)
        
        db.commit()
        db.refresh(settings)
        
        # Log changes
        if changes:
            self._log_security_event(
                tenant_id=tenant_id, user_id=user_id, db=db,
                event_type="settings_changed",
                resource_type="tenant_settings",
                resource_id=settings.id,
                before_values=changes,
                after_values={k: v['new'] for k, v in changes.items()}
            )
        
        return settings
    
    # API Token Methods
    
    def create_api_token(self, tenant_id: str, user_id: str, name: str, 
                        permissions: List[str], db: Session) -> Dict[str, Any]:
        """Create a new API token."""
        # Generate token
        token = f"sbh_{secrets.token_urlsafe(32)}"
        token_prefix = token[:8]
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Store token
        api_token = TenantApiToken(
            tenant_id=tenant_id,
            name=name,
            token_prefix=token_prefix,
            token_hash=token_hash,
            created_by=user_id
        )
        api_token.set_permissions(permissions)
        
        db.add(api_token)
        db.commit()
        db.refresh(api_token)
        
        # Log security event
        self._log_security_event(
            tenant_id=tenant_id, user_id=user_id, db=db,
            event_type="api_token_created",
            resource_type="tenant_api_token",
            resource_id=api_token.id,
            metadata={"token_name": name, "permissions": permissions}
        )
        
        return {
            "token": token,  # Show once only
            "token_data": api_token.to_dict()
        }
    
    def get_api_tokens(self, tenant_id: str, db: Session) -> List[TenantApiToken]:
        """Get API tokens for tenant."""
        return db.query(TenantApiToken).filter(
            TenantApiToken.tenant_id == tenant_id
        ).order_by(TenantApiToken.created_at.desc()).all()
    
    def revoke_api_token(self, token_id: str, tenant_id: str, user_id: str, db: Session) -> bool:
        """Revoke an API token."""
        token = db.query(TenantApiToken).filter(
            TenantApiToken.id == token_id,
            TenantApiToken.tenant_id == tenant_id
        ).first()
        
        if not token:
            return False
        
        token.revoked_at = datetime.utcnow()
        db.commit()
        
        # Log security event
        self._log_security_event(
            tenant_id=tenant_id, user_id=user_id, db=db,
            event_type="api_token_revoked",
            resource_type="tenant_api_token",
            resource_id=token_id,
            metadata={"token_name": token.name}
        )
        
        return True
    
    # Webhook Methods
    
    def create_webhook(self, tenant_id: str, user_id: str, name: str, target_url: str,
                      events: List[str], db: Session) -> OutboundWebhook:
        """Create a new webhook."""
        # Generate signing key
        signing_key = secrets.token_urlsafe(32)
        encrypted_key = self.key_manager.encrypt_data(signing_key.encode('utf-8'))
        
        webhook = OutboundWebhook(
            tenant_id=tenant_id,
            name=name,
            target_url=target_url,
            created_by=user_id
        )
        webhook.set_events(events)
        webhook.signing_key = encrypted_key.hex()
        
        db.add(webhook)
        db.commit()
        db.refresh(webhook)
        
        # Log security event
        self._log_security_event(
            tenant_id=tenant_id, user_id=user_id, db=db,
            event_type="webhook_created",
            resource_type="outbound_webhook",
            resource_id=webhook.id,
            metadata={"webhook_name": name, "target_url": target_url, "events": events}
        )
        
        return webhook
    
    def get_webhooks(self, tenant_id: str, db: Session) -> List[OutboundWebhook]:
        """Get webhooks for tenant."""
        return db.query(OutboundWebhook).filter(
            OutboundWebhook.tenant_id == tenant_id
        ).order_by(OutboundWebhook.created_at.desc()).all()
    
    def update_webhook(self, webhook_id: str, tenant_id: str, user_id: str, db: Session, **kwargs) -> Optional[OutboundWebhook]:
        """Update a webhook."""
        webhook = db.query(OutboundWebhook).filter(
            OutboundWebhook.id == webhook_id,
            OutboundWebhook.tenant_id == tenant_id
        ).first()
        
        if not webhook:
            return None
        
        # Track changes
        changes = {}
        for key, value in kwargs.items():
            if hasattr(webhook, key) and getattr(webhook, key) != value:
                changes[key] = {
                    'old': getattr(webhook, key),
                    'new': value
                }
                setattr(webhook, key, value)
        
        db.commit()
        db.refresh(webhook)
        
        # Log changes
        if changes:
            self._log_security_event(
                tenant_id=tenant_id, user_id=user_id, db=db,
                event_type="webhook_updated",
                resource_type="outbound_webhook",
                resource_id=webhook_id,
                before_values=changes,
                after_values={k: v['new'] for k, v in changes.items()}
            )
        
        return webhook
    
    def delete_webhook(self, webhook_id: str, tenant_id: str, user_id: str, db: Session) -> bool:
        """Delete a webhook."""
        webhook = db.query(OutboundWebhook).filter(
            OutboundWebhook.id == webhook_id,
            OutboundWebhook.tenant_id == tenant_id
        ).first()
        
        if not webhook:
            return False
        
        db.delete(webhook)
        db.commit()
        
        # Log security event
        self._log_security_event(
            tenant_id=tenant_id, user_id=user_id, db=db,
            event_type="webhook_deleted",
            resource_type="outbound_webhook",
            resource_id=webhook_id,
            metadata={"webhook_name": webhook.name}
        )
        
        return True
    
    def test_webhook(self, webhook_id: str, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Test webhook delivery."""
        webhook = db.query(OutboundWebhook).filter(
            OutboundWebhook.id == webhook_id,
            OutboundWebhook.tenant_id == tenant_id
        ).first()
        
        if not webhook:
            return {"success": False, "error": "Webhook not found"}
        
        try:
            # Get signing key
            encrypted_key = bytes.fromhex(webhook.signing_key)
            signing_key = self.key_manager.decrypt_data(encrypted_key).decode('utf-8')
            
            # Create test payload
            test_payload = {
                "event": "webhook.test",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "message": "This is a test webhook delivery",
                    "webhook_id": webhook_id
                }
            }
            
            # TODO: Implement actual webhook delivery
            # For now, just simulate success
            webhook.last_delivery_at = datetime.utcnow()
            webhook.last_delivery_status = 200
            db.commit()
            
            return {
                "success": True,
                "status_code": 200,
                "message": "Test webhook delivered successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to test webhook {webhook_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # Security Methods
    
    def generate_recovery_codes(self, user_id: str, db: Session) -> List[str]:
        """Generate new recovery codes for 2FA."""
        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        codes_str = ",".join(codes)
        
        # Encrypt codes
        encrypted_codes = self.key_manager.encrypt_data(codes_str.encode('utf-8'))
        
        # Update user settings
        settings = self.get_user_settings(user_id, db)
        if not settings:
            settings = self.create_user_settings(user_id, db)
        
        settings.recovery_codes = encrypted_codes.hex()
        db.commit()
        
        # Log security event
        self._log_security_event(
            tenant_id=None, user_id=user_id, db=db,
            event_type="recovery_codes_generated",
            resource_type="user_settings",
            resource_id=settings.id
        )
        
        return codes
    
    def enable_2fa(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Enable 2FA for user."""
        settings = self.get_user_settings(user_id, db)
        if not settings:
            settings = self.create_user_settings(user_id, db)
        
        # Generate TOTP secret
        totp_secret = secrets.token_hex(16)
        
        # Generate recovery codes
        recovery_codes = self.generate_recovery_codes(user_id, db)
        
        settings.two_factor_enabled = True
        db.commit()
        
        # Log security event
        self._log_security_event(
            tenant_id=None, user_id=user_id, db=db,
            event_type="2fa_enabled",
            resource_type="user_settings",
            resource_id=settings.id
        )
        
        return {
            "totp_secret": totp_secret,  # Show once only
            "recovery_codes": recovery_codes,
            "qr_code_url": f"otpauth://totp/SBH:{user_id}?secret={totp_secret}&issuer=SBH"
        }
    
    def disable_2fa(self, user_id: str, db: Session) -> bool:
        """Disable 2FA for user."""
        settings = self.get_user_settings(user_id, db)
        if not settings:
            return False
        
        settings.two_factor_enabled = False
        settings.recovery_codes = None
        db.commit()
        
        # Log security event
        self._log_security_event(
            tenant_id=None, user_id=user_id, db=db,
            event_type="2fa_disabled",
            resource_type="user_settings",
            resource_id=settings.id
        )
        
        return True
    
    # Audit Methods
    
    def _log_security_event(self, tenant_id: Optional[str], user_id: str, db: Session,
                           event_type: str, resource_type: str, resource_id: Optional[str] = None,
                           before_values: Optional[Dict[str, Any]] = None,
                           after_values: Optional[Dict[str, Any]] = None,
                           metadata: Optional[Dict[str, Any]] = None):
        """Log a security event."""
        try:
            event = AuditSecurityEvent(
                tenant_id=tenant_id or "system",
                user_id=user_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            if before_values:
                event.set_before_values(before_values)
            if after_values:
                event.set_after_values(after_values)
            if metadata:
                event.set_metadata(metadata)
            
            db.add(event)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def get_security_events(self, tenant_id: str, db: Session, limit: int = 50) -> List[AuditSecurityEvent]:
        """Get security events for tenant."""
        return db.query(AuditSecurityEvent).filter(
            AuditSecurityEvent.tenant_id == tenant_id
        ).order_by(AuditSecurityEvent.created_at.desc()).limit(limit).all()


# Global service instance
settings_service = SettingsService()
