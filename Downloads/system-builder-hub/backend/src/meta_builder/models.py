"""
SBH Meta-Builder Data Models
Models for guided scaffold generation, template composition, and evaluation.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.database import Base
from src.utils.audit import AuditableMixin
from src.utils.multi_tenancy import TenantScopedMixin


class ScaffoldSession(Base, TenantScopedMixin, AuditableMixin):
    """A scaffold generation session initiated by a user."""
    
    __tablename__ = "scaffold_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Session metadata
    goal_text = Column(Text, nullable=False, comment="Natural language description of the system to build")
    mode = Column(String(20), nullable=False, default="guided", comment="guided|freeform")
    status = Column(String(20), nullable=False, default="draft", comment="draft|planned|built|failed")
    
    # Session configuration
    guided_input = Column(JSON, nullable=True, comment="Structured input from guided form")
    pattern_slugs = Column(JSON, nullable=True, comment="Selected pattern slugs")
    template_slugs = Column(JSON, nullable=True, comment="Selected template slugs")
    composition_rules = Column(JSON, nullable=True, comment="Template composition configuration")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    plans = relationship("ScaffoldPlan", back_populates="session", cascade="all, delete-orphan")
    artifacts = relationship("PlanArtifact", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_scaffold_sessions_tenant_user", "tenant_id", "user_id"),
        Index("idx_scaffold_sessions_status", "tenant_id", "status"),
        Index("idx_scaffold_sessions_created", "tenant_id", "created_at"),
    )


class ScaffoldPlan(Base, TenantScopedMixin, AuditableMixin):
    """A generated plan for building a scaffold."""
    
    __tablename__ = "scaffold_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_sessions.id"), nullable=False)
    
    # Plan metadata
    version = Column(Integer, nullable=False, default=1, comment="Plan version number")
    planner_kind = Column(String(20), nullable=False, default="heuristic", comment="heuristic|llm|hybrid")
    
    # Plan content
    plan_json = Column(JSON, nullable=False, comment="BuilderState draft")
    diffs_json = Column(JSON, nullable=True, comment="Changes from previous version")
    scorecard_json = Column(JSON, nullable=True, comment="Plan quality metrics")
    rationale = Column(Text, nullable=True, comment="Planner's reasoning for the plan")
    risks = Column(JSON, nullable=True, comment="Identified risks and mitigations")
    
    # Build results
    build_status = Column(String(20), nullable=True, comment="pending|building|success|failed")
    build_job_id = Column(String(100), nullable=True, comment="Background job ID for build")
    build_results = Column(JSON, nullable=True, comment="Build output and test results")
    preview_urls = Column(JSON, nullable=True, comment="Generated preview URLs")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("ScaffoldSession", back_populates="plans")
    
    # Indexes
    __table_args__ = (
        Index("idx_scaffold_plans_session_version", "session_id", "version"),
        Index("idx_scaffold_plans_build_status", "tenant_id", "build_status"),
    )


class PatternLibrary(Base, TenantScopedMixin, AuditableMixin):
    """Catalog of build patterns for scaffold generation."""
    
    __tablename__ = "pattern_library"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Pattern metadata
    slug = Column(String(100), nullable=False, unique=True, comment="Unique pattern identifier")
    name = Column(String(200), nullable=False, comment="Human-readable pattern name")
    description = Column(Text, nullable=False, comment="Pattern description")
    tags = Column(JSON, nullable=False, default=list, comment="Pattern tags for categorization")
    
    # Pattern schema
    inputs_schema = Column(JSON, nullable=False, comment="JSON schema for pattern inputs")
    outputs_schema = Column(JSON, nullable=False, comment="JSON schema for pattern outputs")
    compose_points = Column(JSON, nullable=False, default=list, comment="Available composition points")
    
    # Pattern configuration
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether pattern is available")
    is_seeded = Column(Boolean, default=False, nullable=False, comment="Whether pattern is system-seeded")
    priority = Column(Integer, default=0, nullable=False, comment="Pattern priority for matching")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_pattern_library_slug", "slug"),
        Index("idx_pattern_library_tags", "tenant_id", "tags"),
        Index("idx_pattern_library_active", "tenant_id", "is_active"),
    )


class TemplateLink(Base, TenantScopedMixin, AuditableMixin):
    """References to Marketplace templates with composition rules."""
    
    __tablename__ = "template_links"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Template reference
    template_slug = Column(String(100), nullable=False, comment="Marketplace template slug")
    template_version = Column(String(20), nullable=False, comment="Template version")
    
    # Composition rules
    before_hooks = Column(JSON, nullable=True, comment="Pre-composition hooks")
    after_hooks = Column(JSON, nullable=True, comment="Post-composition hooks")
    merge_strategy = Column(String(50), nullable=False, default="namespace", comment="namespace|merge|replace")
    
    # Composition configuration
    compose_points = Column(JSON, nullable=False, default=list, comment="Available composition points")
    dependencies = Column(JSON, nullable=True, comment="Template dependencies")
    conflicts = Column(JSON, nullable=True, comment="Known conflicts with other templates")
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_template_links_slug_version", "template_slug", "template_version"),
        Index("idx_template_links_active", "tenant_id", "is_active"),
    )


class PromptTemplate(Base, TenantScopedMixin, AuditableMixin):
    """Guided prompt schemas for scaffold generation."""
    
    __tablename__ = "prompt_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Template metadata
    slug = Column(String(100), nullable=False, unique=True, comment="Unique template identifier")
    name = Column(String(200), nullable=False, comment="Template name")
    version = Column(String(20), nullable=False, default="1.0.0", comment="Template version")
    
    # Template schema
    schema = Column(JSON, nullable=False, comment="JSON schema for guided input")
    default_values = Column(JSON, nullable=True, comment="Default values for fields")
    validation_rules = Column(JSON, nullable=True, comment="Custom validation rules")
    
    # Template configuration
    pattern_slugs = Column(JSON, nullable=True, comment="Associated pattern slugs")
    template_slugs = Column(JSON, nullable=True, comment="Associated template slugs")
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_prompt_templates_slug", "slug"),
        Index("idx_prompt_templates_active", "tenant_id", "is_active"),
    )


class EvaluationCase(Base, TenantScopedMixin, AuditableMixin):
    """Golden test cases for scaffold evaluation."""
    
    __tablename__ = "evaluation_cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Case metadata
    name = Column(String(200), nullable=False, comment="Test case name")
    description = Column(Text, nullable=False, comment="Test case description")
    category = Column(String(50), nullable=False, comment="Test category")
    
    # Test configuration
    goal_text = Column(Text, nullable=False, comment="Natural language goal for testing")
    expected_patterns = Column(JSON, nullable=True, comment="Expected patterns to be used")
    expected_templates = Column(JSON, nullable=True, comment="Expected templates to be used")
    
    # Assertions
    assertions = Column(JSON, nullable=False, comment="Expected assertions (regex/contains/json-schema)")
    min_score = Column(Integer, nullable=True, comment="Minimum acceptable plan score")
    
    # Test results
    last_run_at = Column(DateTime, nullable=True, comment="Last test run timestamp")
    last_run_results = Column(JSON, nullable=True, comment="Last test run results")
    pass_rate = Column(Integer, nullable=True, comment="Historical pass rate percentage")
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_evaluation_cases_category", "tenant_id", "category"),
        Index("idx_evaluation_cases_active", "tenant_id", "is_active"),
    )


class PlanArtifact(Base, TenantScopedMixin, AuditableMixin):
    """Exportable artifacts from a scaffold session."""
    
    __tablename__ = "plan_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_sessions.id"), nullable=False)
    
    # Artifact metadata
    artifact_type = Column(String(50), nullable=False, comment="builder_state|export_manifest|zip|github_pr")
    filename = Column(String(200), nullable=False, comment="Artifact filename")
    
    # Storage
    file_key = Column(String(500), nullable=True, comment="S3 file key for stored artifacts")
    file_size = Column(Integer, nullable=True, comment="File size in bytes")
    content_type = Column(String(100), nullable=True, comment="MIME type")
    
    # External references
    github_pr_url = Column(String(500), nullable=True, comment="GitHub PR URL if applicable")
    github_repo = Column(String(200), nullable=True, comment="GitHub repository")
    github_branch = Column(String(100), nullable=True, comment="GitHub branch")
    
    # Metadata
    metadata = Column(JSON, nullable=True, comment="Additional artifact metadata")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("ScaffoldSession", back_populates="artifacts")
    
    # Indexes
    __table_args__ = (
        Index("idx_plan_artifacts_session_type", "session_id", "artifact_type"),
        Index("idx_plan_artifacts_created", "tenant_id", "created_at"),
    )


class ScaffoldEvaluation(Base, TenantScopedMixin, AuditableMixin):
    """Results of running evaluation cases against scaffold plans."""
    
    __tablename__ = "scaffold_evaluations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_sessions.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_plans.id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_cases.id"), nullable=False)
    
    # Evaluation results
    status = Column(String(20), nullable=False, comment="pass|fail|error")
    score = Column(Integer, nullable=True, comment="Evaluation score (0-100)")
    details = Column(JSON, nullable=True, comment="Detailed evaluation results")
    errors = Column(JSON, nullable=True, comment="Evaluation errors if any")
    
    # Performance metrics
    execution_time = Column(Integer, nullable=True, comment="Execution time in milliseconds")
    memory_usage = Column(Integer, nullable=True, comment="Memory usage in MB")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_scaffold_evaluations_session", "session_id"),
        Index("idx_scaffold_evaluations_status", "tenant_id", "status"),
        Index("idx_scaffold_evaluations_score", "tenant_id", "score"),
    )
