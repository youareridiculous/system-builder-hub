"""
Gunicorn configuration for production deployment
"""
import os

# Server socket
bind = "0.0.0.0:5001"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', 3))
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Threading
threads = int(os.environ.get('GUNICORN_THREADS', 4))
thread_concurrency = 2

# Timeouts
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))
keepalive = 2
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "sbh"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
