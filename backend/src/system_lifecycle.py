"""
🔄 System Build Hub OS - System Lifecycle Management

This module manages the complete lifecycle of systems from idea to deployment,
including project cataloging, build timelines, and dev chat logs.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

class SystemStage(Enum):
    IDEA = "idea"
    PLAN = "plan"
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    MAINTAIN = "maintain"

class SystemStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"

@dataclass
class SystemMetadata:
    """Metadata for a system"""
    id: str
    name: str
    description: str
    tags: List[str]
    stack: List[str]  # Technologies used
    created_at: datetime
    updated_at: datetime
    status: SystemStatus
    current_stage: SystemStage
    owner: str
    collaborators: List[str]
    estimated_complexity: int  # 1-10 scale
    actual_complexity: Optional[int] = None

@dataclass
class BuildTimeline:
    """Timeline of build events"""
    id: str
    system_id: str
    stage: SystemStage
    event_type: str
    description: str
    timestamp: datetime
    agent_id: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = None

@dataclass
class DevChatLog:
    """Development chat log entry"""
    id: str
    system_id: str
    timestamp: datetime
    speaker: str  # "user", "agent", "system"
    message: str
    context: Dict[str, Any] = None
    attachments: List[str] = None  # File paths

@dataclass
class SystemDecision:
    """Record of a decision made during system development"""
    id: str
    system_id: str
    timestamp: datetime
    decision_type: str  # "architecture", "technology", "design", "implementation"
    description: str
    rationale: str
    alternatives_considered: List[str]
    impact: str  # "low", "medium", "high"
    made_by: str  # agent_id or user_id

class SystemLifecycleManager:
    """
    Manages the complete lifecycle of systems
    """
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.systems_dir = base_dir / "systems"
        self.catalog_file = base_dir / "systems_catalog.json"
        self.systems_dir.mkdir(exist_ok=True)
        
        # Load existing catalog
        self.systems_catalog = self._load_catalog()
    
    def _load_catalog(self) -> Dict[str, SystemMetadata]:
        """Load the systems catalog from file"""
        if self.catalog_file.exists():
            try:
                with open(self.catalog_file, 'r') as f:
                    data = json.load(f)
                    catalog = {}
                    for system_id, system_data in data.items():
                        # Convert string dates back to datetime
                        system_data['created_at'] = datetime.fromisoformat(system_data['created_at'])
                        system_data['updated_at'] = datetime.fromisoformat(system_data['updated_at'])
                        system_data['status'] = SystemStatus(system_data['status'])
                        system_data['current_stage'] = SystemStage(system_data['current_stage'])
                        catalog[system_id] = SystemMetadata(**system_data)
                    return catalog
            except Exception as e:
                print(f"Error loading systems catalog: {e}")
                return {}
        return {}
    
    def _save_catalog(self):
        """Save the systems catalog to file"""
        catalog_data = {}
        for system_id, system in self.systems_catalog.items():
            system_dict = asdict(system)
            # Convert datetime to string for JSON serialization
            system_dict['created_at'] = system.created_at.isoformat()
            system_dict['updated_at'] = system.updated_at.isoformat()
            system_dict['status'] = system.status.value
            system_dict['current_stage'] = system.current_stage.value
            catalog_data[system_id] = system_dict
        
        with open(self.catalog_file, 'w') as f:
            json.dump(catalog_data, f, indent=2)
    
    def create_system(self, name: str, description: str, tags: List[str] = None,
                     stack: List[str] = None, owner: str = "default",
                     estimated_complexity: int = 5) -> str:
        """Create a new system in the catalog"""
        
        system_id = f"system-{uuid.uuid4().hex[:8]}"
        
        system = SystemMetadata(
            id=system_id,
            name=name,
            description=description,
            tags=tags or [],
            stack=stack or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=SystemStatus.DRAFT,
            current_stage=SystemStage.IDEA,
            owner=owner,
            collaborators=[],
            estimated_complexity=estimated_complexity
        )
        
        self.systems_catalog[system_id] = system
        
        # Create system directory
        system_dir = self.systems_dir / system_id
        system_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (system_dir / "builds").mkdir(exist_ok=True)
        (system_dir / "chat_logs").mkdir(exist_ok=True)
        (system_dir / "decisions").mkdir(exist_ok=True)
        (system_dir / "memory").mkdir(exist_ok=True)
        
        # Save catalog
        self._save_catalog()
        
        # Log system creation
        self.log_build_event(system_id, SystemStage.IDEA, "system_created", 
                           f"System '{name}' created", {"description": description})
        
        return system_id
    
    def update_system_stage(self, system_id: str, new_stage: SystemStage, 
                          description: str = None) -> bool:
        """Update the current stage of a system"""
        
        if system_id not in self.systems_catalog:
            return False
        
        system = self.systems_catalog[system_id]
        old_stage = system.current_stage
        system.current_stage = new_stage
        system.updated_at = datetime.now()
        
        # Update status based on stage
        if new_stage == SystemStage.DEPLOY:
            system.status = SystemStatus.ACTIVE
        elif new_stage == SystemStage.MAINTAIN:
            system.status = SystemStatus.COMPLETED
        
        # Log stage transition
        self.log_build_event(system_id, new_stage, "stage_transition",
                           f"Transitioned from {old_stage.value} to {new_stage.value}",
                           {"old_stage": old_stage.value, "new_stage": new_stage.value})
        
        self._save_catalog()
        return True
    
    def log_build_event(self, system_id: str, stage: SystemStage, event_type: str,
                       description: str, metadata: Dict[str, Any] = None,
                       agent_id: str = None, duration: float = None) -> str:
        """Log a build event to the timeline"""
        
        event_id = f"event-{uuid.uuid4().hex[:8]}"
        
        event = BuildTimeline(
            id=event_id,
            system_id=system_id,
            stage=stage,
            event_type=event_type,
            description=description,
            timestamp=datetime.now(),
            agent_id=agent_id,
            duration=duration,
            metadata=metadata or {}
        )
        
        # Save event to file
        system_dir = self.systems_dir / system_id
        events_file = system_dir / "builds" / "timeline.json"
        
        events = []
        if events_file.exists():
            try:
                with open(events_file, 'r') as f:
                    events = json.load(f)
            except:
                events = []
        
        # Convert event to dict
        event_dict = asdict(event)
        event_dict['timestamp'] = event.timestamp.isoformat()
        event_dict['stage'] = event.stage.value
        
        events.append(event_dict)
        
        with open(events_file, 'w') as f:
            json.dump(events, f, indent=2)
        
        return event_id
    
    def add_chat_log(self, system_id: str, speaker: str, message: str,
                    context: Dict[str, Any] = None, attachments: List[str] = None) -> str:
        """Add a chat log entry"""
        
        log_id = f"chat-{uuid.uuid4().hex[:8]}"
        
        chat_log = DevChatLog(
            id=log_id,
            system_id=system_id,
            timestamp=datetime.now(),
            speaker=speaker,
            message=message,
            context=context or {},
            attachments=attachments or []
        )
        
        # Save to file
        system_dir = self.systems_dir / system_id
        chat_file = system_dir / "chat_logs" / "chat.json"
        
        logs = []
        if chat_file.exists():
            try:
                with open(chat_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        log_dict = asdict(chat_log)
        log_dict['timestamp'] = chat_log.timestamp.isoformat()
        
        logs.append(log_dict)
        
        with open(chat_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        return log_id
    
    def record_decision(self, system_id: str, decision_type: str, description: str,
                       rationale: str, alternatives_considered: List[str],
                       impact: str, made_by: str) -> str:
        """Record a decision made during system development"""
        
        decision_id = f"decision-{uuid.uuid4().hex[:8]}"
        
        decision = SystemDecision(
            id=decision_id,
            system_id=system_id,
            timestamp=datetime.now(),
            decision_type=decision_type,
            description=description,
            rationale=rationale,
            alternatives_considered=alternatives_considered,
            impact=impact,
            made_by=made_by
        )
        
        # Save to file
        system_dir = self.systems_dir / system_id
        decisions_file = system_dir / "decisions" / "decisions.json"
        
        decisions = []
        if decisions_file.exists():
            try:
                with open(decisions_file, 'r') as f:
                    decisions = json.load(f)
            except:
                decisions = []
        
        decision_dict = asdict(decision)
        decision_dict['timestamp'] = decision.timestamp.isoformat()
        
        decisions.append(decision_dict)
        
        with open(decisions_file, 'w') as f:
            json.dump(decisions, f, indent=2)
        
        return decision_id
    
    def get_system_info(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a system"""
        
        if system_id not in self.systems_catalog:
            return None
        
        system = self.systems_catalog[system_id]
        system_dir = self.systems_dir / system_id
        
        # Load timeline
        timeline = []
        timeline_file = system_dir / "builds" / "timeline.json"
        if timeline_file.exists():
            try:
                with open(timeline_file, 'r') as f:
                    timeline = json.load(f)
            except:
                timeline = []
        
        # Load chat logs
        chat_logs = []
        chat_file = system_dir / "chat_logs" / "chat.json"
        if chat_file.exists():
            try:
                with open(chat_file, 'r') as f:
                    chat_logs = json.load(f)
            except:
                chat_logs = []
        
        # Load decisions
        decisions = []
        decisions_file = system_dir / "decisions" / "decisions.json"
        if decisions_file.exists():
            try:
                with open(decisions_file, 'r') as f:
                    decisions = json.load(f)
            except:
                decisions = []
        
        return {
            "metadata": asdict(system),
            "timeline": timeline,
            "chat_logs": chat_logs,
            "decisions": decisions,
            "directory": str(system_dir)
        }
    
    def list_systems(self, status: SystemStatus = None, stage: SystemStage = None,
                    tags: List[str] = None) -> List[Dict[str, Any]]:
        """List systems with optional filtering"""
        
        systems = []
        
        for system_id, system in self.systems_catalog.items():
            # Apply filters
            if status and system.status != status:
                continue
            if stage and system.current_stage != stage:
                continue
            if tags and not any(tag in system.tags for tag in tags):
                continue
            
            system_info = {
                "id": system_id,
                "name": system.name,
                "description": system.description,
                "status": system.status.value,
                "current_stage": system.current_stage.value,
                "tags": system.tags,
                "stack": system.stack,
                "created_at": system.created_at.isoformat(),
                "updated_at": system.updated_at.isoformat(),
                "owner": system.owner,
                "estimated_complexity": system.estimated_complexity
            }
            
            systems.append(system_info)
        
        # Sort by updated_at (most recent first)
        systems.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return systems
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall statistics about all systems"""
        
        total_systems = len(self.systems_catalog)
        
        # Count by status
        status_counts = {}
        for status in SystemStatus:
            status_counts[status.value] = len([s for s in self.systems_catalog.values() 
                                             if s.status == status])
        
        # Count by stage
        stage_counts = {}
        for stage in SystemStage:
            stage_counts[stage.value] = len([s for s in self.systems_catalog.values() 
                                           if s.current_stage == stage])
        
        # Count by complexity
        complexity_counts = {}
        for system in self.systems_catalog.values():
            complexity = system.estimated_complexity
            if complexity not in complexity_counts:
                complexity_counts[complexity] = 0
            complexity_counts[complexity] += 1
        
        # Most common tags
        tag_counts = {}
        for system in self.systems_catalog.values():
            for tag in system.tags:
                if tag not in tag_counts:
                    tag_counts[tag] = 0
                tag_counts[tag] += 1
        
        # Most common technologies
        tech_counts = {}
        for system in self.systems_catalog.values():
            for tech in system.stack:
                if tech not in tech_counts:
                    tech_counts[tech] = 0
                tech_counts[tech] += 1
        
        return {
            "total_systems": total_systems,
            "status_distribution": status_counts,
            "stage_distribution": stage_counts,
            "complexity_distribution": complexity_counts,
            "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_technologies": sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
