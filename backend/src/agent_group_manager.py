"""
Priority 25: Agent Group Manager

This module manages agent working groups, role assignments,
quorum rules, and fallback agents for multi-agent planning.
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
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoleType(Enum):
    """Types of roles agents can have in groups"""
    LEADER = "leader"
    PLANNER = "planner"
    EXECUTOR = "executor"
    OBSERVER = "observer"
    VALIDATOR = "validator"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    BACKUP = "backup"

class GroupStatus(Enum):
    """Status of agent groups"""
    FORMING = "forming"
    ACTIVE = "active"
    PAUSED = "paused"
    DISBANDED = "disbanded"
    ARCHIVED = "archived"

class QuorumType(Enum):
    """Types of quorum rules"""
    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    MINIMUM = "minimum"
    WEIGHTED = "weighted"
    LEADER_PLUS_ONE = "leader_plus_one"


class GroupType(str, Enum):
    """Types of agent groups"""
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    COORDINATION = "coordination"
    SPECIALIZED = "specialized"
    EMERGENCY = "emergency"


@dataclass
class GroupMember:
    """Represents a member of an agent group"""
    member_id: str
    group_id: str
    agent_id: str
    role: RoleType
    joined_at: datetime
    status: str  # active, inactive, removed
    permissions: List[str]
    metadata: Dict[str, Any]

@dataclass
class AgentGroup:
    """Represents an agent working group"""
    group_id: str
    name: str
    description: str
    purpose: str
    agents: Dict[str, RoleType]  # agent_id -> role
    leader_agent: str
    quorum_type: QuorumType
    quorum_threshold: float  # 0.0 to 1.0
    min_agents: int
    max_agents: int
    created_at: datetime
    updated_at: datetime
    status: GroupStatus
    metadata: Dict[str, Any]
    performance_metrics: Dict[str, float]

@dataclass
class AgentCapability:
    """Represents an agent's capabilities"""
    agent_id: str
    roles: List[RoleType]
    specializations: List[str]
    performance_score: float  # 0.0 to 1.0
    availability: float  # 0.0 to 1.0
    trust_level: float  # 0.0 to 1.0
    last_seen: datetime
    metadata: Dict[str, Any]

@dataclass
class GroupAssignment:
    """Represents an agent's assignment to a group"""
    assignment_id: str
    group_id: str
    agent_id: str
    role: RoleType
    assigned_at: datetime
    assigned_by: str
    status: str  # active, inactive, removed
    performance_rating: Optional[float]
    notes: Optional[str]

