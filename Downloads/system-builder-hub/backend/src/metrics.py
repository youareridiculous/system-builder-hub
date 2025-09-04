#!/usr/bin/env python3
"""
Prometheus Metrics System
Custom metrics collection for System Builder Hub with latency histograms, error counters, and operational metrics.
"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict, Counter
import json

# Simple Prometheus metrics implementation (in production, use prometheus_client)
class PrometheusMetrics:
    """Prometheus-compatible metrics collection"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.lock = threading.Lock()
        self._start_time = time.time()
        
        # Initialize default metrics
        self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Initialize default metrics"""
        # HTTP metrics
        self.counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
        self.counter('http_errors_total', 'Total HTTP errors', ['method', 'endpoint', 'status'])
        
        # Rate limiting metrics
        self.counter('rate_limit_exceeded_total', 'Total rate limit violations', ['endpoint', 'user_id'])
        
        # Authentication metrics
        self.counter('auth_failures_total', 'Total authentication failures', ['reason'])
        self.counter('auth_success_total', 'Total successful authentications')
        
        # Background task metrics
        self.counter('background_task_runs_total', 'Total background task runs', ['task_name', 'status'])
        self.gauge('background_task_duration_seconds', 'Background task duration', ['task_name'])
        
        # LLM metrics
        self.counter('llm_requests_total', 'Total LLM requests', ['model', 'status'])
        self.histogram('llm_response_time_seconds', 'LLM response time', ['model'])
        
        # Database metrics
        self.counter('db_queries_total', 'Total database queries', ['operation', 'table'])
        self.histogram('db_query_duration_seconds', 'Database query duration', ['operation'])
        
        # Memory metrics
        self.gauge('memory_usage_bytes', 'Memory usage in bytes')
        self.gauge('memory_sessions_active', 'Number of active memory sessions')
        
        # System metrics
        self.gauge('system_uptime_seconds', 'System uptime in seconds')
        self.gauge('active_connections', 'Number of active connections')
    
    def counter(self, name: str, help_text: str, labels: Optional[List[str]] = None):
        """Define a counter metric"""
        with self.lock:
            self.counters[name] = 0
    
    def gauge(self, name: str, help_text: str, labels: Optional[List[str]] = None):
        """Define a gauge metric"""
        with self.lock:
            self.gauges[name] = 0.0
    
    def histogram(self, name: str, help_text: str, labels: Optional[List[str]] = None):
        """Define a histogram metric"""
        with self.lock:
            self.histograms[name] = []
    
    def inc_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter"""
        with self.lock:
            self.counters[name] += value
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge value"""
        with self.lock:
            self.gauges[name] = value
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a histogram value"""
        with self.lock:
            self.histograms[name].append(value)
            # Keep only last 1000 observations to prevent memory bloat
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        # Increment request counter
        self.inc_counter('http_requests_total', labels={'method': method, 'endpoint': endpoint, 'status': str(status)})
        
        # Record error if status >= 400
        if status >= 400:
            self.inc_counter('http_errors_total', labels={'method': method, 'endpoint': endpoint, 'status': str(status)})
        
        # Record response time histogram
        self.observe_histogram('http_response_time_seconds', duration, labels={'method': method, 'endpoint': endpoint})
    
    def record_rate_limit(self, endpoint: str, user_id: str):
        """Record rate limit violation"""
        self.inc_counter('rate_limit_exceeded_total', labels={'endpoint': endpoint, 'user_id': user_id})
    
    def record_auth_failure(self, reason: str):
        """Record authentication failure"""
        self.inc_counter('auth_failures_total', labels={'reason': reason})
    
    def record_auth_success(self):
        """Record successful authentication"""
        self.inc_counter('auth_success_total')
    
    def record_background_task(self, task_name: str, status: str, duration: float):
        """Record background task metrics"""
        self.inc_counter('background_task_runs_total', labels={'task_name': task_name, 'status': status})
        self.set_gauge('background_task_duration_seconds', duration, labels={'task_name': task_name})
    
    def record_llm_request(self, model: str, status: str, duration: float):
        """Record LLM request metrics"""
        self.inc_counter('llm_requests_total', labels={'model': model, 'status': status})
        self.observe_histogram('llm_response_time_seconds', duration, labels={'model': model})
    
    def record_db_query(self, operation: str, table: str, duration: float):
        """Record database query metrics"""
        self.inc_counter('db_queries_total', labels={'operation': operation, 'table': table})
        self.observe_histogram('db_query_duration_seconds', duration, labels={'operation': operation})
    
    def update_system_metrics(self):
        """Update system-level metrics"""
        import psutil
        import os
        
        # Memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        self.set_gauge('memory_usage_bytes', memory_info.rss)
        
        # System uptime
        uptime = time.time() - self._start_time if hasattr(self, '_start_time') else 0
        self.set_gauge('system_uptime_seconds', uptime)
        
        # Active connections (simplified)
        self.set_gauge('active_connections', len(threading.enumerate()))
    
    def generate_prometheus_format(self) -> str:
        """Generate Prometheus-formatted metrics"""
        with self.lock:
            lines = []
            
            # Add timestamp
            timestamp = int(time.time() * 1000)
            
            # Counters
            for name, value in self.counters.items():
                lines.append(f"# HELP {name} Counter metric")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value} {timestamp}")
            
            # Gauges
            for name, value in self.gauges.items():
                lines.append(f"# HELP {name} Gauge metric")
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value} {timestamp}")
            
            # Histograms
            for name, values in self.histograms.items():
                if not values:
                    continue
                
                lines.append(f"# HELP {name} Histogram metric")
                lines.append(f"# TYPE {name} histogram")
                
                # Calculate buckets
                buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
                bucket_counts = []
                
                for bucket in buckets:
                    count = sum(1 for v in values if v <= bucket)
                    bucket_counts.append(count)
                    lines.append(f"{name}_bucket{{le=\"{bucket}\"}} {count} {timestamp}")
                
                # Sum and count
                total_sum = sum(values)
                total_count = len(values)
                lines.append(f"{name}_sum {total_sum} {timestamp}")
                lines.append(f"{name}_count {total_count} {timestamp}")
            
            return "\n".join(lines)
    
    def get_metrics_summary(self) -> Dict:
        """Get a summary of current metrics for API endpoints"""
        with self.lock:
            summary = {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {
                    name: {
                        'count': len(values),
                        'sum': sum(values) if values else 0,
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0,
                        'avg': sum(values) / len(values) if values else 0
                    }
                    for name, values in self.histograms.items()
                },
                'timestamp': datetime.now().isoformat()
            }
            return summary

# Global metrics instance
metrics = PrometheusMetrics()

# Middleware for automatic request metrics
class MetricsMiddleware:
    """Flask middleware for automatic metrics collection"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        start_time = time.time()
        
        def custom_start_response(status, headers, exc_info=None):
            # Record metrics after response
            duration = time.time() - start_time
            status_code = int(status.split()[0])
            method = environ.get('REQUEST_METHOD', 'UNKNOWN')
            path = environ.get('PATH_INFO', '/')
            
            metrics.record_request(method, path, status_code, duration)
            
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)

# Decorator for timing functions
def time_function(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to time function execution and record metrics"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.observe_histogram(metric_name, duration, labels)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.observe_histogram(metric_name, duration, labels)
                raise
        return wrapper
    return decorator

# Background task to update system metrics
def update_system_metrics_task():
    """Background task to update system metrics"""
    metrics.update_system_metrics()
