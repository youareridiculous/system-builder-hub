"""
Distributed Agent Execution for Meta-Builder v4.

This module provides a worker pool abstraction for distributed agent execution
with queue management, concurrency controls, and fault tolerance.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueueClass(Enum):
    """Queue classes for different types of work."""
    CPU = "cpu"      # CPU-intensive tasks
    IO = "io"        # I/O-bound tasks
    LLM = "llm"      # LLM API calls
    HIGH = "high"    # High priority tasks
    LOW = "low"      # Low priority tasks


class WorkerStatus(Enum):
    """Worker status enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class WorkerInfo:
    """Information about a worker."""
    worker_id: str
    queue_class: QueueClass
    status: WorkerStatus
    last_heartbeat: datetime
    current_task_id: Optional[str] = None
    tasks_processed: int = 0
    errors_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskInfo:
    """Information about a task."""
    task_id: str
    run_id: str
    step_id: str
    queue_class: QueueClass
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class WorkerPool:
    """Manages a pool of workers for distributed execution."""
    
    def __init__(self, max_workers: int = 50):
        self.max_workers = max_workers
        self.workers: Dict[str, WorkerInfo] = {}
        self.tasks: Dict[str, TaskInfo] = {}
        self.queues: Dict[QueueClass, List[str]] = {
            queue_class: [] for queue_class in QueueClass
        }
        self.worker_leases: Dict[str, datetime] = {}
        self.lease_duration = timedelta(minutes=5)
        
    async def register_worker(self, worker_id: str, queue_class: QueueClass) -> bool:
        """Register a new worker."""
        if len(self.workers) >= self.max_workers:
            logger.warning(f"Worker pool at capacity, rejecting worker {worker_id}")
            return False
        
        worker = WorkerInfo(
            worker_id=worker_id,
            queue_class=queue_class,
            status=WorkerStatus.IDLE,
            last_heartbeat=datetime.utcnow()
        )
        
        self.workers[worker_id] = worker
        self.queues[queue_class].append(worker_id)
        logger.info(f"Registered worker {worker_id} for queue {queue_class.value}")
        return True
    
    async def unregister_worker(self, worker_id: str):
        """Unregister a worker."""
        if worker_id in self.workers:
            worker = self.workers[worker_id]
            queue_class = worker.queue_class
            
            # Remove from queue
            if worker_id in self.queues[queue_class]:
                self.queues[queue_class].remove(worker_id)
            
            # Requeue any active task
            if worker.current_task_id:
                await self._requeue_task(worker.current_task_id)
            
            # Remove worker
            del self.workers[worker_id]
            if worker_id in self.worker_leases:
                del self.worker_leases[worker_id]
            
            logger.info(f"Unregistered worker {worker_id}")
    
    async def submit_task(self, run_id: str, step_id: str, queue_class: QueueClass,
                         priority: int = 0, max_retries: int = 3) -> str:
        """Submit a task for execution."""
        task_id = f"task_{run_id}_{step_id}_{uuid.uuid4().hex[:8]}"
        
        task = TaskInfo(
            task_id=task_id,
            run_id=run_id,
            step_id=step_id,
            queue_class=queue_class,
            priority=priority,
            max_retries=max_retries
        )
        
        self.tasks[task_id] = task
        
        # Add to appropriate queue
        self.queues[queue_class].append(task_id)
        
        logger.info(f"Submitted task {task_id} to queue {queue_class.value}")
        return task_id
    
    async def get_next_task(self, worker_id: str) -> Optional[TaskInfo]:
        """Get the next task for a worker."""
        if worker_id not in self.workers:
            return None
        
        worker = self.workers[worker_id]
        queue_class = worker.queue_class
        
        # Find available task in worker's queue
        for task_id in self.queues[queue_class]:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == "pending":
                    # Assign task to worker
                    task.worker_id = worker_id
                    task.status = "running"
                    task.started_at = datetime.utcnow()
                    worker.status = WorkerStatus.BUSY
                    worker.current_task_id = task_id
                    
                    # Remove from queue
                    self.queues[queue_class].remove(task_id)
                    
                    logger.info(f"Assigned task {task_id} to worker {worker_id}")
                    return task
        
        return None
    
    async def complete_task(self, worker_id: str, task_id: str, 
                           result: Any = None, error: Optional[str] = None):
        """Mark a task as completed."""
        if worker_id not in self.workers or task_id not in self.tasks:
            return
        
        worker = self.workers[worker_id]
        task = self.tasks[task_id]
        
        if task.worker_id != worker_id:
            logger.warning(f"Worker {worker_id} trying to complete task {task_id} assigned to {task.worker_id}")
            return
        
        # Update task
        task.completed_at = datetime.utcnow()
        task.result = result
        task.error = error
        task.status = "completed" if error is None else "failed"
        
        # Update worker
        worker.status = WorkerStatus.IDLE
        worker.current_task_id = None
        worker.tasks_processed += 1
        if error:
            worker.errors_count += 1
        
        logger.info(f"Completed task {task_id} on worker {worker_id}")
    
    async def heartbeat(self, worker_id: str) -> bool:
        """Update worker heartbeat."""
        if worker_id not in self.workers:
            return False
        
        worker = self.workers[worker_id]
        worker.last_heartbeat = datetime.utcnow()
        
        # Renew lease
        self.worker_leases[worker_id] = datetime.utcnow() + self.lease_duration
        
        return True
    
    async def acquire_lease(self, worker_id: str) -> bool:
        """Acquire a lease for a worker."""
        if worker_id not in self.workers:
            return False
        
        # Check if lease is available
        if worker_id in self.worker_leases:
            lease_expiry = self.worker_leases[worker_id]
            if datetime.utcnow() < lease_expiry:
                return False
        
        # Acquire lease
        self.worker_leases[worker_id] = datetime.utcnow() + self.lease_duration
        return True
    
    async def _requeue_task(self, task_id: str):
        """Requeue a task that was being processed by a failed worker."""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        
        # Reset task state
        task.worker_id = None
        task.started_at = None
        task.status = "pending"
        
        # Add back to queue
        self.queues[task.queue_class].append(task_id)
        
        logger.info(f"Requeued task {task_id}")
    
    async def cleanup_stale_workers(self):
        """Clean up workers that haven't sent heartbeats."""
        now = datetime.utcnow()
        stale_workers = []
        
        for worker_id, worker in self.workers.items():
            if now - worker.last_heartbeat > timedelta(minutes=5):
                stale_workers.append(worker_id)
        
        for worker_id in stale_workers:
            logger.warning(f"Cleaning up stale worker {worker_id}")
            await self.unregister_worker(worker_id)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about queues."""
        stats = {}
        for queue_class in QueueClass:
            queue_tasks = [task_id for task_id in self.queues[queue_class] 
                          if task_id in self.tasks]
            queue_workers = [worker_id for worker_id, worker in self.workers.items()
                           if worker.queue_class == queue_class]
            
            stats[queue_class.value] = {
                "pending_tasks": len(queue_tasks),
                "available_workers": len([w for w in queue_workers 
                                        if self.workers[w].status == WorkerStatus.IDLE]),
                "busy_workers": len([w for w in queue_workers 
                                   if self.workers[w].status == WorkerStatus.BUSY])
            }
        
        return stats
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics about workers."""
        total_workers = len(self.workers)
        idle_workers = len([w for w in self.workers.values() 
                           if w.status == WorkerStatus.IDLE])
        busy_workers = len([w for w in self.workers.values() 
                           if w.status == WorkerStatus.BUSY])
        
        return {
            "total_workers": total_workers,
            "idle_workers": idle_workers,
            "busy_workers": busy_workers,
            "utilization_rate": busy_workers / total_workers if total_workers > 0 else 0.0
        }


