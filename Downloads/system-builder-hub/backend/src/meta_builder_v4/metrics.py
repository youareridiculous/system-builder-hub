"""
Prometheus Metrics for Meta-Builder v4.

This module provides comprehensive metrics collection for monitoring
v4 performance, health, and operational insights.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In a real implementation, you would import prometheus_client
# from prometheus_client import Counter, Gauge, Histogram, Summary

# For now, we'll create simple metric collectors
class MetricCollector:
    """Simple metric collector for demonstration."""
    
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}
        self.summaries: Dict[str, List[float]] = {}
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        self.gauges[key] = value
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a histogram metric."""
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
    
    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a summary metric."""
        key = self._make_key(name, labels)
        if key not in self.summaries:
            self.summaries[key] = []
        self.summaries[key].append(value)
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Make a key for the metric."""
        if labels:
            label_str = ",".join([f"{k}={v}" for k, v in labels.items()])
            return f"{name}[{label_str}]"
        return name
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return {
            "counters": self.counters,
            "gauges": self.gauges,
            "histograms": {k: self._calculate_histogram_stats(v) for k, v in self.histograms.items()},
            "summaries": {k: self._calculate_summary_stats(v) for k, v in self.summaries.items()}
        }
    
    def _calculate_histogram_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate histogram statistics."""
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values)
        }
    
    def _calculate_summary_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate summary statistics."""
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0}
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            "count": count,
            "sum": sum(values),
            "avg": sum(values) / count,
            "p50": sorted_values[count // 2] if count > 0 else 0.0,
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0.0,
            "p99": sorted_values[int(count * 0.99)] if count > 0 else 0.0
        }


class MetaBuilderV4Metrics:
    """Metrics collection for Meta-Builder v4."""
    
    def __init__(self):
        self.collector = MetricCollector()
        self.start_time = datetime.utcnow()
    
    def record_agent_latency(self, agent_name: str, latency_seconds: float, 
                           tenant_id: str, success: bool):
        """Record agent execution latency."""
        labels = {
            "agent": agent_name,
            "tenant_id": tenant_id,
            "success": str(success).lower()
        }
        
        self.collector.observe_histogram("meta_builder_v4_agent_latency_seconds", 
                                       latency_seconds, labels)
        
        # Also record as summary for percentiles
        self.collector.observe_summary("meta_builder_v4_agent_latency_summary", 
                                     latency_seconds, labels)
    
    def record_queue_depth(self, queue_name: str, depth: int):
        """Record queue depth."""
        labels = {"queue": queue_name}
        self.collector.set_gauge("meta_builder_v4_queue_depth", depth, labels)
    
    def record_retry_attempt(self, failure_class: str, tenant_id: str, success: bool):
        """Record retry attempt."""
        labels = {
            "failure_class": failure_class,
            "tenant_id": tenant_id,
            "success": str(success).lower()
        }
        
        self.collector.increment_counter("meta_builder_v4_retry_attempts_total", 1, labels)
    
    def record_replan_attempt(self, tenant_id: str, success: bool):
        """Record re-plan attempt."""
        labels = {
            "tenant_id": tenant_id,
            "success": str(success).lower()
        }
        
        self.collector.increment_counter("meta_builder_v4_replans_total", 1, labels)
    
    def record_rollback_attempt(self, tenant_id: str, success: bool):
        """Record rollback attempt."""
        labels = {
            "tenant_id": tenant_id,
            "success": str(success).lower()
        }
        
        self.collector.increment_counter("meta_builder_v4_rollbacks_total", 1, labels)
    
    def record_budget_exceeded(self, budget_type: str, tenant_id: str):
        """Record budget exceedance."""
        labels = {
            "budget_type": budget_type,
            "tenant_id": tenant_id
        }
        
        self.collector.increment_counter("meta_builder_v4_budget_exceeded_total", 1, labels)
    
    def record_cost_per_run(self, cost_usd: float, tenant_id: str):
        """Record cost per run."""
        labels = {"tenant_id": tenant_id}
        self.collector.observe_histogram("meta_builder_v4_cost_per_run_usd", cost_usd, labels)
    
    def record_circuit_breaker_state(self, failure_class: str, state: str):
        """Record circuit breaker state."""
        labels = {
            "failure_class": failure_class,
            "state": state
        }
        
        # Convert state to numeric value
        state_values = {"closed": 0, "half_open": 1, "open": 2}
        state_value = state_values.get(state, 0)
        
        self.collector.set_gauge("meta_builder_v4_circuit_breaker_state", state_value, labels)
    
    def record_worker_heartbeat(self, worker_id: str, queue_class: str, status: str):
        """Record worker heartbeat."""
        labels = {
            "worker_id": worker_id,
            "queue_class": queue_class,
            "status": status
        }
        
        # Convert status to numeric value
        status_values = {"idle": 0, "busy": 1, "offline": 2, "error": 3}
        status_value = status_values.get(status, 0)
        
        self.collector.set_gauge("meta_builder_v4_worker_status", status_value, labels)
    
    def record_canary_comparison(self, metric_name: str, canary_group: str, 
                               tenant_id: str, value: float):
        """Record canary comparison metrics."""
        labels = {
            "metric_name": metric_name,
            "canary_group": canary_group,
            "tenant_id": tenant_id
        }
        
        self.collector.set_gauge("meta_builder_v4_canary_comparison", value, labels)
    
    def record_chaos_recovery(self, chaos_type: str, recovery_time_seconds: float, 
                            success: bool):
        """Record chaos recovery metrics."""
        labels = {
            "chaos_type": chaos_type,
            "success": str(success).lower()
        }
        
        self.collector.observe_histogram("meta_builder_v4_chaos_recovery_seconds", 
                                       recovery_time_seconds, labels)
    
    def record_repair_phase_duration(self, phase: str, duration_seconds: float, 
                                   tenant_id: str):
        """Record repair phase duration."""
        labels = {
            "phase": phase,
            "tenant_id": tenant_id
        }
        
        self.collector.observe_histogram("meta_builder_v4_repair_phase_duration_seconds", 
                                       duration_seconds, labels)
    
    def record_sla_violation(self, sla_type: str, tenant_id: str):
        """Record SLA violation."""
        labels = {
            "sla_type": sla_type,
            "tenant_id": tenant_id
        }
        
        self.collector.increment_counter("meta_builder_v4_sla_violations_total", 1, labels)
    
    def record_model_selection(self, model_tier: str, provider: str, tenant_id: str):
        """Record model selection."""
        labels = {
            "model_tier": model_tier,
            "provider": provider,
            "tenant_id": tenant_id
        }
        
        self.collector.increment_counter("meta_builder_v4_model_selections_total", 1, labels)
    
    def record_feature_flag_usage(self, flag_name: str, enabled: bool, tenant_id: str):
        """Record feature flag usage."""
        labels = {
            "flag_name": flag_name,
            "enabled": str(enabled).lower(),
            "tenant_id": tenant_id
        }
        
        self.collector.increment_counter("meta_builder_v4_feature_flag_usage_total", 1, labels)
    
    def get_uptime_seconds(self) -> float:
        """Get uptime in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        metrics = self.collector.get_metrics()
        
        # Calculate some derived metrics
        total_runs = sum(metrics["counters"].get("meta_builder_v4_retry_attempts_total", 0))
        total_cost = sum(metrics["histograms"].get("meta_builder_v4_cost_per_run_usd", {}).get("sum", 0))
        
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "total_runs": total_runs,
            "total_cost_usd": total_cost,
            "metrics": metrics
        }


# Global metrics instance
metrics = MetaBuilderV4Metrics()
