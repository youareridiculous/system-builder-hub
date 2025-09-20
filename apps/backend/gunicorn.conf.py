import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = int(os.getenv("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count())))
worker_class = "sync"
timeout = 60
graceful_timeout = 30
keepalive = 5

# IMPORTANT: Do not preload the app while we stabilize startup.
preload_app = False

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

def when_ready(server):
    server.log.info("Gunicorn is ready. Spawning workers...")

def on_starting(server):
    server.log.info("Gunicorn starting up")

def worker_abort(worker):
    worker.log.info("Worker aborted")