class DistributedExecutor:
    """Main interface for distributed execution."""
    
    def __init__(self, max_workers: int = 50):
        self.worker_pool = WorkerPool(max_workers)
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the distributed executor."""
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started distributed executor")
    
    async def stop(self):
        """Stop the distributed executor."""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped distributed executor")
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while self.running:
            try:
                await self.worker_pool.cleanup_stale_workers()
                await asyncio.sleep(60)  # Run every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def submit_agent_task(self, run_id: str, step_id: str, 
                               agent_type: str, priority: int = 0) -> str:
        """Submit an agent task for execution."""
        # Map agent types to queue classes
        queue_mapping = {
            "ProductArchitect": QueueClass.CPU,
            "SystemDesigner": QueueClass.CPU,
            "SecurityCompliance": QueueClass.CPU,
            "CodegenEngineer": QueueClass.CPU,
            "QAEvaluator": QueueClass.IO,
            "AutoFixer": QueueClass.CPU,
            "DevOps": QueueClass.IO,
            "Reviewer": QueueClass.CPU
        }
        
        queue_class = queue_mapping.get(agent_type, QueueClass.CPU)
        return await self.worker_pool.submit_task(run_id, step_id, queue_class, priority)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return {
            "worker_pool": self.worker_pool.get_worker_stats(),
            "queues": self.worker_pool.get_queue_stats(),
            "total_tasks": len(self.worker_pool.tasks),
            "running": self.running
        }
