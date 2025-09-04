"""
Priority 25: Agent Negotiation Engine

This module handles agent-to-agent negotiation logic including
proposal acceptance, counteroffers, arbitration, and deferral.
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
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from collections import defaultdict
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NegotiationState(Enum):
    """States of negotiation"""
    INITIATED = "initiated"
    PROPOSAL_SENT = "proposal_sent"
    COUNTER_OFFER = "counter_offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ARBITRATED = "arbitrated"
    DEFERRED = "deferred"

class NegotiationType(Enum):
    """Types of negotiation"""
    TASK_ASSIGNMENT = "task_assignment"
    RESOURCE_ALLOCATION = "resource_allocation"
    PRIORITY_ADJUSTMENT = "priority_adjustment"
    DEADLINE_NEGOTIATION = "deadline_negotiation"
    CAPABILITY_MATCHING = "capability_matching"
    CONFLICT_RESOLUTION = "conflict_resolution"

class AgentTrustLevel(Enum):
    """Trust levels for agents"""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class NegotiationStatus(str, Enum):
    """Status of negotiation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class NegotiationResult:
    """Result of a negotiation"""
    result_id: str
    negotiation_id: str
    status: NegotiationStatus
    agreement_reached: bool
    final_terms: Dict[str, Any]
    duration: float
    rounds: int
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class NegotiationProposal:
    """Represents a negotiation proposal"""
    proposal_id: str
    session_id: str
    initiator_agent: str
    target_agent: str
    negotiation_type: NegotiationType
    initial_terms: Dict[str, Any]
    current_terms: Dict[str, Any]
    constraints: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    state: NegotiationState
    round_count: int
    max_rounds: int
    history: List[Dict[str, Any]]

@dataclass
class NegotiationOutcome:
    """Represents the outcome of a negotiation"""
    outcome_id: str
    proposal_id: str
    final_terms: Dict[str, Any]
    agreement_reached: bool
    reason: str
    arbitrator_agent: Optional[str]
    arbitration_strategy: Optional[str]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class AgentReliabilityScore:
    """Represents an agent's reliability metrics"""
    agent_id: str
    trust_level: AgentTrustLevel
    success_rate: float  # 0.0 to 1.0
    avg_response_time: float  # seconds
    avg_negotiation_time: float  # seconds
    proposal_acceptance_rate: float  # 0.0 to 1.0
    counter_offer_frequency: float  # 0.0 to 1.0
    last_updated: datetime
    total_negotiations: int
    successful_negotiations: int

