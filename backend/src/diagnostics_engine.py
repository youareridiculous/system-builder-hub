#!/usr/bin/env python3
"""
Diagnostics Engine Module - Priority 22
Visual diagnostics, component interconnections, health scoring, and auto-fix capabilities
"""

import json
import sqlite3
import threading
import time
import uuid
import os
import shutil
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
import logging
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IssueType(Enum):
    """Types of diagnostic issues"""
    STALE_COMPONENT = "stale_component"
    UNLINKED_COMPONENT = "unlinked_component"
    ORPHANED_FILE = "orphaned_file"
    DUPLICATE_CODE = "duplicate_code"
    MISCONFIGURED_ROUTE = "misconfigured_route"
    MISLINKED_AGENT = "mislinked_agent"
    MISSING_HANDLER = "missing_handler"
    FILE_DUPLICATION = "file_duplication"
    MEMORY_LEAK = "memory_leak"
    PERFORMANCE_ISSUE = "performance_issue"

class IssueSeverity(Enum):
    """Issue severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FixStatus(Enum):
    """Fix status for issues"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class DiagnosticIssue:
    """Individual diagnostic issue"""
    issue_id: str
    issue_type: IssueType
    severity: IssueSeverity
    title: str
    description: str
    system_id: Optional[str]
    component_id: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    detected_at: datetime
    fix_status: FixStatus
    fix_description: Optional[str]
    auto_fixable: bool
    metadata: Dict[str, Any]

@dataclass
class ComponentNode:
    """Component node for interconnection mapping"""
    component_id: str
    component_type: str
    name: str
    status: str
    system_id: str
    dependencies: List[str]
    dependents: List[str]
    metadata: Dict[str, Any]

@dataclass
class SystemHealthScore:
    """System health score calculation"""
    system_id: str
    integrity_score: float
    connectivity_score: float
    error_rate_score: float
    optimization_score: float
    overall_score: float
    calculated_at: datetime
    issues_count: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int

@dataclass
class FixSuggestion:
    """Auto-fix suggestion"""
    suggestion_id: str
    issue_id: str
    title: str
    description: str
    fix_action: str
    confidence: float
    risk_level: str
    estimated_time: int  # seconds
    prerequisites: List[str]
    rollback_plan: str

