#!/usr/bin/env python3
"""
P57: Recycle Bin & Storage Policy (Soft-Delete + Retention)
Prevent accidental loss; unify storage policy for cloud/local; add soft-delete with retention and restore.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app
from flask_cors import cross_origin

# Import infrastructure components
from config import config
from metrics import metrics
from feature_flags import flag_required
from idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
recycle_bin_bp = Blueprint('recycle_bin', __name__, url_prefix='/api/file')

# Data Models
class RecycleAction(Enum):
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"
    PURGE = "purge"

@dataclass
class RecycleBinEvent:
    id: str
    file_id: str
    tenant_id: str
    action: RecycleAction
    actor: str
    timestamp: datetime
    meta_json: Dict[str, Any]

class RecycleBinService:
    """Service for recycle bin and storage policy management"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize recycle bin database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Add soft-delete columns to existing files table
                cursor.execute('''
                    ALTER TABLE files ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE
                ''')
                cursor.execute('''
                    ALTER TABLE files ADD COLUMN deleted_at TIMESTAMP
                ''')
                cursor.execute('''
                    ALTER TABLE files ADD COLUMN deleted_by TEXT
                ''')
                
                # Create recycle_bin_events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS recycle_bin_events (
                        id TEXT PRIMARY KEY,
                        file_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        meta_json TEXT,
                        FOREIGN KEY (file_id) REFERENCES files (id)
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_recycle_events_file_id 
                    ON recycle_bin_events (file_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_recycle_events_tenant_id 
                    ON recycle_bin_events (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_recycle_events_timestamp 
                    ON recycle_bin_events (timestamp)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_files_is_deleted 
                    ON files (is_deleted)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_files_deleted_at 
                    ON files (deleted_at)
                ''')
                
                conn.commit()
                logger.info("Recycle bin database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize recycle bin database: {e}")
    
    def soft_delete_file(self, file_id: str, tenant_id: str, actor: str) -> bool:
        """Soft delete a file"""
        try:
            # Check if file exists and belongs to tenant
            file_info = self._get_file_info(file_id, tenant_id)
            if not file_info:
                return False
            
            # Check if already soft-deleted
            if file_info.get('is_deleted', False):
                logger.info(f"File {file_id} already soft-deleted")
                return True
            
            # Perform soft delete
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE files 
                    SET is_deleted = TRUE, deleted_at = ?, deleted_by = ?
                    WHERE id = ? AND tenant_id = ?
                ''', (datetime.now().isoformat(), actor, file_id, tenant_id))
                
                if cursor.rowcount == 0:
                    return False
                
                # Record event
                event_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO recycle_bin_events 
                    (id, file_id, tenant_id, action, actor, timestamp, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    file_id,
                    tenant_id,
                    RecycleAction.SOFT_DELETE.value,
                    actor,
                    datetime.now().isoformat(),
                    json.dumps({'file_size': file_info.get('size', 0)})
                ))
                
                conn.commit()
            
            # Move file to trash prefix if configured
            if config.TRASH_PREFIX:
                self._move_to_trash_prefix(file_id, tenant_id)
            
            # Record metrics
            metrics.counter('sbh_files_soft_deleted_total').inc()
            metrics.gauge('sbh_trash_bytes_current').inc(file_info.get('size', 0))
            
            logger.info(f"Soft deleted file: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to soft delete file: {e}")
            return False
    
    def restore_file(self, file_id: str, tenant_id: str, actor: str) -> bool:
        """Restore a soft-deleted file"""
        try:
            # Check if file exists and is soft-deleted
            file_info = self._get_file_info(file_id, tenant_id)
            if not file_info or not file_info.get('is_deleted', False):
                return False
            
            # Check legal hold
            if file_info.get('legal_hold', False):
                logger.warning(f"Cannot restore file {file_id} - legal hold active")
                return False
            
            # Perform restore
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE files 
                    SET is_deleted = FALSE, deleted_at = NULL, deleted_by = NULL
                    WHERE id = ? AND tenant_id = ?
                ''', (file_id, tenant_id))
                
                if cursor.rowcount == 0:
                    return False
                
                # Record event
                event_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO recycle_bin_events 
                    (id, file_id, tenant_id, action, actor, timestamp, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    file_id,
                    tenant_id,
                    RecycleAction.RESTORE.value,
                    actor,
                    datetime.now().isoformat(),
                    json.dumps({'file_size': file_info.get('size', 0)})
                ))
                
                conn.commit()
            
            # Move file back from trash prefix if configured
            if config.TRASH_PREFIX:
                self._move_from_trash_prefix(file_id, tenant_id)
            
            # Record metrics
            metrics.counter('sbh_trash_restore_total').inc()
            metrics.gauge('sbh_trash_bytes_current').dec(file_info.get('size', 0))
            
            logger.info(f"Restored file: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore file: {e}")
            return False
    
    def purge_file(self, file_id: str, tenant_id: str, actor: str) -> bool:
        """Hard delete a soft-deleted file (admin only)"""
        try:
            # Check if file exists and is soft-deleted
            file_info = self._get_file_info(file_id, tenant_id)
            if not file_info or not file_info.get('is_deleted', False):
                return False
            
            # Check legal hold
            if file_info.get('legal_hold', False):
                logger.warning(f"Cannot purge file {file_id} - legal hold active")
                return False
            
            # Check retention window
            deleted_at = datetime.fromisoformat(file_info.get('deleted_at', ''))
            retention_days = config.TRASH_RETENTION_DAYS
            if datetime.now() - deleted_at < timedelta(days=retention_days):
                logger.warning(f"Cannot purge file {file_id} - retention window not elapsed")
                return False
            
            # Backup before purge (via P31)
            self._backup_before_purge(file_id, tenant_id)
            
            # Perform hard delete
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM files 
                    WHERE id = ? AND tenant_id = ?
                ''', (file_id, tenant_id))
                
                if cursor.rowcount == 0:
                    return False
                
                # Record event
                event_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO recycle_bin_events 
                    (id, file_id, tenant_id, action, actor, timestamp, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    file_id,
                    tenant_id,
                    RecycleAction.PURGE.value,
                    actor,
                    datetime.now().isoformat(),
                    json.dumps({'file_size': file_info.get('size', 0)})
                ))
                
                conn.commit()
            
            # Delete from storage
            self._delete_from_storage(file_id, tenant_id)
            
            # Record metrics
            metrics.counter('sbh_trash_purge_total').inc()
            metrics.gauge('sbh_trash_bytes_current').dec(file_info.get('size', 0))
            
            logger.info(f"Purged file: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to purge file: {e}")
            return False
    
    def list_trash(self, tenant_id: str, page: int = 1, page_size: int = 20, 
                   project_id: Optional[str] = None, system_id: Optional[str] = None) -> Dict[str, Any]:
        """List soft-deleted files with pagination"""
        try:
            offset = (page - 1) * page_size
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                query = '''
                    SELECT id, name, size, project_id, system_id, deleted_at, deleted_by, legal_hold
                    FROM files 
                    WHERE tenant_id = ? AND is_deleted = TRUE
                '''
                params = [tenant_id]
                
                if project_id:
                    query += ' AND project_id = ?'
                    params.append(project_id)
                
                if system_id:
                    query += ' AND system_id = ?'
                    params.append(system_id)
                
                # Get total count
                count_query = query.replace('SELECT id, name, size, project_id, system_id, deleted_at, deleted_by, legal_hold', 'SELECT COUNT(*)')
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                # Get paginated results
                query += ' ORDER BY deleted_at DESC LIMIT ? OFFSET ?'
                params.extend([page_size, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                files = []
                for row in rows:
                    files.append({
                        'id': row[0],
                        'name': row[1],
                        'size': row[2],
                        'project_id': row[3],
                        'system_id': row[4],
                        'deleted_at': row[5],
                        'deleted_by': row[6],
                        'legal_hold': row[7],
                        'days_until_purge': self._calculate_days_until_purge(row[5])
                    })
                
                return {
                    'files': files,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to list trash: {e}")
            return {'files': [], 'pagination': {'page': page, 'page_size': page_size, 'total_count': 0, 'total_pages': 0}}
    
    def _get_file_info(self, file_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get file information"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, size, project_id, system_id, is_deleted, deleted_at, deleted_by, legal_hold
                    FROM files 
                    WHERE id = ? AND tenant_id = ?
                ''', (file_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'size': row[2],
                        'project_id': row[3],
                        'system_id': row[4],
                        'is_deleted': row[5],
                        'deleted_at': row[6],
                        'deleted_by': row[7],
                        'legal_hold': row[8]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return None
    
    def _move_to_trash_prefix(self, file_id: str, tenant_id: str):
        """Move file to trash prefix in storage"""
        try:
            # In reality, this would move the file in the configured storage provider
            # For now, simulate the operation
            logger.info(f"Moving file {file_id} to trash prefix")
            
        except Exception as e:
            logger.error(f"Failed to move file to trash prefix: {e}")
    
    def _move_from_trash_prefix(self, file_id: str, tenant_id: str):
        """Move file back from trash prefix in storage"""
        try:
            # In reality, this would move the file back from trash prefix
            # For now, simulate the operation
            logger.info(f"Moving file {file_id} back from trash prefix")
            
        except Exception as e:
            logger.error(f"Failed to move file from trash prefix: {e}")
    
    def _backup_before_purge(self, file_id: str, tenant_id: str):
        """Backup file before purge (via P31)"""
        try:
            # In reality, this would trigger P31 backup service
            # For now, simulate the operation
            logger.info(f"Backing up file {file_id} before purge")
            
        except Exception as e:
            logger.error(f"Failed to backup file before purge: {e}")
    
    def _delete_from_storage(self, file_id: str, tenant_id: str):
        """Delete file from storage provider"""
        try:
            # In reality, this would delete from the configured storage provider
            # For now, simulate the operation
            logger.info(f"Deleting file {file_id} from storage")
            
        except Exception as e:
            logger.error(f"Failed to delete file from storage: {e}")
    
    def _calculate_days_until_purge(self, deleted_at: str) -> int:
        """Calculate days until file can be purged"""
        try:
            if not deleted_at:
                return 0
            
            deleted_date = datetime.fromisoformat(deleted_at)
            retention_days = config.TRASH_RETENTION_DAYS
            purge_date = deleted_date + timedelta(days=retention_days)
            days_remaining = (purge_date - datetime.now()).days
            
            return max(0, days_remaining)
            
        except Exception as e:
            logger.error(f"Failed to calculate days until purge: {e}")
            return 0

# Initialize service
recycle_bin_service = RecycleBinService()

# API Routes
@recycle_bin_bp.route('/delete/<file_id>', methods=['POST'])
@cross_origin()
@flag_required('recycle_bin')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def soft_delete_file(file_id):
    """Soft delete a file"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        actor = getattr(g, 'user_id', 'unknown')
        
        success = recycle_bin_service.soft_delete_file(file_id, tenant_id, actor)
        
        if not success:
            return jsonify({'error': 'File not found or already deleted'}), 404
        
        return jsonify({
            'success': True,
            'message': 'File soft deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Soft delete file error: {e}")
        return jsonify({'error': str(e)}), 500

@recycle_bin_bp.route('/restore/<file_id>', methods=['POST'])
@cross_origin()
@flag_required('recycle_bin')
@require_tenant_context
@cost_accounted("api", "operation")
def restore_file(file_id):
    """Restore a soft-deleted file"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        actor = getattr(g, 'user_id', 'unknown')
        
        success = recycle_bin_service.restore_file(file_id, tenant_id, actor)
        
        if not success:
            return jsonify({'error': 'File not found or cannot be restored'}), 404
        
        return jsonify({
            'success': True,
            'message': 'File restored successfully'
        })
        
    except Exception as e:
        logger.error(f"Restore file error: {e}")
        return jsonify({'error': str(e)}), 500

@recycle_bin_bp.route('/purge/<file_id>', methods=['DELETE'])
@cross_origin()
@flag_required('recycle_bin')
@require_tenant_context
@cost_accounted("api", "operation")
def purge_file(file_id):
    """Hard delete a soft-deleted file (admin only)"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        actor = getattr(g, 'user_id', 'unknown')
        
        # Check if user has admin privileges
        user_role = getattr(g, 'user_role', 'user')
        if user_role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        
        success = recycle_bin_service.purge_file(file_id, tenant_id, actor)
        
        if not success:
            return jsonify({'error': 'File not found or cannot be purged'}), 404
        
        return jsonify({
            'success': True,
            'message': 'File purged successfully'
        })
        
    except Exception as e:
        logger.error(f"Purge file error: {e}")
        return jsonify({'error': str(e)}), 500

@recycle_bin_bp.route('/trash', methods=['GET'])
@cross_origin()
@flag_required('recycle_bin')
@require_tenant_context
def list_trash():
    """List soft-deleted files"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        project_id = request.args.get('project_id')
        system_id = request.args.get('system_id')
        
        result = recycle_bin_service.list_trash(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            project_id=project_id,
            system_id=system_id
        )
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"List trash error: {e}")
        return jsonify({'error': str(e)}), 500
