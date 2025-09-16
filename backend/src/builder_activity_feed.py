#!/usr/bin/env python3
"""
Builder Activity Feed Module - Priority 22
Timeline tracking of all key system events with filtering and real-time capabilities
"""

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActivityType(Enum):
    """Types of activities tracked"""
    PROMPT_RUN = "prompt_run"
    CODE_CHANGE = "code_change"
    COMPONENT_CREATE = "component_create"
    COMPONENT_DELETE = "component_delete"
    SYSTEM_STATE_CHANGE = "system_state_change"
    AGENT_ACTION = "agent_action"
    LLM_CALL = "llm_call"
    API_REQUEST = "api_request"
    UI_UPDATE = "ui_update"
    BUILD_START = "build_start"
    BUILD_COMPLETE = "build_complete"
    BUILD_FAIL = "build_fail"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ActorType(Enum):
    """Types of actors that can perform activities"""
    USER = "user"
    SUPPORT_AGENT = "support_agent"
    AUTOMATION = "automation"
    AI_COMPONENT = "ai_component"
    SYSTEM = "system"
    AGENT = "agent"
    LLM = "llm"

class SeverityLevel(Enum):
    """Activity severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ActivityEvent:
    """Individual activity event"""
    event_id: str
    timestamp: datetime
    activity_type: ActivityType
    actor_type: ActorType
    actor_id: str
    system_id: Optional[str]
    component_id: Optional[str]
    description: str
    details: Dict[str, Any]
    severity: SeverityLevel
    metadata: Dict[str, Any]

@dataclass
class ActivityFilter:
    """Filter criteria for activity feed"""
    activity_types: Optional[List[ActivityType]] = None
    actor_types: Optional[List[ActorType]] = None
    system_id: Optional[str] = None
    component_id: Optional[str] = None
    severity_levels: Optional[List[SeverityLevel]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0

@dataclass
class ActivitySummary:
    """Summary statistics for activity feed"""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_actor: Dict[str, int]
    events_by_severity: Dict[str, int]
    recent_activity: List[ActivityEvent]

class BuilderActivityFeed:
    """
    Builder Activity Feed providing timeline tracking of all system events
    """
    
    def __init__(self, base_dir: Path, memory_system, agent_orchestrator, 
                 system_lifecycle, access_control):
        self.base_dir = base_dir
        self.memory_system = memory_system
        self.agent_orchestrator = agent_orchestrator
        self.system_lifecycle = system_lifecycle
        self.access_control = access_control
        
        # Database setup
        self.db_path = base_dir / "data" / "activity_feed.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # Real-time streaming
        self.subscribers = {}
        self.streaming_active = True
        self.stream_thread = threading.Thread(target=self._stream_activities, daemon=True)
        self.stream_thread.start()
        
        # Activity cache for performance
        self.activity_cache = {}
        self.cache_size = 1000
        
        logger.info("Builder Activity Feed initialized")
    
    def _init_database(self):
        """Initialize activity feed database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    activity_type TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    system_id TEXT,
                    component_id TEXT,
                    description TEXT NOT NULL,
                    details TEXT,
                    severity TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON activity_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_events(activity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actor_type ON activity_events(actor_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_id ON activity_events(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON activity_events(severity)")
            
            conn.commit()
    
    def log_activity(self, activity_type: ActivityType, actor_type: ActorType, 
                    actor_id: str, description: str, system_id: Optional[str] = None,
                    component_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
                    severity: SeverityLevel = SeverityLevel.INFO, 
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log a new activity event"""
        try:
            event_id = f"event_{uuid.uuid4().hex[:8]}"
            timestamp = datetime.now()
            
            event = ActivityEvent(
                event_id=event_id,
                timestamp=timestamp,
                activity_type=activity_type,
                actor_type=actor_type,
                actor_id=actor_id,
                system_id=system_id,
                component_id=component_id,
                description=description,
                details=details or {},
                severity=severity,
                metadata=metadata or {}
            )
            
            # Store in database
            self._store_event(event)
            
            # Add to cache
            self._add_to_cache(event)
            
            # Notify subscribers
            self._notify_subscribers(event)
            
            logger.info(f"Activity logged: {activity_type.value} by {actor_type.value} - {description}")
            
            return event_id
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return ""
    
    def _store_event(self, event: ActivityEvent):
        """Store event in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO activity_events 
                    (event_id, timestamp, activity_type, actor_type, actor_id, system_id,
                     component_id, description, details, severity, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id, event.timestamp.isoformat(), event.activity_type.value,
                    event.actor_type.value, event.actor_id, event.system_id, event.component_id,
                    event.description, json.dumps(event.details), event.severity.value,
                    json.dumps(event.metadata)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing event: {e}")
    
    def _add_to_cache(self, event: ActivityEvent):
        """Add event to cache"""
        try:
            self.activity_cache[event.event_id] = event
            
            # Maintain cache size
            if len(self.activity_cache) > self.cache_size:
                # Remove oldest events
                oldest_events = sorted(self.activity_cache.items(), 
                                     key=lambda x: x[1].timestamp)[:100]
                for event_id, _ in oldest_events:
                    del self.activity_cache[event_id]
        except Exception as e:
            logger.error(f"Error adding to cache: {e}")
    
    def get_activities(self, filter_criteria: Optional[ActivityFilter] = None) -> List[ActivityEvent]:
        """Get activities with optional filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM activity_events WHERE 1=1"
                params = []
                
                if filter_criteria:
                    if filter_criteria.activity_types:
                        placeholders = ','.join(['?' for _ in filter_criteria.activity_types])
                        query += f" AND activity_type IN ({placeholders})"
                        params.extend([t.value for t in filter_criteria.activity_types])
                    
                    if filter_criteria.actor_types:
                        placeholders = ','.join(['?' for _ in filter_criteria.actor_types])
                        query += f" AND actor_type IN ({placeholders})"
                        params.extend([t.value for t in filter_criteria.actor_types])
                    
                    if filter_criteria.system_id:
                        query += " AND system_id = ?"
                        params.append(filter_criteria.system_id)
                    
                    if filter_criteria.component_id:
                        query += " AND component_id = ?"
                        params.append(filter_criteria.component_id)
                    
                    if filter_criteria.severity_levels:
                        placeholders = ','.join(['?' for _ in filter_criteria.severity_levels])
                        query += f" AND severity IN ({placeholders})"
                        params.extend([s.value for s in filter_criteria.severity_levels])
                    
                    if filter_criteria.start_time:
                        query += " AND timestamp >= ?"
                        params.append(filter_criteria.start_time.isoformat())
                    
                    if filter_criteria.end_time:
                        query += " AND timestamp <= ?"
                        params.append(filter_criteria.end_time.isoformat())
                
                query += " ORDER BY timestamp DESC"
                
                if filter_criteria:
                    query += f" LIMIT {filter_criteria.limit} OFFSET {filter_criteria.offset}"
                else:
                    query += " LIMIT 100"
                
                cursor = conn.execute(query, params)
                
                events = []
                for row in cursor.fetchall():
                    event = ActivityEvent(
                        event_id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        activity_type=ActivityType(row[2]),
                        actor_type=ActorType(row[3]),
                        actor_id=row[4],
                        system_id=row[5],
                        component_id=row[6],
                        description=row[7],
                        details=json.loads(row[8]) if row[8] else {},
                        severity=SeverityLevel(row[9]),
                        metadata=json.loads(row[10]) if row[10] else {}
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Error getting activities: {e}")
            return []
    
    def get_activity_summary(self, system_id: Optional[str] = None, 
                           hours: int = 24) -> ActivitySummary:
        """Get activity summary statistics"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            filter_criteria = ActivityFilter(
                start_time=start_time,
                end_time=end_time,
                system_id=system_id,
                limit=1000
            )
            
            events = self.get_activities(filter_criteria)
            
            # Calculate statistics
            events_by_type = {}
            events_by_actor = {}
            events_by_severity = {}
            
            for event in events:
                # Count by type
                event_type = event.activity_type.value
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                
                # Count by actor
                actor_type = event.actor_type.value
                events_by_actor[actor_type] = events_by_actor.get(actor_type, 0) + 1
                
                # Count by severity
                severity = event.severity.value
                events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
            
            # Get recent activity (last 10 events)
            recent_activity = events[:10]
            
            return ActivitySummary(
                total_events=len(events),
                events_by_type=events_by_type,
                events_by_actor=events_by_actor,
                events_by_severity=events_by_severity,
                recent_activity=recent_activity
            )
            
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            return ActivitySummary(
                total_events=0,
                events_by_type={},
                events_by_actor={},
                events_by_severity={},
                recent_activity=[]
            )
    
    def subscribe_to_activities(self, subscriber_id: str, callback_func):
        """Subscribe to real-time activity updates"""
        try:
            self.subscribers[subscriber_id] = callback_func
            logger.info(f"Subscriber {subscriber_id} added to activity feed")
        except Exception as e:
            logger.error(f"Error adding subscriber: {e}")
    
    def unsubscribe_from_activities(self, subscriber_id: str):
        """Unsubscribe from real-time activity updates"""
        try:
            if subscriber_id in self.subscribers:
                del self.subscribers[subscriber_id]
                logger.info(f"Subscriber {subscriber_id} removed from activity feed")
        except Exception as e:
            logger.error(f"Error removing subscriber: {e}")
    
    def _notify_subscribers(self, event: ActivityEvent):
        """Notify all subscribers of new activity"""
        try:
            for subscriber_id, callback in self.subscribers.items():
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error notifying subscriber {subscriber_id}: {e}")
        except Exception as e:
            logger.error(f"Error notifying subscribers: {e}")
    
    def _stream_activities(self):
        """Background thread for real-time activity streaming"""
        while self.streaming_active:
            try:
                # Check for new activities and notify subscribers
                # This could be enhanced with WebSocket support for real-time streaming
                time.sleep(1)  # Check every second
            except Exception as e:
                logger.error(f"Error in activity streaming: {e}")
                time.sleep(5)  # Wait 5 seconds on error
    
    def get_system_activities(self, system_id: str, limit: int = 100) -> List[ActivityEvent]:
        """Get activities for a specific system"""
        filter_criteria = ActivityFilter(
            system_id=system_id,
            limit=limit
        )
        return self.get_activities(filter_criteria)
    
    def get_component_activities(self, component_id: str, limit: int = 100) -> List[ActivityEvent]:
        """Get activities for a specific component"""
        filter_criteria = ActivityFilter(
            component_id=component_id,
            limit=limit
        )
        return self.get_activities(filter_criteria)
    
    def get_user_activities(self, user_id: str, limit: int = 100) -> List[ActivityEvent]:
        """Get activities by a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM activity_events 
                    WHERE actor_id = ? AND actor_type = 'user'
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (user_id, limit))
                
                events = []
                for row in cursor.fetchall():
                    event = ActivityEvent(
                        event_id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        activity_type=ActivityType(row[2]),
                        actor_type=ActorType(row[3]),
                        actor_id=row[4],
                        system_id=row[5],
                        component_id=row[6],
                        description=row[7],
                        details=json.loads(row[8]) if row[8] else {},
                        severity=SeverityLevel(row[9]),
                        metadata=json.loads(row[10]) if row[10] else {}
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []
    
    def search_activities(self, search_term: str, limit: int = 100) -> List[ActivityEvent]:
        """Search activities by description"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM activity_events 
                    WHERE description LIKE ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (f"%{search_term}%", limit))
                
                events = []
                for row in cursor.fetchall():
                    event = ActivityEvent(
                        event_id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        activity_type=ActivityType(row[2]),
                        actor_type=ActorType(row[3]),
                        actor_id=row[4],
                        system_id=row[5],
                        component_id=row[6],
                        description=row[7],
                        details=json.loads(row[8]) if row[8] else {},
                        severity=SeverityLevel(row[9]),
                        metadata=json.loads(row[10]) if row[10] else {}
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Error searching activities: {e}")
            return []
    
    def cleanup_old_activities(self, days: int = 30):
        """Clean up old activity data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM activity_events WHERE timestamp < ?", 
                           (cutoff_date.isoformat(),))
                conn.commit()
                
            logger.info(f"Cleaned up activities older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old activities: {e}")
    
    def export_activities(self, filter_criteria: Optional[ActivityFilter] = None, 
                         format_type: str = "json") -> str:
        """Export activities to file"""
        try:
            events = self.get_activities(filter_criteria)
            
            if format_type == "json":
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "total_events": len(events),
                    "events": [asdict(event) for event in events]
                }
                
                export_path = self.base_dir / "exports" / f"activity_export_{int(time.time())}.json"
                export_path.parent.mkdir(exist_ok=True)
                
                with open(export_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                return str(export_path)
            
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            logger.error(f"Error exporting activities: {e}")
            return ""
    
    def stop_streaming(self):
        """Stop real-time activity streaming"""
        self.streaming_active = False
        if self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
