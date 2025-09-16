"""
LLM Metrics - Prometheus metrics for LLM operations
"""
import time
from typing import Dict, Any

# Simple metrics storage (in real app, use Prometheus)
class LLMMetrics:
    def __init__(self):
        self.setup_attempts = 0
        self.llm_calls = 0
        self.unavailable_count = 0
        self.test_latencies = []
    
    def record_setup_attempt(self, provider: str, success: bool):
        """Record LLM setup attempt"""
        self.setup_attempts += 1
        # In real app: sbh_llm_setup_attempts_total.labels(provider=provider, success=success).inc()
    
    def record_llm_call(self, provider: str, model: str, endpoint: str, success: bool):
        """Record LLM API call"""
        self.llm_calls += 1
        # In real app: sbh_llm_calls_total.labels(provider=provider, model=model, endpoint=endpoint, success=success).inc()
    
    def record_unavailable(self):
        """Record LLM unavailable event"""
        self.unavailable_count += 1
        # In real app: sbh_llm_unavailable_total.inc()
    
    def record_test_latency(self, latency_ms: int):
        """Record LLM test latency"""
        self.test_latencies.append(latency_ms)
        # In real app: sbh_llm_test_latency_ms.observe(latency_ms)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        avg_latency = sum(self.test_latencies) / len(self.test_latencies) if self.test_latencies else 0
        
        return {
            'setup_attempts_total': self.setup_attempts,
            'llm_calls_total': self.llm_calls,
            'unavailable_total': self.unavailable_count,
            'test_latency_avg_ms': avg_latency,
            'test_latency_count': len(self.test_latencies)
        }

# Global metrics instance
llm_metrics = LLMMetrics()