class AgentNegotiationEngine:
    """
    Agent-to-Agent Negotiation Engine
    
    Handles negotiation logic, proposal management, counteroffers,
    arbitration, and agent reliability scoring.
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
        self.db_path = base_dir / "data" / "agent_negotiation.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Active negotiations and state
        self.active_negotiations: Dict[str, NegotiationProposal] = {}
        self.negotiation_outcomes: Dict[str, NegotiationOutcome] = {}
        self.agent_reliability: Dict[str, AgentReliabilityScore] = {}
        
        # Background processing
        self.running = True
        self.negotiation_worker = threading.Thread(target=self._negotiation_worker, daemon=True)
        self.reliability_worker = threading.Thread(target=self._reliability_worker, daemon=True)
        self.cleanup_worker = threading.Thread(target=self._cleanup_worker, daemon=True)
        
        # Start background threads
        self.negotiation_worker.start()
        self.reliability_worker.start()
        self.cleanup_worker.start()
        
        logger.info("Agent Negotiation Engine initialized")
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS negotiation_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    initiator_agent TEXT NOT NULL,
                    target_agent TEXT NOT NULL,
                    negotiation_type TEXT NOT NULL,
                    initial_terms TEXT NOT NULL,
                    current_terms TEXT NOT NULL,
                    constraints TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    round_count INTEGER NOT NULL,
                    max_rounds INTEGER NOT NULL,
                    history TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS negotiation_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL,
                    final_terms TEXT NOT NULL,
                    agreement_reached BOOLEAN NOT NULL,
                    reason TEXT NOT NULL,
                    arbitrator_agent TEXT,
                    arbitration_strategy TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY (proposal_id) REFERENCES negotiation_proposals (proposal_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_reliability (
                    agent_id TEXT PRIMARY KEY,
                    trust_level TEXT NOT NULL,
                    success_rate REAL NOT NULL,
                    avg_response_time REAL NOT NULL,
                    avg_negotiation_time REAL NOT NULL,
                    proposal_acceptance_rate REAL NOT NULL,
                    counter_offer_frequency REAL NOT NULL,
                    last_updated TEXT NOT NULL,
                    total_negotiations INTEGER NOT NULL,
                    successful_negotiations INTEGER NOT NULL
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proposals_state ON negotiation_proposals(state)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proposals_agents ON negotiation_proposals(initiator_agent, target_agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proposals_expires ON negotiation_proposals(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_proposal ON negotiation_outcomes(proposal_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reliability_agent ON agent_reliability(agent_id)")
            
            conn.commit()
    
    def initiate_negotiation(self, session_id: str, initiator_agent: str, target_agent: str,
                           negotiation_type: NegotiationType, initial_terms: Dict[str, Any],
                           constraints: Optional[Dict[str, Any]] = None,
                           max_rounds: int = 5, timeout_minutes: int = 30) -> str:
        """Initiate a negotiation between agents"""
        proposal_id = str(uuid.uuid4())
        timestamp = datetime.now()
        expires_at = timestamp + timedelta(minutes=timeout_minutes)
        
        # Create proposal
        proposal = NegotiationProposal(
            proposal_id=proposal_id,
            session_id=session_id,
            initiator_agent=initiator_agent,
            target_agent=target_agent,
            negotiation_type=negotiation_type,
            initial_terms=initial_terms,
            current_terms=initial_terms.copy(),
            constraints=constraints or {},
            created_at=timestamp,
            expires_at=expires_at,
            state=NegotiationState.INITIATED,
            round_count=0,
            max_rounds=max_rounds,
            history=[]
        )
        
        # Store proposal
        self._store_proposal(proposal)
        
        # Add to active negotiations
        self.active_negotiations[proposal_id] = proposal
        
        # Send negotiation message
        self._send_negotiation_message(proposal, "initiated")
        
        # Log to black box inspector
        if self.black_box_inspector:
            self.black_box_inspector.log_trace_event(
                trace_type="negotiation_initiated",
                component_id=f"proposal-{proposal_id}",
                payload={
                    "proposal_id": proposal_id,
                    "session_id": session_id,
                    "initiator_agent": initiator_agent,
                    "target_agent": target_agent,
                    "negotiation_type": negotiation_type.value,
                    "max_rounds": max_rounds,
                    "timeout_minutes": timeout_minutes
                },
                metadata={
                    "initial_terms": initial_terms,
                    "constraints": constraints
                }
            )
        
        logger.info(f"Negotiation {proposal_id} initiated between {initiator_agent} and {target_agent}")
        return proposal_id
    
    def _store_proposal(self, proposal: NegotiationProposal):
        """Store a negotiation proposal in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO negotiation_proposals 
                (proposal_id, session_id, initiator_agent, target_agent, negotiation_type,
                 initial_terms, current_terms, constraints, created_at, expires_at,
                 state, round_count, max_rounds, history)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proposal.proposal_id,
                proposal.session_id,
                proposal.initiator_agent,
                proposal.target_agent,
                proposal.negotiation_type.value,
                json.dumps(proposal.initial_terms),
                json.dumps(proposal.current_terms),
                json.dumps(proposal.constraints),
                proposal.created_at.isoformat(),
                proposal.expires_at.isoformat(),
                proposal.state.value,
                proposal.round_count,
                proposal.max_rounds,
                json.dumps(proposal.history)
            ))
            conn.commit()
    
    def _send_negotiation_message(self, proposal: NegotiationProposal, action: str):
        """Send negotiation message to target agent"""
        if not self.agent_messaging_layer:
            return
        
        try:
            message_content = f"Negotiation {action}: {proposal.negotiation_type.value}"
            if action == "initiated":
                message_content += f"\nTerms: {json.dumps(proposal.current_terms, indent=2)}"
            
            self.agent_messaging_layer.send_message(
                sender_id=proposal.initiator_agent,
                receiver_id=proposal.target_agent,
                message_type=self.agent_messaging_layer.MessageType.COORDINATION,
                content=message_content,
                priority=self.agent_messaging_layer.MessagePriority.HIGH,
                metadata={
                    "proposal_id": proposal.proposal_id,
                    "session_id": proposal.session_id,
                    "negotiation_type": proposal.negotiation_type.value,
                    "action": action,
                    "current_terms": proposal.current_terms,
                    "round_count": proposal.round_count,
                    "expires_at": proposal.expires_at.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to send negotiation message: {e}")
    
    def respond_to_negotiation(self, proposal_id: str, responding_agent: str,
                             response_type: str, new_terms: Optional[Dict[str, Any]] = None,
                             reason: Optional[str] = None) -> bool:
        """Respond to a negotiation proposal"""
        if proposal_id not in self.active_negotiations:
            raise ValueError(f"Negotiation proposal {proposal_id} not found")
        
        proposal = self.active_negotiations[proposal_id]
        
        # Verify responding agent is the target
        if responding_agent != proposal.target_agent:
            raise ValueError(f"Agent {responding_agent} is not the target of this negotiation")
        
        # Check if negotiation has expired
        if datetime.now() > proposal.expires_at:
            proposal.state = NegotiationState.EXPIRED
            self._finalize_negotiation(proposal, False, "Negotiation expired")
            return False
        
        # Update proposal based on response
        proposal.round_count += 1
        
        # Record response in history
        history_entry = {
            "round": proposal.round_count,
            "agent": responding_agent,
            "response_type": response_type,
            "timestamp": datetime.now().isoformat(),
            "new_terms": new_terms,
            "reason": reason
        }
        proposal.history.append(history_entry)
        
        if response_type == "accept":
            proposal.state = NegotiationState.ACCEPTED
            if new_terms:
                proposal.current_terms.update(new_terms)
            self._finalize_negotiation(proposal, True, "Agreement reached")
            
        elif response_type == "reject":
            proposal.state = NegotiationState.REJECTED
            self._finalize_negotiation(proposal, False, reason or "Proposal rejected")
            
        elif response_type == "counter_offer":
            if proposal.round_count >= proposal.max_rounds:
                proposal.state = NegotiationState.EXPIRED
                self._finalize_negotiation(proposal, False, "Max rounds reached")
            else:
                proposal.state = NegotiationState.COUNTER_OFFER
                if new_terms:
                    proposal.current_terms.update(new_terms)
                # Send counter-offer back to initiator
                self._send_counter_offer(proposal, new_terms, reason)
                
        elif response_type == "defer":
            proposal.state = NegotiationState.DEFERRED
            self._finalize_negotiation(proposal, False, "Negotiation deferred")
        
        # Update proposal in database
        self._update_proposal(proposal)
        
        # Update agent reliability metrics
        self._update_agent_reliability(responding_agent, response_type, proposal)
        
        logger.info(f"Agent {responding_agent} responded {response_type} to negotiation {proposal_id}")
        return True
    
    def _send_counter_offer(self, proposal: NegotiationProposal, new_terms: Dict[str, Any], reason: str):
        """Send counter-offer back to initiator"""
        if not self.agent_messaging_layer:
            return
        
        try:
            message_content = f"Counter-offer received for {proposal.negotiation_type.value}\nReason: {reason}\nNew terms: {json.dumps(new_terms, indent=2)}"
            
            self.agent_messaging_layer.send_message(
                sender_id=proposal.target_agent,
                receiver_id=proposal.initiator_agent,
                message_type=self.agent_messaging_layer.MessageType.COORDINATION,
                content=message_content,
                priority=self.agent_messaging_layer.MessagePriority.HIGH,
                metadata={
                    "proposal_id": proposal.proposal_id,
                    "session_id": proposal.session_id,
                    "action": "counter_offer",
                    "new_terms": new_terms,
                    "reason": reason,
                    "round_count": proposal.round_count
                }
            )
        except Exception as e:
            logger.error(f"Failed to send counter-offer: {e}")
    
    def _finalize_negotiation(self, proposal: NegotiationProposal, agreement_reached: bool, reason: str):
        """Finalize a negotiation with outcome"""
        outcome_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Determine arbitrator if needed
        arbitrator_agent = None
        arbitration_strategy = None
        
        if not agreement_reached and proposal.round_count >= proposal.max_rounds:
            # Trigger arbitration
            arbitrator_agent = self._select_arbitrator(proposal)
            arbitration_strategy = "automatic"
            if arbitrator_agent:
                final_terms = self._arbitrate_negotiation(proposal, arbitrator_agent)
                agreement_reached = final_terms is not None
                if agreement_reached:
                    proposal.current_terms.update(final_terms)
                    reason = "Arbitration successful"
        
        # Create outcome
        outcome = NegotiationOutcome(
            outcome_id=outcome_id,
            proposal_id=proposal.proposal_id,
            final_terms=proposal.current_terms,
            agreement_reached=agreement_reached,
            reason=reason,
            arbitrator_agent=arbitrator_agent,
            arbitration_strategy=arbitration_strategy,
            created_at=timestamp,
            metadata={
                "round_count": proposal.round_count,
                "negotiation_type": proposal.negotiation_type.value,
                "history": proposal.history
            }
        )
        
        # Store outcome
        self._store_outcome(outcome)
        self.negotiation_outcomes[outcome_id] = outcome
        
        # Remove from active negotiations
        if proposal.proposal_id in self.active_negotiations:
            del self.active_negotiations[proposal.proposal_id]
        
        # Notify both agents
        self._notify_negotiation_outcome(proposal, outcome)
        
        # Log to black box inspector
        if self.black_box_inspector:
            self.black_box_inspector.log_trace_event(
                trace_type="negotiation_finalized",
                component_id=f"outcome-{outcome_id}",
                payload={
                    "outcome_id": outcome_id,
                    "proposal_id": proposal.proposal_id,
                    "agreement_reached": agreement_reached,
                    "round_count": proposal.round_count,
                    "arbitrator_agent": arbitrator_agent
                },
                metadata={
                    "final_terms": proposal.current_terms,
                    "reason": reason,
                    "negotiation_type": proposal.negotiation_type.value
                }
            )
        
        logger.info(f"Negotiation {proposal.proposal_id} finalized: {reason}")
    
    def _select_arbitrator(self, proposal: NegotiationProposal) -> Optional[str]:
        """Select an arbitrator for failed negotiations"""
        # Simple arbitrator selection - can be enhanced with more sophisticated logic
        # For now, use the session leader if available
        if self.multi_agent_planning and proposal.session_id in self.multi_agent_planning.active_sessions:
            session = self.multi_agent_planning.active_sessions[proposal.session_id]
            return session.leader_agent
        
        # Fallback to a neutral agent (could be a dedicated arbitrator agent)
        return None
    
    def _arbitrate_negotiation(self, proposal: NegotiationProposal, arbitrator_agent: str) -> Optional[Dict[str, Any]]:
        """Arbitrate a failed negotiation"""
        # Simple arbitration logic - can be enhanced with LLM-based reasoning
        try:
            # Analyze negotiation history
            initiator_terms = proposal.initial_terms
            target_terms = None
            
            # Find the last counter-offer from target
            for entry in reversed(proposal.history):
                if entry["agent"] == proposal.target_agent and entry["new_terms"]:
                    target_terms = entry["new_terms"]
                    break
            
            if not target_terms:
                return None
            
            # Simple compromise: average numeric values, keep non-numeric from initiator
            final_terms = {}
            for key in initiator_terms:
                if key in target_terms:
                    init_value = initiator_terms[key]
                    target_value = target_terms[key]
                    
                    if isinstance(init_value, (int, float)) and isinstance(target_value, (int, float)):
                        final_terms[key] = (init_value + target_value) / 2
                    else:
                        final_terms[key] = init_value  # Keep initiator's non-numeric values
                else:
                    final_terms[key] = initiator_terms[key]
            
            return final_terms
            
        except Exception as e:
            logger.error(f"Arbitration failed: {e}")
            return None
    
    def _store_outcome(self, outcome: NegotiationOutcome):
        """Store a negotiation outcome in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO negotiation_outcomes 
                (outcome_id, proposal_id, final_terms, agreement_reached, reason,
                 arbitrator_agent, arbitration_strategy, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                outcome.outcome_id,
                outcome.proposal_id,
                json.dumps(outcome.final_terms),
                outcome.agreement_reached,
                outcome.reason,
                outcome.arbitrator_agent,
                outcome.arbitration_strategy,
                outcome.created_at.isoformat(),
                json.dumps(outcome.metadata)
            ))
            conn.commit()
    
    def _notify_negotiation_outcome(self, proposal: NegotiationProposal, outcome: NegotiationOutcome):
        """Notify both agents about negotiation outcome"""
        if not self.agent_messaging_layer:
            return
        
        # Notify initiator
        try:
            self.agent_messaging_layer.send_message(
                sender_id=proposal.target_agent,
                receiver_id=proposal.initiator_agent,
                message_type=self.agent_messaging_layer.MessageType.STATUS_UPDATE,
                content=f"Negotiation {outcome.outcome_id} {outcome.reason}",
                priority=self.agent_messaging_layer.MessagePriority.NORMAL,
                metadata={
                    "proposal_id": proposal.proposal_id,
                    "outcome_id": outcome.outcome_id,
                    "agreement_reached": outcome.agreement_reached,
                    "final_terms": outcome.final_terms,
                    "arbitrator_agent": outcome.arbitrator_agent
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify initiator: {e}")
        
        # Notify target
        try:
            self.agent_messaging_layer.send_message(
                sender_id=proposal.initiator_agent,
                receiver_id=proposal.target_agent,
                message_type=self.agent_messaging_layer.MessageType.STATUS_UPDATE,
                content=f"Negotiation {outcome.outcome_id} {outcome.reason}",
                priority=self.agent_messaging_layer.MessagePriority.NORMAL,
                metadata={
                    "proposal_id": proposal.proposal_id,
                    "outcome_id": outcome.outcome_id,
                    "agreement_reached": outcome.agreement_reached,
                    "final_terms": outcome.final_terms,
                    "arbitrator_agent": outcome.arbitrator_agent
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify target: {e}")
    
    def _update_proposal(self, proposal: NegotiationProposal):
        """Update a proposal in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE negotiation_proposals 
                SET current_terms = ?, state = ?, round_count = ?, history = ?
                WHERE proposal_id = ?
            """, (
                json.dumps(proposal.current_terms),
                proposal.state.value,
                proposal.round_count,
                json.dumps(proposal.history),
                proposal.proposal_id
            ))
            conn.commit()
    
    def _update_agent_reliability(self, agent_id: str, response_type: str, proposal: NegotiationProposal):
        """Update agent reliability metrics"""
        if agent_id not in self.agent_reliability:
            # Initialize reliability score
            self.agent_reliability[agent_id] = AgentReliabilityScore(
                agent_id=agent_id,
                trust_level=AgentTrustLevel.MEDIUM,
                success_rate=0.5,
                avg_response_time=30.0,
                avg_negotiation_time=300.0,
                proposal_acceptance_rate=0.5,
                counter_offer_frequency=0.3,
                last_updated=datetime.now(),
                total_negotiations=0,
                successful_negotiations=0
            )
        
        reliability = self.agent_reliability[agent_id]
        
        # Update metrics
        reliability.total_negotiations += 1
        if response_type == "accept":
            reliability.successful_negotiations += 1
        
        # Calculate new rates
        reliability.success_rate = reliability.successful_negotiations / reliability.total_negotiations
        reliability.proposal_acceptance_rate = reliability.successful_negotiations / reliability.total_negotiations
        
        # Update counter-offer frequency
        counter_offers = sum(1 for entry in proposal.history if entry.get("response_type") == "counter_offer")
        reliability.counter_offer_frequency = counter_offers / max(1, len(proposal.history))
        
        # Update trust level based on success rate
        if reliability.success_rate >= 0.8:
            reliability.trust_level = AgentTrustLevel.HIGH
        elif reliability.success_rate >= 0.6:
            reliability.trust_level = AgentTrustLevel.MEDIUM
        elif reliability.success_rate >= 0.4:
            reliability.trust_level = AgentTrustLevel.LOW
        else:
            reliability.trust_level = AgentTrustLevel.UNTRUSTED
        
        reliability.last_updated = datetime.now()
        
        # Store updated reliability
        self._store_reliability(reliability)
    
    def _store_reliability(self, reliability: AgentReliabilityScore):
        """Store agent reliability score in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_reliability 
                (agent_id, trust_level, success_rate, avg_response_time, avg_negotiation_time,
                 proposal_acceptance_rate, counter_offer_frequency, last_updated,
                 total_negotiations, successful_negotiations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reliability.agent_id,
                reliability.trust_level.value,
                reliability.success_rate,
                reliability.avg_response_time,
                reliability.avg_negotiation_time,
                reliability.proposal_acceptance_rate,
                reliability.counter_offer_frequency,
                reliability.last_updated.isoformat(),
                reliability.total_negotiations,
                reliability.successful_negotiations
            ))
            conn.commit()
    
    def get_agent_reliability(self, agent_id: str) -> Optional[AgentReliabilityScore]:
        """Get reliability score for an agent"""
        return self.agent_reliability.get(agent_id)
    
    def get_negotiation_status(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a negotiation"""
        if proposal_id not in self.active_negotiations:
            return None
        
        proposal = self.active_negotiations[proposal_id]
        
        return {
            "proposal_id": proposal.proposal_id,
            "session_id": proposal.session_id,
            "initiator_agent": proposal.initiator_agent,
            "target_agent": proposal.target_agent,
            "negotiation_type": proposal.negotiation_type.value,
            "current_terms": proposal.current_terms,
            "state": proposal.state.value,
            "round_count": proposal.round_count,
            "max_rounds": proposal.max_rounds,
            "created_at": proposal.created_at.isoformat(),
            "expires_at": proposal.expires_at.isoformat(),
            "history": proposal.history
        }
    
    def get_negotiation_history(self, agent_id: Optional[str] = None, 
                               session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get negotiation history"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT np.*, no.outcome_id, no.agreement_reached, no.reason, no.created_at as outcome_time
                FROM negotiation_proposals np
                LEFT JOIN negotiation_outcomes no ON np.proposal_id = no.proposal_id
            """
            params = []
            
            if agent_id:
                query += " WHERE np.initiator_agent = ? OR np.target_agent = ?"
                params.extend([agent_id, agent_id])
            
            if session_id:
                if agent_id:
                    query += " AND np.session_id = ?"
                else:
                    query += " WHERE np.session_id = ?"
                params.append(session_id)
            
            query += " ORDER BY np.created_at DESC"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "proposal_id": row[0],
                "session_id": row[1],
                "initiator_agent": row[2],
                "target_agent": row[3],
                "negotiation_type": row[4],
                "state": row[10],
                "round_count": row[11],
                "agreement_reached": row[16] if row[16] is not None else False,
                "reason": row[17] if row[17] else "In progress",
                "created_at": row[8],
                "outcome_time": row[19] if row[19] else None
            })
        
        return history
    
    def _negotiation_worker(self):
        """Background worker for processing negotiations"""
        while self.running:
            try:
                # Check for expired negotiations
                current_time = datetime.now()
                expired_proposals = []
                
                for proposal_id, proposal in list(self.active_negotiations.items()):
                    if current_time > proposal.expires_at:
                        expired_proposals.append(proposal)
                
                # Process expired proposals
                for proposal in expired_proposals:
                    proposal.state = NegotiationState.EXPIRED
                    self._finalize_negotiation(proposal, False, "Negotiation expired")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Negotiation worker error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def _reliability_worker(self):
        """Background worker for updating reliability metrics"""
        while self.running:
            try:
                # Update reliability metrics periodically
                # This could include more sophisticated calculations
                time.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Reliability worker error: {e}")
                time.sleep(600)  # Wait 10 minutes on error
    
    def _cleanup_worker(self):
        """Background worker for cleaning up old data"""
        while self.running:
            try:
                # Clean up old negotiations
                cutoff_time = datetime.now() - timedelta(days=7)
                
                with sqlite3.connect(self.db_path) as conn:
                    # Archive old completed negotiations
                    conn.execute("""
                        UPDATE negotiation_proposals 
                        SET state = 'archived' 
                        WHERE state IN ('accepted', 'rejected', 'expired', 'arbitrated', 'deferred') 
                        AND created_at < ?
                    """, (cutoff_time.isoformat(),))
                    
                    conn.commit()
                
                time.sleep(3600)  # Run cleanup every hour
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Proposal counts by state
            cursor = conn.execute("""
                SELECT state, COUNT(*) as count 
                FROM negotiation_proposals 
                GROUP BY state
            """)
            proposal_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Outcome counts
            cursor = conn.execute("""
                SELECT agreement_reached, COUNT(*) as count 
                FROM negotiation_outcomes 
                GROUP BY agreement_reached
            """)
            outcome_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Agent reliability summary
            cursor = conn.execute("""
                SELECT trust_level, COUNT(*) as count, AVG(success_rate) as avg_success
                FROM agent_reliability 
                GROUP BY trust_level
            """)
            reliability_summary = {}
            for row in cursor.fetchall():
                reliability_summary[row[0]] = {
                    "count": row[1],
                    "avg_success_rate": row[2]
                }
        
        return {
            'active_negotiations': len(self.active_negotiations),
            'proposal_counts': proposal_counts,
            'outcome_counts': outcome_counts,
            'reliability_summary': reliability_summary,
            'total_agents': len(self.agent_reliability)
        }
    
    def shutdown(self):
        """Shutdown the negotiation engine"""
        self.running = False
        
        # Wait for background threads to finish
        if self.negotiation_worker.is_alive():
            self.negotiation_worker.join(timeout=5)
        if self.reliability_worker.is_alive():
            self.reliability_worker.join(timeout=5)
        if self.cleanup_worker.is_alive():
            self.cleanup_worker.join(timeout=5)
        
        logger.info("Agent Negotiation Engine shutdown complete")
