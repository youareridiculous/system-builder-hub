"""
Meta-Builder v3 Data Models
Enhanced models for auto-fix system and retry state.
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


class AutoFixOutcome(str, Enum):
    """Auto-fix outcomes."""
    RETRIED = "retried"
    PATCH_APPLIED = "patch_applied"
    REPLANNED = "replanned"
    ESCALATED = "escalated"
    GAVE_UP = "gave_up"


class AutoFixRun(Base):
    """Auto-fix run tracking."""
    __tablename__ = "auto_fix_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("build_steps.id"), nullable=False)
    signal_type = Column(String(50), nullable=False)  # FailureType
    strategy = Column(String(50), nullable=True)  # FixStrategy
    outcome = Column(String(50), nullable=False)  # AutoFixOutcome
    attempt = Column(Integer, nullable=False, default=1)
    backoff = Column(Float, nullable=True)  # Backoff delay in seconds
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    run = relationship("BuildRun", back_populates="auto_fix_runs")
    step = relationship("BuildStep", back_populates="auto_fix_runs")
    
    # Indexes
    __table_args__ = (
        Index("idx_auto_fix_runs_run_id", "run_id"),
        Index("idx_auto_fix_runs_step_id", "step_id"),
        Index("idx_auto_fix_runs_created_at", "created_at"),
    )


class PlanDelta(Base):
    """Plan delta artifacts for re-planning."""
    __tablename__ = "plan_deltas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_plan_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_plans.id"), nullable=False)
    new_plan_id = Column(UUID(as_uuid=True), ForeignKey("scaffold_plans.id"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False)
    delta_data = Column(JSON, nullable=False)  # Plan diff data
    triggered_by = Column(String(100), nullable=False)  # What triggered the re-plan
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    original_plan = relationship("ScaffoldPlan", foreign_keys=[original_plan_id])
    new_plan = relationship("ScaffoldPlan", foreign_keys=[new_plan_id])
    run = relationship("BuildRun", back_populates="plan_deltas")
    
    # Indexes
    __table_args__ = (
        Index("idx_plan_deltas_run_id", "run_id"),
        Index("idx_plan_deltas_original_plan", "original_plan_id"),
        Index("idx_plan_deltas_new_plan", "new_plan_id"),
    )


class RetryState(Base):
    """Retry state for build runs."""
    __tablename__ = "retry_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("build_runs.id"), nullable=False, unique=True)
    attempt_counter = Column(Integer, nullable=False, default=0)
    per_step_attempts = Column(JSON, nullable=False, default=dict)  # {step_id: attempt_count}
    total_attempts = Column(Integer, nullable=False, default=0)
    last_backoff_seconds = Column(Float, nullable=True)
    max_total_attempts = Column(Integer, nullable=False, default=6)
    max_per_step_attempts = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    run = relationship("BuildRun", back_populates="retry_state")
    
    # Indexes
    __table_args__ = (
        Index("idx_retry_states_run_id", "run_id"),
    )


# Extend existing models with new relationships
def extend_existing_models():
    """Extend existing models with new relationships."""
    # This would be called to add relationships to existing models
    # For now, we'll define them here
    
    # Add to BuildRun model
    BuildRun.auto_fix_runs = relationship("AutoFixRun", back_populates="run")
    BuildRun.plan_deltas = relationship("PlanDelta", back_populates="run")
    BuildRun.retry_state = relationship("RetryState", back_populates="run", uselist=False)
    
    # Add to BuildStep model
    BuildStep.auto_fix_runs = relationship("AutoFixRun", back_populates="step")
