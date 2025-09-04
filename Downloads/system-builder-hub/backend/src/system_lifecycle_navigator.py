#!/usr/bin/env python3
"""
Priority 29: ORBIT - System Lifecycle Navigator
Timeline viewer and version management for system lifecycle navigation
"""

import json
import uuid
import sqlite3
import threading
import shutil
import zipfile
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import logging
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimelineViewType(Enum):
    """Types of timeline views"""
    CHRONOLOGICAL = "chronological"
    BY_EVENT_TYPE = "by_event_type"
    BY_MILESTONE = "by_milestone"
    BY_ACTOR = "by_actor"
    COMPACT = "compact"
    DETAILED = "detailed"

class VersionAction(Enum):
    """Version management actions"""
    CREATE = "create"
    ROLLBACK = "rollback"
    BRANCH = "branch"
    MERGE = "merge"
    TAG = "tag"
    ARCHIVE = "archive"
    RESTORE = "restore"

class ExportFormat(Enum):
    """Export formats for system snapshots"""
    JSON = "json"
    YAML = "yaml"
    ZIP = "zip"
    TAR = "tar"
    DOCKER = "docker"


class NavigationType(str, Enum):
    """Types of navigation"""
    TIMELINE = "timeline"
    VERSION = "version"
    COMPARISON = "comparison"
    EXPORT = "export"
    SEARCH = "search"


