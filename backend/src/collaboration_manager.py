"""
Team Collaboration & Shared Editing System
Priority 12: Team Collaboration & Org Management Layer
"""

import os
import json
import time
import threading
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Set, Any
import uuid


class CollaborationStatus(Enum):
    """Collaboration session status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    CONFLICT = "conflict"
    MERGED = "merged"


class EditPermission(Enum):
    """Edit permission levels"""
    READ_ONLY = "read_only"
    SUGGEST = "suggest"
    EDIT = "edit"
    APPROVE = "approve"
    ADMIN = "admin"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    MANUAL = "manual"
    AUTO_MERGE = "auto_merge"
    LAST_WRITE_WINS = "last_write_wins"
    BRANCH = "branch"


@dataclass
class CollaborationSession:
    """Active collaboration session"""
    session_id: str
    resource_id: str
    resource_type: str
    organization_id: str
    created_by: str
    created_at: datetime
    status: CollaborationStatus
    active_users: List[str]
    last_activity: datetime
    lock_holder: Optional[str] = None
    lock_expires: Optional[datetime] = None
    version: int = 1
    conflict_count: int = 0


@dataclass
class EditOperation:
    """Edit operation for conflict resolution"""
    operation_id: str
    session_id: str
    user_id: str
    timestamp: datetime
    operation_type: str  # insert, delete, update
    position: int
    content: str
    metadata: Dict[str, Any]
    resolved: bool = False


@dataclass
class UserPresence:
    """User presence in collaboration session"""
    user_id: str
    session_id: str
    joined_at: datetime
    last_seen: datetime
    cursor_position: Optional[int] = None
    selection_range: Optional[tuple] = None
    status: str = "active"  # active, idle, away


@dataclass
class CollaborationEvent:
    """Collaboration event for real-time updates"""
    event_id: str
    session_id: str
    event_type: str
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]
    broadcast: bool = True


class CollaborationManager:
    """Team Collaboration & Shared Editing System"""
    
    def __init__(self, base_dir: str, access_control, system_delivery, llm_factory):
        self.base_dir = base_dir
        self.access_control = access_control
        self.system_delivery = system_delivery
        self.llm_factory = llm_factory
        self.db_path = f"{base_dir}/collaboration_manager.db"
        
        # Active sessions and presence tracking
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.user_presence: Dict[str, UserPresence] = {}
        self.edit_operations: Dict[str, List[EditOperation]] = {}
        self.event_queue: List[CollaborationEvent] = []
        
        # Threading and synchronization
        self.session_lock = threading.Lock()
        self.presence_lock = threading.Lock()
        self.event_lock = threading.Lock()
        
        # Initialize database and start background tasks
        self._init_database()
        self._start_background_tasks()
    
    def _init_database(self):
        """Initialize collaboration database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collaboration_sessions (
                    session_id TEXT PRIMARY KEY,
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    active_users TEXT,
                    last_activity TEXT NOT NULL,
                    lock_holder TEXT,
                    lock_expires TEXT,
                    version INTEGER DEFAULT 1,
                    conflict_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edit_operations (
                    operation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_presence (
                    user_id TEXT,
                    session_id TEXT,
                    joined_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    cursor_position INTEGER,
                    selection_range TEXT,
                    status TEXT DEFAULT 'active',
                    PRIMARY KEY (user_id, session_id),
                    FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collaboration_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT,
                    broadcast BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (session_id) REFERENCES collaboration_sessions (session_id)
                )
            """)
            
            conn.commit()
    
    def _start_background_tasks(self):
        """Start background tasks for cleanup and event processing"""
        # Cleanup inactive sessions
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        # Process event queue
        self.event_thread = threading.Thread(target=self._event_loop, daemon=True)
        self.event_thread.start()
    
    def create_collaboration_session(self, resource_id: str, resource_type: str, 
                                   organization_id: str, user_id: str) -> CollaborationSession:
        """Create a new collaboration session"""
        # Check user permissions
        if not self._can_edit_resource(user_id, resource_id, resource_type, organization_id):
            raise PermissionError(f"User {user_id} cannot edit resource {resource_id}")
        
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = CollaborationSession(
            session_id=session_id,
            resource_id=resource_id,
            resource_type=resource_type,
            organization_id=organization_id,
            created_by=user_id,
            created_at=now,
            status=CollaborationStatus.ACTIVE,
            active_users=[user_id],
            last_activity=now
        )
        
        with self.session_lock:
            self.active_sessions[session_id] = session
            self._save_session(session)
        
        # Add user presence
        self.join_session(session_id, user_id)
        
        # Create event
        self._create_event(session_id, "session_created", user_id, {
            "resource_id": resource_id,
            "resource_type": resource_type
        })
        
        return session
    
    def join_session(self, session_id: str, user_id: str) -> bool:
        """Join an existing collaboration session"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Check if user can join
            if not self._can_edit_resource(user_id, session.resource_id, 
                                         session.resource_type, session.organization_id):
                return False
            
            # Add user to active users if not already present
            if user_id not in session.active_users:
                session.active_users.append(user_id)
                session.last_activity = datetime.now()
                self._save_session(session)
        
        # Update presence
        with self.presence_lock:
            presence = UserPresence(
                user_id=user_id,
                session_id=session_id,
                joined_at=datetime.now(),
                last_seen=datetime.now(),
                status="active"
            )
            self.user_presence[f"{session_id}:{user_id}"] = presence
            self._save_presence(presence)
        
        # Create event
        self._create_event(session_id, "user_joined", user_id, {
            "user_id": user_id,
            "active_users": session.active_users
        })
        
        return True
    
    def leave_session(self, session_id: str, user_id: str) -> bool:
        """Leave a collaboration session"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Remove user from active users
            if user_id in session.active_users:
                session.active_users.remove(user_id)
                session.last_activity = datetime.now()
                self._save_session(session)
        
        # Remove presence
        with self.presence_lock:
            presence_key = f"{session_id}:{user_id}"
            if presence_key in self.user_presence:
                del self.user_presence[presence_key]
                self._remove_presence(session_id, user_id)
        
        # Create event
        self._create_event(session_id, "user_left", user_id, {
            "user_id": user_id,
            "active_users": session.active_users
        })
        
        return True
    
    def acquire_lock(self, session_id: str, user_id: str, duration_minutes: int = 30) -> bool:
        """Acquire a lock on the session for exclusive editing"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Check if already locked
            if session.lock_holder and session.lock_expires and session.lock_expires > datetime.now():
                return False
            
            # Check user permissions
            if not self._can_edit_resource(user_id, session.resource_id, 
                                         session.resource_type, session.organization_id):
                return False
            
            # Acquire lock
            session.lock_holder = user_id
            session.lock_expires = datetime.now() + timedelta(minutes=duration_minutes)
            session.status = CollaborationStatus.LOCKED
            self._save_session(session)
        
        # Create event
        self._create_event(session_id, "lock_acquired", user_id, {
            "lock_holder": user_id,
            "expires_at": session.lock_expires.isoformat()
        })
        
        return True
    
    def release_lock(self, session_id: str, user_id: str) -> bool:
        """Release a lock on the session"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Check if user holds the lock
            if session.lock_holder != user_id:
                return False
            
            # Release lock
            session.lock_holder = None
            session.lock_expires = None
            session.status = CollaborationStatus.ACTIVE
            self._save_session(session)
        
        # Create event
        self._create_event(session_id, "lock_released", user_id, {})
        
        return True
    
    def apply_edit_operation(self, session_id: str, user_id: str, operation_type: str,
                           position: int, content: str, metadata: Dict[str, Any] = None) -> EditOperation:
        """Apply an edit operation to the session"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            # Check if session is locked by another user
            if session.lock_holder and session.lock_holder != user_id:
                if session.lock_expires and session.lock_expires > datetime.now():
                    raise PermissionError(f"Session is locked by {session.lock_holder}")
                else:
                    # Lock expired, release it
                    session.lock_holder = None
                    session.lock_expires = None
                    session.status = CollaborationStatus.ACTIVE
            
            # Check user permissions
            if not self._can_edit_resource(user_id, session.resource_id, 
                                         session.resource_type, session.organization_id):
                raise PermissionError(f"User {user_id} cannot edit this resource")
        
        # Create edit operation
        operation = EditOperation(
            operation_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.now(),
            operation_type=operation_type,
            position=position,
            content=content,
            metadata=metadata or {}
        )
        
        # Store operation
        if session_id not in self.edit_operations:
            self.edit_operations[session_id] = []
        self.edit_operations[session_id].append(operation)
        self._save_edit_operation(operation)
        
        # Update session
        with self.session_lock:
            session.last_activity = datetime.now()
            session.version += 1
            self._save_session(session)
        
        # Create event
        self._create_event(session_id, "edit_applied", user_id, {
            "operation_id": operation.operation_id,
            "operation_type": operation_type,
            "position": position,
            "version": session.version
        })
        
        return operation
    
    def resolve_conflicts(self, session_id: str, user_id: str, 
                         resolution_strategy: ConflictResolution) -> bool:
        """Resolve conflicts in the session"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            
            # Check if user can resolve conflicts
            if not self._can_approve_resource(user_id, session.resource_id, 
                                            session.resource_type, session.organization_id):
                return False
            
            # Apply resolution strategy
            if resolution_strategy == ConflictResolution.LAST_WRITE_WINS:
                self._resolve_last_write_wins(session_id)
            elif resolution_strategy == ConflictResolution.AUTO_MERGE:
                self._resolve_auto_merge(session_id)
            elif resolution_strategy == ConflictResolution.BRANCH:
                self._resolve_branch(session_id)
            
            session.status = CollaborationStatus.MERGED
            session.conflict_count = 0
            self._save_session(session)
        
        # Create event
        self._create_event(session_id, "conflicts_resolved", user_id, {
            "strategy": resolution_strategy.value,
            "version": session.version
        })
        
        return True
    
    def update_presence(self, session_id: str, user_id: str, 
                       cursor_position: Optional[int] = None,
                       selection_range: Optional[tuple] = None,
                       status: str = "active") -> bool:
        """Update user presence in session"""
        with self.presence_lock:
            presence_key = f"{session_id}:{user_id}"
            if presence_key in self.user_presence:
                presence = self.user_presence[presence_key]
                presence.last_seen = datetime.now()
                presence.cursor_position = cursor_position
                presence.selection_range = selection_range
                presence.status = status
                self._save_presence(presence)
                return True
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive session information"""
        with self.session_lock:
            if session_id not in self.active_sessions:
                return None
            
            session = self.active_sessions[session_id]
            
            # Get active users with presence info
            active_users_info = []
            with self.presence_lock:
                for user_id in session.active_users:
                    presence_key = f"{session_id}:{user_id}"
                    if presence_key in self.user_presence:
                        presence = self.user_presence[presence_key]
                        active_users_info.append({
                            "user_id": user_id,
                            "joined_at": presence.joined_at.isoformat(),
                            "last_seen": presence.last_seen.isoformat(),
                            "cursor_position": presence.cursor_position,
                            "selection_range": presence.selection_range,
                            "status": presence.status
                        })
            
            # Get recent operations
            recent_operations = []
            if session_id in self.edit_operations:
                recent_ops = sorted(self.edit_operations[session_id], 
                                  key=lambda x: x.timestamp, reverse=True)[:10]
                recent_operations = [asdict(op) for op in recent_ops]
            
            return {
                "session": asdict(session),
                "active_users": active_users_info,
                "recent_operations": recent_operations,
                "pending_events": len([e for e in self.event_queue if e.session_id == session_id])
            }
    
    def get_user_sessions(self, user_id: str, organization_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user in an organization"""
        with self.session_lock:
            user_sessions = []
            for session in self.active_sessions.values():
                if session.organization_id == organization_id and user_id in session.active_users:
                    user_sessions.append(asdict(session))
            return user_sessions
    
    def _can_edit_resource(self, user_id: str, resource_id: str, 
                          resource_type: str, organization_id: str) -> bool:
        """Check if user can edit a resource"""
        # This would integrate with access_control system
        # For now, return True for demonstration
        return True
    
    def _can_approve_resource(self, user_id: str, resource_id: str, 
                             resource_type: str, organization_id: str) -> bool:
        """Check if user can approve changes to a resource"""
        # This would integrate with access_control system
        # For now, return True for demonstration
        return True
    
    def _resolve_last_write_wins(self, session_id: str):
        """Resolve conflicts using last-write-wins strategy"""
        if session_id in self.edit_operations:
            # Keep only the most recent operation for each position
            operations = self.edit_operations[session_id]
            latest_ops = {}
            for op in operations:
                key = (op.position, op.operation_type)
                if key not in latest_ops or op.timestamp > latest_ops[key].timestamp:
                    latest_ops[key] = op
            
            # Update operations list
            self.edit_operations[session_id] = list(latest_ops.values())
    
    def _resolve_auto_merge(self, session_id: str):
        """Resolve conflicts using auto-merge strategy"""
        # This would implement intelligent merging logic
        # For now, just use last-write-wins
        self._resolve_last_write_wins(session_id)
    
    def _resolve_branch(self, session_id: str):
        """Resolve conflicts by creating a branch"""
        # This would create a new session with merged content
        # For now, just use last-write-wins
        self._resolve_last_write_wins(session_id)
    
    def _create_event(self, session_id: str, event_type: str, user_id: str, data: Dict[str, Any]):
        """Create a collaboration event"""
        event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            event_type=event_type,
            user_id=user_id,
            timestamp=datetime.now(),
            data=data
        )
        
        with self.event_lock:
            self.event_queue.append(event)
            self._save_event(event)
    
    def _cleanup_loop(self):
        """Background loop to cleanup inactive sessions"""
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes
                self._cleanup_inactive_sessions()
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
    
    def _event_loop(self):
        """Background loop to process events"""
        while True:
            try:
                time.sleep(1)  # Run every second
                self._process_event_queue()
            except Exception as e:
                print(f"Error in event loop: {e}")
    
    def _cleanup_inactive_sessions(self):
        """Cleanup sessions that have been inactive for too long"""
        now = datetime.now()
        inactive_threshold = timedelta(hours=2)
        
        with self.session_lock:
            sessions_to_remove = []
            for session_id, session in self.active_sessions.items():
                if now - session.last_activity > inactive_threshold:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.active_sessions[session_id]
                self._remove_session(session_id)
    
    def _process_event_queue(self):
        """Process events in the queue"""
        with self.event_lock:
            if self.event_queue:
                # Process events (in a real implementation, this would broadcast to connected clients)
                self.event_queue.clear()
    
    def _save_session(self, session: CollaborationSession):
        """Save session to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO collaboration_sessions 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id, session.resource_id, session.resource_type,
                session.organization_id, session.created_by, session.created_at.isoformat(),
                session.status.value, json.dumps(session.active_users),
                session.last_activity.isoformat(), session.lock_holder,
                session.lock_expires.isoformat() if session.lock_expires else None,
                session.version, session.conflict_count
            ))
            conn.commit()
    
    def _save_edit_operation(self, operation: EditOperation):
        """Save edit operation to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO edit_operations 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                operation.operation_id, operation.session_id, operation.user_id,
                operation.timestamp.isoformat(), operation.operation_type,
                operation.position, operation.content, json.dumps(operation.metadata),
                operation.resolved
            ))
            conn.commit()
    
    def _save_presence(self, presence: UserPresence):
        """Save user presence to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_presence 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                presence.user_id, presence.session_id, presence.joined_at.isoformat(),
                presence.last_seen.isoformat(), presence.cursor_position,
                json.dumps(presence.selection_range) if presence.selection_range else None,
                presence.status
            ))
            conn.commit()
    
    def _save_event(self, event: CollaborationEvent):
        """Save event to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO collaboration_events 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.session_id, event.event_type,
                event.user_id, event.timestamp.isoformat(),
                json.dumps(event.data), event.broadcast
            ))
            conn.commit()
    
    def _remove_session(self, session_id: str):
        """Remove session from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM collaboration_sessions WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM edit_operations WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM user_presence WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM collaboration_events WHERE session_id = ?", (session_id,))
            conn.commit()
    
    def _remove_presence(self, session_id: str, user_id: str):
        """Remove user presence from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM user_presence WHERE session_id = ? AND user_id = ?", 
                        (session_id, user_id))
            conn.commit()
    
    def get_collaboration_statistics(self) -> Dict[str, Any]:
        """Get collaboration statistics"""
        with self.session_lock:
            total_sessions = len(self.active_sessions)
            active_users = set()
            for session in self.active_sessions.values():
                active_users.update(session.active_users)
            
            total_operations = sum(len(ops) for ops in self.edit_operations.values())
            
            return {
                "total_sessions": total_sessions,
                "active_users": len(active_users),
                "total_operations": total_operations,
                "sessions_by_type": self._get_sessions_by_type(),
                "recent_activity": self._get_recent_activity()
            }
    
    def _get_sessions_by_type(self) -> Dict[str, int]:
        """Get session count by resource type"""
        session_types = {}
        for session in self.active_sessions.values():
            session_types[session.resource_type] = session_types.get(session.resource_type, 0) + 1
        return session_types
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent collaboration activity"""
        recent_events = []
        with self.event_lock:
            for event in sorted(self.event_queue, key=lambda x: x.timestamp, reverse=True)[:20]:
                recent_events.append({
                    "event_type": event.event_type,
                    "user_id": event.user_id,
                    "timestamp": event.timestamp.isoformat(),
                    "session_id": event.session_id
                })
        return recent_events
