#!/usr/bin/env python3
"""
Background Task Orchestration System
Central registry for background tasks with supervision, auto-restart, and observability.
"""

import threading
import time
import logging
import signal
import sys
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from contextlib import contextmanager
import traceback
import uuid

logger = logging.getLogger(__name__)

@dataclass
class TaskConfig:
    """Configuration for a background task"""
    name: str
    func: Callable
    interval: int  # seconds
    max_retries: int = 3
    backoff_factor: float = 2.0
    timeout: int = 300  # seconds
    enabled: bool = True

class BackgroundTaskRegistry:
    """Central registry for background tasks with supervision"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskConfig] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.task_stats: Dict[str, Dict] = {}
        self.shutdown_event = threading.Event()
        self.registry_lock = threading.Lock()
        
    def register_task(self, task_config: TaskConfig) -> None:
        """Register a new background task"""
        with self.registry_lock:
            self.tasks[task_config.name] = task_config
            self.task_stats[task_config.name] = {
                'started_at': None,
                'last_run': None,
                'last_success': None,
                'last_error': None,
                'run_count': 0,
                'error_count': 0,
                'retry_count': 0,
                'status': 'stopped'
            }
            logger.info(f"Registered background task: {task_config.name}")
    
    def start_task(self, task_name: str) -> bool:
        """Start a specific background task"""
        if task_name not in self.tasks:
            logger.error(f"Task {task_name} not found in registry")
            return False
        
        if task_name in self.running_tasks and self.running_tasks[task_name].is_alive():
            logger.warning(f"Task {task_name} is already running")
            return False
        
        task_config = self.tasks[task_name]
        if not task_config.enabled:
            logger.info(f"Task {task_name} is disabled")
            return False
        
        thread = threading.Thread(
            target=self._run_task_with_supervision,
            args=(task_name,),
            name=f"bg-{task_name}",
            daemon=True
        )
        
        self.running_tasks[task_name] = thread
        self.task_stats[task_name]['started_at'] = datetime.now()
        self.task_stats[task_name]['status'] = 'running'
        
        thread.start()
        logger.info(f"Started background task: {task_name}")
        return True
    
    def stop_task(self, task_name: str) -> bool:
        """Stop a specific background task"""
        if task_name not in self.running_tasks:
            return False
        
        self.task_stats[task_name]['status'] = 'stopping'
        # Note: We can't force-stop threads, but we can mark them for shutdown
        logger.info(f"Stopping background task: {task_name}")
        return True
    
    def start_all_tasks(self) -> None:
        """Start all enabled background tasks"""
        with self.registry_lock:
            for task_name in self.tasks:
                self.start_task(task_name)
    
    def stop_all_tasks(self) -> None:
        """Stop all background tasks"""
        logger.info("Stopping all background tasks...")
        with self.registry_lock:
            for task_name in list(self.running_tasks.keys()):
                self.stop_task(task_name)
        
        # Wait for tasks to finish (with timeout)
        timeout = 30  # seconds
        start_time = time.time()
        while self.running_tasks and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if self.running_tasks:
            logger.warning(f"Some tasks did not stop gracefully: {list(self.running_tasks.keys())}")
    
    def get_task_status(self, task_name: str) -> Optional[Dict]:
        """Get status of a specific task"""
        if task_name not in self.task_stats:
            return None
        return self.task_stats[task_name].copy()
    
    def get_all_task_status(self) -> Dict[str, Dict]:
        """Get status of all tasks"""
        with self.registry_lock:
            return {name: self.get_task_status(name) for name in self.tasks}
    
    def _run_task_with_supervision(self, task_name: str) -> None:
        """Run a task with supervision, auto-restart, and backoff"""
        task_config = self.tasks[task_name]
        stats = self.task_stats[task_name]
        retry_count = 0
        
        while not self.shutdown_event.is_set() and task_name in self.running_tasks:
            try:
                # Generate trace ID for this task run
                trace_id = str(uuid.uuid4())
                
                with self._task_context(task_name, trace_id):
                    logger.info(f"Starting task run: {task_name} (trace_id: {trace_id})")
                    
                    # Run the task with timeout
                    start_time = time.time()
                    result = self._run_with_timeout(task_config.func, task_config.timeout)
                    
                    # Record success
                    duration = time.time() - start_time
                    stats['last_run'] = datetime.now()
                    stats['last_success'] = datetime.now()
                    stats['run_count'] += 1
                    retry_count = 0  # Reset retry count on success
                    
                    logger.info(f"Task completed successfully: {task_name} (duration: {duration:.2f}s)")
                    
            except Exception as e:
                # Record error
                stats['last_run'] = datetime.now()
                stats['last_error'] = datetime.now()
                stats['error_count'] += 1
                retry_count += 1
                
                logger.error(f"Task failed: {task_name} (attempt {retry_count}/{task_config.max_retries}): {str(e)}")
                logger.debug(f"Task error details: {traceback.format_exc()}")
                
                # Check if we should retry
                if retry_count >= task_config.max_retries:
                    logger.error(f"Task {task_name} exceeded max retries, stopping")
                    stats['status'] = 'failed'
                    break
                
                # Calculate backoff delay
                backoff_delay = task_config.interval * (task_config.backoff_factor ** (retry_count - 1))
                logger.info(f"Retrying task {task_name} in {backoff_delay:.1f} seconds")
                time.sleep(backoff_delay)
                continue
            
            # Wait for next run
            if not self.shutdown_event.is_set():
                time.sleep(task_config.interval)
        
        # Clean up
        if task_name in self.running_tasks:
            del self.running_tasks[task_name]
        stats['status'] = 'stopped'
        logger.info(f"Background task stopped: {task_name}")
    
    @contextmanager
    def _task_context(self, task_name: str, trace_id: str):
        """Context manager for task execution with proper logging"""
        try:
            yield
        except Exception as e:
            logger.error(f"Task {task_name} (trace_id: {trace_id}) failed: {str(e)}")
            raise
    
    def _run_with_timeout(self, func: Callable, timeout: int):
        """Run a function with timeout"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Task timed out after {timeout} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]

# Global registry instance
task_registry = BackgroundTaskRegistry()

def register_background_task(name: str, func: Callable, interval: int, **kwargs) -> None:
    """Convenience function to register a background task"""
    config = TaskConfig(name=name, func=func, interval=interval, **kwargs)
    task_registry.register_task(config)

def start_background_tasks() -> None:
    """Start all background tasks"""
    task_registry.start_all_tasks()

def stop_background_tasks() -> None:
    """Stop all background tasks"""
    task_registry.stop_all_tasks()

def get_task_status() -> Dict[str, Dict]:
    """Get status of all background tasks"""
    return task_registry.get_all_task_status()

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    task_registry.shutdown_event.set()
    stop_background_tasks()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
