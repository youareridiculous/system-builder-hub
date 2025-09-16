#!/usr/bin/env python3
"""
Priority 29: ORBIT - System Genesis + Lifecycle Navigator
System Genesis Manager for tracking system creation and lifecycle events
"""

import json
import uuid
import sqlite3
import threading
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

class SystemDomain(Enum):
    """System domain categories"""
    AI_AUTOMATION = "ai_automation"
    DATA_PROCESSING = "data_processing"
    WEB_APPLICATION = "web_application"
    API_SERVICE = "api_service"
    ANALYTICS = "analytics"
    ECOMMERCE = "ecommerce"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    PRODUCTIVITY = "productivity"
    CUSTOM = "custom"

class ArchitectureType(Enum):
    """System architecture types"""
    MONOLITHIC = "monolithic"
    MICROSERVICES = "microservices"
    SERVERLESS = "serverless"
    EVENT_DRIVEN = "event_driven"
    AI_NATIVE = "ai_native"
    HYBRID = "hybrid"
    DISTRIBUTED = "distributed"
    PIPELINE = "pipeline"

class SystemStatus(Enum):
    """System lifecycle status"""
    PROTOTYPE = "prototype"
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DECOMMISSIONED = "decommissioned"

class LifecycleEventType(Enum):
    """Types of lifecycle events"""
    CREATION = "creation"
    EDIT = "edit"
    AGENT_SWAP = "agent_swap"
    API_UPDATE = "api_update"
    COMPLIANCE_CHECK = "compliance_check"
    VERSION_BUMP = "version_bump"
    DEPLOYMENT = "deployment"
    USER_OVERRIDE = "user_override"
    SELF_HEAL = "self_heal"
    ROLLBACK = "rollback"
    SNAPSHOT = "snapshot"
    FORK = "fork"
    UPGRADE = "upgrade"
    DEPRECATION = "deprecation"
    DECOMMISSION = "decommission"
    STATUS_CHANGE = "status_change"
    COMPLIANCE_VIOLATION = "compliance_violation"
    PERFORMANCE_ISSUE = "performance_issue"
    SCALING_EVENT = "scaling_event"


class GenesisType(str, Enum):
    """Types of system genesis"""
    NEW = "new"
    FORK = "fork"
    TEMPLATE = "template"
    MIGRATION = "migration"
    UPGRADE = "upgrade"


