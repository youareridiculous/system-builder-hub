#!/usr/bin/env python3
"""
Backup Scheduler for System Builder Hub
Handles automated backup scheduling, triggers, and coordination.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3

from flask import current_app, g
from config import config

logger = logging.getLogger(__name__)

class BackupType(Enum):
    """Backup types"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"

class BackupTrigger(Enum):
    """Backup triggers"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    SYSTEM_EVENT = "system_event"
    QUOTA_EXCEEDED = "quota_exceeded"

@dataclass
class BackupSchedule:
    """Backup schedule configuration"""
    id: str
    name: str
    backup_type: BackupType
    frequency_hours: int
    retention_days: int
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass
class BackupTrigger:
    """Backup trigger event"""
    id: str
    schedule_id: Optional[str]
    trigger_type: BackupTrigger
    backup_type: BackupType
    metadata: Dict[str, Any]
    created_at: datetime
    processed: bool
    processed_at: Optional[datetime]

class BackupScheduler:
    """Manages backup scheduling and triggers"""
    
    def __init__(self):
        self.schedules: Dict[str, BackupSchedule] = {}
        self.triggers: List[BackupTrigger] = []
        self.running = False
        self.lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        self._load_schedules()
        
        # Start scheduler thread
        self._start_scheduler()
    
    def _init_database(self):
        """Initialize backup scheduler database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create backup_schedules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS backup_schedules (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        backup_type TEXT NOT NULL,
                        frequency_hours INTEGER NOT NULL,
                        retention_days INTEGER NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        last_run TIMESTAMP,
                        next_run TIMESTAMP,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create backup_triggers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS backup_triggers (
                        id TEXT PRIMARY KEY,
                        schedule_id TEXT,
                        trigger_type TEXT NOT NULL,
                        backup_type TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        processed BOOLEAN DEFAULT FALSE,
                        processed_at TIMESTAMP,
                        FOREIGN KEY (schedule_id) REFERENCES backup_schedules (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Backup scheduler database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize backup scheduler database: {e}")
    
    def _load_schedules(self):
        """Load backup schedules from database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM backup_schedules WHERE enabled = TRUE')
                
                for row in cursor.fetchall():
                    schedule = BackupSchedule(
                        id=row[0],
                        name=row[1],
                        backup_type=BackupType(row[2]),
                        frequency_hours=row[3],
                        retention_days=row[4],
                        enabled=bool(row[5]),
                        last_run=datetime.fromisoformat(row[6]) if row[6] else None,
                        next_run=datetime.fromisoformat(row[7]) if row[7] else None,
                        created_at=datetime.fromisoformat(row[8]),
                        updated_at=datetime.fromisoformat(row[9])
                    )
                    self.schedules[schedule.id] = schedule
                
                logger.info(f"Loaded {len(self.schedules)} backup schedules")
                
        except Exception as e:
            logger.error(f"Failed to load backup schedules: {e}")
    
    def _start_scheduler(self):
        """Start the backup scheduler thread"""
        def scheduler_worker():
            while self.running:
                try:
                    self._check_schedules()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Backup scheduler error: {e}")
                    time.sleep(300)  # Wait 5 minutes on error
        
        self.running = True
        thread = threading.Thread(target=scheduler_worker, daemon=True)
        thread.start()
        logger.info("Backup scheduler started")
    
    def _check_schedules(self):
        """Check for schedules that need to run"""
        now = datetime.now()
        
        with self.lock:
            for schedule_id, schedule in self.schedules.items():
                if not schedule.enabled:
                    continue
                
                if schedule.next_run and now >= schedule.next_run:
                    # Create trigger for this schedule
                    trigger = BackupTrigger(
                        id=f"trigger_{int(time.time())}_{schedule_id}",
                        schedule_id=schedule_id,
                        trigger_type=BackupTrigger.SCHEDULED,
                        backup_type=schedule.backup_type,
                        metadata={
                            'schedule_name': schedule.name,
                            'frequency_hours': schedule.frequency_hours
                        },
                        created_at=now,
                        processed=False,
                        processed_at=None
                    )
                    
                    self.triggers.append(trigger)
                    self._save_trigger(trigger)
                    
                    # Update schedule next run time
                    schedule.last_run = now
                    schedule.next_run = now + timedelta(hours=schedule.frequency_hours)
                    self._update_schedule(schedule)
                    
                    logger.info(f"Created backup trigger for schedule: {schedule.name}")
    
    def _save_trigger(self, trigger: BackupTrigger):
        """Save trigger to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO backup_triggers 
                    (id, schedule_id, trigger_type, backup_type, metadata, created_at, processed, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trigger.id,
                    trigger.schedule_id,
                    trigger.trigger_type.value,
                    trigger.backup_type.value,
                    json.dumps(trigger.metadata),
                    trigger.created_at.isoformat(),
                    trigger.processed,
                    trigger.processed_at.isoformat() if trigger.processed_at else None
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save backup trigger: {e}")
    
    def _update_schedule(self, schedule: BackupSchedule):
        """Update schedule in database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE backup_schedules 
                    SET last_run = ?, next_run = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    schedule.last_run.isoformat() if schedule.last_run else None,
                    schedule.next_run.isoformat() if schedule.next_run else None,
                    datetime.now().isoformat(),
                    schedule.id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update backup schedule: {e}")
    
    def create_schedule(self, name: str, backup_type: BackupType, frequency_hours: int, 
                       retention_days: int) -> BackupSchedule:
        """Create a new backup schedule"""
        schedule_id = f"schedule_{int(time.time())}"
        now = datetime.now()
        
        schedule = BackupSchedule(
            id=schedule_id,
            name=name,
            backup_type=backup_type,
            frequency_hours=frequency_hours,
            retention_days=retention_days,
            enabled=True,
            last_run=None,
            next_run=now + timedelta(hours=frequency_hours),
            created_at=now,
            updated_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO backup_schedules 
                    (id, name, backup_type, frequency_hours, retention_days, enabled, 
                     last_run, next_run, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    schedule.id,
                    schedule.name,
                    schedule.backup_type.value,
                    schedule.frequency_hours,
                    schedule.retention_days,
                    schedule.enabled,
                    schedule.last_run.isoformat() if schedule.last_run else None,
                    schedule.next_run.isoformat() if schedule.next_run else None,
                    schedule.created_at.isoformat(),
                    schedule.updated_at.isoformat()
                ))
                conn.commit()
                
                with self.lock:
                    self.schedules[schedule.id] = schedule
                
                logger.info(f"Created backup schedule: {schedule.name}")
                return schedule
                
        except Exception as e:
            logger.error(f"Failed to create backup schedule: {e}")
            raise
    
    def trigger_manual_backup(self, backup_type: BackupType, metadata: Dict[str, Any] = None) -> BackupTrigger:
        """Trigger a manual backup"""
        trigger_id = f"manual_{int(time.time())}"
        now = datetime.now()
        
        trigger = BackupTrigger(
            id=trigger_id,
            schedule_id=None,
            trigger_type=BackupTrigger.MANUAL,
            backup_type=backup_type,
            metadata=metadata or {},
            created_at=now,
            processed=False,
            processed_at=None
        )
        
        self.triggers.append(trigger)
        self._save_trigger(trigger)
        
        logger.info(f"Created manual backup trigger: {trigger_id}")
        return trigger
    
    def trigger_system_event_backup(self, event_type: str, backup_type: BackupType, 
                                   metadata: Dict[str, Any] = None) -> BackupTrigger:
        """Trigger a system event backup"""
        trigger_id = f"event_{int(time.time())}"
        now = datetime.now()
        
        trigger = BackupTrigger(
            id=trigger_id,
            schedule_id=None,
            trigger_type=BackupTrigger.SYSTEM_EVENT,
            backup_type=backup_type,
            metadata={
                'event_type': event_type,
                **(metadata or {})
            },
            created_at=now,
            processed=False,
            processed_at=None
        )
        
        self.triggers.append(trigger)
        self._save_trigger(trigger)
        
        logger.info(f"Created system event backup trigger: {trigger_id}")
        return trigger
    
    def get_pending_triggers(self) -> List[BackupTrigger]:
        """Get all pending backup triggers"""
        with self.lock:
            return [t for t in self.triggers if not t.processed]
    
    def mark_trigger_processed(self, trigger_id: str):
        """Mark a trigger as processed"""
        with self.lock:
            for trigger in self.triggers:
                if trigger.id == trigger_id:
                    trigger.processed = True
                    trigger.processed_at = datetime.now()
                    self._update_trigger_processed(trigger)
                    break
    
    def _update_trigger_processed(self, trigger: BackupTrigger):
        """Update trigger processed status in database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE backup_triggers 
                    SET processed = ?, processed_at = ?
                    WHERE id = ?
                ''', (
                    trigger.processed,
                    trigger.processed_at.isoformat() if trigger.processed_at else None,
                    trigger.id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update trigger processed status: {e}")
    
    def get_schedules(self) -> List[BackupSchedule]:
        """Get all backup schedules"""
        with self.lock:
            return list(self.schedules.values())
    
    def enable_schedule(self, schedule_id: str):
        """Enable a backup schedule"""
        with self.lock:
            if schedule_id in self.schedules:
                self.schedules[schedule_id].enabled = True
                self._update_schedule_enabled(schedule_id, True)
    
    def disable_schedule(self, schedule_id: str):
        """Disable a backup schedule"""
        with self.lock:
            if schedule_id in self.schedules:
                self.schedules[schedule_id].enabled = False
                self._update_schedule_enabled(schedule_id, False)
    
    def _update_schedule_enabled(self, schedule_id: str, enabled: bool):
        """Update schedule enabled status in database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE backup_schedules 
                    SET enabled = ?, updated_at = ?
                    WHERE id = ?
                ''', (enabled, datetime.now().isoformat(), schedule_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update schedule enabled status: {e}")
    
    def stop(self):
        """Stop the backup scheduler"""
        self.running = False
        logger.info("Backup scheduler stopped")

# Global instance
backup_scheduler = BackupScheduler()
