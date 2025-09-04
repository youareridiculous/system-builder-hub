"""
Evaluation Lab Storage

Handles persistence and retrieval of evaluation data.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import logging

from sqlalchemy import create_engine, Column, String, DateTime, Integer, Float, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB

logger = logging.getLogger(__name__)

Base = declarative_base()


class EvalRun(Base):
    """Database model for evaluation runs."""
    __tablename__ = 'eval_runs'
    
    id = Column(String(36), primary_key=True)
    suite_name = Column(String(255), nullable=False, index=True)
    suite_version = Column(String(50))
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime)
    status = Column(String(50), nullable=False, index=True)
    total_cases = Column(Integer, nullable=False)
    passed_cases = Column(Integer, nullable=False)
    failed_cases = Column(Integer, nullable=False)
    pass_rate = Column(Float)
    avg_latency_ms = Column(Float)
    p95_latency_ms = Column(Float)
    p99_latency_ms = Column(Float)
    total_cost_usd = Column(Float)
    cost_per_case_usd = Column(Float)
    privacy_mode = Column(String(50), nullable=False)
    meta_builder_version = Column(String(10))
    environment = Column(String(50), nullable=False)
    meta_json = Column('metadata', JSONB)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class EvalCase(Base):
    """Database model for evaluation cases."""
    __tablename__ = 'eval_cases'
    
    id = Column(String(36), primary_key=True)
    eval_run_id = Column(String(36), nullable=False, index=True)
    case_name = Column(String(255), nullable=False, index=True)
    case_type = Column(String(50), nullable=False)
    sla_class = Column(String(50), nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(50), nullable=False, index=True)
    passed = Column(Boolean)
    latency_ms = Column(Float)
    cost_usd = Column(Float)
    tokens_used = Column(Integer)
    error_message = Column(Text)
    assertion_results = Column(JSONB)
    meta_json = Column('metadata', JSONB)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class EvalMetric(Base):
    """Database model for evaluation metrics."""
    __tablename__ = 'eval_metrics'
    
    id = Column(String(36), primary_key=True)
    eval_run_id = Column(String(36), nullable=False, index=True)
    metric_name = Column(String(255), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50))
    metric_type = Column(String(50), nullable=False)
    threshold = Column(Float)
    operator = Column(String(10))
    passed = Column(Boolean)
    severity = Column(String(20))
    meta_json = Column('metadata', JSONB)
    created_at = Column(DateTime, nullable=False)


class EvalArtifact(Base):
    """Database model for evaluation artifacts."""
    __tablename__ = 'eval_artifacts'
    
    id = Column(String(36), primary_key=True)
    eval_run_id = Column(String(36), nullable=False, index=True)
    eval_case_id = Column(String(36), index=True)
    artifact_type = Column(String(100), nullable=False, index=True)
    artifact_name = Column(String(255), nullable=False)
    artifact_path = Column(String(500), nullable=False)
    artifact_size_bytes = Column(Integer)
    content_type = Column(String(100))
    checksum = Column(String(64))
    meta_json = Column('metadata', JSONB)
    created_at = Column(DateTime, nullable=False)


class EvalRegression(Base):
    """Database model for evaluation regressions."""
    __tablename__ = 'eval_regressions'
    
    id = Column(String(36), primary_key=True)
    baseline_run_id = Column(String(36), nullable=False, index=True)
    current_run_id = Column(String(36), nullable=False, index=True)
    metric_name = Column(String(255), nullable=False, index=True)
    baseline_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    regression_detected = Column(Boolean, nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text)
    meta_json = Column('metadata', JSONB)
    created_at = Column(DateTime, nullable=False)


@dataclass
class EvalRunData:
    """Data class for evaluation run information."""
    id: str
    suite_name: str
    suite_version: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: Optional[float]
    avg_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]
    p99_latency_ms: Optional[float]
    total_cost_usd: Optional[float]
    cost_per_case_usd: Optional[float]
    privacy_mode: str
    meta_builder_version: Optional[str]
    environment: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


@dataclass
class EvalCaseData:
    """Data class for evaluation case information."""
    id: str
    eval_run_id: str
    case_name: str
    case_type: str
    sla_class: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    passed: Optional[bool]
    latency_ms: Optional[float]
    cost_usd: Optional[float]
    tokens_used: Optional[int]
    error_message: Optional[str]
    assertion_results: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class EvaluationStorage:
    """Storage layer for evaluation data."""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def create_eval_run(self, suite_name: str, privacy_mode: str, environment: str = "test",
                       meta_builder_version: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new evaluation run."""
        run_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_run = EvalRun(
                id=run_id,
                suite_name=suite_name,
                started_at=now,
                status="running",
                total_cases=0,
                passed_cases=0,
                failed_cases=0,
                privacy_mode=privacy_mode,
                meta_builder_version=meta_builder_version,
                environment=environment,
                metadata=metadata or {},
                created_at=now,
                updated_at=now
            )
            session.add(eval_run)
            session.commit()
        
        logger.info(f"Created evaluation run {run_id} for suite {suite_name}")
        return run_id
    
    def update_eval_run(self, run_id: str, **kwargs) -> bool:
        """Update an evaluation run."""
        with self.get_session() as session:
            eval_run = session.query(EvalRun).filter(EvalRun.id == run_id).first()
            if not eval_run:
                logger.error(f"Evaluation run {run_id} not found")
                return False
            
            for key, value in kwargs.items():
                if hasattr(eval_run, key):
                    setattr(eval_run, key, value)
            
            eval_run.updated_at = datetime.utcnow()
            session.commit()
        
        logger.info(f"Updated evaluation run {run_id}")
        return True
    
    def complete_eval_run(self, run_id: str, **kwargs) -> bool:
        """Mark an evaluation run as completed."""
        kwargs['completed_at'] = datetime.utcnow()
        kwargs['status'] = 'completed'
        return self.update_eval_run(run_id, **kwargs)
    
    def create_eval_case(self, run_id: str, case_name: str, case_type: str, sla_class: str,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new evaluation case."""
        case_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_case = EvalCase(
                id=case_id,
                eval_run_id=run_id,
                case_name=case_name,
                case_type=case_type,
                sla_class=sla_class,
                started_at=now,
                status="running",
                metadata=metadata or {},
                created_at=now,
                updated_at=now
            )
            session.add(eval_case)
            session.commit()
        
        logger.info(f"Created evaluation case {case_id} for run {run_id}")
        return case_id
    
    def update_eval_case(self, case_id: str, **kwargs) -> bool:
        """Update an evaluation case."""
        with self.get_session() as session:
            eval_case = session.query(EvalCase).filter(EvalCase.id == case_id).first()
            if not eval_case:
                logger.error(f"Evaluation case {case_id} not found")
                return False
            
            for key, value in kwargs.items():
                if hasattr(eval_case, key):
                    setattr(eval_case, key, value)
            
            eval_case.updated_at = datetime.utcnow()
            session.commit()
        
        logger.info(f"Updated evaluation case {case_id}")
        return True
    
    def complete_eval_case(self, case_id: str, **kwargs) -> bool:
        """Mark an evaluation case as completed."""
        kwargs['completed_at'] = datetime.utcnow()
        kwargs['status'] = 'completed'
        return self.update_eval_case(case_id, **kwargs)
    
    def store_metric(self, run_id: str, metric_name: str, metric_value: float, metric_type: str,
                    metric_unit: Optional[str] = None, threshold: Optional[float] = None,
                    operator: Optional[str] = None, passed: Optional[bool] = None,
                    severity: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store an evaluation metric."""
        metric_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_metric = EvalMetric(
                id=metric_id,
                eval_run_id=run_id,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                metric_type=metric_type,
                threshold=threshold,
                operator=operator,
                passed=passed,
                severity=severity,
                metadata=metadata or {},
                created_at=now
            )
            session.add(eval_metric)
            session.commit()
        
        logger.info(f"Stored metric {metric_name}={metric_value} for run {run_id}")
        return metric_id
    
    def store_artifact(self, run_id: str, artifact_type: str, artifact_name: str, artifact_path: str,
                      eval_case_id: Optional[str] = None, artifact_size_bytes: Optional[int] = None,
                      content_type: Optional[str] = None, checksum: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store an evaluation artifact."""
        artifact_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_artifact = EvalArtifact(
                id=artifact_id,
                eval_run_id=run_id,
                eval_case_id=eval_case_id,
                artifact_type=artifact_type,
                artifact_name=artifact_name,
                artifact_path=artifact_path,
                artifact_size_bytes=artifact_size_bytes,
                content_type=content_type,
                checksum=checksum,
                metadata=metadata or {},
                created_at=now
            )
            session.add(eval_artifact)
            session.commit()
        
        logger.info(f"Stored artifact {artifact_name} for run {run_id}")
        return artifact_id
    
    def get_eval_run(self, run_id: str) -> Optional[EvalRunData]:
        """Get an evaluation run by ID."""
        with self.get_session() as session:
            eval_run = session.query(EvalRun).filter(EvalRun.id == run_id).first()
            if not eval_run:
                return None
            
            return EvalRunData(
                id=eval_run.id,
                suite_name=eval_run.suite_name,
                suite_version=eval_run.suite_version,
                started_at=eval_run.started_at,
                completed_at=eval_run.completed_at,
                status=eval_run.status,
                total_cases=eval_run.total_cases,
                passed_cases=eval_run.passed_cases,
                failed_cases=eval_run.failed_cases,
                pass_rate=eval_run.pass_rate,
                avg_latency_ms=eval_run.avg_latency_ms,
                p95_latency_ms=eval_run.p95_latency_ms,
                p99_latency_ms=eval_run.p99_latency_ms,
                total_cost_usd=eval_run.total_cost_usd,
                cost_per_case_usd=eval_run.cost_per_case_usd,
                privacy_mode=eval_run.privacy_mode,
                meta_builder_version=eval_run.meta_builder_version,
                environment=eval_run.environment,
                metadata=eval_run.meta_json,
                created_at=eval_run.created_at,
                updated_at=eval_run.updated_at
            )
    
    def get_eval_cases(self, run_id: str) -> List[EvalCaseData]:
        """Get all evaluation cases for a run."""
        with self.get_session() as session:
            eval_cases = session.query(EvalCase).filter(EvalCase.eval_run_id == run_id).all()
            
            return [
                EvalCaseData(
                    id=case.id,
                    eval_run_id=case.eval_run_id,
                    case_name=case.case_name,
                    case_type=case.case_type,
                    sla_class=case.sla_class,
                    started_at=case.started_at,
                    completed_at=case.completed_at,
                    status=case.status,
                    passed=case.passed,
                    latency_ms=case.latency_ms,
                    cost_usd=case.cost_usd,
                    tokens_used=case.tokens_used,
                    error_message=case.error_message,
                    assertion_results=case.assertion_results,
                    metadata=case.meta_json,
                    created_at=case.created_at,
                    updated_at=case.updated_at
                )
                for case in eval_cases
            ]
    
    def get_recent_runs(self, suite_name: Optional[str] = None, limit: int = 10) -> List[EvalRunData]:
        """Get recent evaluation runs."""
        with self.get_session() as session:
            query = session.query(EvalRun).order_by(EvalRun.started_at.desc())
            
            if suite_name:
                query = query.filter(EvalRun.suite_name == suite_name)
            
            eval_runs = query.limit(limit).all()
            
            return [
                EvalRunData(
                    id=run.id,
                    suite_name=run.suite_name,
                    suite_version=run.suite_version,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    status=run.status,
                    total_cases=run.total_cases,
                    passed_cases=run.passed_cases,
                    failed_cases=run.failed_cases,
                    pass_rate=run.pass_rate,
                    avg_latency_ms=run.avg_latency_ms,
                    p95_latency_ms=run.p95_latency_ms,
                    p99_latency_ms=run.p99_latency_ms,
                    total_cost_usd=run.total_cost_usd,
                    cost_per_case_usd=run.cost_per_case_usd,
                    privacy_mode=run.privacy_mode,
                    meta_builder_version=run.meta_builder_version,
                    environment=run.environment,
                    metadata=run.meta_json,
                    created_at=run.created_at,
                    updated_at=run.updated_at
                )
                for run in eval_runs
            ]


class EvalQuarantineCase(Base):
    """Database model for quarantined evaluation cases."""
    __tablename__ = 'eval_quarantine_cases'
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    suite_id = Column(String(255), nullable=False, index=True)
    case_id = Column(String(255), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    flake_score = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    meta_json = Column('metadata', JSONB)


@dataclass
class EvalQuarantineCaseData:
    """Data class for quarantined case information."""
    id: str
    tenant_id: str
    suite_id: str
    case_id: str
    reason: str
    flake_score: float
    created_at: datetime
    expires_at: datetime
    status: str
    metadata: Optional[Dict[str, Any]]


class EvaluationStorage:
    """Storage layer for evaluation data."""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def create_eval_run(self, suite_name: str, privacy_mode: str, environment: str = "test",
                       meta_builder_version: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new evaluation run."""
        run_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_run = EvalRun(
                id=run_id,
                suite_name=suite_name,
                started_at=now,
                status="running",
                total_cases=0,
                passed_cases=0,
                failed_cases=0,
                privacy_mode=privacy_mode,
                meta_builder_version=meta_builder_version,
                environment=environment,
                meta_json=metadata or {},
                created_at=now,
                updated_at=now
            )
            session.add(eval_run)
            session.commit()
        
        logger.info(f"Created evaluation run {run_id} for suite {suite_name}")
        return run_id
    
    def update_eval_run(self, run_id: str, **kwargs) -> bool:
        """Update an evaluation run."""
        with self.get_session() as session:
            eval_run = session.query(EvalRun).filter(EvalRun.id == run_id).first()
            if not eval_run:
                logger.error(f"Evaluation run {run_id} not found")
                return False
            
            for key, value in kwargs.items():
                if hasattr(eval_run, key):
                    setattr(eval_run, key, value)
            
            eval_run.updated_at = datetime.utcnow()
            session.commit()
        
        logger.info(f"Updated evaluation run {run_id}")
        return True
    
    def complete_eval_run(self, run_id: str, **kwargs) -> bool:
        """Mark an evaluation run as completed."""
        kwargs['completed_at'] = datetime.utcnow()
        kwargs['status'] = 'completed'
        return self.update_eval_run(run_id, **kwargs)
    
    def create_eval_case(self, run_id: str, case_name: str, case_type: str, sla_class: str,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new evaluation case."""
        case_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_case = EvalCase(
                id=case_id,
                eval_run_id=run_id,
                case_name=case_name,
                case_type=case_type,
                sla_class=sla_class,
                started_at=now,
                status="running",
                metadata=metadata or {},
                created_at=now,
                updated_at=now
            )
            session.add(eval_case)
            session.commit()
        
        logger.info(f"Created evaluation case {case_id} for run {run_id}")
        return case_id
    
    def update_eval_case(self, case_id: str, **kwargs) -> bool:
        """Update an evaluation case."""
        with self.get_session() as session:
            eval_case = session.query(EvalCase).filter(EvalCase.id == case_id).first()
            if not eval_case:
                logger.error(f"Evaluation case {case_id} not found")
                return False
            
            for key, value in kwargs.items():
                if hasattr(eval_case, key):
                    setattr(eval_case, key, value)
            
            eval_case.updated_at = datetime.utcnow()
            session.commit()
        
        logger.info(f"Updated evaluation case {case_id}")
        return True
    
    def complete_eval_case(self, case_id: str, **kwargs) -> bool:
        """Mark an evaluation case as completed."""
        kwargs['completed_at'] = datetime.utcnow()
        kwargs['status'] = 'completed'
        return self.update_eval_case(case_id, **kwargs)
    
    def store_metric(self, run_id: str, metric_name: str, metric_value: float, metric_type: str,
                    metric_unit: Optional[str] = None, threshold: Optional[float] = None,
                    operator: Optional[str] = None, passed: Optional[bool] = None,
                    severity: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store an evaluation metric."""
        metric_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_metric = EvalMetric(
                id=metric_id,
                eval_run_id=run_id,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                metric_type=metric_type,
                threshold=threshold,
                operator=operator,
                passed=passed,
                severity=severity,
                metadata=metadata or {},
                created_at=now
            )
            session.add(eval_metric)
            session.commit()
        
        logger.info(f"Stored metric {metric_name}={metric_value} for run {run_id}")
        return metric_id
    
    def store_artifact(self, run_id: str, artifact_type: str, artifact_name: str, artifact_path: str,
                      eval_case_id: Optional[str] = None, artifact_size_bytes: Optional[int] = None,
                      content_type: Optional[str] = None, checksum: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store an evaluation artifact."""
        artifact_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        with self.get_session() as session:
            eval_artifact = EvalArtifact(
                id=artifact_id,
                eval_run_id=run_id,
                eval_case_id=eval_case_id,
                artifact_type=artifact_type,
                artifact_name=artifact_name,
                artifact_path=artifact_path,
                artifact_size_bytes=artifact_size_bytes,
                content_type=content_type,
                checksum=checksum,
                metadata=metadata or {},
                created_at=now
            )
            session.add(eval_artifact)
            session.commit()
        
        logger.info(f"Stored artifact {artifact_name} for run {run_id}")
        return artifact_id
    
    def get_eval_run(self, run_id: str) -> Optional[EvalRunData]:
        """Get an evaluation run by ID."""
        with self.get_session() as session:
            eval_run = session.query(EvalRun).filter(EvalRun.id == run_id).first()
            if not eval_run:
                return None
            
            return EvalRunData(
                id=eval_run.id,
                suite_name=eval_run.suite_name,
                suite_version=eval_run.suite_version,
                started_at=eval_run.started_at,
                completed_at=eval_run.completed_at,
                status=eval_run.status,
                total_cases=eval_run.total_cases,
                passed_cases=eval_run.passed_cases,
                failed_cases=eval_run.failed_cases,
                pass_rate=eval_run.pass_rate,
                avg_latency_ms=eval_run.avg_latency_ms,
                p95_latency_ms=eval_run.p95_latency_ms,
                p99_latency_ms=eval_run.p99_latency_ms,
                total_cost_usd=eval_run.total_cost_usd,
                cost_per_case_usd=eval_run.cost_per_case_usd,
                privacy_mode=eval_run.privacy_mode,
                meta_builder_version=eval_run.meta_builder_version,
                environment=eval_run.environment,
                metadata=eval_run.meta_json,
                created_at=eval_run.created_at,
                updated_at=eval_run.updated_at
            )
    
    def get_eval_cases(self, run_id: str) -> List[EvalCaseData]:
        """Get all evaluation cases for a run."""
        with self.get_session() as session:
            eval_cases = session.query(EvalCase).filter(EvalCase.eval_run_id == run_id).all()
            
            return [
                EvalCaseData(
                    id=case.id,
                    eval_run_id=case.eval_run_id,
                    case_name=case.case_name,
                    case_type=case.case_type,
                    sla_class=case.sla_class,
                    started_at=case.started_at,
                    completed_at=case.completed_at,
                    status=case.status,
                    passed=case.passed,
                    latency_ms=case.latency_ms,
                    cost_usd=case.cost_usd,
                    tokens_used=case.tokens_used,
                    error_message=case.error_message,
                    assertion_results=case.assertion_results,
                    metadata=case.meta_json,
                    created_at=case.created_at,
                    updated_at=case.updated_at
                )
                for case in eval_cases
            ]
    
    def get_recent_runs(self, suite_name: Optional[str] = None, limit: int = 10) -> List[EvalRunData]:
        """Get recent evaluation runs."""
        with self.get_session() as session:
            query = session.query(EvalRun).order_by(EvalRun.started_at.desc())
            
            if suite_name:
                query = query.filter(EvalRun.suite_name == suite_name)
            
            eval_runs = query.limit(limit).all()
            
            return [
                EvalRunData(
                    id=run.id,
                    suite_name=run.suite_name,
                    suite_version=run.suite_version,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    status=run.status,
                    total_cases=run.total_cases,
                    passed_cases=run.passed_cases,
                    failed_cases=run.failed_cases,
                    pass_rate=run.pass_rate,
                    avg_latency_ms=run.avg_latency_ms,
                    p95_latency_ms=run.p95_latency_ms,
                    p99_latency_ms=run.p99_latency_ms,
                    total_cost_usd=run.total_cost_usd,
                    cost_per_case_usd=run.cost_per_case_usd,
                    privacy_mode=run.privacy_mode,
                    meta_builder_version=run.meta_builder_version,
                    environment=run.environment,
                    metadata=run.meta_json,
                    created_at=run.created_at,
                    updated_at=run.updated_at
                )
                for run in eval_runs
            ]
    
    def get_quarantine_cases(self, tenant_id: str, status: Optional[str] = None) -> List[EvalQuarantineCaseData]:
        """Get quarantined cases for a tenant."""
        with self.get_session() as session:
            query = session.query(EvalQuarantineCase).filter(
                EvalQuarantineCase.tenant_id == tenant_id
            )
            
            if status:
                query = query.filter(EvalQuarantineCase.status == status)
            
            quarantine_cases = query.all()
            
            return [
                EvalQuarantineCaseData(
                    id=case.id,
                    tenant_id=case.tenant_id,
                    suite_id=case.suite_id,
                    case_id=case.case_id,
                    reason=case.reason,
                    flake_score=case.flake_score,
                    created_at=case.created_at,
                    expires_at=case.expires_at,
                    status=case.status,
                    metadata=case.meta_json
                )
                for case in quarantine_cases
            ]
    
    def add_quarantine_case(self, tenant_id: str, suite_id: str, case_id: str, reason: str,
                           flake_score: float, ttl_days: int = 7) -> str:
        """Add a case to quarantine."""
        quarantine_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(days=ttl_days)
        
        with self.get_session() as session:
            quarantine_case = EvalQuarantineCase(
                id=quarantine_id,
                tenant_id=tenant_id,
                suite_id=suite_id,
                case_id=case_id,
                reason=reason,
                flake_score=flake_score,
                created_at=now,
                expires_at=expires_at,
                status="ACTIVE",
                metadata={
                    "auto_quarantined": True,
                    "quarantine_reason": reason
                }
            )
            session.add(quarantine_case)
            session.commit()
        
        logger.info(f"Added case {case_id} to quarantine: {reason}")
        return quarantine_id
    
    def release_quarantine_case(self, tenant_id: str, quarantine_id: str) -> bool:
        """Release a case from quarantine."""
        with self.get_session() as session:
            quarantine_case = session.query(EvalQuarantineCase).filter(
                EvalQuarantineCase.id == quarantine_id,
                EvalQuarantineCase.tenant_id == tenant_id
            ).first()
            
            if not quarantine_case:
                return False
            
            quarantine_case.status = "MANUAL_RELEASED"
            quarantine_case.meta_json = quarantine_case.meta_json or {}
            quarantine_case.meta_json["released_at"] = datetime.utcnow().isoformat()
            quarantine_case.meta_json["released_by"] = "manual"
            
            session.commit()
        
        logger.info(f"Released quarantine case {quarantine_id}")
        return True
    
    def cleanup_expired_quarantines(self) -> int:
        """Clean up expired quarantine cases."""
        with self.get_session() as session:
            expired_cases = session.query(EvalQuarantineCase).filter(
                EvalQuarantineCase.status == "ACTIVE",
                EvalQuarantineCase.expires_at <= datetime.utcnow()
            ).all()
            
            for case in expired_cases:
                case.status = "EXPIRED"
                case.meta_json = case.meta_json or {}
                case.meta_json["expired_at"] = datetime.utcnow().isoformat()
            
            session.commit()
            count = len(expired_cases)
        
        logger.info(f"Cleaned up {count} expired quarantine cases")
        return count