class GenesisStatus(str, Enum):
    """Status of genesis process"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenesisResult:
    """Result of genesis process"""
    result_id: str
    system_id: str
    genesis_type: GenesisType
    status: GenesisStatus
    system_config: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class SystemGenesis:
    """Represents the birth/creation of a system"""
    system_id: str
    creator_id: str
    creator_name: str
    name: str
    description: str
    domain: SystemDomain
    architecture: ArchitectureType
    original_prompt: str
    expanded_context: Optional[Dict[str, Any]]
    compliance_report: Optional[Dict[str, Any]]
    cost_estimate: Optional[Dict[str, Any]]
    trust_score: float
    created_at: datetime
    initial_version: str = "1.0.0"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class LifecycleEvent:
    """Represents a lifecycle event for a system"""
    event_id: str
    system_id: str
    event_type: LifecycleEventType
    timestamp: datetime
    actor_id: str  # User or system that triggered the event
    actor_type: str  # "user", "system", "agent"
    description: str
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    trace_id: Optional[str] = None
    related_event_id: Optional[str] = None

@dataclass
class SystemSnapshot:
    """Represents a system snapshot"""
    snapshot_id: str
    system_id: str
    version: str
    label: str
    description: str
    snapshot_data: Dict[str, Any]
    created_by: str
    created_at: datetime
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class SystemGenesisManager:
    """Handles system creation metadata and genesis tracking"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "orbit.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self.db_lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info("System Genesis Manager initialized")
    
    def _init_database(self):
        """Initialize the ORBIT database"""
        with sqlite3.connect(self.db_path) as conn:
            # Systems table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS systems (
                    system_id TEXT PRIMARY KEY,
                    creator_id TEXT NOT NULL,
                    creator_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    original_prompt TEXT NOT NULL,
                    expanded_context TEXT,
                    compliance_report TEXT,
                    cost_estimate TEXT,
                    trust_score REAL NOT NULL DEFAULT 0.0,
                    current_version TEXT NOT NULL DEFAULT '1.0.0',
                    status TEXT NOT NULL DEFAULT 'prototype',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    active BOOLEAN NOT NULL DEFAULT 1
                )
            """)
            
            # System versions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_versions (
                    version_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    changes_summary TEXT NOT NULL,
                    rolled_back_from TEXT,
                    snapshot_label TEXT,
                    created_by TEXT NOT NULL,
                    version_data TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (system_id) REFERENCES systems(system_id)
                )
            """)
            
            # Lifecycle events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lifecycle_events (
                    event_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    before_state TEXT,
                    after_state TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    trace_id TEXT,
                    related_event_id TEXT,
                    FOREIGN KEY (system_id) REFERENCES systems(system_id)
                )
            """)
            
            # System snapshots table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    label TEXT NOT NULL,
                    description TEXT NOT NULL,
                    snapshot_data TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    file_path TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (system_id) REFERENCES systems(system_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_systems_creator ON systems(creator_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_systems_domain ON systems(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_systems_status ON systems(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_systems_created ON systems(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_system ON system_versions(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_system ON lifecycle_events(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON lifecycle_events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON lifecycle_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_system ON system_snapshots(system_id)")
    
    def create_system(self, genesis: SystemGenesis) -> bool:
        """Register a new system's birth"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Insert system record
                    conn.execute("""
                        INSERT INTO systems (
                            system_id, creator_id, creator_name, name, description,
                            domain, architecture, original_prompt, expanded_context,
                            compliance_report, cost_estimate, trust_score, current_version,
                            status, created_at, updated_at, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        genesis.system_id, genesis.creator_id, genesis.creator_name,
                        genesis.name, genesis.description, genesis.domain.value,
                        genesis.architecture.value, genesis.original_prompt,
                        json.dumps(genesis.expanded_context) if genesis.expanded_context else None,
                        json.dumps(genesis.compliance_report) if genesis.compliance_report else None,
                        json.dumps(genesis.cost_estimate) if genesis.cost_estimate else None,
                        genesis.trust_score, genesis.initial_version,
                        SystemStatus.PROTOTYPE.value, genesis.created_at.isoformat(),
                        genesis.created_at.isoformat(), json.dumps(genesis.metadata)
                    ))
                    
                    # Create initial version record
                    version_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO system_versions (
                            version_id, system_id, version, timestamp, changes_summary,
                            created_by, version_data, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        version_id, genesis.system_id, genesis.initial_version,
                        genesis.created_at.isoformat(), "Initial system creation",
                        genesis.creator_id, json.dumps(asdict(genesis)),
                        json.dumps({"is_initial": True})
                    ))
            
            logger.info(f"System {genesis.system_id} ({genesis.name}) created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating system {genesis.system_id}: {e}")
            return False
    
    def get_system(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get system information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM systems WHERE system_id = ?
                """, (system_id,))
                
                row = cursor.fetchone()
                if row:
                    system_data = dict(row)
                    # Parse JSON fields
                    for field in ['expanded_context', 'compliance_report', 'cost_estimate', 'metadata']:
                        if system_data[field]:
                            system_data[field] = json.loads(system_data[field])
                    return system_data
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting system {system_id}: {e}")
            return None
    
    def list_systems(self, creator_id: Optional[str] = None, 
                    domain: Optional[SystemDomain] = None,
                    status: Optional[SystemStatus] = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """List systems with optional filtering"""
        try:
            query = "SELECT * FROM systems WHERE active = 1"
            params = []
            
            if creator_id:
                query += " AND creator_id = ?"
                params.append(creator_id)
            
            if domain:
                query += " AND domain = ?"
                params.append(domain.value)
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                
                systems = []
                for row in cursor.fetchall():
                    system_data = dict(row)
                    # Parse JSON fields
                    for field in ['expanded_context', 'compliance_report', 'cost_estimate', 'metadata']:
                        if system_data[field]:
                            system_data[field] = json.loads(system_data[field])
                    systems.append(system_data)
                
                return systems
                
        except Exception as e:
            logger.error(f"Error listing systems: {e}")
            return []
    
    def update_system_status(self, system_id: str, new_status: SystemStatus,
                           actor_id: str, reason: str = "") -> bool:
        """Update system status and log the change"""
        try:
            # Get current system state
            current_system = self.get_system(system_id)
            if not current_system:
                logger.error(f"System {system_id} not found")
                return False
            
            old_status = current_system['status']
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Update system status
                    conn.execute("""
                        UPDATE systems 
                        SET status = ?, updated_at = ?
                        WHERE system_id = ?
                    """, (new_status.value, datetime.now().isoformat(), system_id))
            
            # Log the lifecycle event
            event = LifecycleEvent(
                event_id=str(uuid.uuid4()),
                system_id=system_id,
                event_type=LifecycleEventType.STATUS_CHANGE,
                timestamp=datetime.now(),
                actor_id=actor_id,
                actor_type="user",
                description=f"Status changed from {old_status} to {new_status.value}. {reason}".strip(),
                before_state={"status": old_status},
                after_state={"status": new_status.value},
                metadata={"reason": reason}
            )
            
            # Use lifecycle event logger to record this
            return True
            
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
            return False
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system creation statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total systems
                cursor = conn.execute("SELECT COUNT(*) FROM systems WHERE active = 1")
                total_systems = cursor.fetchone()[0]
                
                # Systems by domain
                cursor = conn.execute("""
                    SELECT domain, COUNT(*) as count 
                    FROM systems WHERE active = 1 
                    GROUP BY domain
                """)
                by_domain = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Systems by status
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM systems WHERE active = 1 
                    GROUP BY status
                """)
                by_status = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Systems by architecture
                cursor = conn.execute("""
                    SELECT architecture, COUNT(*) as count 
                    FROM systems WHERE active = 1 
                    GROUP BY architecture
                """)
                by_architecture = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Recent activity (last 7 days)
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM systems 
                    WHERE active = 1 AND created_at >= ?
                """, (week_ago,))
                recent_systems = cursor.fetchone()[0]
                
                return {
                    "total_systems": total_systems,
                    "by_domain": by_domain,
                    "by_status": by_status,
                    "by_architecture": by_architecture,
                    "recent_activity": recent_systems,
                    "last_updated": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}

