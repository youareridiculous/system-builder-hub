"""
Canary Testing for Meta-Builder v4.

This module provides canary testing capabilities to compare v4 performance
against v2/v3 baseline with statistical analysis.
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class CanaryGroup(Enum):
    """Canary testing groups."""
    CONTROL = "control"  # v2/v3 baseline
    V4 = "v4"           # v4 experimental


@dataclass
class CanarySample:
    """A sample in canary testing."""
    sample_id: str
    run_id: str
    tenant_id: str
    canary_group: CanaryGroup
    assigned_at: datetime
    completed_at: Optional[datetime] = None
    success: Optional[bool] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    duration_seconds: int = 0
    retry_count: int = 0
    replan_count: int = 0
    rollback_count: int = 0
    
    def is_completed(self) -> bool:
        """Check if sample is completed."""
        return self.completed_at is not None
    
    def get_duration(self) -> int:
        """Get duration in seconds."""
        if self.completed_at and self.assigned_at:
            return int((self.completed_at - self.assigned_at).total_seconds())
        return 0


@dataclass
class CanaryMetrics:
    """Aggregated metrics for a canary group."""
    success_rate: float
    avg_cost_usd: float
    avg_duration_seconds: float
    retry_rate: float
    replan_rate: float
    rollback_rate: float
    confidence_score: float
    sample_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success_rate": self.success_rate,
            "avg_cost_usd": self.avg_cost_usd,
            "avg_duration_seconds": self.avg_duration_seconds,
            "retry_rate": self.retry_rate,
            "replan_rate": self.replan_rate,
            "rollback_rate": self.rollback_rate,
            "confidence_score": self.confidence_score,
            "sample_size": self.sample_size
        }


@dataclass
class CanaryComparison:
    """Comparison between canary groups."""
    control_metrics: CanaryMetrics
    v4_metrics: CanaryMetrics
    success_rate_delta: float
    cost_ratio: float
    duration_ratio: float
    statistical_significance: bool
    p_value: float
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "control": self.control_metrics.to_dict(),
            "v4": self.v4_metrics.to_dict(),
            "success_rate_delta": self.success_rate_delta,
            "cost_ratio": self.cost_ratio,
            "duration_ratio": self.duration_ratio,
            "statistical_significance": self.statistical_significance,
            "p_value": self.p_value,
            "recommendation": self.recommendation
        }


class CanaryManager:
    """Manages canary testing configuration and execution."""
    
    def __init__(self, canary_percent: float = 0.0):
        self.canary_percent = canary_percent
        self.samples: Dict[str, CanarySample] = {}
        self.config = {
            "min_sample_size": 100,
            "max_sample_size": 1000,
            "evaluation_window_hours": 24,
            "success_threshold": 0.95,
            "cost_threshold": 1.2,
            "duration_threshold": 1.1
        }
    
    def should_use_v4(self, run_id: str, tenant_id: str) -> bool:
        """Determine if a run should use v4 based on canary configuration."""
        if self.canary_percent <= 0.0:
            return False
        
        # Check if run is already assigned to a group
        existing_sample = self._get_sample_by_run_id(run_id)
        if existing_sample:
            return existing_sample.canary_group == CanaryGroup.V4
        
        # Determine group based on canary percentage
        use_v4 = random.random() < self.canary_percent
        
        # Create canary sample
        sample_id = f"sample_{run_id}_{int(time.time())}"
        sample = CanarySample(
            sample_id=sample_id,
            run_id=run_id,
            tenant_id=tenant_id,
            canary_group=CanaryGroup.V4 if use_v4 else CanaryGroup.CONTROL,
            assigned_at=datetime.utcnow()
        )
        
        self.samples[sample_id] = sample
        logger.info(f"Assigned run {run_id} to canary group {sample.canary_group.value}")
        
        return use_v4
    
    def _get_sample_by_run_id(self, run_id: str) -> Optional[CanarySample]:
        """Get sample by run ID."""
        for sample in self.samples.values():
            if sample.run_id == run_id:
                return sample
        return None
    
    def record_completion(self, run_id: str, success: bool, metrics: Dict[str, Any],
                         cost_usd: float, duration_seconds: int, retry_count: int = 0,
                         replan_count: int = 0, rollback_count: int = 0):
        """Record completion of a canary sample."""
        sample = self._get_sample_by_run_id(run_id)
        if not sample:
            logger.warning(f"No canary sample found for run {run_id}")
            return
        
        sample.completed_at = datetime.utcnow()
        sample.success = success
        sample.metrics = metrics
        sample.cost_usd = cost_usd
        sample.duration_seconds = duration_seconds
        sample.retry_count = retry_count
        sample.replan_count = replan_count
        sample.rollback_count = rollback_count
        
        logger.info(f"Recorded completion for canary sample {sample.sample_id}")
    
    def get_canary_metrics(self, hours: int = 24) -> Dict[str, CanaryMetrics]:
        """Get metrics for canary groups within the specified time window."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        control_samples = []
        v4_samples = []
        
        for sample in self.samples.values():
            if sample.assigned_at < cutoff or not sample.is_completed():
                continue
            
            if sample.canary_group == CanaryGroup.CONTROL:
                control_samples.append(sample)
            elif sample.canary_group == CanaryGroup.V4:
                v4_samples.append(sample)
        
        return {
            "control": self._calculate_group_metrics(control_samples),
            "v4": self._calculate_group_metrics(v4_samples)
        }
    
    def _calculate_group_metrics(self, samples: List[CanarySample]) -> CanaryMetrics:
        """Calculate metrics for a group of samples."""
        if not samples:
            return CanaryMetrics(
                success_rate=0.0,
                avg_cost_usd=0.0,
                avg_duration_seconds=0.0,
                retry_rate=0.0,
                replan_rate=0.0,
                rollback_rate=0.0,
                confidence_score=0.0,
                sample_size=0
            )
        
        successful_samples = [s for s in samples if s.success]
        success_rate = len(successful_samples) / len(samples)
        
        avg_cost = sum(s.cost_usd for s in samples) / len(samples)
        avg_duration = sum(s.duration_seconds for s in samples) / len(samples)
        
        avg_retries = sum(s.retry_count for s in samples) / len(samples)
        avg_replans = sum(s.replan_count for s in samples) / len(samples)
        avg_rollbacks = sum(s.rollback_count for s in samples) / len(samples)
        
        # Calculate confidence score (simplified)
        confidence_score = success_rate * 0.6 + (1.0 - avg_retries / 10) * 0.4
        
        return CanaryMetrics(
            success_rate=success_rate,
            avg_cost_usd=avg_cost,
            avg_duration_seconds=avg_duration,
            retry_rate=avg_retries,
            replan_rate=avg_replans,
            rollback_rate=avg_rollbacks,
            confidence_score=confidence_score,
            sample_size=len(samples)
        )
    
    def evaluate_canary_performance(self) -> Dict[str, Any]:
        """Evaluate canary performance against thresholds."""
        metrics = self.get_canary_metrics(self.config["evaluation_window_hours"])
        
        control = metrics["control"]
        v4 = metrics["v4"]
        
        # Check if we have enough samples
        if (control.sample_size < self.config["min_sample_size"] or 
            v4.sample_size < self.config["min_sample_size"]):
            return {
                "evaluation_ready": False,
                "reason": "Insufficient sample size",
                "control_samples": control.sample_size,
                "v4_samples": v4.sample_size,
                "min_required": self.config["min_sample_size"]
            }
        
        # Calculate relative performance
        success_ratio = v4.success_rate / control.success_rate if control.success_rate > 0 else 0.0
        cost_ratio = v4.avg_cost_usd / control.avg_cost_usd if control.avg_cost_usd > 0 else 1.0
        duration_ratio = v4.avg_duration_seconds / control.avg_duration_seconds if control.avg_duration_seconds > 0 else 1.0
        
        # Evaluate against thresholds
        success_ok = success_ratio >= self.config["success_threshold"]
        cost_ok = cost_ratio <= self.config["cost_threshold"]
        duration_ok = duration_ratio <= self.config["duration_threshold"]
        
        overall_success = success_ok and cost_ok and duration_ok
        
        # Calculate statistical significance (simplified)
        statistical_significance = self._calculate_statistical_significance(control, v4)
        
        return {
            "evaluation_ready": True,
            "overall_success": overall_success,
            "metrics": {
                "success_rate": {
                    "control": control.success_rate,
                    "v4": v4.success_rate,
                    "ratio": success_ratio,
                    "threshold": self.config["success_threshold"],
                    "pass": success_ok
                },
                "cost": {
                    "control": control.avg_cost_usd,
                    "v4": v4.avg_cost_usd,
                    "ratio": cost_ratio,
                    "threshold": self.config["cost_threshold"],
                    "pass": cost_ok
                },
                "duration": {
                    "control": control.avg_duration_seconds,
                    "v4": v4.avg_duration_seconds,
                    "ratio": duration_ratio,
                    "threshold": self.config["duration_threshold"],
                    "pass": duration_ok
                }
            },
            "statistical_significance": statistical_significance,
            "recommendation": self._get_recommendation(overall_success, success_ratio, cost_ratio, duration_ratio)
        }
    
    def _calculate_statistical_significance(self, control: CanaryMetrics, 
                                          v4: CanaryMetrics) -> bool:
        """Calculate statistical significance (simplified)."""
        # This is a simplified version. In practice, you'd use proper statistical tests
        # like chi-square test for success rates, t-test for continuous variables
        
        # For now, consider significant if sample sizes are large enough and
        # differences are substantial
        min_sample_size = 50
        if control.sample_size < min_sample_size or v4.sample_size < min_sample_size:
            return False
        
        # Check if success rate difference is significant
        success_diff = abs(v4.success_rate - control.success_rate)
        if success_diff > 0.05:  # 5% difference
            return True
        
        # Check if cost difference is significant
        cost_diff = abs(v4.avg_cost_usd - control.avg_cost_usd) / control.avg_cost_usd
        if cost_diff > 0.1:  # 10% difference
            return True
        
        return False
    
    def _get_recommendation(self, overall_success: bool, success_ratio: float,
                           cost_ratio: float, duration_ratio: float) -> str:
        """Get recommendation based on evaluation results."""
        if overall_success:
            if success_ratio > 1.1 and cost_ratio < 0.9:
                return "promote_v4_aggressively"
            elif success_ratio > 1.05:
                return "promote_v4_cautiously"
            else:
                return "maintain_canary"
        else:
            if success_ratio < 0.8:
                return "rollback_v4_immediately"
            elif cost_ratio > 1.5:
                return "reduce_canary_percentage"
            else:
                return "investigate_and_adjust"
    
    def get_canary_stats(self) -> Dict[str, Any]:
        """Get canary testing statistics."""
        total_samples = len(self.samples)
        completed_samples = len([s for s in self.samples.values() if s.is_completed()])
        
        control_samples = [s for s in self.samples.values() if s.canary_group == CanaryGroup.CONTROL]
        v4_samples = [s for s in self.samples.values() if s.canary_group == CanaryGroup.V4]
        
        return {
            "config": {
                "canary_percent": self.canary_percent,
                "evaluation_window_hours": self.config["evaluation_window_hours"]
            },
            "samples": {
                "total": total_samples,
                "completed": completed_samples,
                "control": len(control_samples),
                "v4": len(v4_samples)
            },
            "actual_percent": len(v4_samples) / total_samples if total_samples > 0 else 0.0,
            "evaluation": self.evaluate_canary_performance()
        }


# Global canary manager instance
canary_manager = CanaryManager()
