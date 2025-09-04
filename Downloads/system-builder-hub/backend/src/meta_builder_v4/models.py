"""
Database models for Meta-Builder v4.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class CanarySample(Base):
    """Canary testing samples."""
    __tablename__ = 'mb_v4_canary_sample'
    
    id = Column(String(50), primary_key=True)
    run_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    canary_group = Column(String(20), nullable=False)  # 'control' or 'v4'
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=True)
    metrics = Column(JSON, nullable=True)
    cost_usd = Column(Float, nullable=False, default=0.0)
    duration_seconds = Column(Integer, nullable=False, default=0)
    retry_count = Column(Integer, nullable=False, default=0)
    replan_count = Column(Integer, nullable=False, default=0)
    rollback_count = Column(Integer, nullable=False, default=0)


class ReplayBundle(Base):
    """Deterministic replay bundles."""
    __tablename__ = 'mb_v4_replay_bundle'
    
    id = Column(String(50), primary_key=True)
    run_id = Column(String(50), nullable=False, index=True)
    prompts = Column(JSON, nullable=False)
    tool_io = Column(JSON, nullable=False)
    diffs = Column(JSON, nullable=False)
    final_state = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class QueueLease(Base):
    """Queue lease management."""
    __tablename__ = 'mb_v4_queue_lease'
    
    id = Column(String(50), primary_key=True)
    worker_id = Column(String(50), nullable=False, index=True)
    queue_class = Column(String(20), nullable=False)
    leased_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    task_id = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default='active')  # active, expired, released


class RunBudget(Base):
    """Run-level budget tracking."""
    __tablename__ = 'mb_v4_run_budget'
    
    id = Column(String(50), primary_key=True)
    run_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    cost_budget_usd = Column(Float, nullable=False)
    time_budget_seconds = Column(Integer, nullable=False)
    attempt_budget = Column(Integer, nullable=False)
    current_cost_usd = Column(Float, nullable=False, default=0.0)
    current_time_seconds = Column(Integer, nullable=False, default=0)
    current_attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CircuitBreakerState(Base):
    """Circuit breaker state persistence."""
    __tablename__ = 'mb_v4_circuit_breaker_state'
    
    id = Column(String(50), primary_key=True)
    failure_class = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    state = Column(String(20), nullable=False)  # closed, open, half_open
    failure_count = Column(Integer, nullable=False, default=0)
    threshold = Column(Integer, nullable=False, default=5)
    cooldown_minutes = Column(Integer, nullable=False, default=5)
    last_failure = Column(DateTime, nullable=True)
    last_state_change = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChaosEvent(Base):
    """Chaos testing events."""
    __tablename__ = 'mb_v4_chaos_event'
    
    id = Column(String(50), primary_key=True)
    chaos_type = Column(String(50), nullable=False, index=True)
    run_id = Column(String(50), nullable=False, index=True)
    step_id = Column(String(50), nullable=False)
    tenant_id = Column(String(50), nullable=False, index=True)
    injected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    recovery_successful = Column(Boolean, nullable=True)
    metadata = Column(JSON, nullable=True)


class RepairAttempt(Base):
    """Repair attempt tracking."""
    __tablename__ = 'mb_v4_repair_attempt'
    
    id = Column(String(50), primary_key=True)
    run_id = Column(String(50), nullable=False, index=True)
    step_id = Column(String(50), nullable=False)
    failure_class = Column(String(50), nullable=False)
    repair_phase = Column(String(20), nullable=False)  # retry, patch, replan, rollback
    strategy = Column(String(50), nullable=False)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
