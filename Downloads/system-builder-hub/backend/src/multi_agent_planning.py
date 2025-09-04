"""
Priority 25: Multi-Agent Planning & Negotiation Protocol (MAPNP)

This module implements the core orchestration logic for multi-agent planning,
including planning sessions, milestone generation, subgoal negotiation, and task resolution.
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
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlanningStatus(Enum):
    """Status of planning sessions"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    NEGOTIATING = "negotiating"
    ARBITRATING = "arbitrating"
    CONSENSUS_REACHED = "consensus_reached"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ArbitrationStrategy(Enum):
    """Strategies for resolving conflicts"""
    MAJORITY_VOTE = "majority_vote"
    TRUST_WEIGHTED = "trust_weighted"
    PERFORMANCE_BASED = "performance_based"
    ROUND_ROBIN = "round_robin"
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"
    AUTOMATIC = "automatic"

class ConsensusLevel(Enum):
    """Levels of consensus required"""
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    SUPER_MAJORITY = "super_majority"
    QUORUM = "quorum"
    LEADER_DECISION = "leader_decision"

class AgentTrustLevel(Enum):
    """Trust levels for agents"""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class PlanningType(str, Enum):
    """Types of planning"""
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"
    EMERGENCY = "emergency"
    CONTINUOUS = "continuous"


@dataclass
class PlanResult:
    """Result of a planning operation"""
    plan_id: str
    session_id: str
    plan_type: PlanningType
    status: str
    tasks: List[Dict[str, Any]]
    timeline: Dict[str, Any]
    resources: List[str]
    risks: List[Dict[str, Any]]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class PlanningSession:
    """Represents a multi-agent planning session"""
    session_id: str
    name: str
    description: str
    goal: str
    participants: List[str]
    leader_agent: str
    status: PlanningStatus
    created_at: datetime
    updated_at: datetime
    deadline: Optional[datetime]
    consensus_level: ConsensusLevel
    arbitration_strategy: ArbitrationStrategy
    metadata: Dict[str, Any]
    milestones: List[Dict[str, Any]]
    current_milestone: Optional[str] = None

@dataclass
class GoalProposal:
    """Represents a goal or task proposal"""
    proposal_id: str
    session_id: str
    proposer_agent: str
    goal_description: str
    priority: int
    estimated_duration: int  # minutes
    required_resources: List[str]
    dependencies: List[str]
    success_criteria: List[str]
    risk_assessment: Dict[str, Any]
    created_at: datetime
    status: str  # pending, accepted, rejected, modified
    votes: Dict[str, str]  # agent_id -> vote (approve/reject/modify)
    comments: List[Dict[str, Any]]


