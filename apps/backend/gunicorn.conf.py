# Gunicorn configuration for SBH Backend on ECS Fargate
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = min(4, (multiprocessing.cpu_count() * 2) + 1)
worker_class = "sync"
worker_connections = 1000
timeout = 60
keepalive = 5

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "sbh-backend"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (not used in container, handled by ALB)
keyfile = None
certfile = None

# Preload app for better performance
preload_app = True

# Worker timeout for graceful shutdown
graceful_timeout = 30

# Environment
raw_env = [
    f"GUNICORN_WORKERS={workers}",
    f"GUNICORN_TIMEOUT={timeout}",
    f"GUNICORN_KEEPALIVE={keepalive}",
]

# Worker lifecycle hooks
def on_starting(server):
    server.log.info("SBH Backend starting up")

def on_reload(server):
    server.log.info("SBH Backend reloading")

def when_ready(server):
    server.log.info("SBH Backend is ready. Workers: %s", workers)

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")
