"""
Codegen agent schema definitions
"""
import enum
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime

class RiskLevel(str, enum.Enum):
    """Risk levels for code changes"""
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"

class ExecutionStatus(str, enum.Enum):
    """Execution status for codegen operations"""
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    DRY_RUN = "dry_run"
    FAILED = "failed"

@dataclass
class RepoRef:
    """Repository reference"""
    type: str  # "local" or "github"
    project_id: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    branch: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepoRef':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class CodegenGoal:
    """Codegen goal specification"""
    repo_ref: RepoRef
    branch_base: str = "main"
    goal_text: str = ""
    constraints: Optional[Dict[str, Any]] = None
    allow_paths: Optional[List[str]] = None
    deny_globs: Optional[List[str]] = None
    dry_run: bool = False
    project_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['repo_ref'] = self.repo_ref.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodegenGoal':
        """Create from dictionary"""
        if 'repo_ref' in data:
            data['repo_ref'] = RepoRef.from_dict(data['repo_ref'])
        return cls(**data)

@dataclass
class UnifiedDiff:
    """Unified diff representation"""
    file_path: str
    diff_content: str
    operation: str  # "add", "modify", "delete"
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedDiff':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class TestResult:
    """Test execution result"""
    passed: int
    failed: int
    duration: float
    output: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class LintResult:
    """Lint execution result"""
    ok: bool
    issues: List[Dict[str, Any]]
    output: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class ProposedChange:
    """Proposed code changes"""
    summary: str
    diffs: List[UnifiedDiff]
    risk: RiskLevel
    files_touched: List[str]
    tests_touched: List[str]
    estimated_impact: str = ""
    tool_transcript: Optional['ToolTranscript'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['diffs'] = [diff.to_dict() for diff in self.diffs]
        data['risk'] = self.risk.value
        if self.tool_transcript:
            data['tool_transcript'] = self.tool_transcript.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProposedChange':
        """Create from dictionary"""
        if 'diffs' in data:
            data['diffs'] = [UnifiedDiff.from_dict(d) for d in data['diffs']]
        if 'risk' in data:
            data['risk'] = RiskLevel(data['risk'])
        if 'tool_transcript' in data and data['tool_transcript']:
            from src.agent_tools.types import ToolTranscript
            data['tool_transcript'] = ToolTranscript.from_dict(data['tool_transcript'])
        return cls(**data)

@dataclass
class ExecutionResult:
    """Codegen execution result"""
    branch: str
    commit_sha: Optional[str] = None
    tests: TestResult
    lint: LintResult
    status: ExecutionStatus
    pr_url: Optional[str] = None
    logs_url: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['tests'] = self.tests.to_dict()
        data['lint'] = self.lint.to_dict()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionResult':
        """Create from dictionary"""
        if 'tests' in data:
            data['tests'] = TestResult(**data['tests'])
        if 'lint' in data:
            data['lint'] = LintResult(**data['lint'])
        if 'status' in data:
            data['status'] = ExecutionStatus(data['status'])
        return cls(**data)

@dataclass
class CodegenJob:
    """Codegen job for async execution"""
    job_id: str
    goal: CodegenGoal
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[ExecutionResult] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['goal'] = self.goal.to_dict()
        if self.result:
            data['result'] = self.result.to_dict()
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodegenJob':
        """Create from dictionary"""
        if 'goal' in data:
            data['goal'] = CodegenGoal.from_dict(data['goal'])
        if 'result' in data and data['result']:
            data['result'] = ExecutionResult.from_dict(data['result'])
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'completed_at' in data and data['completed_at']:
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)
