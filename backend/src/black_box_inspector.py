#!/usr/bin/env python3
"""
Black Box Inspector Module - Priority 23
Unified tracing, debugging, and root cause analysis framework
"""

import json
import sqlite3
import threading
import time
import uuid
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import logging
import hashlib
import inspect
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TraceType(Enum):
    """Types of system traces"""
    AGENT_EXECUTION = "agent_execution"
    LLM_CALL = "llm_call"
    MEMORY_ACCESS = "memory_access"
    FUNCTION_CALL = "function_call"
    DECISION_BRANCH = "decision_branch"
    ERROR = "error"
    PERFORMANCE = "performance"
    INTER_AGENT = "inter_agent"
    SYSTEM_EVENT = "system_event"
    ANOMALY = "anomaly"

class TraceLevel(Enum):
    """Trace detail levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    VERBOSE = "verbose"
    DEBUG = "debug"

class AnomalyType(Enum):
    """Types of anomalies"""
    LLM_OUTPUT_DEVIATION = "llm_output_deviation"
    AGENT_BEHAVIOR_CHANGE = "agent_behavior_change"
    MEMORY_RETRIEVAL_ISSUE = "memory_retrieval_issue"
    PERFORMANCE_SPIKE = "performance_spike"
    ERROR_PATTERN = "error_pattern"
    MODEL_SWITCHING = "model_switching"
    TOKEN_USAGE_ANOMALY = "token_usage_anomaly"
    LATENCY_ANOMALY = "latency_anomaly"

class RootCauseCategory(Enum):
    """Root cause categories"""
    PROMPT_ISSUE = "prompt_issue"
    MEMORY_CONTEXT = "memory_context"
    AGENT_LOGIC = "agent_logic"
    LLM_MODEL = "llm_model"
    API_FAILURE = "api_failure"
    DATA_QUALITY = "data_quality"
    SYSTEM_RESOURCE = "system_resource"
    CONFIGURATION = "configuration"


class InspectionType(str, Enum):
    """Types of inspections"""
    TRACE = "trace"
    MEMORY = "memory"
    PROMPT = "prompt"
    LATENT = "latent"
    ROOT_CAUSE = "root_cause"


@dataclass
class InspectionResult:
    """Result of an inspection"""
    inspection_id: str
    inspection_type: InspectionType
    target_id: str
    target_type: str
    findings: Dict[str, Any]
    recommendations: List[str]
    severity: str
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class TraceEvent:
    """Individual trace event"""
    trace_id: str
    timestamp: datetime
    trace_type: TraceType
    component_id: str
    component_type: str
    session_id: Optional[str]
    system_id: Optional[str]
    agent_id: Optional[str]
    llm_model: Optional[str]
    function_name: Optional[str]
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    duration_ms: Optional[float]
    error: Optional[str]
    trace_level: TraceLevel
    parent_trace_id: Optional[str]
    correlation_id: Optional[str]

@dataclass
class LLMReasoningRecord:
    """LLM prompt-response reasoning record"""
    record_id: str
    timestamp: datetime
    model: str
    temperature: float
    max_tokens: int
    prompt: str
    response: str
    token_usage: Dict[str, int]
    cost_usd: float
    confidence_score: Optional[float]
    agent_context: Optional[Dict[str, Any]]
    goal_context: Optional[Dict[str, Any]]
    memory_context: Optional[Dict[str, Any]]
    session_id: Optional[str]
    system_id: Optional[str]
    trace_id: str
    metadata: Dict[str, Any]

@dataclass
class AgentExecutionTrace:
    """Agent execution trace"""
    trace_id: str
    agent_id: str
    agent_type: str
    start_time: datetime
    end_time: Optional[datetime]
    function_calls: List[Dict[str, Any]]
    decision_branches: List[Dict[str, Any]]
    memory_operations: List[Dict[str, Any]]
    inter_agent_messages: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    retries: int
    session_id: Optional[str]
    system_id: Optional[str]
    goal: Optional[str]
    status: str
    metadata: Dict[str, Any]

@dataclass
class RootCauseAnalysis:
    """Root cause analysis result"""
    analysis_id: str
    timestamp: datetime
    error_id: Optional[str]
    system_id: Optional[str]
    session_id: Optional[str]
    primary_cause: RootCauseCategory
    contributing_factors: List[Dict[str, Any]]
    cause_chain: List[Dict[str, Any]]
    blame_attribution: Dict[str, float]
    suggested_prevention: List[str]
    confidence_score: float
    trace_ids: List[str]
    metadata: Dict[str, Any]

@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    anomaly_id: str
    timestamp: datetime
    anomaly_type: AnomalyType
    component_id: str
    component_type: str
    severity: str
    description: str
    baseline_value: Any
    current_value: Any
    deviation_percentage: float
    confidence_score: float
    suggested_action: str
    system_id: Optional[str]
    session_id: Optional[str]
    trace_ids: List[str]
    metadata: Dict[str, Any]

@dataclass
class LLMPerformanceMetrics:
    """LLM performance metrics"""
    model: str
    timestamp: datetime
    avg_latency_ms: float
    avg_cost_usd: float
    avg_token_usage: int
    success_rate: float
    failure_count: int
    anomaly_count: int
    model_switches: int
    outlier_prompts: int
    session_id: Optional[str]
    system_id: Optional[str]

class BlackBoxInspector:
    """
    Unified Black Box Inspector providing comprehensive tracing and debugging
    """
    
    def __init__(self, base_dir: Path, memory_system, agent_orchestrator, 
                 system_lifecycle, predictive_intelligence, self_healing, 
                 diagnostics_engine, llm_factory):
        self.base_dir = base_dir
        self.memory_system = memory_system
        self.agent_orchestrator = agent_orchestrator
        self.system_lifecycle = system_lifecycle
        self.predictive_intelligence = predictive_intelligence
        self.self_healing = self_healing
        self.diagnostics_engine = diagnostics_engine
        self.llm_factory = llm_factory
        
        # Database setup
        self.db_path = base_dir / "data" / "black_box_inspector.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # Active traces
        self.active_traces = {}
        self.trace_stack = {}
        
        # Performance tracking
        self.performance_baselines = {}
        self.anomaly_thresholds = {}
        
        # Background processing
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._background_processing, daemon=True)
        self.processing_thread.start()
        
        # Subscribers for real-time updates
        self.subscribers = {}
        
        logger.info("Black Box Inspector initialized")
    
    def _init_database(self):
        """Initialize black box inspector database"""
        with sqlite3.connect(self.db_path) as conn:
            # Trace events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trace_events (
                    trace_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    trace_type TEXT NOT NULL,
                    component_id TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    session_id TEXT,
                    system_id TEXT,
                    agent_id TEXT,
                    llm_model TEXT,
                    function_name TEXT,
                    payload TEXT,
                    metadata TEXT,
                    duration_ms REAL,
                    error TEXT,
                    trace_level TEXT NOT NULL,
                    parent_trace_id TEXT,
                    correlation_id TEXT
                )
            """)
            
            # LLM reasoning records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_reasoning_records (
                    record_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    model TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    max_tokens INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    token_usage TEXT NOT NULL,
                    cost_usd REAL NOT NULL,
                    confidence_score REAL,
                    agent_context TEXT,
                    goal_context TEXT,
                    memory_context TEXT,
                    session_id TEXT,
                    system_id TEXT,
                    trace_id TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Agent execution traces table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_execution_traces (
                    trace_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    function_calls TEXT,
                    decision_branches TEXT,
                    memory_operations TEXT,
                    inter_agent_messages TEXT,
                    errors TEXT,
                    retries INTEGER DEFAULT 0,
                    session_id TEXT,
                    system_id TEXT,
                    goal TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Root cause analysis table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS root_cause_analysis (
                    analysis_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    error_id TEXT,
                    system_id TEXT,
                    session_id TEXT,
                    primary_cause TEXT NOT NULL,
                    contributing_factors TEXT,
                    cause_chain TEXT,
                    blame_attribution TEXT,
                    suggested_prevention TEXT,
                    confidence_score REAL NOT NULL,
                    trace_ids TEXT,
                    metadata TEXT
                )
            """)
            
            # Anomaly detection table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS anomaly_detections (
                    anomaly_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    component_id TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    baseline_value TEXT,
                    current_value TEXT,
                    deviation_percentage REAL NOT NULL,
                    confidence_score REAL NOT NULL,
                    suggested_action TEXT NOT NULL,
                    system_id TEXT,
                    session_id TEXT,
                    trace_ids TEXT,
                    metadata TEXT
                )
            """)
            
            # LLM performance metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    avg_latency_ms REAL NOT NULL,
                    avg_cost_usd REAL NOT NULL,
                    avg_token_usage INTEGER NOT NULL,
                    success_rate REAL NOT NULL,
                    failure_count INTEGER DEFAULT 0,
                    anomaly_count INTEGER DEFAULT 0,
                    model_switches INTEGER DEFAULT 0,
                    outlier_prompts INTEGER DEFAULT 0,
                    session_id TEXT,
                    system_id TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_timestamp ON trace_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_type ON trace_events(trace_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_component ON trace_events(component_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_session ON trace_events(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_system ON trace_events(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_correlation ON trace_events(correlation_id)")
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_timestamp ON llm_reasoning_records(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_model ON llm_reasoning_records(model)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_trace ON llm_reasoning_records(trace_id)")
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_trace_id ON agent_execution_traces(trace_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_start_time ON agent_execution_traces(start_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_status ON agent_execution_traces(status)")
            
            conn.commit()
    
    @contextmanager
    def trace_execution(self, trace_type: TraceType, component_id: str, 
                       component_type: str, session_id: Optional[str] = None,
                       system_id: Optional[str] = None, agent_id: Optional[str] = None,
                       llm_model: Optional[str] = None, function_name: Optional[str] = None,
                       trace_level: TraceLevel = TraceLevel.DETAILED,
                       parent_trace_id: Optional[str] = None,
                       correlation_id: Optional[str] = None):
        """Context manager for tracing execution"""
        trace_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Create trace event
        trace_event = TraceEvent(
            trace_id=trace_id,
            timestamp=start_time,
            trace_type=trace_type,
            component_id=component_id,
            component_type=component_type,
            session_id=session_id,
            system_id=system_id,
            agent_id=agent_id,
            llm_model=llm_model,
            function_name=function_name,
            payload={},
            metadata={},
            duration_ms=None,
            error=None,
            trace_level=trace_level,
            parent_trace_id=parent_trace_id,
            correlation_id=correlation_id
        )
        
        # Store initial trace
        self._store_trace_event(trace_event)
        
        # Track active trace
        self.active_traces[trace_id] = trace_event
        
        try:
            yield trace_id
        except Exception as e:
            # Update trace with error
            trace_event.error = str(e)
            trace_event.payload = {"error_traceback": traceback.format_exc()}
            self._store_trace_event(trace_event)
            raise
        finally:
            # Update trace with completion
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            trace_event.duration_ms = duration_ms
            self._store_trace_event(trace_event)
            
            # Remove from active traces
            if trace_id in self.active_traces:
                del self.active_traces[trace_id]
    
    def log_trace_event(self, trace_type: TraceType, component_id: str, 
                       component_type: str, payload: Dict[str, Any],
                       session_id: Optional[str] = None, system_id: Optional[str] = None,
                       agent_id: Optional[str] = None, llm_model: Optional[str] = None,
                       function_name: Optional[str] = None, error: Optional[str] = None,
                       trace_level: TraceLevel = TraceLevel.BASIC,
                       parent_trace_id: Optional[str] = None,
                       correlation_id: Optional[str] = None) -> str:
        """Log a trace event"""
        trace_id = str(uuid.uuid4())
        
        trace_event = TraceEvent(
            trace_id=trace_id,
            timestamp=datetime.now(),
            trace_type=trace_type,
            component_id=component_id,
            component_type=component_type,
            session_id=session_id,
            system_id=system_id,
            agent_id=agent_id,
            llm_model=llm_model,
            function_name=function_name,
            payload=payload,
            metadata={},
            duration_ms=None,
            error=error,
            trace_level=trace_level,
            parent_trace_id=parent_trace_id,
            correlation_id=correlation_id
        )
        
        self._store_trace_event(trace_event)
        return trace_id
    
    def log_llm_reasoning(self, model: str, temperature: float, max_tokens: int,
                         prompt: str, response: str, token_usage: Dict[str, int],
                         cost_usd: float, trace_id: str,
                         confidence_score: Optional[float] = None,
                         agent_context: Optional[Dict[str, Any]] = None,
                         goal_context: Optional[Dict[str, Any]] = None,
                         memory_context: Optional[Dict[str, Any]] = None,
                         session_id: Optional[str] = None,
                         system_id: Optional[str] = None) -> str:
        """Log LLM reasoning record"""
        record_id = str(uuid.uuid4())
        
        reasoning_record = LLMReasoningRecord(
            record_id=record_id,
            timestamp=datetime.now(),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt=prompt,
            response=response,
            token_usage=token_usage,
            cost_usd=cost_usd,
            confidence_score=confidence_score,
            agent_context=agent_context,
            goal_context=goal_context,
            memory_context=memory_context,
            session_id=session_id,
            system_id=system_id,
            trace_id=trace_id,
            metadata={}
        )
        
        self._store_llm_reasoning_record(reasoning_record)
        
        # Check for anomalies
        self._check_llm_anomalies(reasoning_record)
        
        return record_id
    
    def start_agent_trace(self, agent_id: str, agent_type: str,
                         session_id: Optional[str] = None, system_id: Optional[str] = None,
                         goal: Optional[str] = None) -> str:
        """Start agent execution trace"""
        trace_id = str(uuid.uuid4())
        
        agent_trace = AgentExecutionTrace(
            trace_id=trace_id,
            agent_id=agent_id,
            agent_type=agent_type,
            start_time=datetime.now(),
            end_time=None,
            function_calls=[],
            decision_branches=[],
            memory_operations=[],
            inter_agent_messages=[],
            errors=[],
            retries=0,
            session_id=session_id,
            system_id=system_id,
            goal=goal,
            status="running",
            metadata={}
        )
        
        self._store_agent_execution_trace(agent_trace)
        return trace_id
    
    def update_agent_trace(self, trace_id: str, function_call: Optional[Dict[str, Any]] = None,
                          decision_branch: Optional[Dict[str, Any]] = None,
                          memory_operation: Optional[Dict[str, Any]] = None,
                          inter_agent_message: Optional[Dict[str, Any]] = None,
                          error: Optional[Dict[str, Any]] = None,
                          retry: bool = False):
        """Update agent execution trace"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current trace
                cursor = conn.execute("""
                    SELECT * FROM agent_execution_traces WHERE trace_id = ?
                """, (trace_id,))
                row = cursor.fetchone()
                
                if not row:
                    return
                
                # Parse existing data
                function_calls = json.loads(row[4]) if row[4] else []
                decision_branches = json.loads(row[5]) if row[5] else []
                memory_operations = json.loads(row[6]) if row[6] else []
                inter_agent_messages = json.loads(row[7]) if row[7] else []
                errors = json.loads(row[8]) if row[8] else []
                retries = row[9]
                
                # Update with new data
                if function_call:
                    function_calls.append(function_call)
                if decision_branch:
                    decision_branches.append(decision_branch)
                if memory_operation:
                    memory_operations.append(memory_operation)
                if inter_agent_message:
                    inter_agent_messages.append(inter_agent_message)
                if error:
                    errors.append(error)
                if retry:
                    retries += 1
                
                # Update database
                conn.execute("""
                    UPDATE agent_execution_traces 
                    SET function_calls = ?, decision_branches = ?, memory_operations = ?,
                        inter_agent_messages = ?, errors = ?, retries = ?
                    WHERE trace_id = ?
                """, (
                    json.dumps(function_calls), json.dumps(decision_branches),
                    json.dumps(memory_operations), json.dumps(inter_agent_messages),
                    json.dumps(errors), retries, trace_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating agent trace: {e}")
    
    def end_agent_trace(self, trace_id: str, status: str = "completed"):
        """End agent execution trace"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE agent_execution_traces 
                    SET end_time = ?, status = ?
                    WHERE trace_id = ?
                """, (datetime.now().isoformat(), status, trace_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Error ending agent trace: {e}")
    
    def analyze_root_cause(self, error_id: Optional[str] = None, system_id: Optional[str] = None,
                          session_id: Optional[str] = None, trace_ids: Optional[List[str]] = None) -> RootCauseAnalysis:
        """Analyze root cause of an error or issue"""
        analysis_id = str(uuid.uuid4())
        
        # Get relevant traces
        if not trace_ids:
            trace_ids = self._get_relevant_trace_ids(error_id, system_id, session_id)
        
        # Analyze cause chain
        cause_chain = self._build_cause_chain(trace_ids)
        
        # Determine primary cause
        primary_cause = self._determine_primary_cause(cause_chain)
        
        # Calculate blame attribution
        blame_attribution = self._calculate_blame_attribution(trace_ids)
        
        # Generate prevention suggestions
        suggested_prevention = self._generate_prevention_suggestions(primary_cause, cause_chain)
        
        # Calculate confidence
        confidence_score = self._calculate_analysis_confidence(cause_chain, blame_attribution)
        
        analysis = RootCauseAnalysis(
            analysis_id=analysis_id,
            timestamp=datetime.now(),
            error_id=error_id,
            system_id=system_id,
            session_id=session_id,
            primary_cause=primary_cause,
            contributing_factors=cause_chain,
            cause_chain=cause_chain,
            blame_attribution=blame_attribution,
            suggested_prevention=suggested_prevention,
            confidence_score=confidence_score,
            trace_ids=trace_ids,
            metadata={}
        )
        
        self._store_root_cause_analysis(analysis)
        return analysis
    
    def detect_anomalies(self, component_id: Optional[str] = None,
                        component_type: Optional[str] = None,
                        system_id: Optional[str] = None) -> List[AnomalyDetection]:
        """Detect anomalies in system behavior"""
        anomalies = []
        
        # Check LLM output deviations
        llm_anomalies = self._detect_llm_anomalies(component_id, system_id)
        anomalies.extend(llm_anomalies)
        
        # Check agent behavior changes
        agent_anomalies = self._detect_agent_anomalies(component_id, system_id)
        anomalies.extend(agent_anomalies)
        
        # Check memory retrieval issues
        memory_anomalies = self._detect_memory_anomalies(component_id, system_id)
        anomalies.extend(memory_anomalies)
        
        # Check performance spikes
        performance_anomalies = self._detect_performance_anomalies(component_id, system_id)
        anomalies.extend(performance_anomalies)
        
        # Store anomalies
        for anomaly in anomalies:
            self._store_anomaly_detection(anomaly)
        
        return anomalies
    
    def get_trace_timeline(self, start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          trace_types: Optional[List[TraceType]] = None,
                          component_ids: Optional[List[str]] = None,
                          session_id: Optional[str] = None,
                          system_id: Optional[str] = None,
                          limit: int = 1000) -> List[TraceEvent]:
        """Get timeline of trace events"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM trace_events WHERE 1=1"
                params = []
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.isoformat())
                
                if trace_types:
                    placeholders = ','.join(['?' for _ in trace_types])
                    query += f" AND trace_type IN ({placeholders})"
                    params.extend([t.value for t in trace_types])
                
                if component_ids:
                    placeholders = ','.join(['?' for _ in component_ids])
                    query += f" AND component_id IN ({placeholders})"
                    params.extend(component_ids)
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if system_id:
                    query += " AND system_id = ?"
                    params.append(system_id)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                events = []
                for row in cursor.fetchall():
                    event = TraceEvent(
                        trace_id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        trace_type=TraceType(row[2]),
                        component_id=row[3],
                        component_type=row[4],
                        session_id=row[5],
                        system_id=row[6],
                        agent_id=row[7],
                        llm_model=row[8],
                        function_name=row[9],
                        payload=json.loads(row[10]) if row[10] else {},
                        metadata=json.loads(row[11]) if row[11] else {},
                        duration_ms=row[12],
                        error=row[13],
                        trace_level=TraceLevel(row[14]),
                        parent_trace_id=row[15],
                        correlation_id=row[16]
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Error getting trace timeline: {e}")
            return []
    
    def get_llm_reasoning_log(self, model: Optional[str] = None,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             session_id: Optional[str] = None,
                             system_id: Optional[str] = None,
                             limit: int = 100) -> List[LLMReasoningRecord]:
        """Get LLM reasoning log"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM llm_reasoning_records WHERE 1=1"
                params = []
                
                if model:
                    query += " AND model = ?"
                    params.append(model)
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.isoformat())
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if system_id:
                    query += " AND system_id = ?"
                    params.append(system_id)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                records = []
                for row in cursor.fetchall():
                    record = LLMReasoningRecord(
                        record_id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        model=row[2],
                        temperature=row[3],
                        max_tokens=row[4],
                        prompt=row[5],
                        response=row[6],
                        token_usage=json.loads(row[7]),
                        cost_usd=row[8],
                        confidence_score=row[9],
                        agent_context=json.loads(row[10]) if row[10] else None,
                        goal_context=json.loads(row[11]) if row[11] else None,
                        memory_context=json.loads(row[12]) if row[12] else None,
                        session_id=row[13],
                        system_id=row[14],
                        trace_id=row[15],
                        metadata=json.loads(row[16]) if row[16] else {}
                    )
                    records.append(record)
                
                return records
                
        except Exception as e:
            logger.error(f"Error getting LLM reasoning log: {e}")
            return []
    
    def _store_trace_event(self, event: TraceEvent):
        """Store trace event in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO trace_events 
                    (trace_id, timestamp, trace_type, component_id, component_type,
                     session_id, system_id, agent_id, llm_model, function_name,
                     payload, metadata, duration_ms, error, trace_level, parent_trace_id, correlation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.trace_id, event.timestamp.isoformat(), event.trace_type.value,
                    event.component_id, event.component_type, event.session_id, event.system_id,
                    event.agent_id, event.llm_model, event.function_name,
                    json.dumps(event.payload), json.dumps(event.metadata),
                    event.duration_ms, event.error, event.trace_level.value,
                    event.parent_trace_id, event.correlation_id
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing trace event: {e}")
    
    def _store_llm_reasoning_record(self, record: LLMReasoningRecord):
        """Store LLM reasoning record in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO llm_reasoning_records 
                    (record_id, timestamp, model, temperature, max_tokens, prompt, response,
                     token_usage, cost_usd, confidence_score, agent_context, goal_context,
                     memory_context, session_id, system_id, trace_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.record_id, record.timestamp.isoformat(), record.model,
                    record.temperature, record.max_tokens, record.prompt, record.response,
                    json.dumps(record.token_usage), record.cost_usd, record.confidence_score,
                    json.dumps(record.agent_context) if record.agent_context else None,
                    json.dumps(record.goal_context) if record.goal_context else None,
                    json.dumps(record.memory_context) if record.memory_context else None,
                    record.session_id, record.system_id, record.trace_id,
                    json.dumps(record.metadata)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing LLM reasoning record: {e}")
    
    def _store_agent_execution_trace(self, trace: AgentExecutionTrace):
        """Store agent execution trace in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO agent_execution_traces 
                    (trace_id, agent_id, agent_type, start_time, end_time, function_calls,
                     decision_branches, memory_operations, inter_agent_messages, errors,
                     retries, session_id, system_id, goal, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trace.trace_id, trace.agent_id, trace.agent_type,
                    trace.start_time.isoformat(), trace.end_time.isoformat() if trace.end_time else None,
                    json.dumps(trace.function_calls), json.dumps(trace.decision_branches),
                    json.dumps(trace.memory_operations), json.dumps(trace.inter_agent_messages),
                    json.dumps(trace.errors), trace.retries, trace.session_id, trace.system_id,
                    trace.goal, trace.status, json.dumps(trace.metadata)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing agent execution trace: {e}")
    
    def _store_root_cause_analysis(self, analysis: RootCauseAnalysis):
        """Store root cause analysis in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO root_cause_analysis 
                    (analysis_id, timestamp, error_id, system_id, session_id, primary_cause,
                     contributing_factors, cause_chain, blame_attribution, suggested_prevention,
                     confidence_score, trace_ids, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis.analysis_id, analysis.timestamp.isoformat(), analysis.error_id,
                    analysis.system_id, analysis.session_id, analysis.primary_cause.value,
                    json.dumps(analysis.contributing_factors), json.dumps(analysis.cause_chain),
                    json.dumps(analysis.blame_attribution), json.dumps(analysis.suggested_prevention),
                    analysis.confidence_score, json.dumps(analysis.trace_ids),
                    json.dumps(analysis.metadata)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing root cause analysis: {e}")
    
    def _store_anomaly_detection(self, anomaly: AnomalyDetection):
        """Store anomaly detection in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO anomaly_detections 
                    (anomaly_id, timestamp, anomaly_type, component_id, component_type,
                     severity, description, baseline_value, current_value, deviation_percentage,
                     confidence_score, suggested_action, system_id, session_id, trace_ids, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    anomaly.anomaly_id, anomaly.timestamp.isoformat(), anomaly.anomaly_type.value,
                    anomaly.component_id, anomaly.component_type, anomaly.severity,
                    anomaly.description, json.dumps(anomaly.baseline_value),
                    json.dumps(anomaly.current_value), anomaly.deviation_percentage,
                    anomaly.confidence_score, anomaly.suggested_action, anomaly.system_id,
                    anomaly.session_id, json.dumps(anomaly.trace_ids), json.dumps(anomaly.metadata)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing anomaly detection: {e}")
    
    def _check_llm_anomalies(self, reasoning_record: LLMReasoningRecord):
        """Check for LLM anomalies"""
        # Check for unusual token usage
        total_tokens = reasoning_record.token_usage.get('total_tokens', 0)
        baseline_tokens = self.performance_baselines.get(f"{reasoning_record.model}_tokens", 1000)
        
        if total_tokens > baseline_tokens * 2:
            anomaly = AnomalyDetection(
                anomaly_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                anomaly_type=AnomalyType.TOKEN_USAGE_ANOMALY,
                component_id=reasoning_record.model,
                component_type="llm_model",
                severity="warning",
                description=f"Unusual token usage: {total_tokens} vs baseline {baseline_tokens}",
                baseline_value=baseline_tokens,
                current_value=total_tokens,
                deviation_percentage=((total_tokens - baseline_tokens) / baseline_tokens) * 100,
                confidence_score=0.8,
                suggested_action="Review prompt length and complexity",
                system_id=reasoning_record.system_id,
                session_id=reasoning_record.session_id,
                trace_ids=[reasoning_record.trace_id],
                metadata={}
            )
            self._store_anomaly_detection(anomaly)
    
    def _get_relevant_trace_ids(self, error_id: Optional[str], system_id: Optional[str],
                               session_id: Optional[str]) -> List[str]:
        """Get relevant trace IDs for analysis"""
        # Implementation would query traces based on error, system, or session
        # For now, return recent traces
        recent_traces = self.get_trace_timeline(
            start_time=datetime.now() - timedelta(hours=1),
            system_id=system_id,
            session_id=session_id,
            limit=100
        )
        return [trace.trace_id for trace in recent_traces]
    
    def _build_cause_chain(self, trace_ids: List[str]) -> List[Dict[str, Any]]:
        """Build cause chain from trace IDs"""
        # Implementation would analyze traces to build cause chain
        # For now, return mock data
        return [
            {"step": 1, "component": "memory", "action": "context_retrieval", "result": "success"},
            {"step": 2, "component": "agent", "action": "decision_making", "result": "success"},
            {"step": 3, "component": "llm", "action": "reasoning", "result": "failure"}
        ]
    
    def _determine_primary_cause(self, cause_chain: List[Dict[str, Any]]) -> RootCauseCategory:
        """Determine primary cause from cause chain"""
        # Implementation would analyze cause chain to determine primary cause
        # For now, return a default
        return RootCauseCategory.LLM_MODEL
    
    def _calculate_blame_attribution(self, trace_ids: List[str]) -> Dict[str, float]:
        """Calculate blame attribution matrix"""
        # Implementation would analyze traces to calculate blame
        # For now, return mock data
        return {
            "llm_model": 0.6,
            "agent_logic": 0.2,
            "memory_context": 0.1,
            "system_resource": 0.1
        }
    
    def _generate_prevention_suggestions(self, primary_cause: RootCauseCategory,
                                       cause_chain: List[Dict[str, Any]]) -> List[str]:
        """Generate prevention suggestions"""
        suggestions = []
        
        if primary_cause == RootCauseCategory.LLM_MODEL:
            suggestions.extend([
                "Add fallback model configuration",
                "Implement prompt validation",
                "Add response quality checks"
            ])
        elif primary_cause == RootCauseCategory.MEMORY_CONTEXT:
            suggestions.extend([
                "Improve memory retrieval algorithms",
                "Add context validation",
                "Implement memory fallbacks"
            ])
        
        return suggestions
    
    def _calculate_analysis_confidence(self, cause_chain: List[Dict[str, Any]],
                                     blame_attribution: Dict[str, float]) -> float:
        """Calculate analysis confidence score"""
        # Implementation would calculate confidence based on data quality
        # For now, return a default
        return 0.85
    
    def _detect_llm_anomalies(self, component_id: Optional[str],
                             system_id: Optional[str]) -> List[AnomalyDetection]:
        """Detect LLM-related anomalies"""
        # Implementation would detect LLM anomalies
        # For now, return empty list
        return []
    
    def _detect_agent_anomalies(self, component_id: Optional[str],
                               system_id: Optional[str]) -> List[AnomalyDetection]:
        """Detect agent behavior anomalies"""
        # Implementation would detect agent anomalies
        # For now, return empty list
        return []
    
    def _detect_memory_anomalies(self, component_id: Optional[str],
                                system_id: Optional[str]) -> List[AnomalyDetection]:
        """Detect memory retrieval anomalies"""
        # Implementation would detect memory anomalies
        # For now, return empty list
        return []
    
    def _detect_performance_anomalies(self, component_id: Optional[str],
                                     system_id: Optional[str]) -> List[AnomalyDetection]:
        """Detect performance anomalies"""
        # Implementation would detect performance anomalies
        # For now, return empty list
        return []
    
    def _background_processing(self):
        """Background processing for anomaly detection and cleanup"""
        while self.processing_active:
            try:
                # Detect anomalies
                self.detect_anomalies()
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(300)  # Process every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in background processing: {e}")
                time.sleep(600)  # Wait 10 minutes on error
    
    def _cleanup_old_data(self, days: int = 30):
        """Clean up old trace data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM trace_events WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                conn.execute("""
                    DELETE FROM llm_reasoning_records WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                conn.commit()
                
            logger.info(f"Cleaned up trace data older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def stop_processing(self):
        """Stop background processing"""
        self.processing_active = False
        if self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