class NavigationStatus(str, Enum):
    """Status of navigation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NavigationResult:
    """Result of navigation operation"""
    result_id: str
    navigation_type: NavigationType
    status: NavigationStatus
    data: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class TimelineItem:
    """Represents an item in the system timeline"""
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: str
    actor_id: str
    actor_type: str
    color: str
    icon: str
    category: str = "general"
    importance: int = 1  # 1-5, higher is more important
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SystemVersion:
    """Represents a version of a system"""
    version_id: str
    system_id: str
    version: str
    timestamp: datetime
    changes_summary: str
    created_by: str
    version_data: Dict[str, Any]
    rolled_back_from: Optional[str] = None
    snapshot_label: Optional[str] = None
    is_current: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SystemComparison:
    """Represents a comparison between two system versions"""
    version_a: str
    version_b: str
    differences: Dict[str, Any]
    added_features: List[str]
    removed_features: List[str]
    modified_features: List[str]
    compatibility_score: float


class SystemLifecycleNavigator:
    """Navigates system lifecycle and timeline"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "lifecycle.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        logger.info("System Lifecycle Navigator initialized")
    
    def _init_database(self):
        """Initialize the lifecycle database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS timeline_events (
                    id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_versions (
                    version_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    changes_summary TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    version_data TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
    
    def add_timeline_event(self, system_id: str, event_type: str, title: str, 
                          description: str, actor_id: str, actor_type: str,
                          metadata: Dict[str, Any] = None) -> str:
        """Add a timeline event"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO timeline_events 
                (id, system_id, timestamp, event_type, title, description, 
                 actor_id, actor_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, system_id, timestamp.isoformat(), event_type, title,
                description, actor_id, actor_type, json.dumps(metadata or {}),
                timestamp.isoformat()
            ))
        
        logger.info(f"Added timeline event {event_id} for system {system_id}")
        return event_id
    
    def get_timeline(self, system_id: str, limit: int = 100) -> List[TimelineItem]:
        """Get timeline for a system"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, timestamp, event_type, title, description, 
                       actor_id, actor_type, metadata
                FROM timeline_events 
                WHERE system_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (system_id, limit))
            
            events = []
            for row in cursor.fetchall():
                events.append(TimelineItem(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    event_type=row[2],
                    title=row[3],
                    description=row[4],
                    actor_id=row[5],
                    actor_type=row[6],
                    color="#007bff",
                    icon="📅",
                    metadata=json.loads(row[7])
                ))
            
            return events
    migration_complexity: str

@dataclass
class SystemMilestone:
    """Represents a significant milestone in system lifecycle"""
    milestone_id: str
    system_id: str
    milestone_type: str
    title: str
    description: str
    achieved_at: datetime
    version: str
    significance: int  # 1-5, higher is more significant
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class SystemTimelineViewer:
    """Fetches and renders visual timeline of system state transitions"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "orbit.db"
        
        logger.info("System Timeline Viewer initialized")
    
    def get_timeline(self, system_id: str, view_type: TimelineViewType = TimelineViewType.CHRONOLOGICAL,
                    start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                    event_types: Optional[List[str]] = None) -> List[TimelineItem]:
        """Get timeline data for a system"""
        try:
            query = """
                SELECT le.*, s.name as system_name
                FROM lifecycle_events le
                JOIN systems s ON le.system_id = s.system_id
                WHERE le.system_id = ?
            """
            params = [system_id]
            
            if start_date:
                query += " AND le.timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND le.timestamp <= ?"
                params.append(end_date.isoformat())
            
            if event_types:
                placeholders = ",".join("?" * len(event_types))
                query += f" AND le.event_type IN ({placeholders})"
                params.extend(event_types)
            
            query += " ORDER BY le.timestamp"
            if view_type == TimelineViewType.CHRONOLOGICAL:
                query += " DESC"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                
                timeline_items = []
                for row in cursor.fetchall():
                    event_data = dict(row)
                    
                    # Parse JSON fields
                    for field in ['before_state', 'after_state', 'metadata']:
                        if event_data[field]:
                            event_data[field] = json.loads(event_data[field])
                    
                    # Create timeline item
                    item = TimelineItem(
                        id=event_data["event_id"],
                        timestamp=datetime.fromisoformat(event_data["timestamp"]),
                        event_type=event_data["event_type"],
                        title=self._get_event_title(event_data),
                        description=event_data["description"],
                        actor_id=event_data["actor_id"],
                        actor_type=event_data["actor_type"],
                        color=self._get_event_color(event_data["event_type"]),
                        icon=self._get_event_icon(event_data["event_type"]),
                        category=self._get_event_category(event_data["event_type"]),
                        importance=self._get_event_importance(event_data["event_type"]),
                        metadata=event_data.get("metadata", {})
                    )
                    timeline_items.append(item)
                
                # Apply view-specific sorting and grouping
                if view_type == TimelineViewType.BY_EVENT_TYPE:
                    timeline_items.sort(key=lambda x: (x.event_type, x.timestamp))
                elif view_type == TimelineViewType.BY_MILESTONE:
                    timeline_items = [item for item in timeline_items if item.importance >= 3]
                elif view_type == TimelineViewType.BY_ACTOR:
                    timeline_items.sort(key=lambda x: (x.actor_id, x.timestamp))
                
                return timeline_items
                
        except Exception as e:
            logger.error(f"Error getting timeline: {e}")
            return []
    
    def get_milestones(self, system_id: str) -> List[SystemMilestone]:
        """Get significant milestones for a system"""
        try:
            # Define milestone event types
            milestone_events = [
                "creation", "deployment", "version_bump", 
                "compliance_check", "self_heal", "upgrade"
            ]
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                placeholders = ",".join("?" * len(milestone_events))
                cursor = conn.execute(f"""
                    SELECT le.*, s.current_version
                    FROM lifecycle_events le
                    JOIN systems s ON le.system_id = s.system_id
                    WHERE le.system_id = ? AND le.event_type IN ({placeholders})
                    ORDER BY le.timestamp ASC
                """, [system_id] + milestone_events)
                
                milestones = []
                for row in cursor.fetchall():
                    event_data = dict(row)
                    
                    milestone = SystemMilestone(
                        milestone_id=str(uuid.uuid4()),
                        system_id=system_id,
                        milestone_type=event_data["event_type"],
                        title=self._get_milestone_title(event_data),
                        description=event_data["description"],
                        achieved_at=datetime.fromisoformat(event_data["timestamp"]),
                        version=event_data.get("current_version", "1.0.0"),
                        significance=self._get_milestone_significance(event_data["event_type"]),
                        metadata=json.loads(event_data["metadata"]) if event_data["metadata"] else {}
                    )
                    milestones.append(milestone)
                
                return milestones
                
        except Exception as e:
            logger.error(f"Error getting milestones: {e}")
            return []
    
    def get_timeline_stats(self, system_id: str) -> Dict[str, Any]:
        """Get timeline statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total events
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM lifecycle_events WHERE system_id = ?
                """, (system_id,))
                total_events = cursor.fetchone()[0]
                
                # Events by type
                cursor = conn.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM lifecycle_events 
                    WHERE system_id = ?
                    GROUP BY event_type
                    ORDER BY count DESC
                """, (system_id,))
                events_by_type = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Recent activity (last 30 days)
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM lifecycle_events 
                    WHERE system_id = ? AND timestamp >= ?
                """, (system_id, thirty_days_ago))
                recent_activity = cursor.fetchone()[0]
                
                # Most active actor
                cursor = conn.execute("""
                    SELECT actor_id, COUNT(*) as count
                    FROM lifecycle_events 
                    WHERE system_id = ?
                    GROUP BY actor_id
                    ORDER BY count DESC
                    LIMIT 1
                """, (system_id,))
                most_active_result = cursor.fetchone()
                most_active_actor = most_active_result[0] if most_active_result else None
                
                # System age
                cursor = conn.execute("""
                    SELECT created_at FROM systems WHERE system_id = ?
                """, (system_id,))
                created_at_result = cursor.fetchone()
                system_age_days = 0
                if created_at_result:
                    created_at = datetime.fromisoformat(created_at_result[0])
                    system_age_days = (datetime.now() - created_at).days
                
                return {
                    "total_events": total_events,
                    "events_by_type": events_by_type,
                    "recent_activity": recent_activity,
                    "most_active_actor": most_active_actor,
                    "system_age_days": system_age_days,
                    "last_updated": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting timeline stats: {e}")
            return {}
    
    def _get_event_title(self, event: Dict[str, Any]) -> str:
        """Generate user-friendly title for event"""
        event_type = event["event_type"]
        
        titles = {
            "creation": "System Born",
            "edit": "Modified",
            "agent_swap": "Agent Changed",
            "api_update": "API Updated",
            "compliance_check": "Compliance Verified",
            "version_bump": "Version Released",
            "deployment": "Deployed Live",
            "user_override": "Manual Override",
            "self_heal": "Auto-Healed",
            "rollback": "Version Restored",
            "snapshot": "Saved Snapshot",
            "fork": "System Forked",
            "upgrade": "Upgraded",
            "deprecation": "Deprecated",
            "decommission": "Decommissioned",
            "status_change": "Status Updated",
            "compliance_violation": "Compliance Issue",
            "performance_issue": "Performance Alert",
            "scaling_event": "Scaled"
        }
        
        return titles.get(event_type, event_type.replace("_", " ").title())
    
    def _get_event_color(self, event_type: str) -> str:
        """Get color for event type"""
        colors = {
            "creation": "#28a745",
            "edit": "#007bff",
            "agent_swap": "#6f42c1",
            "api_update": "#17a2b8",
            "compliance_check": "#ffc107",
            "version_bump": "#20c997",
            "deployment": "#28a745",
            "user_override": "#fd7e14",
            "self_heal": "#28a745",
            "rollback": "#dc3545",
            "snapshot": "#6c757d",
            "fork": "#e83e8c",
            "upgrade": "#20c997",
            "deprecation": "#ffc107",
            "decommission": "#dc3545",
            "status_change": "#17a2b8",
            "compliance_violation": "#dc3545",
            "performance_issue": "#fd7e14",
            "scaling_event": "#6f42c1"
        }
        
        return colors.get(event_type, "#6c757d")
    
    def _get_event_icon(self, event_type: str) -> str:
        """Get icon for event type"""
        icons = {
            "creation": "fas fa-star",
            "edit": "fas fa-edit",
            "agent_swap": "fas fa-exchange-alt",
            "api_update": "fas fa-plug",
            "compliance_check": "fas fa-shield-alt",
            "version_bump": "fas fa-tag",
            "deployment": "fas fa-rocket",
            "user_override": "fas fa-user-cog",
            "self_heal": "fas fa-magic",
            "rollback": "fas fa-undo",
            "snapshot": "fas fa-camera",
            "fork": "fas fa-code-branch",
            "upgrade": "fas fa-arrow-up",
            "deprecation": "fas fa-exclamation-triangle",
            "decommission": "fas fa-trash",
            "status_change": "fas fa-exchange-alt",
            "compliance_violation": "fas fa-exclamation-circle",
            "performance_issue": "fas fa-tachometer-alt",
            "scaling_event": "fas fa-expand-arrows-alt"
        }
        
        return icons.get(event_type, "fas fa-circle")
    
    def _get_event_category(self, event_type: str) -> str:
        """Get category for event type"""
        categories = {
            "creation": "lifecycle",
            "edit": "development",
            "agent_swap": "development",
            "api_update": "development",
            "compliance_check": "compliance",
            "version_bump": "lifecycle",
            "deployment": "operations",
            "user_override": "operations",
            "self_heal": "operations",
            "rollback": "operations",
            "snapshot": "maintenance",
            "fork": "development",
            "upgrade": "lifecycle",
            "deprecation": "lifecycle",
            "decommission": "lifecycle",
            "status_change": "operations",
            "compliance_violation": "compliance",
            "performance_issue": "operations",
            "scaling_event": "operations"
        }
        
        return categories.get(event_type, "general")
    
    def _get_event_importance(self, event_type: str) -> int:
        """Get importance level (1-5) for event type"""
        importance = {
            "creation": 5,
            "deployment": 5,
            "decommission": 5,
            "compliance_violation": 4,
            "self_heal": 4,
            "version_bump": 4,
            "upgrade": 4,
            "rollback": 4,
            "fork": 3,
            "deprecation": 3,
            "performance_issue": 3,
            "compliance_check": 2,
            "edit": 2,
            "agent_swap": 2,
            "api_update": 2,
            "user_override": 2,
            "status_change": 2,
            "snapshot": 1,
            "scaling_event": 1
        }
        
        return importance.get(event_type, 1)
    
    def _get_milestone_title(self, event: Dict[str, Any]) -> str:
        """Get milestone title"""
        event_type = event["event_type"]
        
        titles = {
            "creation": "System Genesis",
            "deployment": "First Deployment",
            "version_bump": "Major Release",
            "compliance_check": "Compliance Milestone",
            "self_heal": "Self-Healing Achievement",
            "upgrade": "System Evolution"
        }
        
        return titles.get(event_type, event_type.replace("_", " ").title())
    
    def _get_milestone_significance(self, event_type: str) -> int:
        """Get milestone significance (1-5)"""
        significance = {
            "creation": 5,
            "deployment": 5,
            "upgrade": 4,
            "version_bump": 3,
            "self_heal": 3,
            "compliance_check": 2
        }
        
        return significance.get(event_type, 1)

class SystemVersionManager:
    """Allows rollback, branching, snapshotting, and exporting of system versions"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "orbit.db"
        self.snapshots_dir = base_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self.db_lock = threading.Lock()
        
        logger.info("System Version Manager initialized")
    
    def create_version(self, system_id: str, version: str, changes_summary: str,
                      created_by: str, version_data: Dict[str, Any],
                      action: VersionAction = VersionAction.CREATE) -> str:
        """Create a new version of a system"""
        try:
            version_id = str(uuid.uuid4())
            
            # Validate semantic version
            if not self._is_valid_semver(version):
                logger.error(f"Invalid semantic version: {version}")
                return None
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Insert version record
                    conn.execute("""
                        INSERT INTO system_versions (
                            version_id, system_id, version, timestamp, changes_summary,
                            created_by, version_data, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        version_id, system_id, version, datetime.now().isoformat(),
                        changes_summary, created_by, json.dumps(version_data),
                        json.dumps({"action": action.value})
                    ))
                    
                    # Update system current version
                    conn.execute("""
                        UPDATE systems 
                        SET current_version = ?, updated_at = ?
                        WHERE system_id = ?
                    """, (version, datetime.now().isoformat(), system_id))
            
            logger.info(f"Created version {version} for system {system_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Error creating version: {e}")
            return None
    
    def get_version_history(self, system_id: str) -> List[SystemVersion]:
        """Get version history for a system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT sv.*, s.current_version
                    FROM system_versions sv
                    JOIN systems s ON sv.system_id = s.system_id
                    WHERE sv.system_id = ?
                    ORDER BY sv.timestamp DESC
                """, (system_id,))
                
                versions = []
                for row in cursor.fetchall():
                    version_data = dict(row)
                    
                    # Parse JSON fields
                    version_data["version_data"] = json.loads(version_data["version_data"])
                    version_data["metadata"] = json.loads(version_data["metadata"]) if version_data["metadata"] else {}
                    
                    version = SystemVersion(
                        version_id=version_data["version_id"],
                        system_id=version_data["system_id"],
                        version=version_data["version"],
                        timestamp=datetime.fromisoformat(version_data["timestamp"]),
                        changes_summary=version_data["changes_summary"],
                        created_by=version_data["created_by"],
                        version_data=version_data["version_data"],
                        rolled_back_from=version_data.get("rolled_back_from"),
                        snapshot_label=version_data.get("snapshot_label"),
                        is_current=version_data["version"] == version_data["current_version"],
                        metadata=version_data["metadata"]
                    )
                    versions.append(version)
                
                return versions
                
        except Exception as e:
            logger.error(f"Error getting version history: {e}")
            return []
    
    def rollback_to_version(self, system_id: str, target_version: str,
                           actor_id: str, reason: str = "") -> bool:
        """Rollback system to a previous version"""
        try:
            # Get target version data
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM system_versions 
                    WHERE system_id = ? AND version = ?
                """, (system_id, target_version))
                
                target_row = cursor.fetchone()
                if not target_row:
                    logger.error(f"Target version {target_version} not found")
                    return False
                
                target_data = dict(target_row)
                
                # Get current version
                cursor = conn.execute("""
                    SELECT current_version FROM systems WHERE system_id = ?
                """, (system_id,))
                current_version_row = cursor.fetchone()
                current_version = current_version_row[0] if current_version_row else "unknown"
                
                # Create rollback version
                rollback_version = self._increment_patch_version(current_version)
                rollback_version_id = str(uuid.uuid4())
                
                # Insert rollback version
                conn.execute("""
                    INSERT INTO system_versions (
                        version_id, system_id, version, timestamp, changes_summary,
                        rolled_back_from, created_by, version_data, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rollback_version_id, system_id, rollback_version,
                    datetime.now().isoformat(),
                    f"Rollback to version {target_version}. {reason}".strip(),
                    current_version, actor_id, target_data["version_data"],
                    json.dumps({"action": "rollback", "reason": reason})
                ))
                
                # Update system current version
                conn.execute("""
                    UPDATE systems 
                    SET current_version = ?, updated_at = ?
                    WHERE system_id = ?
                """, (rollback_version, datetime.now().isoformat(), system_id))
            
            logger.info(f"Rolled back system {system_id} to version {target_version}")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back system: {e}")
            return False
    
    def create_snapshot(self, system_id: str, label: str, description: str,
                       created_by: str, include_data: bool = True) -> str:
        """Create a snapshot of the current system state"""
        try:
            snapshot_id = str(uuid.uuid4())
            
            # Get current system data
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM systems WHERE system_id = ?
                """, (system_id,))
                
                system_row = cursor.fetchone()
                if not system_row:
                    logger.error(f"System {system_id} not found")
                    return None
                
                system_data = dict(system_row)
                
                # Get latest version data if requested
                snapshot_data = {
                    "system": system_data,
                    "timestamp": datetime.now().isoformat(),
                    "created_by": created_by
                }
                
                if include_data:
                    # Get version history
                    cursor = conn.execute("""
                        SELECT * FROM system_versions 
                        WHERE system_id = ?
                        ORDER BY timestamp DESC
                    """, (system_id,))
                    
                    versions = [dict(row) for row in cursor.fetchall()]
                    snapshot_data["versions"] = versions
                    
                    # Get lifecycle events
                    cursor = conn.execute("""
                        SELECT * FROM lifecycle_events 
                        WHERE system_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 100
                    """, (system_id,))
                    
                    events = [dict(row) for row in cursor.fetchall()]
                    snapshot_data["events"] = events
                
                # Save snapshot file
                snapshot_file = self.snapshots_dir / f"{snapshot_id}.json"
                with open(snapshot_file, 'w') as f:
                    json.dump(snapshot_data, f, indent=2, default=str)
                
                # Insert snapshot record
                conn.execute("""
                    INSERT INTO system_snapshots (
                        snapshot_id, system_id, version, label, description,
                        snapshot_data, created_by, created_at, file_path, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot_id, system_id, system_data["current_version"],
                    label, description, json.dumps({"file_path": str(snapshot_file)}),
                    created_by, datetime.now().isoformat(), str(snapshot_file),
                    json.dumps({"include_data": include_data})
                ))
            
            logger.info(f"Created snapshot {snapshot_id} for system {system_id}")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")
            return None
    
    def export_system(self, system_id: str, export_format: ExportFormat,
                     include_history: bool = True) -> Optional[str]:
        """Export system in specified format"""
        try:
            # Create a comprehensive snapshot first
            snapshot_id = self.create_snapshot(
                system_id=system_id,
                label=f"Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="System export",
                created_by="system",
                include_data=include_history
            )
            
            if not snapshot_id:
                return None
            
            snapshot_file = self.snapshots_dir / f"{snapshot_id}.json"
            
            if export_format == ExportFormat.JSON:
                return str(snapshot_file)
            
            elif export_format == ExportFormat.ZIP:
                zip_file = self.snapshots_dir / f"{system_id}_export_{snapshot_id}.zip"
                with zipfile.ZipFile(zip_file, 'w') as zf:
                    zf.write(snapshot_file, f"{system_id}.json")
                return str(zip_file)
            
            elif export_format == ExportFormat.YAML:
                import yaml
                yaml_file = self.snapshots_dir / f"{system_id}_export_{snapshot_id}.yaml"
                
                with open(snapshot_file, 'r') as jf:
                    data = json.load(jf)
                
                with open(yaml_file, 'w') as yf:
                    yaml.dump(data, yf, default_flow_style=False)
                
                return str(yaml_file)
            
            else:
                logger.warning(f"Export format {export_format.value} not yet implemented")
                return str(snapshot_file)
                
        except Exception as e:
            logger.error(f"Error exporting system: {e}")
            return None
    
    def compare_versions(self, system_id: str, version_a: str, version_b: str) -> SystemComparison:
        """Compare two versions of a system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get version A data
                cursor = conn.execute("""
                    SELECT version_data FROM system_versions 
                    WHERE system_id = ? AND version = ?
                """, (system_id, version_a))
                
                version_a_row = cursor.fetchone()
                if not version_a_row:
                    raise ValueError(f"Version {version_a} not found")
                
                version_a_data = json.loads(version_a_row[0])
                
                # Get version B data
                cursor = conn.execute("""
                    SELECT version_data FROM system_versions 
                    WHERE system_id = ? AND version = ?
                """, (system_id, version_b))
                
                version_b_row = cursor.fetchone()
                if not version_b_row:
                    raise ValueError(f"Version {version_b} not found")
                
                version_b_data = json.loads(version_b_row[0])
                
                # Perform comparison
                differences = self._calculate_differences(version_a_data, version_b_data)
                added_features = self._get_added_features(version_a_data, version_b_data)
                removed_features = self._get_removed_features(version_a_data, version_b_data)
                modified_features = self._get_modified_features(version_a_data, version_b_data)
                
                # Calculate compatibility score (0-1)
                compatibility_score = self._calculate_compatibility_score(
                    added_features, removed_features, modified_features
                )
                
                # Determine migration complexity
                migration_complexity = self._determine_migration_complexity(
                    compatibility_score, len(removed_features), len(modified_features)
                )
                
                return SystemComparison(
                    version_a=version_a,
                    version_b=version_b,
                    differences=differences,
                    added_features=added_features,
                    removed_features=removed_features,
                    modified_features=modified_features,
                    compatibility_score=compatibility_score,
                    migration_complexity=migration_complexity
                )
                
        except Exception as e:
            logger.error(f"Error comparing versions: {e}")
            return None
    
    def get_snapshots(self, system_id: str) -> List[Dict[str, Any]]:
        """Get all snapshots for a system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM system_snapshots 
                    WHERE system_id = ?
                    ORDER BY created_at DESC
                """, (system_id,))
                
                snapshots = []
                for row in cursor.fetchall():
                    snapshot_data = dict(row)
                    # Parse JSON fields
                    snapshot_data["snapshot_data"] = json.loads(snapshot_data["snapshot_data"])
                    snapshot_data["metadata"] = json.loads(snapshot_data["metadata"]) if snapshot_data["metadata"] else {}
                    snapshots.append(snapshot_data)
                
                return snapshots
                
        except Exception as e:
            logger.error(f"Error getting snapshots: {e}")
            return []
    
    def _is_valid_semver(self, version: str) -> bool:
        """Check if version is valid semantic version"""
        try:
            semver.VersionInfo.parse(version)
            return True
        except ValueError:
            return False
    
    def _increment_patch_version(self, version: str) -> str:
        """Increment patch version"""
        try:
            ver = semver.VersionInfo.parse(version)
            return str(ver.bump_patch())
        except ValueError:
            # Fallback for invalid semver
            parts = version.split('.')
            if len(parts) >= 3:
                try:
                    patch = int(parts[2]) + 1
                    return f"{parts[0]}.{parts[1]}.{patch}"
                except ValueError:
                    pass
            return f"{version}.1"
    
    def _calculate_differences(self, data_a: Dict[str, Any], data_b: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate differences between two data structures"""
        differences = {}
        
        # Simple difference calculation - can be enhanced with more sophisticated diffing
        all_keys = set(data_a.keys()) | set(data_b.keys())
        
        for key in all_keys:
            if key not in data_a:
                differences[key] = {"status": "added", "new_value": data_b[key]}
            elif key not in data_b:
                differences[key] = {"status": "removed", "old_value": data_a[key]}
            elif data_a[key] != data_b[key]:
                differences[key] = {
                    "status": "modified",
                    "old_value": data_a[key],
                    "new_value": data_b[key]
                }
        
        return differences
    
    def _get_added_features(self, data_a: Dict[str, Any], data_b: Dict[str, Any]) -> List[str]:
        """Get features added in version B"""
        return [key for key in data_b.keys() if key not in data_a]
    
    def _get_removed_features(self, data_a: Dict[str, Any], data_b: Dict[str, Any]) -> List[str]:
        """Get features removed in version B"""
        return [key for key in data_a.keys() if key not in data_b]
    
    def _get_modified_features(self, data_a: Dict[str, Any], data_b: Dict[str, Any]) -> List[str]:
        """Get features modified in version B"""
        return [key for key in data_a.keys() if key in data_b and data_a[key] != data_b[key]]
    
    def _calculate_compatibility_score(self, added: List[str], removed: List[str], modified: List[str]) -> float:
        """Calculate compatibility score between versions"""
        total_changes = len(added) + len(removed) + len(modified)
        if total_changes == 0:
            return 1.0
        
        # Removals are more impactful than additions or modifications
        impact_score = len(removed) * 0.7 + len(modified) * 0.5 + len(added) * 0.2
        
        # Normalize to 0-1 scale (assuming max 20 significant changes)
        normalized_impact = min(impact_score / 20, 1.0)
        
        return max(0.0, 1.0 - normalized_impact)
    
    def _determine_migration_complexity(self, compatibility_score: float, 
                                      removed_count: int, modified_count: int) -> str:
        """Determine migration complexity based on changes"""
        if compatibility_score >= 0.9 and removed_count == 0:
            return "minimal"
        elif compatibility_score >= 0.7 and removed_count <= 2:
            return "low"
        elif compatibility_score >= 0.5 and removed_count <= 5:
            return "medium"
        elif compatibility_score >= 0.3:
            return "high"
        else:
            return "very_high"

