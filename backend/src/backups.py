#!/usr/bin/env python3
"""
Backup Framework for System Builder Hub
Main orchestration module for backup operations.
"""

import os
import json
import time
import logging
import threading
import tempfile
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

from flask import current_app, g
from config import config

# Import backup components
from backup_scheduler import backup_scheduler, BackupType, BackupTrigger
from snapshot_store import snapshot_store, SnapshotMetadata
from backup_manifest import backup_manifest_manager, BackupManifest, BackupStatus, BackupEventType, RetentionPolicy

logger = logging.getLogger(__name__)

@dataclass
class BackupConfig:
    """Backup configuration"""
    max_bytes_per_day: int
    max_concurrent_restores: int
    enable_cold_tier: bool
    default_retention_days: int
    default_max_backups: int

class BackupFramework:
    """Main backup framework orchestrator"""
    
    def __init__(self):
        self.config = self._load_config()
        self.active_restores = 0
        self.daily_bytes_used = 0
        self.last_daily_reset = datetime.now()
        self.lock = threading.Lock()
        
        # Initialize default retention policy if none exists
        self._ensure_default_retention_policy()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _load_config(self) -> BackupConfig:
        """Load backup configuration from environment"""
        return BackupConfig(
            max_bytes_per_day=int(os.getenv('BACKUP_MAX_BYTES_PER_DAY', '5368709120')),  # 5GB
            max_concurrent_restores=int(os.getenv('BACKUP_MAX_CONCURRENT_RESTORES', '2')),
            enable_cold_tier=os.getenv('BACKUP_ENABLE_COLD_TIER', 'false').lower() == 'true',
            default_retention_days=int(os.getenv('BACKUP_DEFAULT_RETENTION_DAYS', '30')),
            default_max_backups=int(os.getenv('BACKUP_DEFAULT_MAX_BACKUPS', '100'))
        )
    
    def _ensure_default_retention_policy(self):
        """Ensure default retention policy exists"""
        policies = backup_manifest_manager.list_retention_policies()
        if not policies:
            backup_manifest_manager.create_retention_policy(
                name="Default Policy",
                description="Default retention policy for backups",
                retention_days=self.config.default_retention_days,
                max_backups=self.config.default_max_backups
            )
            logger.info("Created default retention policy")
    
    def _start_background_tasks(self):
        """Start background tasks for backup management"""
        def daily_reset_task():
            while True:
                time.sleep(3600)  # Check every hour
                now = datetime.now()
                if (now - self.last_daily_reset).days >= 1:
                    with self.lock:
                        self.daily_bytes_used = 0
                        self.last_daily_reset = now
                    logger.info("Reset daily backup bytes counter")
        
        thread = threading.Thread(target=daily_reset_task, daemon=True)
        thread.start()
        logger.info("Started backup background tasks")
    
    def trigger_backup(self, backup_type: str, name: str, description: str = "", 
                      tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Trigger a backup operation"""
        try:
            # Check daily quota
            if not self._check_daily_quota():
                logger.warning("Daily backup quota exceeded")
                return None
            
            # Get default retention policy
            policies = backup_manifest_manager.list_retention_policies()
            if not policies:
                logger.error("No retention policies available")
                return None
            
            retention_policy = policies[0]  # Use first available policy
            
            # Create backup manifest
            manifest = backup_manifest_manager.create_manifest(
                name=name,
                description=description,
                backup_type=backup_type,
                retention_policy_id=retention_policy.id,
                created_by=getattr(g, 'user_id', 'system'),
                metadata=metadata or {},
                tags=tags or {}
            )
            
            # Create backup data
            backup_data = self._create_backup_data(backup_type, metadata or {})
            if not backup_data:
                backup_manifest_manager.update_manifest_status(
                    manifest.id, BackupStatus.FAILED
                )
                return None
            
            # Update manifest with backup info
            backup_manifest_manager.update_manifest_status(
                manifest.id, BackupStatus.IN_PROGRESS
            )
            
            # Store snapshot
            snapshot_metadata = snapshot_store.create_snapshot(
                name=name,
                data=backup_data,
                tags=tags or {}
            )
            
            if snapshot_metadata:
                # Update manifest with snapshot info
                backup_manifest_manager.update_manifest_status(
                    manifest.id, BackupStatus.COMPLETED,
                    size_bytes=snapshot_metadata.size_bytes,
                    checksum=snapshot_metadata.checksum,
                    compression_type=snapshot_metadata.compression_type,
                    encryption_enabled=snapshot_metadata.encryption_enabled
                )
                
                # Update daily quota
                with self.lock:
                    self.daily_bytes_used += snapshot_metadata.size_bytes
                
                # Create restore event
                backup_manifest_manager.create_event(
                    manifest.id, BackupEventType.COMPLETED,
                    f"Backup completed successfully. Size: {snapshot_metadata.size_bytes} bytes"
                )
                
                logger.info(f"Backup completed: {manifest.id}")
                return manifest.id
            else:
                backup_manifest_manager.update_manifest_status(
                    manifest.id, BackupStatus.FAILED
                )
                return None
                
        except Exception as e:
            logger.error(f"Failed to trigger backup: {e}")
            return None
    
    def _create_backup_data(self, backup_type: str, metadata: Dict[str, Any]) -> Optional[bytes]:
        """Create backup data based on type"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    
                    if backup_type == 'full':
                        # Full system backup
                        self._add_database_backup(zip_file)
                        self._add_config_backup(zip_file)
                        self._add_user_data_backup(zip_file)
                        
                    elif backup_type == 'incremental':
                        # Incremental backup (since last backup)
                        self._add_incremental_backup(zip_file, metadata)
                        
                    elif backup_type == 'database':
                        # Database only backup
                        self._add_database_backup(zip_file)
                        
                    elif backup_type == 'config':
                        # Configuration only backup
                        self._add_config_backup(zip_file)
                        
                    else:
                        logger.error(f"Unknown backup type: {backup_type}")
                        return None
                    
                    # Add backup metadata
                    backup_info = {
                        'backup_type': backup_type,
                        'created_at': datetime.now().isoformat(),
                        'metadata': metadata,
                        'version': '1.0'
                    }
                    zip_file.writestr('backup_info.json', json.dumps(backup_info, indent=2))
                
                # Read the zip file
                with open(temp_file.name, 'rb') as f:
                    data = f.read()
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                return data
                
        except Exception as e:
            logger.error(f"Failed to create backup data: {e}")
            return None
    
    def _add_database_backup(self, zip_file: zipfile.ZipFile):
        """Add database backup to zip file"""
        try:
            db_path = config.DATABASE_URL.replace('sqlite:///', '')
            if os.path.exists(db_path):
                zip_file.write(db_path, 'database/system_builder_hub.db')
                logger.info("Added database backup")
        except Exception as e:
            logger.error(f"Failed to add database backup: {e}")
    
    def _add_config_backup(self, zip_file: zipfile.ZipFile):
        """Add configuration backup to zip file"""
        try:
            # Add environment variables (sanitized)
            env_vars = {}
            for key, value in os.environ.items():
                if key.startswith('BACKUP_') or key.startswith('SBH_'):
                    # Sanitize sensitive values
                    if 'KEY' in key or 'SECRET' in key or 'PASSWORD' in key:
                        env_vars[key] = '***REDACTED***'
                    else:
                        env_vars[key] = value
            
            zip_file.writestr('config/environment.json', json.dumps(env_vars, indent=2))
            logger.info("Added configuration backup")
            
        except Exception as e:
            logger.error(f"Failed to add configuration backup: {e}")
    
    def _add_user_data_backup(self, zip_file: zipfile.ZipFile):
        """Add user data backup to zip file"""
        try:
            # Add user uploads and sessions
            upload_dir = config.UPLOAD_FOLDER
            if os.path.exists(upload_dir):
                for root, dirs, files in os.walk(upload_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, upload_dir)
                        zip_file.write(file_path, f'user_data/{arc_name}')
            
            logger.info("Added user data backup")
            
        except Exception as e:
            logger.error(f"Failed to add user data backup: {e}")
    
    def _add_incremental_backup(self, zip_file: zipfile.ZipFile, metadata: Dict[str, Any]):
        """Add incremental backup to zip file"""
        try:
            # For now, just add recent changes
            # In a real implementation, you'd track file modifications
            last_backup_time = metadata.get('last_backup_time')
            
            # Add recent database changes
            self._add_database_backup(zip_file)
            
            # Add recent user data changes
            self._add_user_data_backup(zip_file)
            
            logger.info("Added incremental backup")
            
        except Exception as e:
            logger.error(f"Failed to add incremental backup: {e}")
    
    def _check_daily_quota(self) -> bool:
        """Check if daily backup quota is available"""
        with self.lock:
            return self.daily_bytes_used < self.config.max_bytes_per_day
    
    def restore_backup(self, backup_id: str, restore_type: str = 'full', 
                      target_path: str = None) -> bool:
        """Restore from backup"""
        try:
            # Check concurrent restore limit
            if not self._check_concurrent_restores():
                logger.warning("Maximum concurrent restores reached")
                return False
            
            # Get backup manifest
            manifest = backup_manifest_manager.get_manifest(backup_id)
            if not manifest:
                logger.error(f"Backup manifest not found: {backup_id}")
                return False
            
            # Verify backup integrity
            if not snapshot_store.verify_snapshot(backup_id):
                logger.error(f"Backup verification failed: {backup_id}")
                return False
            
            # Start restore
            with self.lock:
                self.active_restores += 1
            
            try:
                # Retrieve backup data
                backup_data = snapshot_store.retrieve_snapshot(backup_id)
                if not backup_data:
                    logger.error(f"Failed to retrieve backup data: {backup_id}")
                    return False
                
                # Extract and restore
                success = self._extract_and_restore(backup_data, restore_type, target_path)
                
                if success:
                    # Create restore event
                    backup_manifest_manager.create_event(
                        backup_id, BackupEventType.RESTORED,
                        f"Backup restored successfully. Type: {restore_type}"
                    )
                    logger.info(f"Backup restored successfully: {backup_id}")
                
                return success
                
            finally:
                with self.lock:
                    self.active_restores -= 1
                
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def _check_concurrent_restores(self) -> bool:
        """Check if concurrent restore limit is available"""
        with self.lock:
            return self.active_restores < self.config.max_concurrent_restores
    
    def _extract_and_restore(self, backup_data: bytes, restore_type: str, target_path: str) -> bool:
        """Extract backup data and restore"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_file.write(backup_data)
                temp_file.flush()
                
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    # Read backup info
                    backup_info = json.loads(zip_file.read('backup_info.json'))
                    
                    if restore_type == 'full' or restore_type == 'database':
                        self._restore_database(zip_file, target_path)
                    
                    if restore_type == 'full' or restore_type == 'config':
                        self._restore_config(zip_file, target_path)
                    
                    if restore_type == 'full' or restore_type == 'user_data':
                        self._restore_user_data(zip_file, target_path)
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to extract and restore backup: {e}")
            return False
    
    def _restore_database(self, zip_file: zipfile.ZipFile, target_path: str):
        """Restore database from backup"""
        try:
            if 'database/system_builder_hub.db' in zip_file.namelist():
                db_data = zip_file.read('database/system_builder_hub.db')
                db_path = target_path or config.DATABASE_URL.replace('sqlite:///', '')
                
                # Create backup of current database
                if os.path.exists(db_path):
                    backup_path = f"{db_path}.backup.{int(time.time())}"
                    shutil.copy2(db_path, backup_path)
                    logger.info(f"Created database backup: {backup_path}")
                
                # Write new database
                with open(db_path, 'wb') as f:
                    f.write(db_data)
                
                logger.info("Database restored successfully")
                
        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
    
    def _restore_config(self, zip_file: zipfile.ZipFile, target_path: str):
        """Restore configuration from backup"""
        try:
            if 'config/environment.json' in zip_file.namelist():
                config_data = zip_file.read('config/environment.json')
                config_info = json.loads(config_data)
                
                # Note: In production, you'd want to be more careful about restoring config
                logger.info("Configuration backup available (manual restore required)")
                
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
    
    def _restore_user_data(self, zip_file: zipfile.ZipFile, target_path: str):
        """Restore user data from backup"""
        try:
            user_data_dir = target_path or config.UPLOAD_FOLDER
            
            # Extract user data files
            for file_info in zip_file.filelist:
                if file_info.filename.startswith('user_data/'):
                    # Extract to target directory
                    zip_file.extract(file_info, user_data_dir)
            
            logger.info("User data restored successfully")
            
        except Exception as e:
            logger.error(f"Failed to restore user data: {e}")
    
    def list_backups(self, status: BackupStatus = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List available backups"""
        try:
            manifests = backup_manifest_manager.list_manifests(status, limit)
            
            backup_list = []
            for manifest in manifests:
                backup_info = asdict(manifest)
                backup_info['status'] = manifest.status.value
                backup_info['created_at'] = manifest.created_at.isoformat()
                if manifest.started_at:
                    backup_info['started_at'] = manifest.started_at.isoformat()
                if manifest.completed_at:
                    backup_info['completed_at'] = manifest.completed_at.isoformat()
                if manifest.expires_at:
                    backup_info['expires_at'] = manifest.expires_at.isoformat()
                
                backup_list.append(backup_info)
            
            return backup_list
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed backup information"""
        try:
            manifest = backup_manifest_manager.get_manifest(backup_id)
            if not manifest:
                return None
            
            # Get events
            events = backup_manifest_manager.get_backup_events(backup_id)
            
            # Get retention policy
            retention_policy = backup_manifest_manager.get_retention_policy(manifest.retention_policy_id)
            
            backup_info = asdict(manifest)
            backup_info['status'] = manifest.status.value
            backup_info['created_at'] = manifest.created_at.isoformat()
            if manifest.started_at:
                backup_info['started_at'] = manifest.started_at.isoformat()
            if manifest.completed_at:
                backup_info['completed_at'] = manifest.completed_at.isoformat()
            if manifest.expires_at:
                backup_info['expires_at'] = manifest.expires_at.isoformat()
            
            backup_info['events'] = [asdict(event) for event in events]
            backup_info['retention_policy'] = asdict(retention_policy) if retention_policy else None
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to get backup info: {e}")
            return None
    
    def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity"""
        try:
            # Update manifest status
            backup_manifest_manager.update_manifest_status(
                backup_id, BackupStatus.IN_PROGRESS
            )
            
            # Verify snapshot
            success = snapshot_store.verify_snapshot(backup_id)
            
            # Update manifest status
            status = BackupStatus.VERIFIED if success else BackupStatus.FAILED
            backup_manifest_manager.update_manifest_status(backup_id, status)
            
            # Create verification event
            event_type = BackupEventType.VERIFIED if success else BackupEventType.FAILED
            message = "Backup verification successful" if success else "Backup verification failed"
            backup_manifest_manager.create_event(backup_id, event_type, message)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to verify backup: {e}")
            return False
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete backup"""
        try:
            # Delete from snapshot store
            if snapshot_store.delete_snapshot(backup_id):
                # Delete manifest and events
                if backup_manifest_manager.delete_manifest(backup_id):
                    logger.info(f"Backup deleted successfully: {backup_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics"""
        try:
            manifests = backup_manifest_manager.list_manifests()
            
            total_backups = len(manifests)
            total_size = sum(m.size_bytes for m in manifests)
            completed_backups = len([m for m in manifests if m.status == BackupStatus.COMPLETED])
            failed_backups = len([m for m in manifests if m.status == BackupStatus.FAILED])
            
            return {
                'total_backups': total_backups,
                'completed_backups': completed_backups,
                'failed_backups': failed_backups,
                'total_size_bytes': total_size,
                'daily_bytes_used': self.daily_bytes_used,
                'daily_bytes_limit': self.config.max_bytes_per_day,
                'active_restores': self.active_restores,
                'max_concurrent_restores': self.config.max_concurrent_restores
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup stats: {e}")
            return {}

# Global instance
backup_framework = BackupFramework()