class AgentGroupManager:
    """
    Agent Group Manager
    
    Manages agent working groups, role assignments, quorum rules,
    and fallback agents for multi-agent planning.
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
        self.db_path = base_dir / "data" / "agent_groups.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Group state
        self.active_groups: Dict[str, AgentGroup] = {}
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self.group_assignments: Dict[str, List[GroupAssignment]] = defaultdict(list)
        
        # Background processing
        self.running = True
        self.monitoring_worker = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.optimization_worker = threading.Thread(target=self._optimization_worker, daemon=True)
        self.cleanup_worker = threading.Thread(target=self._cleanup_worker, daemon=True)
        
        # Start background threads
        self.monitoring_worker.start()
        self.optimization_worker.start()
        self.cleanup_worker.start()
        
        logger.info("Agent Group Manager initialized")
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_groups (
                    group_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    agents TEXT NOT NULL,
                    leader_agent TEXT NOT NULL,
                    quorum_type TEXT NOT NULL,
                    quorum_threshold REAL NOT NULL,
                    min_agents INTEGER NOT NULL,
                    max_agents INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_capabilities (
                    agent_id TEXT PRIMARY KEY,
                    roles TEXT NOT NULL,
                    specializations TEXT NOT NULL,
                    performance_score REAL NOT NULL,
                    availability REAL NOT NULL,
                    trust_level REAL NOT NULL,
                    last_seen TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS group_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    assigned_by TEXT NOT NULL,
                    status TEXT NOT NULL,
                    performance_rating REAL,
                    notes TEXT,
                    FOREIGN KEY (group_id) REFERENCES agent_groups (group_id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_status ON agent_groups(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_leader ON agent_groups(leader_agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_group ON group_assignments(group_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_agent ON group_assignments(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_status ON group_assignments(status)")
            
            conn.commit()
    
    def create_agent_group(self, name: str, description: str, purpose: str,
                          leader_agent: str, agents: Dict[str, RoleType],
                          quorum_type: QuorumType = QuorumType.MAJORITY,
                          quorum_threshold: float = 0.5, min_agents: int = 2,
                          max_agents: int = 10, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new agent working group"""
        group_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Validate agents
        if leader_agent not in agents:
            agents[leader_agent] = RoleType.LEADER
        
        if len(agents) < min_agents:
            raise ValueError(f"Group must have at least {min_agents} agents")
        
        if len(agents) > max_agents:
            raise ValueError(f"Group cannot have more than {max_agents} agents")
        
        # Create group
        group = AgentGroup(
            group_id=group_id,
            name=name,
            description=description,
            purpose=purpose,
            agents=agents,
            leader_agent=leader_agent,
            quorum_type=quorum_type,
            quorum_threshold=quorum_threshold,
            min_agents=min_agents,
            max_agents=max_agents,
            created_at=timestamp,
            updated_at=timestamp,
            status=GroupStatus.FORMING,
            metadata=metadata or {},
            performance_metrics={}
        )
        
        # Store group
        self._store_group(group)
        
        # Create assignments
        for agent_id, role in agents.items():
            assignment = GroupAssignment(
                assignment_id=str(uuid.uuid4()),
                group_id=group_id,
                agent_id=agent_id,
                role=role,
                assigned_at=timestamp,
                assigned_by=leader_agent,
                status="active",
                performance_rating=None,
                notes=f"Initial assignment to {name}"
            )
            self._store_assignment(assignment)
            self.group_assignments[group_id].append(assignment)
        
        # Add to active groups
        self.active_groups[group_id] = group
        
        # Notify agents
        self._notify_group_creation(group)
        
        # Log to black box inspector
        if self.black_box_inspector:
            self.black_box_inspector.log_trace_event(
                trace_type="agent_group_created",
                component_id=f"group-{group_id}",
                payload={
                    "group_id": group_id,
                    "name": name,
                    "leader_agent": leader_agent,
                    "agent_count": len(agents),
                    "quorum_type": quorum_type.value,
                    "quorum_threshold": quorum_threshold
                },
                metadata={
                    "purpose": purpose,
                    "agents": {agent_id: role.value for agent_id, role in agents.items()}
                }
            )
        
        logger.info(f"Created agent group {group_id} with {len(agents)} agents")
        return group_id
    
    def _store_group(self, group: AgentGroup):
        """Store an agent group in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agent_groups 
                (group_id, name, description, purpose, agents, leader_agent,
                 quorum_type, quorum_threshold, min_agents, max_agents,
                 created_at, updated_at, status, metadata, performance_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                group.group_id,
                group.name,
                group.description,
                group.purpose,
                json.dumps({agent_id: role.value for agent_id, role in group.agents.items()}),
                group.leader_agent,
                group.quorum_type.value,
                group.quorum_threshold,
                group.min_agents,
                group.max_agents,
                group.created_at.isoformat(),
                group.updated_at.isoformat(),
                group.status.value,
                json.dumps(group.metadata),
                json.dumps(group.performance_metrics)
            ))
            conn.commit()
    
    def _store_assignment(self, assignment: GroupAssignment):
        """Store a group assignment in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO group_assignments 
                (assignment_id, group_id, agent_id, role, assigned_at, assigned_by,
                 status, performance_rating, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.assignment_id,
                assignment.group_id,
                assignment.agent_id,
                assignment.role.value,
                assignment.assigned_at.isoformat(),
                assignment.assigned_by,
                assignment.status,
                assignment.performance_rating,
                assignment.notes
            ))
            conn.commit()
    
    def _notify_group_creation(self, group: AgentGroup):
        """Notify agents about group creation"""
        if not self.agent_messaging_layer:
            return
        
        for agent_id, role in group.agents.items():
            if agent_id != group.leader_agent:
                try:
                    self.agent_messaging_layer.send_message(
                        sender_id=group.leader_agent,
                        receiver_id=agent_id,
                        message_type=self.agent_messaging_layer.MessageType.COORDINATION,
                        content=f"You have been assigned to group '{group.name}' as {role.value}",
                        priority=self.agent_messaging_layer.MessagePriority.HIGH,
                        metadata={
                            "group_id": group.group_id,
                            "action": "group_assignment",
                            "role": role.value,
                            "purpose": group.purpose,
                            "quorum_type": group.quorum_type.value
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to notify agent {agent_id}: {e}")
    
    def add_agent_to_group(self, group_id: str, agent_id: str, role: RoleType,
                          assigned_by: str, notes: Optional[str] = None) -> bool:
        """Add an agent to an existing group"""
        if group_id not in self.active_groups:
            raise ValueError(f"Group {group_id} not found")
        
        group = self.active_groups[group_id]
        
        # Check if group is full
        if len(group.agents) >= group.max_agents:
            raise ValueError(f"Group {group_id} is at maximum capacity")
        
        # Check if agent is already in group
        if agent_id in group.agents:
            raise ValueError(f"Agent {agent_id} is already in group {group_id}")
        
        # Add agent to group
        group.agents[agent_id] = role
        group.updated_at = datetime.now()
        self._update_group(group)
        
        # Create assignment
        assignment = GroupAssignment(
            assignment_id=str(uuid.uuid4()),
            group_id=group_id,
            agent_id=agent_id,
            role=role,
            assigned_at=datetime.now(),
            assigned_by=assigned_by,
            status="active",
            performance_rating=None,
            notes=notes or f"Added to {group.name}"
        )
        self._store_assignment(assignment)
        self.group_assignments[group_id].append(assignment)
        
        # Notify agent
        self._notify_agent_addition(group, agent_id, role)
        
        logger.info(f"Added agent {agent_id} to group {group_id} as {role.value}")
        return True
    
    def remove_agent_from_group(self, group_id: str, agent_id: str, 
                               removed_by: str, reason: Optional[str] = None) -> bool:
        """Remove an agent from a group"""
        if group_id not in self.active_groups:
            raise ValueError(f"Group {group_id} not found")
        
        group = self.active_groups[group_id]
        
        # Check if agent is in group
        if agent_id not in group.agents:
            raise ValueError(f"Agent {agent_id} is not in group {group_id}")
        
        # Check if removing leader
        if agent_id == group.leader_agent:
            raise ValueError("Cannot remove the group leader")
        
        # Check minimum agents requirement
        if len(group.agents) <= group.min_agents:
            raise ValueError(f"Cannot remove agent: group must have at least {group.min_agents} agents")
        
        # Remove agent from group
        del group.agents[agent_id]
        group.updated_at = datetime.now()
        self._update_group(group)
        
        # Update assignment status
        for assignment in self.group_assignments[group_id]:
            if assignment.agent_id == agent_id:
                assignment.status = "removed"
                assignment.notes = reason or "Removed from group"
                self._update_assignment(assignment)
                break
        
        # Notify agent
        self._notify_agent_removal(group, agent_id, reason)
        
        logger.info(f"Removed agent {agent_id} from group {group_id}")
        return True
    
    def update_agent_role(self, group_id: str, agent_id: str, new_role: RoleType,
                         updated_by: str, reason: Optional[str] = None) -> bool:
        """Update an agent's role in a group"""
        if group_id not in self.active_groups:
            raise ValueError(f"Group {group_id} not found")
        
        group = self.active_groups[group_id]
        
        # Check if agent is in group
        if agent_id not in group.agents:
            raise ValueError(f"Agent {agent_id} is not in group {group_id}")
        
        # Check if trying to change leader
        if agent_id == group.leader_agent and new_role != RoleType.LEADER:
            raise ValueError("Cannot change the group leader's role")
        
        # Update role
        old_role = group.agents[agent_id]
        group.agents[agent_id] = new_role
        group.updated_at = datetime.now()
        self._update_group(group)
        
        # Update assignment
        for assignment in self.group_assignments[group_id]:
            if assignment.agent_id == agent_id:
                assignment.role = new_role
                assignment.notes = f"Role changed from {old_role.value} to {new_role.value}: {reason or 'No reason provided'}"
                self._update_assignment(assignment)
                break
        
        # Notify agent
        self._notify_role_change(group, agent_id, old_role, new_role, reason)
        
        logger.info(f"Updated agent {agent_id} role from {old_role.value} to {new_role.value} in group {group_id}")
        return True
    
    def check_quorum(self, group_id: str, present_agents: List[str]) -> bool:
        """Check if a group has quorum with the given present agents"""
        if group_id not in self.active_groups:
            return False
        
        group = self.active_groups[group_id]
        total_agents = len(group.agents)
        present_count = len(present_agents)
        
        if group.quorum_type == QuorumType.MAJORITY:
            return present_count > total_agents / 2
        
        elif group.quorum_type == QuorumType.UNANIMOUS:
            return present_count == total_agents
        
        elif group.quorum_type == QuorumType.MINIMUM:
            return present_count >= group.min_agents
        
        elif group.quorum_type == QuorumType.WEIGHTED:
            # Calculate weighted presence based on agent capabilities
            total_weight = 0
            present_weight = 0
            
            for agent_id in group.agents:
                capability = self.agent_capabilities.get(agent_id)
                weight = capability.performance_score if capability else 0.5
                total_weight += weight
                
                if agent_id in present_agents:
                    present_weight += weight
            
            return present_weight / total_weight >= group.quorum_threshold
        
        elif group.quorum_type == QuorumType.LEADER_PLUS_ONE:
            return group.leader_agent in present_agents and present_count >= 2
        
        return False
    
    def get_fallback_agents(self, group_id: str, unavailable_agents: List[str]) -> List[str]:
        """Get fallback agents for a group when some agents are unavailable"""
        if group_id not in self.active_groups:
            return []
        
        group = self.active_groups[group_id]
        available_agents = [agent_id for agent_id in group.agents if agent_id not in unavailable_agents]
        
        # Check if we still have quorum
        if self.check_quorum(group_id, available_agents):
            return available_agents
        
        # Find backup agents
        backup_agents = []
        for agent_id, role in group.agents.items():
            if role == RoleType.BACKUP and agent_id not in unavailable_agents:
                backup_agents.append(agent_id)
        
        # If we have backup agents, check quorum with them
        if backup_agents:
            all_available = available_agents + backup_agents
            if self.check_quorum(group_id, all_available):
                return all_available
        
        # If still no quorum, try to find replacement agents
        replacement_agents = self._find_replacement_agents(group, unavailable_agents)
        
        return available_agents + replacement_agents
    
    def _find_replacement_agents(self, group: AgentGroup, unavailable_agents: List[str]) -> List[str]:
        """Find replacement agents for unavailable ones"""
        replacements = []
        
        # Find agents with similar capabilities
        for agent_id, role in group.agents.items():
            if agent_id in unavailable_agents:
                # Look for agents with the same role
                for capability_id, capability in self.agent_capabilities.items():
                    if (capability_id not in group.agents and 
                        role in capability.roles and 
                        capability.availability > 0.7):
                        replacements.append(capability_id)
                        break
        
        return replacements
    
    def register_agent_capability(self, agent_id: str, roles: List[RoleType],
                                specializations: List[str], performance_score: float = 0.5,
                                availability: float = 1.0, trust_level: float = 0.5,
                                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register an agent's capabilities"""
        capability = AgentCapability(
            agent_id=agent_id,
            roles=roles,
            specializations=specializations,
            performance_score=max(0.0, min(1.0, performance_score)),
            availability=max(0.0, min(1.0, availability)),
            trust_level=max(0.0, min(1.0, trust_level)),
            last_seen=datetime.now(),
            metadata=metadata or {}
        )
        
        # Store capability
        self._store_capability(capability)
        
        # Add to in-memory capabilities
        self.agent_capabilities[agent_id] = capability
        
        logger.info(f"Registered capabilities for agent {agent_id}")
        return True
    
    def _store_capability(self, capability: AgentCapability):
        """Store agent capability in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_capabilities 
                (agent_id, roles, specializations, performance_score, availability,
                 trust_level, last_seen, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                capability.agent_id,
                json.dumps([role.value for role in capability.roles]),
                json.dumps(capability.specializations),
                capability.performance_score,
                capability.availability,
                capability.trust_level,
                capability.last_seen.isoformat(),
                json.dumps(capability.metadata)
            ))
            conn.commit()
    
    def get_group_info(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a group"""
        if group_id not in self.active_groups:
            return None
        
        group = self.active_groups[group_id]
        assignments = self.group_assignments[group_id]
        
        return {
            "group_id": group.group_id,
            "name": group.name,
            "description": group.description,
            "purpose": group.purpose,
            "leader_agent": group.leader_agent,
            "quorum_type": group.quorum_type.value,
            "quorum_threshold": group.quorum_threshold,
            "min_agents": group.min_agents,
            "max_agents": group.max_agents,
            "status": group.status.value,
            "created_at": group.created_at.isoformat(),
            "updated_at": group.updated_at.isoformat(),
            "agents": [
                {
                    "agent_id": agent_id,
                    "role": role.value,
                    "assignment": next((a for a in assignments if a.agent_id == agent_id), None)
                }
                for agent_id, role in group.agents.items()
            ],
            "performance_metrics": group.performance_metrics
        }
    
    def get_agent_groups(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all groups an agent belongs to"""
        groups = []
        
        for group in self.active_groups.values():
            if agent_id in group.agents:
                group_info = self.get_group_info(group.group_id)
                if group_info:
                    groups.append(group_info)
        
        return groups
    
    def _update_group(self, group: AgentGroup):
        """Update a group in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE agent_groups 
                SET agents = ?, updated_at = ?, status = ?, performance_metrics = ?
                WHERE group_id = ?
            """, (
                json.dumps({agent_id: role.value for agent_id, role in group.agents.items()}),
                group.updated_at.isoformat(),
                group.status.value,
                json.dumps(group.performance_metrics),
                group.group_id
            ))
            conn.commit()
    
    def _update_assignment(self, assignment: GroupAssignment):
        """Update a group assignment in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE group_assignments 
                SET role = ?, status = ?, performance_rating = ?, notes = ?
                WHERE assignment_id = ?
            """, (
                assignment.role.value,
                assignment.status,
                assignment.performance_rating,
                assignment.notes,
                assignment.assignment_id
            ))
            conn.commit()
    
    def _notify_agent_addition(self, group: AgentGroup, agent_id: str, role: RoleType):
        """Notify agent about addition to group"""
        if not self.agent_messaging_layer:
            return
        
        try:
            self.agent_messaging_layer.send_message(
                sender_id=group.leader_agent,
                receiver_id=agent_id,
                message_type=self.agent_messaging_layer.MessageType.COORDINATION,
                content=f"You have been added to group '{group.name}' as {role.value}",
                priority=self.agent_messaging_layer.MessagePriority.HIGH,
                metadata={
                    "group_id": group.group_id,
                    "action": "agent_added",
                    "role": role.value,
                    "purpose": group.purpose
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify agent {agent_id}: {e}")
    
    def _notify_agent_removal(self, group: AgentGroup, agent_id: str, reason: Optional[str]):
        """Notify agent about removal from group"""
        if not self.agent_messaging_layer:
            return
        
        try:
            self.agent_messaging_layer.send_message(
                sender_id=group.leader_agent,
                receiver_id=agent_id,
                message_type=self.agent_messaging_layer.MessageType.STATUS_UPDATE,
                content=f"You have been removed from group '{group.name}'. Reason: {reason or 'No reason provided'}",
                priority=self.agent_messaging_layer.MessagePriority.NORMAL,
                metadata={
                    "group_id": group.group_id,
                    "action": "agent_removed",
                    "reason": reason
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify agent {agent_id}: {e}")
    
    def _notify_role_change(self, group: AgentGroup, agent_id: str, old_role: RoleType, 
                           new_role: RoleType, reason: Optional[str]):
        """Notify agent about role change"""
        if not self.agent_messaging_layer:
            return
        
        try:
            self.agent_messaging_layer.send_message(
                sender_id=group.leader_agent,
                receiver_id=agent_id,
                message_type=self.agent_messaging_layer.MessageType.STATUS_UPDATE,
                content=f"Your role in group '{group.name}' has changed from {old_role.value} to {new_role.value}",
                priority=self.agent_messaging_layer.MessagePriority.NORMAL,
                metadata={
                    "group_id": group.group_id,
                    "action": "role_changed",
                    "old_role": old_role.value,
                    "new_role": new_role.value,
                    "reason": reason
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify agent {agent_id}: {e}")
    
    def _monitoring_worker(self):
        """Background worker for monitoring group health"""
        while self.running:
            try:
                # Monitor group health and performance
                for group_id, group in list(self.active_groups.items()):
                    self._update_group_metrics(group)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Monitoring worker error: {e}")
                time.sleep(120)  # Wait 2 minutes on error
    
    def _optimization_worker(self):
        """Background worker for group optimization"""
        while self.running:
            try:
                # Optimize group compositions
                for group_id, group in list(self.active_groups.items()):
                    self._optimize_group_composition(group)
                
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Optimization worker error: {e}")
                time.sleep(600)  # Wait 10 minutes on error
    
    def _cleanup_worker(self):
        """Background worker for cleaning up inactive groups"""
        while self.running:
            try:
                # Clean up inactive groups
                cutoff_time = datetime.now() - timedelta(days=7)
                
                for group_id, group in list(self.active_groups.items()):
                    if group.updated_at < cutoff_time and group.status == GroupStatus.PAUSED:
                        group.status = GroupStatus.ARCHIVED
                        self._update_group(group)
                        logger.info(f"Archived inactive group {group_id}")
                
                time.sleep(3600)  # Run cleanup every hour
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _update_group_metrics(self, group: AgentGroup):
        """Update performance metrics for a group"""
        # Calculate group performance based on agent capabilities
        total_performance = 0
        total_availability = 0
        agent_count = len(group.agents)
        
        for agent_id in group.agents:
            capability = self.agent_capabilities.get(agent_id)
            if capability:
                total_performance += capability.performance_score
                total_availability += capability.availability
        
        if agent_count > 0:
            avg_performance = total_performance / agent_count
            avg_availability = total_availability / agent_count
            
            group.performance_metrics.update({
                "avg_performance": avg_performance,
                "avg_availability": avg_availability,
                "agent_count": agent_count,
                "last_updated": datetime.now().isoformat()
            })
            
            self._update_group(group)
    
    def _optimize_group_composition(self, group: AgentGroup):
        """Optimize group composition based on performance"""
        # Simple optimization - can be enhanced with more sophisticated algorithms
        # For now, just update metrics
        self._update_group_metrics(group)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Group counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM agent_groups 
                GROUP BY status
            """)
            group_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Assignment counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM group_assignments 
                GROUP BY status
            """)
            assignment_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Agent capability summary
            cursor = conn.execute("""
                SELECT AVG(performance_score) as avg_performance, 
                       AVG(availability) as avg_availability,
                       AVG(trust_level) as avg_trust,
                       COUNT(*) as total_agents
                FROM agent_capabilities
            """)
            capability_summary = cursor.fetchone()
        
        return {
            'active_groups': len(self.active_groups),
            'group_counts': group_counts,
            'assignment_counts': assignment_counts,
            'capability_summary': {
                'avg_performance': capability_summary[0] if capability_summary[0] else 0,
                'avg_availability': capability_summary[1] if capability_summary[1] else 0,
                'avg_trust': capability_summary[2] if capability_summary[2] else 0,
                'total_agents': capability_summary[3] if capability_summary[3] else 0
            },
            'total_capabilities': len(self.agent_capabilities)
        }
    
    def shutdown(self):
        """Shutdown the agent group manager"""
        self.running = False
        
        # Wait for background threads to finish
        if self.monitoring_worker.is_alive():
            self.monitoring_worker.join(timeout=5)
        if self.optimization_worker.is_alive():
            self.optimization_worker.join(timeout=5)
        if self.cleanup_worker.is_alive():
            self.cleanup_worker.join(timeout=5)
        
        logger.info("Agent Group Manager shutdown complete")
