#!/usr/bin/env python3
"""
Backup Manifest for System Builder Hub
Handles backup manifests, retention policies, and backup events.
"""

import os
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from config import config

logger = logging.getLogger(__name__)

class BackupStatus(Enum):
    """Backup status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    EXPIRED = "expired"

class BackupEventType(Enum):
    """Backup event types"""
    TRIGGERED = "triggered"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    RESTORED = "restored"
    EXPIRED = "expired"
    DELETED = "deleted"

@dataclass
class BackupManifest:
    """Backup manifest"""
    id: str
    name: str
    description: str
    backup_type: str
    status: BackupStatus
    size_bytes: int
    checksum: str
    compression_type: str
    encryption_enabled: bool
    retention_policy_id: str
    created_by: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]
    tags: Dict[str, str]

@dataclass
class RetentionPolicy:
    """Retention policy"""
    id: str
    name: str
    description: str
    retention_days: int
    max_backups: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class BackupEvent:
    """Backup event"""
    id: str
    backup_id: str
    event_type: BackupEventType
    message: str
    metadata: Dict[str, Any]
    created_at: datetime

class BackupManifestManager:
    """Manages backup manifests, retention policies, and events"""
    
    def __init__(self):
        self._init_database()
    
    def _init_database(self):
        """Initialize backup manifest database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create backup_manifests table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS backup_manifests (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        backup_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        size_bytes INTEGER DEFAULT 0,
                        checksum TEXT,
                        compression_type TEXT,
                        encryption_enabled BOOLEAN DEFAULT FALSE,
                        retention_policy_id TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        metadata TEXT,
                        tags TEXT
                    )
                ''')
                
                # Create retention_policies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS retention_policies (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        retention_days INTEGER NOT NULL,
                        max_backups INTEGER NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create backup_events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS backup_events (
                        id TEXT PRIMARY KEY,
                        backup_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (backup_id) REFERENCES backup_manifests (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Backup manifest database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize backup manifest database: {e}")
    
    def create_manifest(self, name: str, description: str, backup_type: str, 
                       retention_policy_id: str, created_by: str, 
                       metadata: Dict[str, Any] = None, tags: Dict[str, str] = None) -> BackupManifest:
        """Create a new backup manifest"""
        manifest_id = f"manifest_{int(time.time())}"
        now = datetime.now()
        
        manifest = BackupManifest(
            id=manifest_id,
            name=name,
            description=description,
            backup_type=backup_type,
            status=BackupStatus.PENDING,
            size_bytes=0,
            checksum="",
            compression_type="",
            encryption_enabled=False,
            retention_policy_id=retention_policy_id,
            created_by=created_by,
            created_at=now,
            started_at=None,
            completed_at=None,
            expires_at=None,
            metadata=metadata or {},
            tags=tags or {}
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO backup_manifests 
                    (id, name, description, backup_type, status, size_bytes, checksum, 
                     compression_type, encryption_enabled, retention_policy_id, created_by, 
                     created_at, started_at, completed_at, expires_at, metadata, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    manifest.id,
                    manifest.name,
                    manifest.description,
                    manifest.backup_type,
                    manifest.status.value,
                    manifest.size_bytes,
                    manifest.checksum,
                    manifest.compression_type,
                    manifest.encryption_enabled,
                    manifest.retention_policy_id,
                    manifest.created_by,
                    manifest.created_at.isoformat(),
                    manifest.started_at.isoformat() if manifest.started_at else None,
                    manifest.completed_at.isoformat() if manifest.completed_at else None,
                    manifest.expires_at.isoformat() if manifest.expires_at else None,
                    json.dumps(manifest.metadata),
                    json.dumps(manifest.tags)
                ))
                conn.commit()
                
                # Create initial event
                self.create_event(manifest_id, BackupEventType.TRIGGERED, "Backup manifest created")
                
                logger.info(f"Created backup manifest: {manifest_id}")
                return manifest
                
        except Exception as e:
            logger.error(f"Failed to create backup manifest: {e}")
            raise
    
    def update_manifest_status(self, manifest_id: str, status: BackupStatus, 
                              size_bytes: int = None, checksum: str = None,
                              compression_type: str = None, encryption_enabled: bool = None):
        """Update backup manifest status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Build update query
                updates = ["status = ?"]
                params = [status.value]
                
                if size_bytes is not None:
                    updates.append("size_bytes = ?")
                    params.append(size_bytes)
                
                if checksum is not None:
                    updates.append("checksum = ?")
                    params.append(checksum)
                
                if compression_type is not None:
                    updates.append("compression_type = ?")
                    params.append(compression_type)
                
                if encryption_enabled is not None:
                    updates.append("encryption_enabled = ?")
                    params.append(encryption_enabled)
                
                # Set timestamps based on status
                if status == BackupStatus.IN_PROGRESS:
                    updates.append("started_at = ?")
                    params.append(datetime.now().isoformat())
                elif status in [BackupStatus.COMPLETED, BackupStatus.FAILED]:
                    updates.append("completed_at = ?")
                    params.append(datetime.now().isoformat())
                
                params.append(manifest_id)
                
                cursor.execute(f'''
                    UPDATE backup_manifests 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                # Create event
                event_type = {
                    BackupStatus.IN_PROGRESS: BackupEventType.STARTED,
                    BackupStatus.COMPLETED: BackupEventType.COMPLETED,
                    BackupStatus.FAILED: BackupEventType.FAILED,
                    BackupStatus.VERIFIED: BackupEventType.VERIFIED
                }.get(status, BackupEventType.TRIGGERED)
                
                self.create_event(manifest_id, event_type, f"Backup status changed to {status.value}")
                
                logger.info(f"Updated backup manifest {manifest_id} status to {status.value}")
                
        except Exception as e:
            logger.error(f"Failed to update backup manifest status: {e}")
            raise
    
    def get_manifest(self, manifest_id: str) -> Optional[BackupManifest]:
        """Get backup manifest by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM backup_manifests WHERE id = ?', (manifest_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return self._row_to_manifest(row)
                
        except Exception as e:
            logger.error(f"Failed to get backup manifest: {e}")
            return None
    
    def list_manifests(self, status: BackupStatus = None, limit: int = 100) -> List[BackupManifest]:
        """List backup manifests"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM backup_manifests'
                params = []
                
                if status:
                    query += ' WHERE status = ?'
                    params.append(status.value)
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_manifest(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list backup manifests: {e}")
            return []
    
    def _row_to_manifest(self, row) -> BackupManifest:
        """Convert database row to BackupManifest"""
        return BackupManifest(
            id=row[0],
            name=row[1],
            description=row[2],
            backup_type=row[3],
            status=BackupStatus(row[4]),
            size_bytes=row[5],
            checksum=row[6],
            compression_type=row[7],
            encryption_enabled=bool(row[8]),
            retention_policy_id=row[9],
            created_by=row[10],
            created_at=datetime.fromisoformat(row[11]),
            started_at=datetime.fromisoformat(row[12]) if row[12] else None,
            completed_at=datetime.fromisoformat(row[13]) if row[13] else None,
            expires_at=datetime.fromisoformat(row[14]) if row[14] else None,
            metadata=json.loads(row[15]) if row[15] else {},
            tags=json.loads(row[16]) if row[16] else {}
        )
    
    def create_retention_policy(self, name: str, description: str, retention_days: int, 
                               max_backups: int) -> RetentionPolicy:
        """Create a new retention policy"""
        policy_id = f"policy_{int(time.time())}"
        now = datetime.now()
        
        policy = RetentionPolicy(
            id=policy_id,
            name=name,
            description=description,
            retention_days=retention_days,
            max_backups=max_backups,
            enabled=True,
            created_at=now,
            updated_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO retention_policies 
                    (id, name, description, retention_days, max_backups, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    policy.id,
                    policy.name,
                    policy.description,
                    policy.retention_days,
                    policy.max_backups,
                    policy.enabled,
                    policy.created_at.isoformat(),
                    policy.updated_at.isoformat()
                ))
                conn.commit()
                
                logger.info(f"Created retention policy: {policy_id}")
                return policy
                
        except Exception as e:
            logger.error(f"Failed to create retention policy: {e}")
            raise
    
    def get_retention_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Get retention policy by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM retention_policies WHERE id = ?', (policy_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return RetentionPolicy(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    retention_days=row[3],
                    max_backups=row[4],
                    enabled=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7])
                )
                
        except Exception as e:
            logger.error(f"Failed to get retention policy: {e}")
            return None
    
    def list_retention_policies(self) -> List[RetentionPolicy]:
        """List all retention policies"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM retention_policies ORDER BY created_at DESC')
                rows = cursor.fetchall()
                
                return [RetentionPolicy(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    retention_days=row[3],
                    max_backups=row[4],
                    enabled=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7])
                ) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list retention policies: {e}")
            return []
    
    def create_event(self, backup_id: str, event_type: BackupEventType, message: str, 
                    metadata: Dict[str, Any] = None) -> BackupEvent:
        """Create a backup event"""
        event_id = f"event_{int(time.time())}"
        now = datetime.now()
        
        event = BackupEvent(
            id=event_id,
            backup_id=backup_id,
            event_type=event_type,
            message=message,
            metadata=metadata or {},
            created_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO backup_events 
                    (id, backup_id, event_type, message, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event.id,
                    event.backup_id,
                    event.event_type.value,
                    event.message,
                    json.dumps(event.metadata),
                    event.created_at.isoformat()
                ))
                conn.commit()
                
                logger.info(f"Created backup event: {event_id} for backup {backup_id}")
                return event
                
        except Exception as e:
            logger.error(f"Failed to create backup event: {e}")
            raise
    
    def get_backup_events(self, backup_id: str, limit: int = 50) -> List[BackupEvent]:
        """Get events for a backup"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM backup_events 
                    WHERE backup_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (backup_id, limit))
                rows = cursor.fetchall()
                
                return [BackupEvent(
                    id=row[0],
                    backup_id=row[1],
                    event_type=BackupEventType(row[2]),
                    message=row[3],
                    metadata=json.loads(row[4]) if row[4] else {},
                    created_at=datetime.fromisoformat(row[5])
                ) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get backup events: {e}")
            return []
    
    def delete_manifest(self, manifest_id: str) -> bool:
        """Delete backup manifest and all associated events"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Delete events first
                cursor.execute('DELETE FROM backup_events WHERE backup_id = ?', (manifest_id,))
                
                # Delete manifest
                cursor.execute('DELETE FROM backup_manifests WHERE id = ?', (manifest_id,))
                
                conn.commit()
                
                logger.info(f"Deleted backup manifest: {manifest_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete backup manifest: {e}")
            return False
    
    def get_expired_manifests(self) -> List[BackupManifest]:
        """Get manifests that have expired"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM backup_manifests 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                ''', (datetime.now().isoformat(),))
                rows = cursor.fetchall()
                
                return [self._row_to_manifest(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get expired manifests: {e}")
            return []

# Global instance
backup_manifest_manager = BackupManifestManager()