class DiagnosticsEngine:
    """
    Diagnostics Engine providing comprehensive system diagnostics and health scoring
    """
    
    def __init__(self, base_dir: Path, memory_system, agent_orchestrator, 
                 system_lifecycle, self_healing, access_control):
        self.base_dir = base_dir
        self.memory_system = memory_system
        self.agent_orchestrator = agent_orchestrator
        self.system_lifecycle = system_lifecycle
        self.self_healing = self_healing
        self.access_control = access_control
        
        # Database setup
        self.db_path = base_dir / "data" / "diagnostics.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # Component graph for interconnections
        self.component_graph = nx.DiGraph()
        
        # Background scanning
        self.scanning_active = True
        self.scan_thread = threading.Thread(target=self._background_scan, daemon=True)
        self.scan_thread.start()
        
        # Issue cache
        self.issue_cache = {}
        self.health_cache = {}
        
        logger.info("Diagnostics Engine initialized")
    
    def _init_database(self):
        """Initialize diagnostics database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS diagnostic_issues (
                    issue_id TEXT PRIMARY KEY,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    system_id TEXT,
                    component_id TEXT,
                    file_path TEXT,
                    line_number INTEGER,
                    detected_at TIMESTAMP,
                    fix_status TEXT DEFAULT 'pending',
                    fix_description TEXT,
                    auto_fixable BOOLEAN DEFAULT FALSE,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS component_nodes (
                    component_id TEXT PRIMARY KEY,
                    component_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    system_id TEXT NOT NULL,
                    dependencies TEXT,
                    dependents TEXT,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_health_scores (
                    system_id TEXT PRIMARY KEY,
                    integrity_score REAL DEFAULT 0.0,
                    connectivity_score REAL DEFAULT 0.0,
                    error_rate_score REAL DEFAULT 0.0,
                    optimization_score REAL DEFAULT 0.0,
                    overall_score REAL DEFAULT 0.0,
                    calculated_at TIMESTAMP,
                    issues_count INTEGER DEFAULT 0,
                    critical_issues INTEGER DEFAULT 0,
                    high_issues INTEGER DEFAULT 0,
                    medium_issues INTEGER DEFAULT 0,
                    low_issues INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fix_suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    fix_action TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    risk_level TEXT DEFAULT 'low',
                    estimated_time INTEGER DEFAULT 0,
                    prerequisites TEXT,
                    rollback_plan TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_issue_type ON diagnostic_issues(issue_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON diagnostic_issues(severity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_id ON diagnostic_issues(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fix_status ON diagnostic_issues(fix_status)")
            
            conn.commit()
    
    def scan_system(self, system_id: str) -> List[DiagnosticIssue]:
        """Perform comprehensive system scan"""
        try:
            issues = []
            
            # Scan for different types of issues
            issues.extend(self._scan_stale_components(system_id))
            issues.extend(self._scan_unlinked_components(system_id))
            issues.extend(self._scan_orphaned_files(system_id))
            issues.extend(self._scan_duplicate_code(system_id))
            issues.extend(self._scan_misconfigured_routes(system_id))
            issues.extend(self._scan_mislinked_agents(system_id))
            issues.extend(self._scan_missing_handlers(system_id))
            issues.extend(self._scan_file_duplication(system_id))
            issues.extend(self._scan_memory_leaks(system_id))
            issues.extend(self._scan_performance_issues(system_id))
            
            # Store issues in database
            for issue in issues:
                self._store_issue(issue)
            
            # Update component graph
            self._update_component_graph(system_id)
            
            # Calculate health score
            self._calculate_health_score(system_id)
            
            logger.info(f"System scan completed for {system_id}: {len(issues)} issues found")
            return issues
            
        except Exception as e:
            logger.error(f"Error scanning system {system_id}: {e}")
            return []
    
    def _scan_stale_components(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for stale or unused components"""
        issues = []
        try:
            # Mock implementation - would check actual component usage
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"stale_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.STALE_COMPONENT,
                    severity=IssueSeverity.MEDIUM,
                    title="Stale Component Detected",
                    description="Component has not been used in the last 30 days",
                    system_id=system_id,
                    component_id="comp_123",
                    file_path=None,
                    line_number=None,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Consider removing or updating the component",
                    auto_fixable=True,
                    metadata={"last_used": "2024-01-01", "usage_count": 0}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning stale components: {e}")
        return issues
    
    def _scan_unlinked_components(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for unlinked components"""
        issues = []
        try:
            # Mock implementation - would check component dependencies
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"unlinked_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.UNLINKED_COMPONENT,
                    severity=IssueSeverity.HIGH,
                    title="Unlinked Component Detected",
                    description="Component exists but is not connected to any other components",
                    system_id=system_id,
                    component_id="comp_456",
                    file_path=None,
                    line_number=None,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Link the component to other system components",
                    auto_fixable=False,
                    metadata={"dependency_count": 0, "dependent_count": 0}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning unlinked components: {e}")
        return issues
    
    def _scan_orphaned_files(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for orphaned files"""
        issues = []
        try:
            # Mock implementation - would scan file system
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"orphaned_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.ORPHANED_FILE,
                    severity=IssueSeverity.LOW,
                    title="Orphaned File Detected",
                    description="File exists but is not referenced by any component",
                    system_id=system_id,
                    component_id=None,
                    file_path="/path/to/orphaned/file.txt",
                    line_number=None,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Remove the file or link it to a component",
                    auto_fixable=True,
                    metadata={"file_size": 1024, "created_date": "2024-01-01"}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning orphaned files: {e}")
        return issues
    
    def _scan_duplicate_code(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for duplicate code"""
        issues = []
        try:
            # Mock implementation - would perform code analysis
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"duplicate_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.DUPLICATE_CODE,
                    severity=IssueSeverity.MEDIUM,
                    title="Duplicate Code Detected",
                    description="Similar code blocks found in multiple files",
                    system_id=system_id,
                    component_id=None,
                    file_path="/path/to/file1.py",
                    line_number=42,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Extract common code into a shared function",
                    auto_fixable=False,
                    metadata={"duplicate_files": ["file1.py", "file2.py"], "similarity": 0.95}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning duplicate code: {e}")
        return issues
    
    def _scan_misconfigured_routes(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for misconfigured API routes"""
        issues = []
        try:
            # Mock implementation - would check route configurations
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"route_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.MISCONFIGURED_ROUTE,
                    severity=IssueSeverity.HIGH,
                    title="Misconfigured Route Detected",
                    description="API route is configured but handler is missing",
                    system_id=system_id,
                    component_id="api_comp_123",
                    file_path="/path/to/routes.py",
                    line_number=15,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Add missing route handler or remove route",
                    auto_fixable=True,
                    metadata={"route_path": "/api/missing", "method": "GET"}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning misconfigured routes: {e}")
        return issues
    
    def _scan_mislinked_agents(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for mislinked agents"""
        issues = []
        try:
            # Mock implementation - would check agent connections
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"agent_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.MISLINKED_AGENT,
                    severity=IssueSeverity.CRITICAL,
                    title="Mislinked Agent Detected",
                    description="Agent is configured but cannot communicate with other agents",
                    system_id=system_id,
                    component_id="agent_789",
                    file_path=None,
                    line_number=None,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Fix agent communication links",
                    auto_fixable=False,
                    metadata={"connection_status": "disconnected", "last_heartbeat": "2024-01-01"}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning mislinked agents: {e}")
        return issues
    
    def _scan_missing_handlers(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for missing event handlers"""
        issues = []
        try:
            # Mock implementation - would check event handler registrations
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"handler_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.MISSING_HANDLER,
                    severity=IssueSeverity.HIGH,
                    title="Missing Event Handler",
                    description="Event is being triggered but no handler is registered",
                    system_id=system_id,
                    component_id="event_comp_456",
                    file_path="/path/to/events.py",
                    line_number=23,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Register event handler or remove event trigger",
                    auto_fixable=True,
                    metadata={"event_type": "user_action", "trigger_count": 5}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning missing handlers: {e}")
        return issues
    
    def _scan_file_duplication(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for file duplication"""
        issues = []
        try:
            # Mock implementation - would check for duplicate files
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"file_dup_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.FILE_DUPLICATION,
                    severity=IssueSeverity.LOW,
                    title="Duplicate File Detected",
                    description="Identical files found in multiple locations",
                    system_id=system_id,
                    component_id=None,
                    file_path="/path/to/duplicate/file.txt",
                    line_number=None,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Remove duplicate files and use symbolic links",
                    auto_fixable=True,
                    metadata={"duplicate_paths": ["/path1/file.txt", "/path2/file.txt"]}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning file duplication: {e}")
        return issues
    
    def _scan_memory_leaks(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for memory leaks"""
        issues = []
        try:
            # Mock implementation - would monitor memory usage
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"memory_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.MEMORY_LEAK,
                    severity=IssueSeverity.CRITICAL,
                    title="Potential Memory Leak Detected",
                    description="Memory usage is increasing without corresponding activity",
                    system_id=system_id,
                    component_id="memory_comp_123",
                    file_path=None,
                    line_number=None,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Investigate and fix memory allocation issues",
                    auto_fixable=False,
                    metadata={"memory_growth_rate": "2MB/hour", "current_usage": "512MB"}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning memory leaks: {e}")
        return issues
    
    def _scan_performance_issues(self, system_id: str) -> List[DiagnosticIssue]:
        """Scan for performance issues"""
        issues = []
        try:
            # Mock implementation - would analyze performance metrics
            if system_id:  # Placeholder logic
                issue = DiagnosticIssue(
                    issue_id=f"perf_{uuid.uuid4().hex[:8]}",
                    issue_type=IssueType.PERFORMANCE_ISSUE,
                    severity=IssueSeverity.MEDIUM,
                    title="Performance Issue Detected",
                    description="Response time is above acceptable threshold",
                    system_id=system_id,
                    component_id="perf_comp_456",
                    file_path=None,
                    line_number=None,
                    detected_at=datetime.now(),
                    fix_status=FixStatus.PENDING,
                    fix_description="Optimize code or add caching",
                    auto_fixable=False,
                    metadata={"response_time": "2.5s", "threshold": "1.0s"}
                )
                issues.append(issue)
        except Exception as e:
            logger.error(f"Error scanning performance issues: {e}")
        return issues
    
    def _store_issue(self, issue: DiagnosticIssue):
        """Store issue in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO diagnostic_issues 
                    (issue_id, issue_type, severity, title, description, system_id,
                     component_id, file_path, line_number, detected_at, fix_status,
                     fix_description, auto_fixable, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    issue.issue_id, issue.issue_type.value, issue.severity.value,
                    issue.title, issue.description, issue.system_id, issue.component_id,
                    issue.file_path, issue.line_number, issue.detected_at.isoformat(),
                    issue.fix_status.value, issue.fix_description, issue.auto_fixable,
                    json.dumps(issue.metadata)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing issue: {e}")
    
    def _update_component_graph(self, system_id: str):
        """Update component interconnection graph"""
        try:
            # Clear existing nodes for this system
            nodes_to_remove = [node for node in self.component_graph.nodes() 
                             if self.component_graph.nodes[node].get('system_id') == system_id]
            self.component_graph.remove_nodes_from(nodes_to_remove)
            
            # Add new component nodes (mock data)
            components = [
                ComponentNode(
                    component_id="comp_1",
                    component_type="agent",
                    name="Main Agent",
                    status="active",
                    system_id=system_id,
                    dependencies=["comp_2", "comp_3"],
                    dependents=[],
                    metadata={"type": "orchestrator"}
                ),
                ComponentNode(
                    component_id="comp_2",
                    component_type="memory",
                    name="Memory System",
                    status="active",
                    system_id=system_id,
                    dependencies=[],
                    dependents=["comp_1"],
                    metadata={"type": "storage"}
                ),
                ComponentNode(
                    component_id="comp_3",
                    component_type="api",
                    name="API Gateway",
                    status="active",
                    system_id=system_id,
                    dependencies=[],
                    dependents=["comp_1"],
                    metadata={"type": "interface"}
                )
            ]
            
            # Add nodes to graph
            for comp in components:
                self.component_graph.add_node(comp.component_id, **asdict(comp))
                
                # Add edges for dependencies
                for dep in comp.dependencies:
                    if dep in self.component_graph:
                        self.component_graph.add_edge(dep, comp.component_id)
            
        except Exception as e:
            logger.error(f"Error updating component graph: {e}")
    
    def _calculate_health_score(self, system_id: str):
        """Calculate comprehensive health score for system"""
        try:
            # Get all issues for the system
            issues = self.get_issues(system_id)
            
            # Count issues by severity
            critical_issues = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
            high_issues = len([i for i in issues if i.severity == IssueSeverity.HIGH])
            medium_issues = len([i for i in issues if i.severity == IssueSeverity.MEDIUM])
            low_issues = len([i for i in issues if i.severity == IssueSeverity.LOW])
            
            # Calculate scores (0-100, higher is better)
            integrity_score = max(0, 100 - (critical_issues * 20) - (high_issues * 10) - (medium_issues * 5))
            connectivity_score = self._calculate_connectivity_score(system_id)
            error_rate_score = max(0, 100 - (critical_issues * 15) - (high_issues * 8))
            optimization_score = max(0, 100 - (medium_issues * 3) - (low_issues * 1))
            
            # Overall score (weighted average)
            overall_score = (integrity_score * 0.4 + connectivity_score * 0.3 + 
                           error_rate_score * 0.2 + optimization_score * 0.1)
            
            health_score = SystemHealthScore(
                system_id=system_id,
                integrity_score=integrity_score,
                connectivity_score=connectivity_score,
                error_rate_score=error_rate_score,
                optimization_score=optimization_score,
                overall_score=overall_score,
                calculated_at=datetime.now(),
                issues_count=len(issues),
                critical_issues=critical_issues,
                high_issues=high_issues,
                medium_issues=medium_issues,
                low_issues=low_issues
            )
            
            # Store health score
            self._store_health_score(health_score)
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
    
    def _calculate_connectivity_score(self, system_id: str) -> float:
        """Calculate connectivity score based on component graph"""
        try:
            # Get components for this system
            system_nodes = [node for node in self.component_graph.nodes() 
                          if self.component_graph.nodes[node].get('system_id') == system_id]
            
            if not system_nodes:
                return 0.0
            
            # Calculate connectivity metrics
            total_possible_edges = len(system_nodes) * (len(system_nodes) - 1)
            actual_edges = len(self.component_graph.edges(system_nodes))
            
            if total_possible_edges == 0:
                return 100.0
            
            connectivity_ratio = actual_edges / total_possible_edges
            return min(100.0, connectivity_ratio * 100)
            
        except Exception as e:
            logger.error(f"Error calculating connectivity score: {e}")
            return 0.0
    
    def _store_health_score(self, health_score: SystemHealthScore):
        """Store health score in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_health_scores 
                    (system_id, integrity_score, connectivity_score, error_rate_score,
                     optimization_score, overall_score, calculated_at, issues_count,
                     critical_issues, high_issues, medium_issues, low_issues)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    health_score.system_id, health_score.integrity_score,
                    health_score.connectivity_score, health_score.error_rate_score,
                    health_score.optimization_score, health_score.overall_score,
                    health_score.calculated_at.isoformat(), health_score.issues_count,
                    health_score.critical_issues, health_score.high_issues,
                    health_score.medium_issues, health_score.low_issues
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing health score: {e}")
    
    def get_issues(self, system_id: Optional[str] = None, 
                  issue_type: Optional[IssueType] = None,
                  severity: Optional[IssueSeverity] = None) -> List[DiagnosticIssue]:
        """Get diagnostic issues with optional filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM diagnostic_issues WHERE 1=1"
                params = []
                
                if system_id:
                    query += " AND system_id = ?"
                    params.append(system_id)
                
                if issue_type:
                    query += " AND issue_type = ?"
                    params.append(issue_type.value)
                
                if severity:
                    query += " AND severity = ?"
                    params.append(severity.value)
                
                query += " ORDER BY detected_at DESC"
                
                cursor = conn.execute(query, params)
                
                issues = []
                for row in cursor.fetchall():
                    issue = DiagnosticIssue(
                        issue_id=row[0],
                        issue_type=IssueType(row[1]),
                        severity=IssueSeverity(row[2]),
                        title=row[3],
                        description=row[4],
                        system_id=row[5],
                        component_id=row[6],
                        file_path=row[7],
                        line_number=row[8],
                        detected_at=datetime.fromisoformat(row[9]),
                        fix_status=FixStatus(row[10]),
                        fix_description=row[11],
                        auto_fixable=bool(row[12]),
                        metadata=json.loads(row[13]) if row[13] else {}
                    )
                    issues.append(issue)
                
                return issues
                
        except Exception as e:
            logger.error(f"Error getting issues: {e}")
            return []
    
    def get_health_score(self, system_id: str) -> Optional[SystemHealthScore]:
        """Get health score for a system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM system_health_scores WHERE system_id = ?
                """, (system_id,))
                
                row = cursor.fetchone()
                if row:
                    return SystemHealthScore(
                        system_id=row[0],
                        integrity_score=row[1],
                        connectivity_score=row[2],
                        error_rate_score=row[3],
                        optimization_score=row[4],
                        overall_score=row[5],
                        calculated_at=datetime.fromisoformat(row[6]),
                        issues_count=row[7],
                        critical_issues=row[8],
                        high_issues=row[9],
                        medium_issues=row[10],
                        low_issues=row[11]
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting health score: {e}")
            return None
    
    def get_component_graph(self, system_id: str) -> Dict[str, Any]:
        """Get component interconnection graph as JSON"""
        try:
            system_nodes = [node for node in self.component_graph.nodes() 
                          if self.component_graph.nodes[node].get('system_id') == system_id]
            
            nodes = []
            edges = []
            
            for node in system_nodes:
                node_data = self.component_graph.nodes[node]
                nodes.append({
                    "id": node,
                    "type": node_data.get("component_type", "unknown"),
                    "name": node_data.get("name", "Unknown"),
                    "status": node_data.get("status", "unknown"),
                    "system_id": node_data.get("system_id", "")
                })
            
            for edge in self.component_graph.edges(system_nodes):
                edges.append({
                    "source": edge[0],
                    "target": edge[1],
                    "type": "dependency"
                })
            
            return {
                "nodes": nodes,
                "edges": edges,
                "system_id": system_id
            }
            
        except Exception as e:
            logger.error(f"Error getting component graph: {e}")
            return {"nodes": [], "edges": [], "system_id": system_id}
    
    def generate_fix_suggestions(self, issue_id: str) -> List[FixSuggestion]:
        """Generate auto-fix suggestions for an issue"""
        try:
            # Get the issue
            issues = self.get_issues()
            issue = next((i for i in issues if i.issue_id == issue_id), None)
            
            if not issue:
                return []
            
            suggestions = []
            
            if issue.issue_type == IssueType.STALE_COMPONENT:
                suggestion = FixSuggestion(
                    suggestion_id=f"suggestion_{uuid.uuid4().hex[:8]}",
                    issue_id=issue_id,
                    title="Remove Stale Component",
                    description="Automatically remove the unused component",
                    fix_action="delete_component",
                    confidence=0.8,
                    risk_level="low",
                    estimated_time=30,
                    prerequisites=["backup_system"],
                    rollback_plan="Restore from backup"
                )
                suggestions.append(suggestion)
            
            elif issue.issue_type == IssueType.ORPHANED_FILE:
                suggestion = FixSuggestion(
                    suggestion_id=f"suggestion_{uuid.uuid4().hex[:8]}",
                    issue_id=issue_id,
                    title="Remove Orphaned File",
                    description="Delete the unused file",
                    fix_action="delete_file",
                    confidence=0.9,
                    risk_level="low",
                    estimated_time=5,
                    prerequisites=["file_backup"],
                    rollback_plan="Restore from backup"
                )
                suggestions.append(suggestion)
            
            # Store suggestions
            for suggestion in suggestions:
                self._store_fix_suggestion(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating fix suggestions: {e}")
            return []
    
    def _store_fix_suggestion(self, suggestion: FixSuggestion):
        """Store fix suggestion in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO fix_suggestions 
                    (suggestion_id, issue_id, title, description, fix_action,
                     confidence, risk_level, estimated_time, prerequisites, rollback_plan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    suggestion.suggestion_id, suggestion.issue_id, suggestion.title,
                    suggestion.description, suggestion.fix_action, suggestion.confidence,
                    suggestion.risk_level, suggestion.estimated_time,
                    json.dumps(suggestion.prerequisites), suggestion.rollback_plan
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing fix suggestion: {e}")
    
    def auto_fix_issue(self, issue_id: str, suggestion_id: str) -> bool:
        """Automatically fix an issue using a suggestion"""
        try:
            # Get the issue and suggestion
            issues = self.get_issues()
            issue = next((i for i in issues if i.issue_id == issue_id), None)
            
            if not issue or not issue.auto_fixable:
                return False
            
            # Update issue status
            issue.fix_status = FixStatus.IN_PROGRESS
            self._store_issue(issue)
            
            # Perform the fix (mock implementation)
            if issue.issue_type == IssueType.STALE_COMPONENT:
                # Mock: Remove component
                logger.info(f"Removing stale component: {issue.component_id}")
                time.sleep(1)  # Simulate fix time
                
            elif issue.issue_type == IssueType.ORPHANED_FILE:
                # Mock: Remove file
                logger.info(f"Removing orphaned file: {issue.file_path}")
                time.sleep(1)  # Simulate fix time
            
            # Update issue status to completed
            issue.fix_status = FixStatus.COMPLETED
            issue.fix_description = "Auto-fix completed successfully"
            self._store_issue(issue)
            
            logger.info(f"Auto-fix completed for issue: {issue_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error auto-fixing issue: {e}")
            
            # Update issue status to failed
            if issue:
                issue.fix_status = FixStatus.FAILED
                issue.fix_description = f"Auto-fix failed: {str(e)}"
                self._store_issue(issue)
            
            return False
    
    def _background_scan(self):
        """Background scanning of all systems"""
        while self.scanning_active:
            try:
                # Get all systems
                systems = self.system_lifecycle.list_systems() if self.system_lifecycle else []
                
                for system in systems:
                    system_id = system.get('id', 'unknown')
                    
                    # Perform system scan
                    self.scan_system(system_id)
                
                # Clean up old issues
                self._cleanup_old_issues()
                
                time.sleep(300)  # Scan every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in background scan: {e}")
                time.sleep(600)  # Wait 10 minutes on error
    
    def _cleanup_old_issues(self, days: int = 30):
        """Clean up old resolved issues"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM diagnostic_issues 
                    WHERE fix_status = 'completed' AND detected_at < ?
                """, (cutoff_date.isoformat(),))
                conn.commit()
                
            logger.info(f"Cleaned up resolved issues older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old issues: {e}")
    
    def stop_scanning(self):
        """Stop background scanning"""
        self.scanning_active = False
        if self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5)