class LifecycleEventLogger:
    """Logs and manages system lifecycle events"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "orbit.db"
        
        # Thread lock for database operations
        self.db_lock = threading.Lock()
        
        logger.info("Lifecycle Event Logger initialized")
    
    def log_event(self, event: LifecycleEvent) -> bool:
        """Log a lifecycle event"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO lifecycle_events (
                            event_id, system_id, event_type, timestamp, actor_id, actor_type,
                            description, before_state, after_state, metadata, trace_id, related_event_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id, event.system_id, event.event_type.value,
                        event.timestamp.isoformat(), event.actor_id, event.actor_type,
                        event.description,
                        json.dumps(event.before_state) if event.before_state else None,
                        json.dumps(event.after_state) if event.after_state else None,
                        json.dumps(event.metadata), event.trace_id, event.related_event_id
                    ))
            
            logger.info(f"Logged event {event.event_type.value} for system {event.system_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging lifecycle event: {e}")
            return False
    
    def get_system_events(self, system_id: str, event_types: Optional[List[LifecycleEventType]] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get lifecycle events for a system"""
        try:
            query = "SELECT * FROM lifecycle_events WHERE system_id = ?"
            params = [system_id]
            
            if event_types:
                placeholders = ",".join("?" * len(event_types))
                query += f" AND event_type IN ({placeholders})"
                params.extend([et.value for et in event_types])
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                
                events = []
                for row in cursor.fetchall():
                    event_data = dict(row)
                    # Parse JSON fields
                    for field in ['before_state', 'after_state', 'metadata']:
                        if event_data[field]:
                            event_data[field] = json.loads(event_data[field])
                    events.append(event_data)
                
                return events
                
        except Exception as e:
            logger.error(f"Error getting system events: {e}")
            return []
    
    def get_event_timeline(self, system_id: str) -> List[Dict[str, Any]]:
        """Get timeline data for visualization"""
        events = self.get_system_events(system_id)
        
        timeline = []
        for event in events:
            timeline_item = {
                "id": event["event_id"],
                "type": event["event_type"],
                "timestamp": event["timestamp"],
                "title": self._get_event_title(event),
                "description": event["description"],
                "actor": event["actor_id"],
                "actor_type": event["actor_type"],
                "color": self._get_event_color(event["event_type"]),
                "icon": self._get_event_icon(event["event_type"]),
                "metadata": event.get("metadata", {})
            }
            timeline.append(timeline_item)
        
        return timeline
    
    def _get_event_title(self, event: Dict[str, Any]) -> str:
        """Generate a user-friendly title for an event"""
        event_type = event["event_type"]
        
        titles = {
            "creation": "System Created",
            "edit": "System Edited",
            "agent_swap": "Agent Swapped",
            "api_update": "API Updated",
            "compliance_check": "Compliance Check",
            "version_bump": "Version Updated",
            "deployment": "Deployed",
            "user_override": "User Override",
            "self_heal": "Self-Healed",
            "rollback": "Rolled Back",
            "snapshot": "Snapshot Created",
            "fork": "System Forked",
            "upgrade": "System Upgraded",
            "deprecation": "Deprecated",
            "decommission": "Decommissioned",
            "status_change": "Status Changed",
            "compliance_violation": "Compliance Violation",
            "performance_issue": "Performance Issue",
            "scaling_event": "Scaling Event"
        }
        
        return titles.get(event_type, event_type.replace("_", " ").title())
    
    def _get_event_color(self, event_type: str) -> str:
        """Get color for event type"""
        colors = {
            "creation": "#28a745",  # Green
            "edit": "#007bff",      # Blue
            "agent_swap": "#6f42c1", # Purple
            "api_update": "#17a2b8", # Teal
            "compliance_check": "#ffc107", # Yellow
            "version_bump": "#20c997", # Turquoise
            "deployment": "#28a745",  # Green
            "user_override": "#fd7e14", # Orange
            "self_heal": "#28a745",   # Green
            "rollback": "#dc3545",    # Red
            "snapshot": "#6c757d",    # Gray
            "fork": "#e83e8c",        # Pink
            "upgrade": "#20c997",     # Turquoise
            "deprecation": "#ffc107", # Yellow
            "decommission": "#dc3545", # Red
            "status_change": "#17a2b8", # Teal
            "compliance_violation": "#dc3545", # Red
            "performance_issue": "#fd7e14", # Orange
            "scaling_event": "#6f42c1"  # Purple
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
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent activity across all systems"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT le.*, s.name as system_name, s.creator_name
                    FROM lifecycle_events le
                    JOIN systems s ON le.system_id = s.system_id
                    WHERE s.active = 1
                    ORDER BY le.timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                activities = []
                for row in cursor.fetchall():
                    activity = dict(row)
                    # Parse JSON fields
                    for field in ['before_state', 'after_state', 'metadata']:
                        if activity[field]:
                            activity[field] = json.loads(activity[field])
                    
                    # Add display information
                    activity["title"] = self._get_event_title(activity)
                    activity["color"] = self._get_event_color(activity["event_type"])
                    activity["icon"] = self._get_event_icon(activity["event_type"])
                    
                    activities.append(activity)
                
                return activities
                
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    def log_system_creation(self, system_id: str, creator_id: str, system_name: str,
                           original_prompt: str, metadata: Dict[str, Any] = None) -> bool:
        """Convenience method to log system creation"""
        event = LifecycleEvent(
            event_id=str(uuid.uuid4()),
            system_id=system_id,
            event_type=LifecycleEventType.CREATION,
            timestamp=datetime.now(),
            actor_id=creator_id,
            actor_type="user",
            description=f"System '{system_name}' created",
            before_state=None,
            after_state={"status": SystemStatus.PROTOTYPE.value},
            metadata={
                "original_prompt": original_prompt,
                **(metadata or {})
            }
        )
        
        return self.log_event(event)
    
    def log_compliance_check(self, system_id: str, actor_id: str, 
                            compliance_result: Dict[str, Any]) -> bool:
        """Log compliance check event"""
        passed = compliance_result.get("status") == "passed"
        
        event = LifecycleEvent(
            event_id=str(uuid.uuid4()),
            system_id=system_id,
            event_type=LifecycleEventType.COMPLIANCE_CHECK,
            timestamp=datetime.now(),
            actor_id=actor_id,
            actor_type="system",
            description=f"Compliance check {'passed' if passed else 'failed'}",
            before_state=None,
            after_state={"compliance_status": "passed" if passed else "failed"},
            metadata=compliance_result
        )
        
        return self.log_event(event)
    
    def log_self_heal_event(self, system_id: str, issue_type: str, 
                           resolution: str, metadata: Dict[str, Any] = None) -> bool:
        """Log self-healing event"""
        event = LifecycleEvent(
            event_id=str(uuid.uuid4()),
            system_id=system_id,
            event_type=LifecycleEventType.SELF_HEAL,
            timestamp=datetime.now(),
            actor_id="system",
            actor_type="system",
            description=f"Self-healed: {issue_type} - {resolution}",
            before_state={"issue": issue_type},
            after_state={"resolution": resolution},
            metadata={
                "issue_type": issue_type,
                "resolution": resolution,
                **(metadata or {})
            }
        )
        
        return self.log_event(event)

# Main ORBIT manager that coordinates all components
class OrbitManager:
    """Main manager for the ORBIT system lifecycle navigation"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        
        # Initialize components
        self.genesis_manager = SystemGenesisManager(base_dir)
        self.event_logger = LifecycleEventLogger(base_dir)
        
        logger.info("ORBIT Manager initialized")
    
    def create_system_with_logging(self, genesis: SystemGenesis) -> bool:
        """Create system and log the creation event"""
        success = self.genesis_manager.create_system(genesis)
        
        if success:
            # Log the creation event
            self.event_logger.log_system_creation(
                system_id=genesis.system_id,
                creator_id=genesis.creator_id,
                system_name=genesis.name,
                original_prompt=genesis.original_prompt,
                metadata={
                    "domain": genesis.domain.value,
                    "architecture": genesis.architecture.value,
                    "trust_score": genesis.trust_score
                }
            )
        
        return success
    
    def get_system_orbit_data(self, system_id: str) -> Dict[str, Any]:
        """Get comprehensive orbit data for a system"""
        system_data = self.genesis_manager.get_system(system_id)
        if not system_data:
            return {}
        
        timeline = self.event_logger.get_event_timeline(system_id)
        events = self.event_logger.get_system_events(system_id)
        
        return {
            "system": system_data,
            "timeline": timeline,
            "events": events,
            "event_count": len(events),
            "last_activity": events[0]["timestamp"] if events else None
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for the ORBIT dashboard"""
        statistics = self.genesis_manager.get_system_statistics()
        recent_activity = self.event_logger.get_recent_activity()
        recent_systems = self.genesis_manager.list_systems(limit=10)
        
        return {
            "statistics": statistics,
            "recent_activity": recent_activity,
            "recent_systems": recent_systems,
            "timestamp": datetime.now().isoformat()
        }
