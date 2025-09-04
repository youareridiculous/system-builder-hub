#!/usr/bin/env python3
"""
P35: Collaboration & Design Versioning
Real-time multi-user collaboration in the builder with presence, comments, branching, and reviews.
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
from streaming import sse_stream, create_log_stream

logger = logging.getLogger(__name__)

# Create blueprint
collab_workspace_bp = Blueprint('collab_workspace', __name__, url_prefix='/api/collab')

# Data Models
class SessionStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ENDED = "ended"

class LockType(Enum):
    CANVAS = "canvas"
    WORKFLOW = "workflow"
    COMPONENT = "component"

class PresenceStatus(Enum):
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"

@dataclass
class CollaborationSession:
    id: str
    project_id: str
    session_name: str
    created_by: str
    status: SessionStatus
    max_participants: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

@dataclass
class SessionParticipant:
    id: str
    session_id: str
    user_id: str
    username: str
    status: PresenceStatus
    last_seen: datetime
    joined_at: datetime
    metadata: Dict[str, Any]

@dataclass
class SessionLock:
    id: str
    session_id: str
    user_id: str
    lock_type: LockType
    resource_id: str
    acquired_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any]

class CollaborationWorkspaceService:
    """Service for managing collaboration sessions, presence, and locking"""
    
    def __init__(self):
        self._init_database()
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.session_participants: Dict[str, List[SessionParticipant]] = {}
        self.session_locks: Dict[str, Dict[str, SessionLock]] = {}
        self.presence_heartbeats: Dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize collaboration workspace database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create collaboration_sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS collaboration_sessions (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        session_name TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        status TEXT NOT NULL,
                        max_participants INTEGER DEFAULT 20,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (project_id) REFERENCES builder_projects (id)
                    )
                ''')
                
                # Create session_participants table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS session_participants (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        status TEXT NOT NULL,
                        last_seen TIMESTAMP NOT NULL,
                        joined_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES collaboration_sessions (id)
                    )
                ''')
                
                # Create session_locks table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS session_locks (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        lock_type TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        acquired_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES collaboration_sessions (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Collaboration workspace database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize collaboration workspace database: {e}")
    
    def create_session(self, project_id: str, session_name: str, 
                      created_by: str, max_participants: int = 20) -> Optional[CollaborationSession]:
        """Create a new collaboration session"""
        try:
            session_id = f"session_{int(time.time())}"
            now = datetime.now()
            
            session = CollaborationSession(
                id=session_id,
                project_id=project_id,
                session_name=session_name,
                created_by=created_by,
                status=SessionStatus.ACTIVE,
                max_participants=max_participants,
                created_at=now,
                updated_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO collaboration_sessions 
                    (id, project_id, session_name, created_by, status, max_participants, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.id,
                    session.project_id,
                    session.session_name,
                    session.created_by,
                    session.status.value,
                    session.max_participants,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    json.dumps(session.metadata)
                ))
                conn.commit()
            
            # Add to active sessions
            with self._lock:
                self.active_sessions[session_id] = session
                self.session_participants[session_id] = []
                self.session_locks[session_id] = {}
            
            # Update metrics
            metrics.increment_counter('sbh_collab_sessions_active')
            
            logger.info(f"Created collaboration session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create collaboration session: {e}")
            return None
    
    def join_session(self, session_id: str, user_id: str, username: str) -> Optional[SessionParticipant]:
        """Join a collaboration session"""
        try:
            # Check if session exists and is active
            with self._lock:
                if session_id not in self.active_sessions:
                    return None
                
                session = self.active_sessions[session_id]
                participants = self.session_participants[session_id]
                
                # Check if user is already in session
                existing_participant = next((p for p in participants if p.user_id == user_id), None)
                if existing_participant:
                    # Update last seen
                    existing_participant.last_seen = datetime.now()
                    existing_participant.status = PresenceStatus.ONLINE
                    return existing_participant
                
                # Check if session is full
                if len(participants) >= session.max_participants:
                    return None
            
            # Create new participant
            participant_id = f"participant_{int(time.time())}"
            now = datetime.now()
            
            participant = SessionParticipant(
                id=participant_id,
                session_id=session_id,
                user_id=user_id,
                username=username,
                status=PresenceStatus.ONLINE,
                last_seen=now,
                joined_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO session_participants 
                    (id, session_id, user_id, username, status, last_seen, joined_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    participant.id,
                    participant.session_id,
                    participant.user_id,
                    participant.username,
                    participant.status.value,
                    participant.last_seen.isoformat(),
                    participant.joined_at.isoformat(),
                    json.dumps(participant.metadata)
                ))
                conn.commit()
            
            # Add to active participants
            with self._lock:
                self.session_participants[session_id].append(participant)
                self.presence_heartbeats[f"{session_id}_{user_id}"] = now
            
            logger.info(f"User {user_id} joined session {session_id}")
            return participant
            
        except Exception as e:
            logger.error(f"Failed to join session: {e}")
            return None
    
    def leave_session(self, session_id: str, user_id: str) -> bool:
        """Leave a collaboration session"""
        try:
            with self._lock:
                if session_id not in self.session_participants:
                    return False
                
                participants = self.session_participants[session_id]
                participant = next((p for p in participants if p.user_id == user_id), None)
                
                if participant:
                    # Update status to offline
                    participant.status = PresenceStatus.OFFLINE
                    participant.last_seen = datetime.now()
                    
                    # Remove from active participants
                    participants.remove(participant)
                    
                    # Remove heartbeat
                    heartbeat_key = f"{session_id}_{user_id}"
                    if heartbeat_key in self.presence_heartbeats:
                        del self.presence_heartbeats[heartbeat_key]
                    
                    # Update database
                    with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE session_participants 
                            SET status = ?, last_seen = ?
                            WHERE session_id = ? AND user_id = ?
                        ''', (
                            PresenceStatus.OFFLINE.value,
                            participant.last_seen.isoformat(),
                            session_id,
                            user_id
                        ))
                        conn.commit()
                    
                    logger.info(f"User {user_id} left session {session_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to leave session: {e}")
            return False
    
    def update_presence(self, session_id: str, user_id: str, status: PresenceStatus) -> bool:
        """Update user presence status"""
        try:
            with self._lock:
                if session_id not in self.session_participants:
                    return False
                
                participants = self.session_participants[session_id]
                participant = next((p for p in participants if p.user_id == user_id), None)
                
                if participant:
                    participant.status = status
                    participant.last_seen = datetime.now()
                    self.presence_heartbeats[f"{session_id}_{user_id}"] = participant.last_seen
                    
                    # Update database
                    with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE session_participants 
                            SET status = ?, last_seen = ?
                            WHERE session_id = ? AND user_id = ?
                        ''', (
                            status.value,
                            participant.last_seen.isoformat(),
                            session_id,
                            user_id
                        ))
                        conn.commit()
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update presence: {e}")
            return False
    
    def acquire_lock(self, session_id: str, user_id: str, lock_type: LockType, 
                    resource_id: str, duration_minutes: int = 30) -> Optional[SessionLock]:
        """Acquire a lock on a resource"""
        try:
            with self._lock:
                if session_id not in self.session_locks:
                    return None
                
                locks = self.session_locks[session_id]
                lock_key = f"{lock_type.value}_{resource_id}"
                
                # Check if resource is already locked
                if lock_key in locks:
                    existing_lock = locks[lock_key]
                    if existing_lock.expires_at > datetime.now():
                        return None  # Resource is locked
                    else:
                        # Lock expired, remove it
                        del locks[lock_key]
                
                # Create new lock
                lock_id = f"lock_{int(time.time())}"
                now = datetime.now()
                expires_at = now + timedelta(minutes=duration_minutes)
                
                lock = SessionLock(
                    id=lock_id,
                    session_id=session_id,
                    user_id=user_id,
                    lock_type=lock_type,
                    resource_id=resource_id,
                    acquired_at=now,
                    expires_at=expires_at,
                    metadata={}
                )
                
                locks[lock_key] = lock
                
                # Save to database
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO session_locks 
                        (id, session_id, user_id, lock_type, resource_id, acquired_at, expires_at, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        lock.id,
                        lock.session_id,
                        lock.user_id,
                        lock.lock_type.value,
                        lock.resource_id,
                        lock.acquired_at.isoformat(),
                        lock.expires_at.isoformat(),
                        json.dumps(lock.metadata)
                    ))
                    conn.commit()
                
                logger.info(f"Lock acquired: {lock_key} by user {user_id}")
                return lock
            
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return None
    
    def release_lock(self, session_id: str, user_id: str, lock_type: LockType, 
                    resource_id: str) -> bool:
        """Release a lock on a resource"""
        try:
            with self._lock:
                if session_id not in self.session_locks:
                    return False
                
                locks = self.session_locks[session_id]
                lock_key = f"{lock_type.value}_{resource_id}"
                
                if lock_key in locks:
                    lock = locks[lock_key]
                    if lock.user_id == user_id:
                        del locks[lock_key]
                        
                        # Remove from database
                        with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                DELETE FROM session_locks 
                                WHERE session_id = ? AND user_id = ? AND lock_type = ? AND resource_id = ?
                            ''', (session_id, user_id, lock_type.value, resource_id))
                            conn.commit()
                        
                        logger.info(f"Lock released: {lock_key} by user {user_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
            return False
    
    def get_session_participants(self, session_id: str) -> List[SessionParticipant]:
        """Get all participants in a session"""
        try:
            with self._lock:
                if session_id not in self.session_participants:
                    return []
                
                # Clean up stale participants
                now = datetime.now()
                participants = self.session_participants[session_id]
                active_participants = []
                
                for participant in participants:
                    # Check if participant is still active (within 5 minutes)
                    if (now - participant.last_seen).total_seconds() < 300:
                        active_participants.append(participant)
                    else:
                        participant.status = PresenceStatus.OFFLINE
                
                self.session_participants[session_id] = active_participants
                return active_participants
                
        except Exception as e:
            logger.error(f"Failed to get session participants: {e}")
            return []
    
    def get_session_locks(self, session_id: str) -> List[SessionLock]:
        """Get all active locks in a session"""
        try:
            with self._lock:
                if session_id not in self.session_locks:
                    return []
                
                locks = self.session_locks[session_id]
                now = datetime.now()
                active_locks = []
                
                for lock in locks.values():
                    if lock.expires_at > now:
                        active_locks.append(lock)
                
                return active_locks
                
        except Exception as e:
            logger.error(f"Failed to get session locks: {e}")
            return []
    
    def cleanup_expired_locks(self):
        """Clean up expired locks"""
        try:
            with self._lock:
                now = datetime.now()
                
                for session_id, locks in self.session_locks.items():
                    expired_keys = []
                    for lock_key, lock in locks.items():
                        if lock.expires_at <= now:
                            expired_keys.append(lock_key)
                    
                    for key in expired_keys:
                        del locks[key]
                
                logger.info("Cleaned up expired locks")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired locks: {e}")

# Initialize service
collab_workspace_service = CollaborationWorkspaceService()

# API Routes
@collab_workspace_bp.route('/session/<project_id>', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_session(project_id):
    """Create a new collaboration session"""
    try:
        data = request.get_json()
        session_name = data.get('session_name')
        max_participants = data.get('max_participants', 20)
        
        if not session_name:
            return jsonify({'error': 'session_name is required'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        session = collab_workspace_service.create_session(
            project_id=project_id,
            session_name=session_name,
            created_by=user_id,
            max_participants=max_participants
        )
        
        if not session:
            return jsonify({'error': 'Failed to create session'}), 500
        
        return jsonify({
            'success': True,
            'session': asdict(session)
        })
        
    except Exception as e:
        logger.error(f"Create session error: {e}")
        return jsonify({'error': str(e)}), 500

@collab_workspace_bp.route('/session/<session_id>/join', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@cost_accounted("api", "operation")
def join_session(session_id):
    """Join a collaboration session"""
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({'error': 'username is required'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        participant = collab_workspace_service.join_session(
            session_id=session_id,
            user_id=user_id,
            username=username
        )
        
        if not participant:
            return jsonify({'error': 'Failed to join session'}), 500
        
        return jsonify({
            'success': True,
            'participant': asdict(participant)
        })
        
    except Exception as e:
        logger.error(f"Join session error: {e}")
        return jsonify({'error': str(e)}), 500

@collab_workspace_bp.route('/session/<session_id>/leave', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@cost_accounted("api", "operation")
def leave_session(session_id):
    """Leave a collaboration session"""
    try:
        user_id = getattr(g, 'user_id', 'system')
        
        success = collab_workspace_service.leave_session(session_id, user_id)
        
        if not success:
            return jsonify({'error': 'Failed to leave session'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Left session successfully'
        })
        
    except Exception as e:
        logger.error(f"Leave session error: {e}")
        return jsonify({'error': str(e)}), 500

@collab_workspace_bp.route('/presence/<session_id>', methods=['GET'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@sse_stream(lambda: create_log_stream())
def get_presence(session_id):
    """Get session presence via SSE"""
    try:
        participants = collab_workspace_service.get_session_participants(session_id)
        
        return jsonify({
            'success': True,
            'participants': [asdict(p) for p in participants]
        })
        
    except Exception as e:
        logger.error(f"Get presence error: {e}")
        return jsonify({'error': str(e)}), 500

@collab_workspace_bp.route('/presence/<session_id>/update', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@cost_accounted("api", "operation")
def update_presence(session_id):
    """Update presence status"""
    try:
        data = request.get_json()
        status = data.get('status')
        
        if not status:
            return jsonify({'error': 'status is required'}), 400
        
        try:
            presence_status = PresenceStatus(status)
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        success = collab_workspace_service.update_presence(session_id, user_id, presence_status)
        
        if not success:
            return jsonify({'error': 'Failed to update presence'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Presence updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Update presence error: {e}")
        return jsonify({'error': str(e)}), 500

@collab_workspace_bp.route('/lock/<session_id>/acquire', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@cost_accounted("api", "operation")
def acquire_lock(session_id):
    """Acquire a lock on a resource"""
    try:
        data = request.get_json()
        lock_type = data.get('lock_type')
        resource_id = data.get('resource_id')
        duration_minutes = data.get('duration_minutes', 30)
        
        if not all([lock_type, resource_id]):
            return jsonify({'error': 'lock_type and resource_id are required'}), 400
        
        try:
            lock_type_enum = LockType(lock_type)
        except ValueError:
            return jsonify({'error': 'Invalid lock_type'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        lock = collab_workspace_service.acquire_lock(
            session_id=session_id,
            user_id=user_id,
            lock_type=lock_type_enum,
            resource_id=resource_id,
            duration_minutes=duration_minutes
        )
        
        if not lock:
            return jsonify({'error': 'Failed to acquire lock'}), 500
        
        return jsonify({
            'success': True,
            'lock': asdict(lock)
        })
        
    except Exception as e:
        logger.error(f"Acquire lock error: {e}")
        return jsonify({'error': str(e)}), 500

@collab_workspace_bp.route('/lock/<session_id>/release', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@cost_accounted("api", "operation")
def release_lock(session_id):
    """Release a lock on a resource"""
    try:
        data = request.get_json()
        lock_type = data.get('lock_type')
        resource_id = data.get('resource_id')
        
        if not all([lock_type, resource_id]):
            return jsonify({'error': 'lock_type and resource_id are required'}), 400
        
        try:
            lock_type_enum = LockType(lock_type)
        except ValueError:
            return jsonify({'error': 'Invalid lock_type'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        success = collab_workspace_service.release_lock(
            session_id=session_id,
            user_id=user_id,
            lock_type=lock_type_enum,
            resource_id=resource_id
        )
        
        if not success:
            return jsonify({'error': 'Failed to release lock'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Lock released successfully'
        })
        
    except Exception as e:
        logger.error(f"Release lock error: {e}")
        return jsonify({'error': str(e)}), 500
