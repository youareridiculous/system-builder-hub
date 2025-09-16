"""
SBH Meta-Builder v2 Data Models
Multi-agent, iterative scaffold generation with approval gates.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, 
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class SpecMode(str, Enum):
    """Specification input modes."""
    GUIDED = "guided"
    FREEFORM = "freeform"


class SpecStatus(str, Enum):
    """Specification status."""
    DRAFT = "draft"
    PLANNED = "planned"
    APPROVED = "approved"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    """Build run status."""
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_APPROVAL = "needs_approval"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class StepName(str, Enum):
    """Build step names."""
    PLAN = "plan"
    CODEGEN = "codegen"
    TEST = "test"
    EVALUATE = "evaluate"
    AUTOFIX = "autofix"
    APPROVAL = "approval"
    FINALIZE = "finalize"


class StepStatus(str, Enum):
    """Build step status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ArtifactKind(str, Enum):
    """Build artifact kinds."""
    ZIP = "zip"
    EXPORT_MANIFEST = "export_manifest"
    PR_URL = "pr_url"
    RELEASE_MANIFEST = "release_manifest"


class ApprovalStatus(str, Enum):
    """Approval gate status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class ScaffoldSpec(Base):
    """Scaffold specification - tenant-scoped, audit-enabled."""
    __tablename__ = "scaffold_specs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    mode = Column(String(20), nullable=False, default=SpecMode.FREEFORM)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    guided_input = Column(JSON)  # Structured guided form data
    attachments = Column(JSON)   # File attachments metadata
    status = Column(String(20), nullable=False, default=SpecStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plans = relationship("ScaffoldPlan", back_populates="spec", cascade="all, delete-orphan")
    runs = relationship("BuildRun", back_populates="spec", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_scaffold_specs_tenant_status', 'tenant_id', 'status'),
        Index('idx_scaffold_specs_created_by', 'created_by'),
    )


class ScaffoldPlan(Base):
    """Scaffold plan - generated from spec by Product Architect."""
    __tablename__ = "scaffold_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spec_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_specs.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    summary = Column(Text, nullable=False)
    risk_score = Column(Float, nullable=False, default=0.0)  # 0-100
    agents_used = Column(JSON, nullable=False, default=list)  # List of agent names
    plan_graph = Column(JSON, nullable=False)  # Entities, endpoints, pages, integrations
    diff_preview = Column(Text)  # Optional human-readable diff summary
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    spec = relationship("ScaffoldSpec", back_populates="plans")
    runs = relationship("BuildRun", back_populates="plan", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_scaffold_plans_spec_version', 'spec_id', 'version'),
        UniqueConstraint('spec_id', 'version', name='uq_spec_version'),
    )


class BuildRun(Base):
    """Build run - orchestrates the multi-agent build process."""
    __tablename__ = "build_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    spec_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_specs.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_plans.id"), nullable=False)
    status = Column(String(20), nullable=False, default=RunStatus.PENDING)
    iteration = Column(Integer, nullable=False, default=0)
    max_iterations = Column(Integer, nullable=False, default=4)
    branch_ref = Column(String(255))  # GitHub branch reference
    elapsed_ms = Column(Integer)  # Total elapsed time in milliseconds
    metrics = Column(JSON, nullable=False, default=dict)  # Token usage, cache hits, etc.
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    
    # Relationships
    spec = relationship("ScaffoldSpec", back_populates="runs")
    plan = relationship("ScaffoldPlan", back_populates="runs")
    steps = relationship("BuildStep", back_populates="run", cascade="all, delete-orphan")
    diffs = relationship("DiffArtifact", back_populates="run", cascade="all, delete-orphan")
    evaluations = relationship("EvalReport", back_populates="run", cascade="all, delete-orphan")
    approvals = relationship("ApprovalGate", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("BuildArtifact", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_build_runs_tenant_status', 'tenant_id', 'status'),
        Index('idx_build_runs_spec', 'spec_id'),
        Index('idx_build_runs_started_at', 'started_at'),
    )


class BuildStep(Base):
    """Build step - individual agent execution within a run."""
    __tablename__ = "build_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False)
    name = Column(String(20), nullable=False)  # StepName enum
    status = Column(String(20), nullable=False, default=StepStatus.PENDING)
    input = Column(JSON, nullable=False, default=dict)  # Step input data
    output = Column(JSON, nullable=False, default=dict)  # Step output data
    logs_url = Column(String(500))  # Optional logs storage URL
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    
    # Relationships
    run = relationship("BuildRun", back_populates="steps")
    
    __table_args__ = (
        Index('idx_build_steps_run_name', 'run_id', 'name'),
        Index('idx_build_steps_status', 'status'),
    )


class DiffArtifact(Base):
    """Diff artifact - unified diff from codegen step."""
    __tablename__ = "diff_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False)
    iteration = Column(Integer, nullable=False)
    unified_diff = Column(Text, nullable=False)  # Raw unified diff
    files_changed = Column(Integer, nullable=False, default=0)
    risk = Column(JSON, nullable=False, default=dict)  # Risk assessment
    summary = Column(Text)  # Human-readable summary
    
    # Relationships
    run = relationship("BuildRun", back_populates="diffs")
    
    __table_args__ = (
        Index('idx_diff_artifacts_run_iteration', 'run_id', 'iteration'),
        UniqueConstraint('run_id', 'iteration', name='uq_run_iteration'),
    )


class EvalReport(Base):
    """Evaluation report - test results and scoring."""
    __tablename__ = "eval_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False)
    iteration = Column(Integer, nullable=False)
    scores = Column(JSON, nullable=False, default=dict)  # Per-category scores
    failed_cases = Column(JSON, nullable=False, default=list)  # Failed test cases
    junit_xml = Column(Text)  # Optional JUnit XML report
    html_report_url = Column(String(500))  # Optional HTML report URL
    pass_rate = Column(Float, nullable=False, default=0.0)  # Overall pass rate
    
    # Relationships
    run = relationship("BuildRun", back_populates="evaluations")
    
    __table_args__ = (
        Index('idx_eval_reports_run_iteration', 'run_id', 'iteration'),
        UniqueConstraint('run_id', 'iteration', name='uq_eval_run_iteration'),
    )


class ApprovalGate(Base):
    """Approval gate - human review checkpoint."""
    __tablename__ = "approval_gates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False)
    iteration = Column(Integer, nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, default=ApprovalStatus.PENDING)
    requested_by = Column(UUID(as_uuid=True), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True))  # Null until approved/rejected
    notes = Column(Text)  # Approval/rejection notes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    run = relationship("BuildRun", back_populates="approvals")
    
    __table_args__ = (
        Index('idx_approval_gates_run_status', 'run_id', 'status'),
        Index('idx_approval_gates_reviewer', 'reviewer_id'),
        UniqueConstraint('run_id', 'iteration', name='uq_approval_run_iteration'),
    )


class BuildArtifact(Base):
    """Build artifact - final outputs (ZIP, PR, manifest)."""
    __tablename__ = "build_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False)
    kind = Column(String(20), nullable=False)  # ArtifactKind enum
    url = Column(String(500), nullable=False)  # Artifact URL
    artifact_metadata = Column(JSON, nullable=False, default=dict)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    run = relationship("BuildRun", back_populates="artifacts")
    
    __table_args__ = (
        Index('idx_build_artifacts_run_kind', 'run_id', 'kind'),
        Index('idx_build_artifacts_created_at', 'created_at'),
    )


# Helper functions for model operations
def create_spec(
    tenant_id: uuid.UUID,
    created_by: uuid.UUID,
    title: str,
    description: str = None,
    mode: SpecMode = SpecMode.FREEFORM,
    guided_input: Dict[str, Any] = None,
    attachments: List[Dict[str, Any]] = None
) -> ScaffoldSpec:
    """Create a new scaffold specification."""
    return ScaffoldSpec(
        tenant_id=tenant_id,
        created_by=created_by,
        title=title,
        description=description,
        mode=mode,
        guided_input=guided_input or {},
        attachments=attachments or [], status=SpecStatus.DRAFT
    )


def create_plan(
    spec_id: uuid.UUID,
    summary: str,
    plan_graph: Dict[str, Any],
    risk_score: float = 0.0,
    agents_used: List[str] = None,
    diff_preview: str = None
) -> ScaffoldPlan:
    """Create a new scaffold plan."""
    return ScaffoldPlan(
        spec_id=spec_id,
        summary=summary,
        plan_graph=plan_graph,
        risk_score=risk_score,
        agents_used=agents_used or [],
        diff_preview=diff_preview, version=1
    )


def create_run(
    tenant_id: uuid.UUID,
    spec_id: uuid.UUID,
    plan_id: uuid.UUID,
    max_iterations: int = 4,
    branch_ref: str = None
) -> BuildRun:
    """Create a new build run."""
    return BuildRun(
        tenant_id=tenant_id,
        spec_id=spec_id,
        plan_id=plan_id,
        max_iterations=max_iterations,
        branch_ref=branch_ref, status=RunStatus.PENDING, iteration=0
    )


def create_step(
    run_id: uuid.UUID,
    name: StepName,
    input_data: Dict[str, Any] = None
) -> BuildStep:
    """Create a new build step."""
    return BuildStep(
        run_id=run_id,
        name=name,
        input=input_data or {}
    )


def create_diff_artifact(
    run_id: uuid.UUID,
    iteration: int,
    unified_diff: str,
    files_changed: int = 0,
    risk: Dict[str, Any] = None,
    summary: str = None
) -> DiffArtifact:
    """Create a new diff artifact."""
    return DiffArtifact(
        run_id=run_id,
        iteration=iteration,
        unified_diff=unified_diff,
        files_changed=files_changed,
        risk=risk or {},
        summary=summary
    )


def create_eval_report(
    run_id: uuid.UUID,
    iteration: int,
    scores: Dict[str, float],
    failed_cases: List[Dict[str, Any]] = None,
    pass_rate: float = 0.0,
    junit_xml: str = None,
    html_report_url: str = None
) -> EvalReport:
    """Create a new evaluation report."""
    return EvalReport(
        run_id=run_id,
        iteration=iteration,
        scores=scores,
        failed_cases=failed_cases or [],
        pass_rate=pass_rate,
        junit_xml=junit_xml,
        html_report_url=html_report_url
    )


def create_approval_gate(
    run_id: uuid.UUID,
    iteration: int,
    requested_by: uuid.UUID,
    required: bool = True
) -> ApprovalGate:
    """Create a new approval gate."""
    return ApprovalGate(
        run_id=run_id,
        iteration=iteration,
        required=required,
        requested_by=requested_by
    )


def create_build_artifact(
    run_id: uuid.UUID,
    kind: ArtifactKind,
    url: str,
    artifact_metadata: Dict[str, Any] = None
) -> BuildArtifact:
    """Create a new build artifact."""
    return BuildArtifact(
        run_id=run_id,
        kind=kind,
        url=url,
        artifact_metadata=artifact_metadata or {}
    )
