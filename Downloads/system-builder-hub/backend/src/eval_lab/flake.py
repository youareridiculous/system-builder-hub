"""
Evaluation Lab Flake Detection

Detects flaky test cases and manages quarantine pipeline.
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FlakeClass(Enum):
    """Classification of test case flakiness."""
    STABLE = "stable"
    FLAKY = "flaky"
    QUARANTINE_RECOMMENDED = "quarantine_recommended"


@dataclass
class FlakeScore:
    """Flakiness score and analysis for a test case."""
    score: float  # 0.0 to 1.0, where 1.0 is most flaky
    reasons: List[str] = field(default_factory=list)
    class_: FlakeClass = FlakeClass.STABLE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlakeHeuristics:
    """Configuration for flake detection heuristics."""
    pass_fail_pass_threshold: int = 3  # Number of runs to detect PFP pattern
    latency_variance_threshold: float = 1.5  # P95 * threshold for high variance
    provider_error_threshold: float = 0.3  # 30% provider errors considered flaky
    time_of_day_correlation: bool = False  # Enable time-of-day analysis
    min_runs_for_analysis: int = 5  # Minimum runs needed for analysis
    quarantine_score_threshold: float = 0.7  # Score above which to quarantine


class FlakeDetector:
    """Detects flaky test cases using multiple heuristics."""
    
    def __init__(self, heuristics: Optional[FlakeHeuristics] = None):
        self.heuristics = heuristics or FlakeHeuristics()
    
    def analyze_case_flakiness(self, case_runs: List[Dict[str, Any]]) -> FlakeScore:
        """Analyze flakiness of a test case based on historical runs."""
        if len(case_runs) < self.heuristics.min_runs_for_analysis:
            return FlakeScore(
                score=0.0,
                reasons=["Insufficient data for analysis"],
                class_=FlakeClass.STABLE
            )
        
        # Sort runs by timestamp
        sorted_runs = sorted(case_runs, key=lambda x: x.get('started_at', ''))
        
        # Calculate individual flake indicators
        pass_fail_pass_score = self._detect_pass_fail_pass_pattern(sorted_runs)
        latency_variance_score = self._detect_latency_variance(sorted_runs)
        provider_error_score = self._detect_provider_errors(sorted_runs)
        time_correlation_score = self._detect_time_correlation(sorted_runs)
        
        # Combine scores with weights
        scores = [
            (pass_fail_pass_score, 0.4),  # 40% weight
            (latency_variance_score, 0.3),  # 30% weight
            (provider_error_score, 0.2),  # 20% weight
            (time_correlation_score, 0.1),  # 10% weight
        ]
        
        total_score = sum(score * weight for score, weight in scores)
        reasons = []
        
        # Collect reasons for flakiness
        if pass_fail_pass_score > 0.5:
            reasons.append("Inconsistent pass/fail pattern detected")
        if latency_variance_score > 0.5:
            reasons.append("High latency variance observed")
        if provider_error_score > 0.5:
            reasons.append("Intermittent provider errors")
        if time_correlation_score > 0.5:
            reasons.append("Time-of-day correlation detected")
        
        # Determine classification
        if total_score >= self.heuristics.quarantine_score_threshold:
            class_ = FlakeClass.QUARANTINE_RECOMMENDED
        elif total_score >= 0.3:
            class_ = FlakeClass.FLAKY
        else:
            class_ = FlakeClass.STABLE
        
        return FlakeScore(
            score=total_score,
            reasons=reasons,
            class_=class_,
            metadata={
                "pass_fail_pass_score": pass_fail_pass_score,
                "latency_variance_score": latency_variance_score,
                "provider_error_score": provider_error_score,
                "time_correlation_score": time_correlation_score,
                "total_runs": len(case_runs),
                "analyzed_at": datetime.utcnow().isoformat()
            }
        )
    
    def _detect_pass_fail_pass_pattern(self, runs: List[Dict[str, Any]]) -> float:
        """Detect Pass→Fail→Pass pattern in recent runs."""
        if len(runs) < self.heuristics.pass_fail_pass_threshold:
            return 0.0
        
        # Get recent runs (last N runs)
        recent_runs = runs[-self.heuristics.pass_fail_pass_threshold:]
        results = [run.get('passed', False) for run in recent_runs]
        
        # Check for PFP pattern
        pfp_patterns = 0
        for i in range(len(results) - 2):
            if results[i] and not results[i+1] and results[i+2]:
                pfp_patterns += 1
        
        # Also check for FPF pattern
        fpf_patterns = 0
        for i in range(len(results) - 2):
            if not results[i] and results[i+1] and not results[i+2]:
                fpf_patterns += 1
        
        total_patterns = pfp_patterns + fpf_patterns
        max_possible_patterns = len(results) - 2
        
        if max_possible_patterns == 0:
            return 0.0
        
        return min(1.0, total_patterns / max_possible_patterns)
    
    def _detect_latency_variance(self, runs: List[Dict[str, Any]]) -> float:
        """Detect high variance in latency across runs."""
        latencies = [run.get('latency_ms', 0) for run in runs if run.get('latency_ms')]
        
        if len(latencies) < 3:
            return 0.0
        
        # Calculate P95 latency
        sorted_latencies = sorted(latencies)
        p95_index = int(0.95 * len(sorted_latencies))
        p95_latency = sorted_latencies[p95_index]
        
        # Calculate coefficient of variation
        mean_latency = statistics.mean(latencies)
        if mean_latency == 0:
            return 0.0
        
        std_dev = statistics.stdev(latencies)
        cv = std_dev / mean_latency
        
        # Check if variance exceeds threshold
        if cv > 0.5:  # 50% coefficient of variation
            return min(1.0, cv)
        
        return 0.0
    
    def _detect_provider_errors(self, runs: List[Dict[str, Any]]) -> float:
        """Detect intermittent provider errors vs deterministic failures."""
        provider_errors = 0
        deterministic_failures = 0
        total_runs = len(runs)
        
        for run in runs:
            error_message = run.get('error_message', '')
            if not error_message:
                continue
            
            # Check for provider errors (HTTP 429, 5xx)
            if any(code in error_message for code in ['429', '500', '502', '503', '504']):
                provider_errors += 1
            elif 'assertion' in error_message.lower() or 'validation' in error_message.lower():
                deterministic_failures += 1
        
        if total_runs == 0:
            return 0.0
        
        provider_error_rate = provider_errors / total_runs
        
        # If high provider error rate and low deterministic failures, likely flaky
        if provider_error_rate > self.heuristics.provider_error_threshold:
            return provider_error_rate
        
        return 0.0
    
    def _detect_time_correlation(self, runs: List[Dict[str, Any]]) -> float:
        """Detect time-of-day correlation in failures (optional)."""
        if not self.heuristics.time_of_day_correlation:
            return 0.0
        
        if len(runs) < 10:  # Need more data for time correlation
            return 0.0
        
        # Group failures by hour of day
        hour_failures = {}
        for run in runs:
            if not run.get('passed', True):
                started_at = run.get('started_at')
                if started_at:
                    if isinstance(started_at, str):
                        started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    hour = started_at.hour
                    hour_failures[hour] = hour_failures.get(hour, 0) + 1
        
        if not hour_failures:
            return 0.0
        
        # Check if failures are concentrated in specific hours
        total_failures = sum(hour_failures.values())
        max_failures_in_hour = max(hour_failures.values())
        
        concentration_ratio = max_failures_in_hour / total_failures
        
        # If more than 50% of failures occur in one hour, consider it time-correlated
        if concentration_ratio > 0.5:
            return concentration_ratio
        
        return 0.0


class QuarantineManager:
    """Manages quarantine pipeline for flaky test cases."""
    
    def __init__(self, storage, ttl_days: int = 7):
        self.storage = storage
        self.ttl_days = ttl_days
    
    def add_to_quarantine(self, tenant_id: str, suite_id: str, case_id: str, 
                         reason: str, flake_score: float) -> str:
        """Add a case to quarantine."""
        quarantine_id = f"quarantine_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{case_id}"
        expires_at = datetime.utcnow() + timedelta(days=self.ttl_days)
        
        with self.storage.get_session() as session:
            from src.eval_lab.storage import EvalQuarantineCase
            
            quarantine_case = EvalQuarantineCase(
                id=quarantine_id,
                tenant_id=tenant_id,
                suite_id=suite_id,
                case_id=case_id,
                reason=reason,
                flake_score=flake_score,
                created_at=datetime.utcnow(),
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
    
    def is_quarantined(self, tenant_id: str, suite_id: str, case_id: str) -> bool:
        """Check if a case is currently quarantined."""
        with self.storage.get_session() as session:
            from src.eval_lab.storage import EvalQuarantineCase
            
            quarantine_case = session.query(EvalQuarantineCase).filter(
                EvalQuarantineCase.tenant_id == tenant_id,
                EvalQuarantineCase.suite_id == suite_id,
                EvalQuarantineCase.case_id == case_id,
                EvalQuarantineCase.status == "ACTIVE",
                EvalQuarantineCase.expires_at > datetime.utcnow()
            ).first()
            
            return quarantine_case is not None
    
    def release_from_quarantine(self, tenant_id: str, quarantine_id: str) -> bool:
        """Manually release a case from quarantine."""
        with self.storage.get_session() as session:
            from src.eval_lab.storage import EvalQuarantineCase
            
            quarantine_case = session.query(EvalQuarantineCase).filter(
                EvalQuarantineCase.id == quarantine_id,
                EvalQuarantineCase.tenant_id == tenant_id
            ).first()
            
            if not quarantine_case:
                return False
            
            quarantine_case.status = "MANUAL_RELEASED"
            quarantine_case.metadata = quarantine_case.metadata or {}
            quarantine_case.metadata["released_at"] = datetime.utcnow().isoformat()
            quarantine_case.metadata["released_by"] = "manual"
            
            session.commit()
        
        logger.info(f"Released quarantine case {quarantine_id}")
        return True
    
    def cleanup_expired_quarantines(self) -> int:
        """Clean up expired quarantine cases."""
        with self.storage.get_session() as session:
            from src.eval_lab.storage import EvalQuarantineCase
            
            expired_cases = session.query(EvalQuarantineCase).filter(
                EvalQuarantineCase.status == "ACTIVE",
                EvalQuarantineCase.expires_at <= datetime.utcnow()
            ).all()
            
            for case in expired_cases:
                case.status = "EXPIRED"
                case.metadata = case.metadata or {}
                case.metadata["expired_at"] = datetime.utcnow().isoformat()
            
            session.commit()
            count = len(expired_cases)
        
        logger.info(f"Cleaned up {count} expired quarantine cases")
        return count
    
    def get_quarantine_list(self, tenant_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of quarantined cases for a tenant."""
        with self.storage.get_session() as session:
            from src.eval_lab.storage import EvalQuarantineCase
            
            query = session.query(EvalQuarantineCase).filter(
                EvalQuarantineCase.tenant_id == tenant_id
            )
            
            if status:
                query = query.filter(EvalQuarantineCase.status == status)
            
            quarantine_cases = query.all()
            
            return [
                {
                    "id": case.id,
                    "suite_id": case.suite_id,
                    "case_id": case.case_id,
                    "reason": case.reason,
                    "flake_score": case.flake_score,
                    "created_at": case.created_at.isoformat(),
                    "expires_at": case.expires_at.isoformat(),
                    "status": case.status,
                    "metadata": case.metadata
                }
                for case in quarantine_cases
            ]
