"""
Prometheus metrics for SBH
"""
import os
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Blueprint, Response

# Create metrics blueprint
metrics_bp = Blueprint('metrics', __name__)

# HTTP metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Business metrics
builder_generate_total = Counter(
    'builder_generate_total',
    'Total builder generations',
    ['mode']  # sync, async
)

rate_limit_hits_total = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['endpoint']
)

jobs_enqueued_total = Counter(
    'jobs_enqueued_total',
    'Total jobs enqueued',
    ['queue', 'type']
)

audit_events_total = Counter(
    'audit_events_total',
    'Total audit events',
    ['type', 'action']
)

# System metrics
active_users_gauge = Gauge(
    'active_users',
    'Number of active users'
)

builds_in_progress = Gauge(
    'builds_in_progress',
    'Number of builds in progress'
)

def record_http_request(method: str, endpoint: str, status: int, duration: float):
    """Record HTTP request metrics"""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(endpoint=endpoint).observe(duration)

def record_builder_generate(mode: str):
    """Record builder generation"""
    builder_generate_total.labels(mode=mode).inc()

def record_rate_limit_hit(endpoint: str):
    """Record rate limit hit"""
    rate_limit_hits_total.labels(endpoint=endpoint).inc()

def record_job_enqueued(queue: str, job_type: str):
    """Record job enqueued"""
    jobs_enqueued_total.labels(queue=queue, type=job_type).inc()

def record_audit_event(event_type: str, action: str):
    """Record audit event"""
    audit_events_total.labels(type=event_type, action=action).inc()

def set_active_users(count: int):
    """Set active users gauge"""
    active_users_gauge.set(count)

def set_builds_in_progress(count: int):
    """Set builds in progress gauge"""
    builds_in_progress.set(count)

# Analytics metrics
analytics_events_total = Counter(
    'sbh_analytics_events_total',
    'Total analytics events',
    ['tenant', 'event', 'source']
)

usage_count_total = Counter(
    'sbh_usage_count_total',
    'Usage count by metric',
    ['tenant', 'metric']
)

quota_exceeded_total = Counter(
    'sbh_quota_exceeded_total',
    'Quota exceeded events',
    ['tenant', 'metric']
)

analytics_export_requests_total = Counter(
    'sbh_analytics_export_requests_total',
    'Analytics export requests',
    ['tenant']
)

analytics_rollup_runs_total = Counter(
    'sbh_analytics_rollup_runs_total',
    'Analytics rollup job runs'
)

analytics_rollup_duration_seconds = Histogram(
    'sbh_analytics_rollup_duration_seconds',
    'Analytics rollup job duration',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

analytics_query_duration_seconds = Histogram(
    'sbh_analytics_query_duration_seconds',
    'Analytics query duration',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

def get_analytics_events_counter():
    """Get analytics events counter"""
    return analytics_events_total

def get_usage_count_counter():
    """Get usage count counter"""
    return usage_count_total

def get_quota_exceeded_counter():
    """Get quota exceeded counter"""
    return quota_exceeded_total

def get_analytics_export_counter():
    """Get analytics export counter"""
    return analytics_export_requests_total

def get_rollup_runs_counter():
    """Get rollup runs counter"""
    return analytics_rollup_runs_total

def get_rollup_duration_histogram():
    """Get rollup duration histogram"""
    return analytics_rollup_duration_seconds

def get_analytics_query_duration_histogram():
    """Get analytics query duration histogram"""
    return analytics_query_duration_seconds

@metrics_bp.route('/metrics')
def metrics():
    """Expose Prometheus metrics"""
    # Check if metrics are enabled
    if not os.environ.get('PROMETHEUS_METRICS_ENABLED', 'true').lower() == 'true':
        return Response('Metrics disabled', status=404)
    
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Middleware to record HTTP metrics
class MetricsMiddleware:
    """Middleware to record HTTP metrics"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        import time
        
        # Store start time
        start_time = time.time()
        
        # Call the application
        def custom_start_response(status, headers, exc_info=None):
            # Calculate duration
            duration = time.time() - start_time
            
            # Extract request info
            method = environ.get('REQUEST_METHOD', 'UNKNOWN')
            path = environ.get('PATH_INFO', '/')
            status_code = int(status.split()[0])
            
            # Record metrics
            record_http_request(method, path, status_code, duration)
            
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)