class MultiAgentPlanner:
    """Multi-agent planning and negotiation orchestrator"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "system_builder_hub.db"
        self.sessions: Dict[str, PlanningSession] = {}
        self.active_negotiations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_session(self, name: str, description: str, goal: str, 
                      participants: List[str], leader_agent: str,
                      consensus_level: ConsensusLevel = ConsensusLevel.MAJORITY,
                      arbitration_strategy: ArbitrationStrategy = ArbitrationStrategy.TRUST_WEIGHTED,
                      deadline: Optional[datetime] = None) -> str:
        """Create a new planning session"""
        session_id = str(uuid.uuid4())
        session = PlanningSession(
            session_id=session_id,
            name=name,
            description=description,
            goal=goal,
            participants=participants,
            leader_agent=leader_agent,
            status=PlanningStatus.INITIALIZING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deadline=deadline,
            consensus_level=consensus_level,
            arbitration_strategy=arbitration_strategy,
            metadata={},
            milestones=[],
            current_milestone=None
        )
        
        with self._lock:
            self.sessions[session_id] = session
        
        logger.info(f"Created planning session {session_id}: {name}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[PlanningSession]:
        """Get a planning session by ID"""
        return self.sessions.get(session_id)
    
    def update_session_status(self, session_id: str, status: PlanningStatus) -> bool:
        """Update session status"""
        if session_id not in self.sessions:
            return False
        
        with self._lock:
            self.sessions[session_id].status = status
            self.sessions[session_id].updated_at = datetime.now()
        
        logger.info(f"Updated session {session_id} status to {status}")
        return True

@dataclass
class TaskAssignment:
    """Represents a task assignment to an agent"""
    assignment_id: str
    session_id: str
    task_id: str
    assigned_agent: str
    assigned_by: str
    priority: int
    deadline: datetime
    status: str  # assigned, in_progress, completed, failed
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

@dataclass
class ConsensusRecord:
    """Record of consensus decisions"""
    record_id: str
    session_id: str
    decision_type: str
    participants: List[str]
    decision: Dict[str, Any]
    consensus_level: ConsensusLevel
    voting_results: Dict[str, str]
    created_at: datetime
    expires_at: Optional[datetime] = None

class MultiAgentPlanning:
    """
    Core Multi-Agent Planning Orchestrator
    
    Manages planning sessions, goal proposals, task assignments,
    and arbitration for multi-agent collaboration.
    """
    
    def __init__(self, base_dir: Path, agent_messaging_layer, access_control, 
                 llm_factory, black_box_inspector=None, predictive_intelligence=None):
        self.base_dir = base_dir
        self.agent_messaging_layer = agent_messaging_layer
        self.access_control = access_control
        self.llm_factory = llm_factory
        self.black_box_inspector = black_box_inspector
        self.predictive_intelligence = predictive_intelligence
        
        # Database setup
        self.db_path = base_dir / "data" / "multi_agent_planning.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Active sessions and state
        self.active_sessions: Dict[str, PlanningSession] = {}
        self.session_proposals: Dict[str, List[GoalProposal]] = defaultdict(list)
        self.session_assignments: Dict[str, List[TaskAssignment]] = defaultdict(list)
        self.session_consensus: Dict[str, List[ConsensusRecord]] = defaultdict(list)
        
        # Background processing
        self.running = True
        self.planning_worker = threading.Thread(target=self._planning_worker, daemon=True)
        self.arbitration_worker = threading.Thread(target=self._arbitration_worker, daemon=True)
        self.cleanup_worker = threading.Thread(target=self._cleanup_worker, daemon=True)
        
        # Start background threads
        self.planning_worker.start()
        self.arbitration_worker.start()
        self.cleanup_worker.start()
        
        logger.info("Multi-Agent Planning initialized")
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS planning_sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    participants TEXT NOT NULL,
                    leader_agent TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deadline TEXT,
                    consensus_level TEXT NOT NULL,
                    arbitration_strategy TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    milestones TEXT NOT NULL,
                    current_milestone TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goal_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    proposer_agent TEXT NOT NULL,
                    goal_description TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    estimated_duration INTEGER NOT NULL,
                    required_resources TEXT NOT NULL,
                    dependencies TEXT NOT NULL,
                    success_criteria TEXT NOT NULL,
                    risk_assessment TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    votes TEXT NOT NULL,
                    comments TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES planning_sessions (session_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    assigned_agent TEXT NOT NULL,
                    assigned_by TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    deadline TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress_percentage REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    notes TEXT,
                    FOREIGN KEY (session_id) REFERENCES planning_sessions (session_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consensus_records (
                    record_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    participants TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    consensus_level TEXT NOT NULL,
                    voting_results TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES planning_sessions (session_id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON planning_sessions(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_leader ON planning_sessions(leader_agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proposals_session ON goal_proposals(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proposals_status ON goal_proposals(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_session ON task_assignments(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_agent ON task_assignments(assigned_agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_consensus_session ON consensus_records(session_id)")
            
            conn.commit()
    
    def create_planning_session(self, name: str, description: str, goal: str, 
                               participants: List[str], leader_agent: str,
                               consensus_level: ConsensusLevel = ConsensusLevel.MAJORITY,
                               arbitration_strategy: ArbitrationStrategy = ArbitrationStrategy.TRUST_WEIGHTED,
                               deadline: Optional[datetime] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new planning session"""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Validate participants
        if leader_agent not in participants:
            participants.append(leader_agent)
        
        # Create session
        session = PlanningSession(
            session_id=session_id,
            name=name,
            description=description,
            goal=goal,
            participants=participants,
            leader_agent=leader_agent,
            status=PlanningStatus.INITIALIZING,
            created_at=timestamp,
            updated_at=timestamp,
            deadline=deadline,
            consensus_level=consensus_level,
            arbitration_strategy=arbitration_strategy,
            metadata=metadata or {},
            milestones=[],
            current_milestone=None
        )
        
        # Store in database
        self._store_session(session)
        
        # Add to active sessions
        self.active_sessions[session_id] = session
        
        # Notify participants
        self._notify_session_created(session)
        
        # Log to black box inspector
        if self.black_box_inspector:
            self.black_box_inspector.log_trace_event(
                trace_type="planning_session_created",
                component_id=f"session-{session_id}",
                payload={
                    "session_id": session_id,
                    "name": name,
                    "participants": participants,
                    "leader_agent": leader_agent,
                    "consensus_level": consensus_level.value,
                    "arbitration_strategy": arbitration_strategy.value
                },
                metadata={
                    "goal": goal,
                    "deadline": deadline.isoformat() if deadline else None
                }
            )
        
        logger.info(f"Created planning session {session_id} with {len(participants)} participants")
        return session_id
    
    def _store_session(self, session: PlanningSession):
        """Store a planning session in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO planning_sessions 
                (session_id, name, description, goal, participants, leader_agent, 
                 status, created_at, updated_at, deadline, consensus_level, 
                 arbitration_strategy, metadata, milestones, current_milestone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.name,
                session.description,
                session.goal,
                json.dumps(session.participants),
                session.leader_agent,
                session.status.value,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.deadline.isoformat() if session.deadline else None,
                session.consensus_level.value,
                session.arbitration_strategy.value,
                json.dumps(session.metadata),
                json.dumps(session.milestones),
                session.current_milestone
            ))
            conn.commit()
    
    def _notify_session_created(self, session: PlanningSession):
        """Notify participants about session creation"""
        if not self.agent_messaging_layer:
            return
        
        for participant in session.participants:
            if participant != session.leader_agent:
                try:
                    self.agent_messaging_layer.send_message(
                        sender_id=session.leader_agent,
                        receiver_id=participant,
                        message_type=self.agent_messaging_layer.MessageType.COORDINATION,
                        content=f"Planning session '{session.name}' created. Goal: {session.goal}",
                        priority=self.agent_messaging_layer.MessagePriority.NORMAL,
                        metadata={
                            "session_id": session.session_id,
                            "action": "session_created",
                            "deadline": session.deadline.isoformat() if session.deadline else None
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to notify participant {participant}: {e}")
    
    def submit_goal_proposal(self, session_id: str, proposer_agent: str, 
                           goal_description: str, priority: int = 5,
                           estimated_duration: int = 60, required_resources: Optional[List[str]] = None,
                           dependencies: Optional[List[str]] = None, success_criteria: Optional[List[str]] = None,
                           risk_assessment: Optional[Dict[str, Any]] = None) -> str:
        """Submit a goal proposal to a planning session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Planning session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Check if proposer is a participant
        if proposer_agent not in session.participants:
            raise ValueError(f"Agent {proposer_agent} is not a participant in session {session_id}")
        
        proposal_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Create proposal
        proposal = GoalProposal(
            proposal_id=proposal_id,
            session_id=session_id,
            proposer_agent=proposer_agent,
            goal_description=goal_description,
            priority=priority,
            estimated_duration=estimated_duration,
            required_resources=required_resources or [],
            dependencies=dependencies or [],
            success_criteria=success_criteria or [],
            risk_assessment=risk_assessment or {},
            created_at=timestamp,
            status="pending",
            votes={},
            comments=[]
        )
        
        # Store proposal
        self._store_proposal(proposal)
        
        # Add to session proposals
        self.session_proposals[session_id].append(proposal)
        
        # Update session status
        session.status = PlanningStatus.NEGOTIATING
        session.updated_at = timestamp
        self._update_session(session)
        
        # Notify participants
        self._notify_proposal_submitted(session, proposal)
        
        # Log to black box inspector
        if self.black_box_inspector:
            self.black_box_inspector.log_trace_event(
                trace_type="goal_proposal_submitted",
                component_id=f"proposal-{proposal_id}",
                payload={
                    "proposal_id": proposal_id,
                    "session_id": session_id,
                    "proposer_agent": proposer_agent,
                    "priority": priority,
                    "estimated_duration": estimated_duration
                },
                metadata={
                    "goal_description": goal_description,
                    "required_resources": required_resources,
                    "dependencies": dependencies
                }
            )
        
        logger.info(f"Goal proposal {proposal_id} submitted to session {session_id}")
        return proposal_id
    
    def _store_proposal(self, proposal: GoalProposal):
        """Store a goal proposal in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO goal_proposals 
                (proposal_id, session_id, proposer_agent, goal_description, priority,
                 estimated_duration, required_resources, dependencies, success_criteria,
                 risk_assessment, created_at, status, votes, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proposal.proposal_id,
                proposal.session_id,
                proposal.proposer_agent,
                proposal.goal_description,
                proposal.priority,
                proposal.estimated_duration,
                json.dumps(proposal.required_resources),
                json.dumps(proposal.dependencies),
                json.dumps(proposal.success_criteria),
                json.dumps(proposal.risk_assessment),
                proposal.created_at.isoformat(),
                proposal.status,
                json.dumps(proposal.votes),
                json.dumps(proposal.comments)
            ))
            conn.commit()
    
    def _notify_proposal_submitted(self, session: PlanningSession, proposal: GoalProposal):
        """Notify participants about proposal submission"""
        if not self.agent_messaging_layer:
            return
        
        for participant in session.participants:
            if participant != proposal.proposer_agent:
                try:
                    self.agent_messaging_layer.send_message(
                        sender_id=proposal.proposer_agent,
                        receiver_id=participant,
                        message_type=self.agent_messaging_layer.MessageType.GOAL_DELEGATION,
                        content=f"New goal proposal: {proposal.goal_description}",
                        priority=self.agent_messaging_layer.MessagePriority.HIGH,
                        metadata={
                            "session_id": session.session_id,
                            "proposal_id": proposal.proposal_id,
                            "action": "proposal_submitted",
                            "priority": proposal.priority,
                            "estimated_duration": proposal.estimated_duration
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to notify participant {participant}: {e}")
    
    def vote_on_proposal(self, session_id: str, proposal_id: str, agent_id: str, 
                        vote: str, comment: Optional[str] = None) -> bool:
        """Vote on a goal proposal"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Planning session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Find proposal
        proposal = None
        for p in self.session_proposals[session_id]:
            if p.proposal_id == proposal_id:
                proposal = p
                break
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        # Check if agent is a participant
        if agent_id not in session.participants:
            raise ValueError(f"Agent {agent_id} is not a participant")
        
        # Record vote
        proposal.votes[agent_id] = vote
        
        # Add comment if provided
        if comment:
            proposal.comments.append({
                "agent_id": agent_id,
                "comment": comment,
                "timestamp": datetime.now().isoformat()
            })
        
        # Update proposal in database
        self._update_proposal(proposal)
        
        # Check if consensus reached
        if self._check_consensus_reached(session, proposal):
            self._finalize_proposal(session, proposal)
        
        logger.info(f"Agent {agent_id} voted {vote} on proposal {proposal_id}")
        return True
    
    def _check_consensus_reached(self, session: PlanningSession, proposal: GoalProposal) -> bool:
        """Check if consensus has been reached on a proposal"""
        total_participants = len(session.participants)
        total_votes = len(proposal.votes)
        
        if total_votes < total_participants:
            return False  # Not everyone has voted yet
        
        approve_votes = sum(1 for vote in proposal.votes.values() if vote == "approve")
        reject_votes = sum(1 for vote in proposal.votes.values() if vote == "reject")
        
        if session.consensus_level == ConsensusLevel.UNANIMOUS:
            return approve_votes == total_participants
        elif session.consensus_level == ConsensusLevel.MAJORITY:
            return approve_votes > total_participants / 2
        elif session.consensus_level == ConsensusLevel.SUPER_MAJORITY:
            return approve_votes > (total_participants * 2) / 3
        elif session.consensus_level == ConsensusLevel.QUORUM:
            return approve_votes >= (total_participants * 3) / 4
        elif session.consensus_level == ConsensusLevel.LEADER_DECISION:
            return session.leader_agent in proposal.votes and proposal.votes[session.leader_agent] == "approve"
        
        return False
    
    def _finalize_proposal(self, session: PlanningSession, proposal: GoalProposal):
        """Finalize a proposal after consensus is reached"""
        approve_votes = sum(1 for vote in proposal.votes.values() if vote == "approve")
        total_votes = len(proposal.votes)
        
        if approve_votes > total_votes / 2:
            proposal.status = "accepted"
            session.status = PlanningStatus.CONSENSUS_REACHED
            
            # Create task assignments
            self._create_task_assignments(session, proposal)
        else:
            proposal.status = "rejected"
            session.status = PlanningStatus.ACTIVE
        
        # Update proposal and session
        self._update_proposal(proposal)
        self._update_session(session)
        
        # Notify participants
        self._notify_proposal_finalized(session, proposal)
        
        logger.info(f"Proposal {proposal.proposal_id} finalized with status: {proposal.status}")
    
    def _create_task_assignments(self, session: PlanningSession, proposal: GoalProposal):
        """Create task assignments for an accepted proposal"""
        # Simple assignment logic - can be enhanced with more sophisticated algorithms
        available_agents = [agent for agent in session.participants if agent != session.leader_agent]
        
        if not available_agents:
            return
        
        # Create a task assignment
        assignment_id = str(uuid.uuid4())
        assigned_agent = available_agents[0]  # Simple round-robin
        
        assignment = TaskAssignment(
            assignment_id=assignment_id,
            session_id=session.session_id,
            task_id=proposal.proposal_id,
            assigned_agent=assigned_agent,
            assigned_by=session.leader_agent,
            priority=proposal.priority,
            deadline=datetime.now() + timedelta(minutes=proposal.estimated_duration),
            status="assigned",
            progress_percentage=0.0,
            created_at=datetime.now(),
            notes=f"Assigned based on proposal: {proposal.goal_description}"
        )
        
        # Store assignment
        self._store_assignment(assignment)
        self.session_assignments[session.session_id].append(assignment)
        
        # Notify assigned agent
        if self.agent_messaging_layer:
            try:
                self.agent_messaging_layer.send_message(
                    sender_id=session.leader_agent,
                    receiver_id=assigned_agent,
                    message_type=self.agent_messaging_layer.MessageType.INSTRUCTION,
                    content=f"Task assigned: {proposal.goal_description}",
                    priority=self.agent_messaging_layer.MessagePriority.HIGH,
                    metadata={
                        "session_id": session.session_id,
                        "assignment_id": assignment_id,
                        "task_id": proposal.proposal_id,
                        "deadline": assignment.deadline.isoformat(),
                        "priority": assignment.priority
                    }
                )
            except Exception as e:
                logger.error(f"Failed to notify assigned agent {assigned_agent}: {e}")
    
    def _store_assignment(self, assignment: TaskAssignment):
        """Store a task assignment in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_assignments 
                (assignment_id, session_id, task_id, assigned_agent, assigned_by,
                 priority, deadline, status, progress_percentage, created_at,
                 started_at, completed_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.assignment_id,
                assignment.session_id,
                assignment.task_id,
                assignment.assigned_agent,
                assignment.assigned_by,
                assignment.priority,
                assignment.deadline.isoformat(),
                assignment.status,
                assignment.progress_percentage,
                assignment.created_at.isoformat(),
                assignment.started_at.isoformat() if assignment.started_at else None,
                assignment.completed_at.isoformat() if assignment.completed_at else None,
                assignment.notes
            ))
            conn.commit()
    
    def _notify_proposal_finalized(self, session: PlanningSession, proposal: GoalProposal):
        """Notify participants about proposal finalization"""
        if not self.agent_messaging_layer:
            return
        
        for participant in session.participants:
            try:
                self.agent_messaging_layer.send_message(
                    sender_id=session.leader_agent,
                    receiver_id=participant,
                    message_type=self.agent_messaging_layer.MessageType.STATUS_UPDATE,
                    content=f"Proposal '{proposal.goal_description}' {proposal.status}",
                    priority=self.agent_messaging_layer.MessagePriority.NORMAL,
                    metadata={
                        "session_id": session.session_id,
                        "proposal_id": proposal.proposal_id,
                        "action": "proposal_finalized",
                        "status": proposal.status,
                        "votes": proposal.votes
                    }
                )
            except Exception as e:
                logger.error(f"Failed to notify participant {participant}: {e}")
    
    def _update_proposal(self, proposal: GoalProposal):
        """Update a proposal in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE goal_proposals 
                SET status = ?, votes = ?, comments = ?
                WHERE proposal_id = ?
            """, (
                proposal.status,
                json.dumps(proposal.votes),
                json.dumps(proposal.comments),
                proposal.proposal_id
            ))
            conn.commit()
    
    def _update_session(self, session: PlanningSession):
        """Update a session in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE planning_sessions 
                SET status = ?, updated_at = ?, milestones = ?, current_milestone = ?
                WHERE session_id = ?
            """, (
                session.status.value,
                session.updated_at.isoformat(),
                json.dumps(session.milestones),
                session.current_milestone,
                session.session_id
            ))
            conn.commit()
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a planning session"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        proposals = self.session_proposals[session_id]
        assignments = self.session_assignments[session_id]
        
        return {
            "session_id": session.session_id,
            "name": session.name,
            "status": session.status.value,
            "participants": session.participants,
            "leader_agent": session.leader_agent,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "deadline": session.deadline.isoformat() if session.deadline else None,
            "consensus_level": session.consensus_level.value,
            "arbitration_strategy": session.arbitration_strategy.value,
            "proposal_count": len(proposals),
            "assignment_count": len(assignments),
            "active_proposals": [p for p in proposals if p.status == "pending"],
            "completed_assignments": [a for a in assignments if a.status == "completed"]
        }
    
    def get_session_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the history of a planning session"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        proposals = self.session_proposals[session_id]
        assignments = self.session_assignments[session_id]
        consensus_records = self.session_consensus[session_id]
        
        return {
            "session": {
                "session_id": session.session_id,
                "name": session.name,
                "goal": session.goal,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            },
            "proposals": [
                {
                    "proposal_id": p.proposal_id,
                    "proposer_agent": p.proposer_agent,
                    "goal_description": p.goal_description,
                    "priority": p.priority,
                    "status": p.status,
                    "votes": p.votes,
                    "created_at": p.created_at.isoformat()
                }
                for p in proposals
            ],
            "assignments": [
                {
                    "assignment_id": a.assignment_id,
                    "assigned_agent": a.assigned_agent,
                    "status": a.status,
                    "progress_percentage": a.progress_percentage,
                    "created_at": a.created_at.isoformat(),
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None
                }
                for a in assignments
            ],
            "consensus_records": [
                {
                    "record_id": c.record_id,
                    "decision_type": c.decision_type,
                    "decision": c.decision,
                    "voting_results": c.voting_results,
                    "created_at": c.created_at.isoformat()
                }
                for c in consensus_records
            ]
        }
    
    def _planning_worker(self):
        """Background worker for processing planning activities"""
        while self.running:
            try:
                # Process active sessions
                for session_id, session in list(self.active_sessions.items()):
                    self._process_session(session)
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Planning worker error: {e}")
                time.sleep(30)  # Wait 30 seconds on error
    
    def _process_session(self, session: PlanningSession):
        """Process a planning session"""
        try:
            # Check for deadline
            if session.deadline and datetime.now() > session.deadline:
                session.status = PlanningStatus.FAILED
                self._update_session(session)
                logger.info(f"Session {session.session_id} failed due to deadline")
                return
            
            # Check for completed assignments
            assignments = self.session_assignments[session.session_id]
            completed_count = sum(1 for a in assignments if a.status == "completed")
            
            if completed_count == len(assignments) and len(assignments) > 0:
                session.status = PlanningStatus.COMPLETED
                self._update_session(session)
                logger.info(f"Session {session.session_id} completed")
                return
            
            # Check for stuck proposals
            proposals = self.session_proposals[session.session_id]
            pending_proposals = [p for p in proposals if p.status == "pending"]
            
            if pending_proposals and session.status == PlanningStatus.NEGOTIATING:
                # Check if any proposals have been pending too long
                for proposal in pending_proposals:
                    if datetime.now() - proposal.created_at > timedelta(minutes=30):
                        # Trigger arbitration
                        self._trigger_arbitration(session, proposal)
            
        except Exception as e:
            logger.error(f"Error processing session {session.session_id}: {e}")
    
    def _trigger_arbitration(self, session: PlanningSession, proposal: GoalProposal):
        """Trigger arbitration for a stuck proposal"""
        session.status = PlanningStatus.ARBITRATING
        self._update_session(session)
        
        # Apply arbitration strategy
        if session.arbitration_strategy == ArbitrationStrategy.TRUST_WEIGHTED:
            self._arbitrate_trust_weighted(session, proposal)
        elif session.arbitration_strategy == ArbitrationStrategy.MAJORITY_VOTE:
            self._arbitrate_majority_vote(session, proposal)
        elif session.arbitration_strategy == ArbitrationStrategy.LEADER_DECISION:
            self._arbitrate_leader_decision(session, proposal)
        else:
            # Default to automatic acceptance
            proposal.status = "accepted"
            self._update_proposal(proposal)
            self._finalize_proposal(session, proposal)
    
    def _arbitration_worker(self):
        """Background worker for handling arbitration"""
        while self.running:
            try:
                # Process arbitration requests
                # This could be enhanced with more sophisticated arbitration logic
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Arbitration worker error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def _arbitrate_trust_weighted(self, session: PlanningSession, proposal: GoalProposal):
        """Arbitrate using trust-weighted voting"""
        # Simple implementation - can be enhanced with actual trust scores
        approve_votes = sum(1 for vote in proposal.votes.values() if vote == "approve")
        total_votes = len(proposal.votes)
        
        if approve_votes >= total_votes / 2:
            proposal.status = "accepted"
        else:
            proposal.status = "rejected"
        
        self._update_proposal(proposal)
        self._finalize_proposal(session, proposal)
    
    def _arbitrate_majority_vote(self, session: PlanningSession, proposal: GoalProposal):
        """Arbitrate using majority vote"""
        approve_votes = sum(1 for vote in proposal.votes.values() if vote == "approve")
        total_votes = len(proposal.votes)
        
        if approve_votes > total_votes / 2:
            proposal.status = "accepted"
        else:
            proposal.status = "rejected"
        
        self._update_proposal(proposal)
        self._finalize_proposal(session, proposal)
    
    def _arbitrate_leader_decision(self, session: PlanningSession, proposal: GoalProposal):
        """Arbitrate using leader decision"""
        if session.leader_agent in proposal.votes:
            if proposal.votes[session.leader_agent] == "approve":
                proposal.status = "accepted"
            else:
                proposal.status = "rejected"
        else:
            # Leader hasn't voted, default to accept
            proposal.status = "accepted"
        
        self._update_proposal(proposal)
        self._finalize_proposal(session, proposal)
    
    def _cleanup_worker(self):
        """Background worker for cleaning up old data"""
        while self.running:
            try:
                # Clean up old sessions
                cutoff_time = datetime.now() - timedelta(days=7)
                
                with sqlite3.connect(self.db_path) as conn:
                    # Archive old completed sessions
                    conn.execute("""
                        UPDATE planning_sessions 
                        SET status = 'archived' 
                        WHERE status IN ('completed', 'failed', 'cancelled') 
                        AND updated_at < ?
                    """, (cutoff_time.isoformat(),))
                    
                    conn.commit()
                
                time.sleep(3600)  # Run cleanup every hour
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Session counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM planning_sessions 
                GROUP BY status
            """)
            session_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Proposal counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM goal_proposals 
                GROUP BY status
            """)
            proposal_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Assignment counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM task_assignments 
                GROUP BY status
            """)
            assignment_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'total_sessions': sum(session_counts.values()),
            'active_sessions': len(self.active_sessions),
            'session_counts': session_counts,
            'proposal_counts': proposal_counts,
            'assignment_counts': assignment_counts,
            'consensus_records': sum(len(records) for records in self.session_consensus.values())
        }
    
    def shutdown(self):
        """Shutdown the planning system"""
        self.running = False
        
        # Wait for background threads to finish
        if self.planning_worker.is_alive():
            self.planning_worker.join(timeout=5)
        if self.arbitration_worker.is_alive():
            self.arbitration_worker.join(timeout=5)
        if self.cleanup_worker.is_alive():
            self.cleanup_worker.join(timeout=5)
        
        logger.info("Multi-Agent Planning shutdown complete")
