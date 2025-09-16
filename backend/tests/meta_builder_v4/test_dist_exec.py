"""
Tests for distributed execution module.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from src.meta_builder_v4.dist_exec import (
    DistributedExecutor, WorkerPool, QueueClass, WorkerStatus, TaskInfo
)


class TestWorkerPool:
    """Test worker pool functionality."""
    
    @pytest.fixture
    def worker_pool(self):
        """Create a worker pool for testing."""
        return WorkerPool(max_workers=10)
    
    @pytest.mark.asyncio
    async def test_register_worker(self, worker_pool):
        """Test worker registration."""
        # Register a worker
        result = await worker_pool.register_worker("worker_1", QueueClass.CPU)
        assert result is True
        
        # Check worker is registered
        assert "worker_1" in worker_pool.workers
        worker = worker_pool.workers["worker_1"]
        assert worker.worker_id == "worker_1"
        assert worker.queue_class == QueueClass.CPU
        assert worker.status == WorkerStatus.IDLE
    
    @pytest.mark.asyncio
    async def test_register_worker_at_capacity(self, worker_pool):
        """Test worker registration when at capacity."""
        # Fill up the pool
        for i in range(10):
            await worker_pool.register_worker(f"worker_{i}", QueueClass.CPU)
        
        # Try to register one more
        result = await worker_pool.register_worker("worker_11", QueueClass.CPU)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_unregister_worker(self, worker_pool):
        """Test worker unregistration."""
        # Register a worker
        await worker_pool.register_worker("worker_1", QueueClass.CPU)
        
        # Unregister the worker
        await worker_pool.unregister_worker("worker_1")
        
        # Check worker is removed
        assert "worker_1" not in worker_pool.workers
        assert "worker_1" not in worker_pool.queues[QueueClass.CPU]
    
    @pytest.mark.asyncio
    async def test_submit_task(self, worker_pool):
        """Test task submission."""
        # Submit a task
        task_id = await worker_pool.submit_task("run_1", "step_1", QueueClass.CPU)
        
        # Check task is created
        assert task_id in worker_pool.tasks
        task = worker_pool.tasks[task_id]
        assert task.run_id == "run_1"
        assert task.step_id == "step_1"
        assert task.queue_class == QueueClass.CPU
        assert task.status == "pending"
    
    @pytest.mark.asyncio
    async def test_get_next_task(self, worker_pool):
        """Test getting next task for a worker."""
        # Register a worker
        await worker_pool.register_worker("worker_1", QueueClass.CPU)
        
        # Submit a task
        task_id = await worker_pool.submit_task("run_1", "step_1", QueueClass.CPU)
        
        # Get next task
        task = await worker_pool.get_next_task("worker_1")
        
        # Check task is assigned
        assert task is not None
        assert task.task_id == task_id
        assert task.worker_id == "worker_1"
        assert task.status == "running"
        
        # Check worker status
        worker = worker_pool.workers["worker_1"]
        assert worker.status == WorkerStatus.BUSY
        assert worker.current_task_id == task_id
    
    @pytest.mark.asyncio
    async def test_complete_task(self, worker_pool):
        """Test task completion."""
        # Register a worker
        await worker_pool.register_worker("worker_1", QueueClass.CPU)
        
        # Submit and get a task
        task_id = await worker_pool.submit_task("run_1", "step_1", QueueClass.CPU)
        task = await worker_pool.get_next_task("worker_1")
        
        # Complete the task
        await worker_pool.complete_task("worker_1", task_id, result="success")
        
        # Check task is completed
        task = worker_pool.tasks[task_id]
        assert task.status == "completed"
        assert task.result == "success"
        assert task.completed_at is not None
        
        # Check worker is idle
        worker = worker_pool.workers["worker_1"]
        assert worker.status == WorkerStatus.IDLE
        assert worker.current_task_id is None
        assert worker.tasks_processed == 1
    
    @pytest.mark.asyncio
    async def test_heartbeat(self, worker_pool):
        """Test worker heartbeat."""
        # Register a worker
        await worker_pool.register_worker("worker_1", QueueClass.CPU)
        
        # Record heartbeat
        result = await worker_pool.heartbeat("worker_1")
        assert result is True
        
        # Check heartbeat is updated
        worker = worker_pool.workers["worker_1"]
        assert worker.last_heartbeat > datetime.utcnow() - timedelta(seconds=1)
    
    @pytest.mark.asyncio
    async def test_acquire_lease(self, worker_pool):
        """Test lease acquisition."""
        # Register a worker
        await worker_pool.register_worker("worker_1", QueueClass.CPU)
        
        # Acquire lease
        result = await worker_pool.acquire_lease("worker_1")
        assert result is True
        
        # Check lease is created
        assert "worker_1" in worker_pool.worker_leases
        lease_expiry = worker_pool.worker_leases["worker_1"]
        assert lease_expiry > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_get_queue_stats(self, worker_pool):
        """Test queue statistics."""
        # Register workers and submit tasks
        await worker_pool.register_worker("worker_1", QueueClass.CPU)
        await worker_pool.register_worker("worker_2", QueueClass.IO)
        await worker_pool.submit_task("run_1", "step_1", QueueClass.CPU)
        await worker_pool.submit_task("run_2", "step_2", QueueClass.IO)
        
        # Get stats
        stats = worker_pool.get_queue_stats()
        
        # Check stats
        assert "cpu" in stats
        assert "io" in stats
        assert stats["cpu"]["pending_tasks"] == 1
        assert stats["io"]["pending_tasks"] == 1
        assert stats["cpu"]["available_workers"] == 1
        assert stats["io"]["available_workers"] == 1
    
    @pytest.mark.asyncio
    async def test_get_worker_stats(self, worker_pool):
        """Test worker statistics."""
        # Register workers
        await worker_pool.register_worker("worker_1", QueueClass.CPU)
        await worker_pool.register_worker("worker_2", QueueClass.IO)
        
        # Get stats
        stats = worker_pool.get_worker_stats()
        
        # Check stats
        assert stats["total_workers"] == 2
        assert stats["idle_workers"] == 2
        assert stats["busy_workers"] == 0
        assert stats["utilization_rate"] == 0.0


class TestDistributedExecutor:
    """Test distributed executor functionality."""
    
    @pytest.fixture
    def executor(self):
        """Create a distributed executor for testing."""
        return DistributedExecutor(max_workers=5)
    
    @pytest.mark.asyncio
    async def test_start_stop(self, executor):
        """Test executor start and stop."""
        # Start executor
        await executor.start()
        assert executor.running is True
        
        # Stop executor
        await executor.stop()
        assert executor.running is False
    
    @pytest.mark.asyncio
    async def test_submit_agent_task(self, executor):
        """Test agent task submission."""
        # Start executor
        await executor.start()
        
        # Submit agent task
        task_id = await executor.submit_agent_task("run_1", "step_1", "ProductArchitect")
        
        # Check task is submitted
        assert task_id is not None
        assert task_id in executor.worker_pool.tasks
        
        # Stop executor
        await executor.stop()
    
    def test_get_stats(self, executor):
        """Test getting executor statistics."""
        stats = executor.get_stats()
        
        # Check stats structure
        assert "worker_pool" in stats
        assert "queues" in stats
        assert "total_tasks" in stats
        assert "running" in stats
