"""
Priority 25: Consensus Memory

This module provides temporary shared memory pool for planning groups
with memory merge logic, conflict resolution, and read/write gating.
"""

import sqlite3
import json
import uuid
import time
import threading
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from collections import defaultdict
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryAccessLevel(Enum):
    """Access levels for memory operations"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"

class ConflictResolutionStrategy(Enum):
    """Strategies for resolving memory conflicts"""
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"
    CONSENSUS = "consensus"
    MANUAL = "manual"
    REJECT = "reject"

class MemoryStatus(Enum):
    """Status of memory entries"""
    ACTIVE = "active"
    MERGED = "merged"
    CONFLICTED = "conflicted"
    EXPIRED = "expired"
    ARCHIVED = "archived"

@dataclass
class ConsensusMemoryEntry:
    """Represents an entry in consensus memory"""
    entry_id: str
    session_id: str
    agent_id: str
    key: str
    value: Any
    data_type: str
    access_level: MemoryAccessLevel
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    version: int
    status: MemoryStatus
    metadata: Dict[str, Any]
    checksum: str

@dataclass
class MemoryConflict:
    """Represents a memory conflict"""
    conflict_id: str
    session_id: str
    key: str
    conflicting_entries: List[str]  # entry_ids
    conflict_type: str
    detected_at: datetime
    resolution_strategy: ConflictResolutionStrategy
    resolved: bool
    resolution_result: Optional[Dict[str, Any]]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]

@dataclass
class MemoryAccessLog:
    """Log of memory access operations"""
    log_id: str
    session_id: str
    agent_id: str
    operation: str  # read, write, merge, conflict
    key: str
    entry_id: Optional[str]
    timestamp: datetime
    success: bool
    details: Dict[str, Any]

class ConsensusMemory:
    """
    Consensus Memory Manager
    
    Provides temporary shared memory pool for planning groups with
    memory merge logic, conflict resolution, and access control.
    """
    
    def __init__(self, base_dir: Path, agent_messaging_layer, multi_agent_planning,
                 access_control, llm_factory, black_box_inspector=None):
        self.base_dir = base_dir
        self.agent_messaging_layer = agent_messaging_layer
        self.multi_agent_planning = multi_agent_planning
        self.access_control = access_control
        self.llm_factory = llm_factory
        self.black_box_inspector = black_box_inspector
        
        # Database setup
        self.db_path = base_dir / "data" / "consensus_memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Memory state
        self.session_memory: Dict[str, Dict[str, ConsensusMemoryEntry]] = defaultdict(dict)
        self.memory_conflicts: Dict[str, List[MemoryConflict]] = defaultdict(list)
        self.access_logs: List[MemoryAccessLog] = []
        
        # Locks for thread safety
        self.memory_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        
        # Background processing
        self.running = True
        self.merge_worker = threading.Thread(target=self._merge_worker, daemon=True)
        self.conflict_worker = threading.Thread(target=self._conflict_worker, daemon=True)
        self.cleanup_worker = threading.Thread(target=self._cleanup_worker, daemon=True)
        
        # Start background threads
        self.merge_worker.start()
        self.conflict_worker.start()
        self.cleanup_worker.start()
        
        logger.info("Consensus Memory initialized")
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consensus_memory_entries (
                    entry_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    access_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    checksum TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    conflicting_entries TEXT NOT NULL,
                    conflict_type TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    resolution_strategy TEXT NOT NULL,
                    resolved BOOLEAN NOT NULL,
                    resolution_result TEXT,
                    resolved_by TEXT,
                    resolved_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_access_logs (
                    log_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    key TEXT NOT NULL,
                    entry_id TEXT,
                    timestamp TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    details TEXT NOT NULL
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_session ON consensus_memory_entries(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_key ON consensus_memory_entries(key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_status ON consensus_memory_entries(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_session ON memory_conflicts(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_resolved ON memory_conflicts(resolved)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_session ON memory_access_logs(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON memory_access_logs(timestamp)")
            
            conn.commit()
    
    def write_memory(self, session_id: str, agent_id: str, key: str, value: Any,
                    data_type: str = "json", access_level: MemoryAccessLevel = MemoryAccessLevel.READ_WRITE,
                    ttl_minutes: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Write a value to consensus memory"""
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now()
        expires_at = timestamp + timedelta(minutes=ttl_minutes) if ttl_minutes else None
        
        # Calculate checksum
        value_str = json.dumps(value, sort_keys=True)
        checksum = hashlib.sha256(value_str.encode()).hexdigest()
        
        # Create memory entry
        entry = ConsensusMemoryEntry(
            entry_id=entry_id,
            session_id=session_id,
            agent_id=agent_id,
            key=key,
            value=value,
            data_type=data_type,
            access_level=access_level,
            created_at=timestamp,
            updated_at=timestamp,
            expires_at=expires_at,
            version=1,
            status=MemoryStatus.ACTIVE,
            metadata=metadata or {},
            checksum=checksum
        )
        
        # Check for conflicts
        existing_entries = self._get_entries_for_key(session_id, key)
        if existing_entries:
            conflict = self._detect_conflict(session_id, key, entry, existing_entries)
            if conflict:
                self._handle_conflict(conflict)
                return entry_id
        
        # Store entry
        self._store_entry(entry)
        
        # Add to session memory
        with self.memory_locks[session_id]:
            self.session_memory[session_id][key] = entry
        
        # Log access
        self._log_access(session_id, agent_id, "write", key, entry_id, True, {
            "data_type": data_type,
            "access_level": access_level.value,
            "ttl_minutes": ttl_minutes
        })
        
        # Log to black box inspector
        if self.black_box_inspector:
            self.black_box_inspector.log_trace_event(
                trace_type="memory_write",
                component_id=f"entry-{entry_id}",
                payload={
                    "entry_id": entry_id,
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "key": key,
                    "data_type": data_type,
                    "access_level": access_level.value
                },
                metadata={
                    "value_size": len(value_str),
                    "checksum": checksum,
                    "ttl_minutes": ttl_minutes
                }
            )
        
        logger.info(f"Memory entry {entry_id} written for session {session_id}, key: {key}")
        return entry_id
    
    def read_memory(self, session_id: str, agent_id: str, key: str) -> Optional[Any]:
        """Read a value from consensus memory"""
        with self.memory_locks[session_id]:
            entry = self.session_memory[session_id].get(key)
        
        if not entry:
            # Try to load from database
            entry = self._load_entry_from_db(session_id, key)
            if entry:
                with self.memory_locks[session_id]:
                    self.session_memory[session_id][key] = entry
        
        if not entry:
            self._log_access(session_id, agent_id, "read", key, None, False, {"reason": "not_found"})
            return None
        
        # Check if entry has expired
        if entry.expires_at and datetime.now() > entry.expires_at:
            entry.status = MemoryStatus.EXPIRED
            self._update_entry(entry)
            self._log_access(session_id, agent_id, "read", key, entry.entry_id, False, {"reason": "expired"})
            return None
        
        # Check access permissions
        if not self._check_access_permission(agent_id, entry.access_level):
            self._log_access(session_id, agent_id, "read", key, entry.entry_id, False, {"reason": "permission_denied"})
            return None
        
        # Log successful access
        self._log_access(session_id, agent_id, "read", key, entry.entry_id, True, {
            "data_type": entry.data_type,
            "version": entry.version
        })
        
        return entry.value
    
    def merge_memory(self, session_id: str, agent_id: str, key: str, 
                    merge_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MERGE) -> bool:
        """Merge conflicting memory entries"""
        with self.memory_locks[session_id]:
            entry = self.session_memory[session_id].get(key)
        
        if not entry:
            return False
        
        # Find conflicts for this key
        conflicts = [c for c in self.memory_conflicts[session_id] if c.key == key and not c.resolved]
        
        if not conflicts:
            return False
        
        conflict = conflicts[0]
        
        # Apply merge strategy
        if merge_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            success = self._merge_last_write_wins(conflict)
        elif merge_strategy == ConflictResolutionStrategy.MERGE:
            success = self._merge_values(conflict)
        elif merge_strategy == ConflictResolutionStrategy.CONSENSUS:
            success = self._merge_consensus(conflict)
        else:
            success = False
        
        if success:
            conflict.resolved = True
            conflict.resolution_result = {"strategy": merge_strategy.value, "success": True}
            conflict.resolved_by = agent_id
            conflict.resolved_at = datetime.now()
            
            self._update_conflict(conflict)
            
            # Log access
            self._log_access(session_id, agent_id, "merge", key, entry.entry_id, True, {
                "conflict_id": conflict.conflict_id,
                "strategy": merge_strategy.value
            })
            
            logger.info(f"Memory conflict {conflict.conflict_id} resolved for key {key}")
            return True
        
        return False
    
    def _get_entries_for_key(self, session_id: str, key: str) -> List[ConsensusMemoryEntry]:
        """Get all entries for a specific key in a session"""
        with self.memory_locks[session_id]:
            entry = self.session_memory[session_id].get(key)
        
        if entry:
            return [entry]
        
        # Load from database
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM consensus_memory_entries 
                WHERE session_id = ? AND key = ? AND status = 'active'
            """, (session_id, key))
            rows = cursor.fetchall()
        
        entries = []
        for row in rows:
            entry = self._row_to_entry(row)
            entries.append(entry)
        
        return entries
    
    def _detect_conflict(self, session_id: str, key: str, new_entry: ConsensusMemoryEntry,
                        existing_entries: List[ConsensusMemoryEntry]) -> Optional[MemoryConflict]:
        """Detect conflicts between memory entries"""
        if not existing_entries:
            return None
        
        # Check for value conflicts
        conflicting_entries = []
        for entry in existing_entries:
            if entry.checksum != new_entry.checksum:
                conflicting_entries.append(entry.entry_id)
        
        if not conflicting_entries:
            return None
        
        # Create conflict record
        conflict_id = str(uuid.uuid4())
        conflict = MemoryConflict(
            conflict_id=conflict_id,
            session_id=session_id,
            key=key,
            conflicting_entries=conflicting_entries + [new_entry.entry_id],
            conflict_type="value_conflict",
            detected_at=datetime.now(),
            resolution_strategy=ConflictResolutionStrategy.MERGE,
            resolved=False,
            resolution_result=None,
            resolved_by=None,
            resolved_at=None
        )
        
        return conflict
    
    def _handle_conflict(self, conflict: MemoryConflict):
        """Handle a detected memory conflict"""
        # Store conflict
        self._store_conflict(conflict)
        
        # Add to session conflicts
        self.memory_conflicts[conflict.session_id].append(conflict)
        
        # Update entry status
        for entry_id in conflict.conflicting_entries:
            entry = self._load_entry_by_id(entry_id)
            if entry:
                entry.status = MemoryStatus.CONFLICTED
                self._update_entry(entry)
        
        # Notify agents about conflict
        self._notify_conflict(conflict)
        
        logger.info(f"Memory conflict {conflict.conflict_id} detected for key {conflict.key}")
    
    def _merge_last_write_wins(self, conflict: MemoryConflict) -> bool:
        """Merge using last-write-wins strategy"""
        entries = []
        for entry_id in conflict.conflicting_entries:
            entry = self._load_entry_by_id(entry_id)
            if entry:
                entries.append(entry)
        
        if not entries:
            return False
        
        # Find the most recent entry
        latest_entry = max(entries, key=lambda e: e.updated_at)
        
        # Mark other entries as merged
        for entry in entries:
            if entry.entry_id != latest_entry.entry_id:
                entry.status = MemoryStatus.MERGED
                self._update_entry(entry)
        
        # Keep the latest entry active
        latest_entry.status = MemoryStatus.ACTIVE
        self._update_entry(latest_entry)
        
        return True
    
    def _merge_values(self, conflict: MemoryConflict) -> bool:
        """Merge values using intelligent merging"""
        entries = []
        for entry_id in conflict.conflicting_entries:
            entry = self._load_entry_by_id(entry_id)
            if entry:
                entries.append(entry)
        
        if not entries:
            return False
        
        # Simple merge strategy - can be enhanced with LLM-based merging
        merged_value = self._merge_json_values([entry.value for entry in entries])
        
        # Create new merged entry
        merged_entry = ConsensusMemoryEntry(
            entry_id=str(uuid.uuid4()),
            session_id=conflict.session_id,
            agent_id="consensus_system",
            key=conflict.key,
            value=merged_value,
            data_type="json",
            access_level=MemoryAccessLevel.READ_WRITE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=None,
            version=max(entry.version for entry in entries) + 1,
            status=MemoryStatus.ACTIVE,
            metadata={"merged_from": [e.entry_id for e in entries]},
            checksum=hashlib.sha256(json.dumps(merged_value, sort_keys=True).encode()).hexdigest()
        )
        
        # Store merged entry
        self._store_entry(merged_entry)
        
        # Mark original entries as merged
        for entry in entries:
            entry.status = MemoryStatus.MERGED
            self._update_entry(entry)
        
        return True
    
    def _merge_json_values(self, values: List[Any]) -> Any:
        """Merge JSON values intelligently"""
        if not values:
            return None
        
        if len(values) == 1:
            return values[0]
        
        # Simple merge for dictionaries
        if all(isinstance(v, dict) for v in values):
            merged = {}
            for value in values:
                merged.update(value)
            return merged
        
        # Simple merge for lists
        if all(isinstance(v, list) for v in values):
            merged = []
            for value in values:
                merged.extend(value)
            return merged
        
        # For other types, return the last value
        return values[-1]
    
    def _merge_consensus(self, conflict: MemoryConflict) -> bool:
        """Merge using consensus-based approach"""
        # This could be enhanced with LLM-based consensus building
        # For now, use simple majority voting
        entries = []
        for entry_id in conflict.conflicting_entries:
            entry = self._load_entry_by_id(entry_id)
            if entry:
                entries.append(entry)
        
        if not entries:
            return False
        
        # Group by value checksums
        value_groups = defaultdict(list)
        for entry in entries:
            value_groups[entry.checksum].append(entry)
        
        # Find the most common value
        most_common_checksum = max(value_groups.keys(), key=lambda k: len(value_groups[k]))
        consensus_entries = value_groups[most_common_checksum]
        
        # Use the most recent entry from the consensus group
        consensus_entry = max(consensus_entries, key=lambda e: e.updated_at)
        
        # Mark other entries as merged
        for entry in entries:
            if entry.entry_id != consensus_entry.entry_id:
                entry.status = MemoryStatus.MERGED
                self._update_entry(entry)
        
        # Keep consensus entry active
        consensus_entry.status = MemoryStatus.ACTIVE
        self._update_entry(consensus_entry)
        
        return True
    
    def _check_access_permission(self, agent_id: str, access_level: MemoryAccessLevel) -> bool:
        """Check if agent has permission to access memory"""
        # Simple permission check - can be enhanced with access control system
        if access_level == MemoryAccessLevel.READ_ONLY:
            return True  # Anyone can read
        elif access_level == MemoryAccessLevel.READ_WRITE:
            return True  # Anyone can read/write for now
        elif access_level == MemoryAccessLevel.ADMIN:
            # Check if agent is admin
            return agent_id in ["consensus_system", "admin_agent"]
        
        return False
    
    def _store_entry(self, entry: ConsensusMemoryEntry):
        """Store a memory entry in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO consensus_memory_entries 
                (entry_id, session_id, agent_id, key, value, data_type, access_level,
                 created_at, updated_at, expires_at, version, status, metadata, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id,
                entry.session_id,
                entry.agent_id,
                entry.key,
                json.dumps(entry.value),
                entry.data_type,
                entry.access_level.value,
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
                entry.expires_at.isoformat() if entry.expires_at else None,
                entry.version,
                entry.status.value,
                json.dumps(entry.metadata),
                entry.checksum
            ))
            conn.commit()
    
    def _update_entry(self, entry: ConsensusMemoryEntry):
        """Update a memory entry in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE consensus_memory_entries 
                SET value = ?, updated_at = ?, version = ?, status = ?, metadata = ?, checksum = ?
                WHERE entry_id = ?
            """, (
                json.dumps(entry.value),
                entry.updated_at.isoformat(),
                entry.version,
                entry.status.value,
                json.dumps(entry.metadata),
                entry.checksum,
                entry.entry_id
            ))
            conn.commit()
    
    def _store_conflict(self, conflict: MemoryConflict):
        """Store a memory conflict in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO memory_conflicts 
                (conflict_id, session_id, key, conflicting_entries, conflict_type,
                 detected_at, resolution_strategy, resolved, resolution_result,
                 resolved_by, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conflict.conflict_id,
                conflict.session_id,
                conflict.key,
                json.dumps(conflict.conflicting_entries),
                conflict.conflict_type,
                conflict.detected_at.isoformat(),
                conflict.resolution_strategy.value,
                conflict.resolved,
                json.dumps(conflict.resolution_result) if conflict.resolution_result else None,
                conflict.resolved_by,
                conflict.resolved_at.isoformat() if conflict.resolved_at else None
            ))
            conn.commit()
    
    def _update_conflict(self, conflict: MemoryConflict):
        """Update a memory conflict in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE memory_conflicts 
                SET resolved = ?, resolution_result = ?, resolved_by = ?, resolved_at = ?
                WHERE conflict_id = ?
            """, (
                conflict.resolved,
                json.dumps(conflict.resolution_result) if conflict.resolution_result else None,
                conflict.resolved_by,
                conflict.resolved_at.isoformat() if conflict.resolved_at else None,
                conflict.conflict_id
            ))
            conn.commit()
    
    def _load_entry_from_db(self, session_id: str, key: str) -> Optional[ConsensusMemoryEntry]:
        """Load an entry from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM consensus_memory_entries 
                WHERE session_id = ? AND key = ? AND status = 'active'
                ORDER BY updated_at DESC LIMIT 1
            """, (session_id, key))
            row = cursor.fetchone()
        
        if row:
            return self._row_to_entry(row)
        return None
    
    def _load_entry_by_id(self, entry_id: str) -> Optional[ConsensusMemoryEntry]:
        """Load an entry by ID from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM consensus_memory_entries 
                WHERE entry_id = ?
            """, (entry_id,))
            row = cursor.fetchone()
        
        if row:
            return self._row_to_entry(row)
        return None
    
    def _row_to_entry(self, row) -> ConsensusMemoryEntry:
        """Convert database row to ConsensusMemoryEntry"""
        return ConsensusMemoryEntry(
            entry_id=row['entry_id'],
            session_id=row['session_id'],
            agent_id=row['agent_id'],
            key=row['key'],
            value=json.loads(row['value']),
            data_type=row['data_type'],
            access_level=MemoryAccessLevel(row['access_level']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            version=row['version'],
            status=MemoryStatus(row['status']),
            metadata=json.loads(row['metadata']),
            checksum=row['checksum']
        )
    
    def _log_access(self, session_id: str, agent_id: str, operation: str, key: str,
                   entry_id: Optional[str], success: bool, details: Dict[str, Any]):
        """Log memory access operation"""
        log = MemoryAccessLog(
            log_id=str(uuid.uuid4()),
            session_id=session_id,
            agent_id=agent_id,
            operation=operation,
            key=key,
            entry_id=entry_id,
            timestamp=datetime.now(),
            success=success,
            details=details
        )
        
        # Store log
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO memory_access_logs 
                (log_id, session_id, agent_id, operation, key, entry_id, timestamp, success, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.log_id,
                log.session_id,
                log.agent_id,
                log.operation,
                log.key,
                log.entry_id,
                log.timestamp.isoformat(),
                log.success,
                json.dumps(log.details)
            ))
            conn.commit()
        
        # Add to in-memory logs
        self.access_logs.append(log)
    
    def _notify_conflict(self, conflict: MemoryConflict):
        """Notify agents about memory conflict"""
        if not self.agent_messaging_layer:
            return
        
        # Get session participants
        if self.multi_agent_planning and conflict.session_id in self.multi_agent_planning.active_sessions:
            session = self.multi_agent_planning.active_sessions[conflict.session_id]
            participants = session.participants
        else:
            participants = []
        
        # Notify participants
        for participant in participants:
            try:
                self.agent_messaging_layer.send_message(
                    sender_id="consensus_system",
                    receiver_id=participant,
                    message_type=self.agent_messaging_layer.MessageType.ALERT,
                    content=f"Memory conflict detected for key: {conflict.key}",
                    priority=self.agent_messaging_layer.MessagePriority.HIGH,
                    metadata={
                        "session_id": conflict.session_id,
                        "conflict_id": conflict.conflict_id,
                        "key": conflict.key,
                        "conflict_type": conflict.conflict_type,
                        "conflicting_entries": conflict.conflicting_entries
                    }
                )
            except Exception as e:
                logger.error(f"Failed to notify participant {participant}: {e}")
    
    def get_session_memory(self, session_id: str) -> Dict[str, Any]:
        """Get all memory entries for a session"""
        with self.memory_locks[session_id]:
            memory = {}
            for key, entry in self.session_memory[session_id].items():
                if entry.status == MemoryStatus.ACTIVE:
                    memory[key] = {
                        "value": entry.value,
                        "agent_id": entry.agent_id,
                        "data_type": entry.data_type,
                        "version": entry.version,
                        "updated_at": entry.updated_at.isoformat()
                    }
        
        return memory
    
    def get_conflicts(self, session_id: str) -> List[Dict[str, Any]]:
        """Get unresolved conflicts for a session"""
        conflicts = [c for c in self.memory_conflicts[session_id] if not c.resolved]
        
        return [
            {
                "conflict_id": c.conflict_id,
                "key": c.key,
                "conflict_type": c.conflict_type,
                "detected_at": c.detected_at.isoformat(),
                "conflicting_entries": c.conflicting_entries
            }
            for c in conflicts
        ]
    
    def _merge_worker(self):
        """Background worker for memory merging"""
        while self.running:
            try:
                # Process pending merges
                for session_id in list(self.session_memory.keys()):
                    conflicts = [c for c in self.memory_conflicts[session_id] if not c.resolved]
                    for conflict in conflicts:
                        self._auto_resolve_conflict(conflict)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Merge worker error: {e}")
                time.sleep(120)  # Wait 2 minutes on error
    
    def _conflict_worker(self):
        """Background worker for conflict detection"""
        while self.running:
            try:
                # Detect new conflicts
                # This could be enhanced with more sophisticated detection
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Conflict worker error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def _cleanup_worker(self):
        """Background worker for cleaning up expired memory"""
        while self.running:
            try:
                # Clean up expired entries
                current_time = datetime.now()
                
                for session_id in list(self.session_memory.keys()):
                    with self.memory_locks[session_id]:
                        expired_keys = []
                        for key, entry in self.session_memory[session_id].items():
                            if entry.expires_at and current_time > entry.expires_at:
                                entry.status = MemoryStatus.EXPIRED
                                self._update_entry(entry)
                                expired_keys.append(key)
                        
                        for key in expired_keys:
                            del self.session_memory[session_id][key]
                
                time.sleep(300)  # Run cleanup every 5 minutes
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(600)  # Wait 10 minutes on error
    
    def _auto_resolve_conflict(self, conflict: MemoryConflict):
        """Automatically resolve conflicts using default strategy"""
        if conflict.resolution_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            self._merge_last_write_wins(conflict)
        elif conflict.resolution_strategy == ConflictResolutionStrategy.MERGE:
            self._merge_values(conflict)
        elif conflict.resolution_strategy == ConflictResolutionStrategy.CONSENSUS:
            self._merge_consensus(conflict)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Entry counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM consensus_memory_entries 
                GROUP BY status
            """)
            entry_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Conflict counts
            cursor = conn.execute("""
                SELECT resolved, COUNT(*) as count 
                FROM memory_conflicts 
                GROUP BY resolved
            """)
            conflict_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Access log summary
            cursor = conn.execute("""
                SELECT operation, COUNT(*) as count, AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate
                FROM memory_access_logs 
                GROUP BY operation
            """)
            access_summary = {}
            for row in cursor.fetchall():
                access_summary[row[0]] = {
                    "count": row[1],
                    "success_rate": row[2]
                }
        
        return {
            'active_sessions': len(self.session_memory),
            'entry_counts': entry_counts,
            'conflict_counts': conflict_counts,
            'access_summary': access_summary,
            'total_access_logs': len(self.access_logs)
        }
    
    def shutdown(self):
        """Shutdown the consensus memory system"""
        self.running = False
        
        # Wait for background threads to finish
        if self.merge_worker.is_alive():
            self.merge_worker.join(timeout=5)
        if self.conflict_worker.is_alive():
            self.conflict_worker.join(timeout=5)
        if self.cleanup_worker.is_alive():
            self.cleanup_worker.join(timeout=5)
        
        logger.info("Consensus Memory shutdown complete")