# Main navigator that coordinates timeline and version management
class LifecycleNavigator:
    """Main navigator for system lifecycle management"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        
        # Initialize components
        self.timeline_viewer = SystemTimelineViewer(base_dir)
        self.version_manager = SystemVersionManager(base_dir)
        
        logger.info("Lifecycle Navigator initialized")
    
    def get_full_system_lifecycle(self, system_id: str) -> Dict[str, Any]:
        """Get comprehensive lifecycle data for a system"""
        timeline = self.timeline_viewer.get_timeline(system_id)
        milestones = self.timeline_viewer.get_milestones(system_id)
        timeline_stats = self.timeline_viewer.get_timeline_stats(system_id)
        version_history = self.version_manager.get_version_history(system_id)
        snapshots = self.version_manager.get_snapshots(system_id)
        
        return {
            "timeline": [asdict(item) for item in timeline],
            "milestones": [asdict(milestone) for milestone in milestones],
            "timeline_stats": timeline_stats,
            "version_history": [asdict(version) for version in version_history],
            "snapshots": snapshots,
            "last_updated": datetime.now().isoformat()
        }
    
    def perform_system_action(self, system_id: str, action: str, 
                             actor_id: str, **kwargs) -> Dict[str, Any]:
        """Perform a system lifecycle action"""
        try:
            if action == "rollback":
                target_version = kwargs.get("target_version")
                reason = kwargs.get("reason", "")
                success = self.version_manager.rollback_to_version(
                    system_id, target_version, actor_id, reason
                )
                return {"success": success, "action": "rollback", "target_version": target_version}
            
            elif action == "snapshot":
                label = kwargs.get("label", f"Snapshot {datetime.now().strftime('%Y%m%d_%H%M%S')}")
                description = kwargs.get("description", "Manual snapshot")
                snapshot_id = self.version_manager.create_snapshot(
                    system_id, label, description, actor_id
                )
                return {"success": bool(snapshot_id), "action": "snapshot", "snapshot_id": snapshot_id}
            
            elif action == "export":
                export_format = kwargs.get("format", ExportFormat.JSON)
                include_history = kwargs.get("include_history", True)
                file_path = self.version_manager.export_system(
                    system_id, export_format, include_history
                )
                return {"success": bool(file_path), "action": "export", "file_path": file_path}
            
            elif action == "compare":
                version_a = kwargs.get("version_a")
                version_b = kwargs.get("version_b")
                comparison = self.version_manager.compare_versions(system_id, version_a, version_b)
                return {
                    "success": bool(comparison), 
                    "action": "compare", 
                    "comparison": asdict(comparison) if comparison else None
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Error performing system action {action}: {e}")
            return {"success": False, "error": str(e)}
