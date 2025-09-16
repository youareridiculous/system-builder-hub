"""
Meta-Builder v3 Metrics
Prometheus metrics for auto-fix operations and observability.
"""

import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge

# Auto-fix attempt metrics
autofix_attempts_total = Counter(
    'autofix_attempts_total',
    'Total number of auto-fix attempts',
    ['signal_type', 'outcome']
)

# Auto-fix backoff metrics
autofix_backoff_seconds = Histogram(
    'autofix_backoff_seconds',
    'Backoff delay in seconds for auto-fix retries',
    buckets=[1, 2, 5, 10, 30, 60, 120, 300]
)

# Auto-fix re-plan metrics
autofix_replans_total = Counter(
    'autofix_replans_total',
    'Total number of re-plans triggered by auto-fix'
)

# Auto-fix success ratio
autofix_success_ratio = Gauge(
    'autofix_success_ratio',
    'Success ratio of auto-fix attempts (0.0 to 1.0)'
)

# Approval metrics
approval_requests_total = Counter(
    'approval_requests_total',
    'Total number of approval requests',
    ['gate_type', 'status']
)

# Processing time metrics
autofix_processing_seconds = Histogram(
    'autofix_processing_seconds',
    'Time spent processing auto-fix operations',
    ['operation_type']
)


class MetricsCollector:
    """Collector for Meta-Builder v3 metrics."""
    
    def __init__(self):
        self.success_count = 0
        self.total_count = 0
    
    def record_autofix_attempt(self, signal_type: str, outcome: str):
        """Record an auto-fix attempt."""
        autofix_attempts_total.labels(signal_type=signal_type, outcome=outcome).inc()
        
        # Update success ratio
        self.total_count += 1
        if outcome in ['patch_applied', 'retried']:
            self.success_count += 1
        
        if self.total_count > 0:
            autofix_success_ratio.set(self.success_count / self.total_count)
    
    def record_backoff(self, seconds: float):
        """Record backoff delay."""
        autofix_backoff_seconds.observe(seconds)
    
    def record_replan(self):
        """Record a re-plan event."""
        autofix_replans_total.inc()
    
    def record_approval_request(self, gate_type: str, status: str):
        """Record an approval request."""
        approval_requests_total.labels(gate_type=gate_type, status=status).inc()
    
    def record_processing_time(self, operation_type: str, start_time: float):
        """Record processing time for an operation."""
        duration = time.time() - start_time
        autofix_processing_seconds.labels(operation_type=operation_type).observe(duration)


# Global metrics collector instance
metrics = MetricsCollector()
