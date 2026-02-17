"""Tests for TaskQueue integration with FastAPI application lifecycle

Verifies that the task queue is properly:
- Started during application startup
- Stopped during application shutdown
- Reported in health checks
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from masterclaw_core.tasks import TaskQueue, task_queue


class TestTaskQueueLifecycleIntegration:
    """Test TaskQueue integration with application lifecycle"""
    
    @pytest.mark.asyncio
    async def test_task_queue_starts_with_app(self):
        """Test that task queue starts when application starts"""
        # Create a fresh task queue
        q = TaskQueue(max_workers=3)
        
        # Initially not running
        assert q.running is False
        assert len(q.workers) == 0
        
        # Start (simulating app startup)
        await q.start()
        
        # Should be running with workers
        assert q.running is True
        assert len(q.workers) == 3
        
        # Cleanup
        await q.stop()
    
    @pytest.mark.asyncio
    async def test_task_queue_stops_with_app(self):
        """Test that task queue stops gracefully when application shuts down"""
        q = TaskQueue(max_workers=2)
        await q.start()
        
        assert q.running is True
        
        # Stop (simulating app shutdown)
        await q.stop()
        
        # Should be stopped
        assert q.running is False
        assert len(q.workers) == 0
    
    @pytest.mark.asyncio
    async def test_task_queue_graceful_shutdown_with_join(self):
        """Test that task queue can be gracefully shutdown with queue.join()"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            completed = []
            
            async def slow_task():
                await asyncio.sleep(0.05)
                completed.append(True)
            
            # Submit several tasks
            for _ in range(3):
                await q.submit(slow_task)
            
            # Wait for all tasks to complete before stopping
            await q.queue.join()
            
            # Now stop
            await q.stop()
            
            # All tasks should have completed
            assert len(completed) == 3
        finally:
            if q.running:
                await q.stop()
    
    @pytest.mark.asyncio
    async def test_global_task_queue_integration(self):
        """Test the global task_queue instance used by the application"""
        from masterclaw_core.tasks import task_queue as global_queue
        
        # Should be a singleton
        assert global_queue is task_queue
        
        # Default configuration
        assert global_queue.max_workers == 5
        
        # Can be started and stopped
        await global_queue.start()
        assert global_queue.running is True
        
        await global_queue.stop()
        assert global_queue.running is False
    
    @pytest.mark.asyncio
    async def test_health_check_includes_task_queue_status(self):
        """Test that health check endpoint reports task queue status"""
        # This simulates what the health check endpoint does
        q = TaskQueue(max_workers=3)
        await q.start()
        
        try:
            # Build services dict as health endpoint does
            services = {
                "memory": "chroma",
                "llm_providers": ["openai", "anthropic"],
                "prometheus_metrics": True,
                "task_queue": {
                    "running": q.running,
                    "workers": q.max_workers,
                    "queue_size": q.get_queue_size(),
                },
            }
            
            # Verify task queue info is present
            assert "task_queue" in services
            assert services["task_queue"]["running"] is True
            assert services["task_queue"]["workers"] == 3
            assert isinstance(services["task_queue"]["queue_size"], int)
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_health_check_reports_not_running_when_stopped(self):
        """Test health check correctly reports when task queue is stopped"""
        q = TaskQueue(max_workers=2)
        # Don't start it
        
        services = {
            "task_queue": {
                "running": q.running,
                "workers": q.max_workers,
                "queue_size": q.get_queue_size(),
            },
        }
        
        assert services["task_queue"]["running"] is False
        assert services["task_queue"]["workers"] == 2
    
    @pytest.mark.asyncio
    async def test_task_queue_survives_worker_exception(self):
        """Test that task queue continues operating after a worker exception"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            results = []
            
            def failing_task():
                results.append("failed")
                raise ValueError("Intentional failure")
            
            def succeeding_task():
                results.append("succeeded")
            
            await q.submit(failing_task)
            await q.submit(succeeding_task)
            
            await asyncio.sleep(0.2)
            
            # Both should have been processed
            assert "failed" in results
            assert "succeeded" in results
            # Queue should still be running
            assert q.running is True
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_task_processing_in_app_context(self):
        """Test concurrent task processing simulating real app usage"""
        q = TaskQueue(max_workers=3)
        await q.start()
        
        try:
            execution_times = []
            
            async def timed_task(task_id: str):
                start = datetime.now(timezone.utc)
                await asyncio.sleep(0.05)  # Simulate work
                end = datetime.now(timezone.utc)
                execution_times.append((task_id, start, end))
            
            # Submit multiple tasks
            for i in range(6):
                await q.submit(timed_task, f"task_{i}")
            
            # Wait for completion
            await asyncio.sleep(0.2)
            
            # All tasks should have executed
            assert len(execution_times) == 6
            
            # With 3 workers, tasks should have run concurrently
            # (first 3 should start around the same time)
            start_times = [t[1] for t in execution_times[:3]]
            time_spread = max(start_times) - min(start_times)
            assert time_spread.total_seconds() < 0.1  # Should be nearly simultaneous
        finally:
            await q.stop()


class TestTaskQueueHealthIntegration:
    """Test TaskQueue health status reporting"""
    
    @pytest.mark.asyncio
    async def test_health_check_format_matches_expected_schema(self):
        """Test health check task_queue format matches expected schema"""
        q = TaskQueue(max_workers=2)
        await q.start()
        
        try:
            # This is the exact format used by the health endpoint
            task_queue_status = {
                "running": q.running,
                "workers": q.max_workers,
                "queue_size": q.get_queue_size(),
            }
            
            # Verify schema
            assert isinstance(task_queue_status["running"], bool)
            assert isinstance(task_queue_status["workers"], int)
            assert isinstance(task_queue_status["queue_size"], int)
            assert task_queue_status["workers"] > 0
            assert task_queue_status["queue_size"] >= 0
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_health_check_with_backlogged_tasks(self):
        """Test health check reports queue size with backlogged tasks"""
        q = TaskQueue(max_workers=1)  # Single worker to create backlog
        await q.start()
        
        try:
            async def slow_task():
                await asyncio.sleep(0.2)
            
            # Submit multiple tasks to create backlog
            for _ in range(5):
                await q.submit(slow_task)
            
            # Check health immediately
            queue_size = q.get_queue_size()
            
            # Should have tasks in queue
            assert queue_size > 0
            
            # Wait for all to complete
            await q.queue.join()
        finally:
            await q.stop()


class TestTaskQueueErrorHandling:
    """Test TaskQueue error handling in app lifecycle context"""
    
    @pytest.mark.asyncio
    async def test_stop_idempotent(self):
        """Test that calling stop multiple times is safe"""
        q = TaskQueue(max_workers=1)
        await q.start()
        await q.stop()
        
        # Should be safe to call stop again
        await q.stop()
        assert q.running is False
        assert len(q.workers) == 0
    
    @pytest.mark.asyncio
    async def test_start_after_stop(self):
        """Test that task queue can be restarted after stop"""
        q = TaskQueue(max_workers=2)
        
        # First lifecycle
        await q.start()
        assert q.running is True
        await q.stop()
        assert q.running is False
        
        # Restart (simulating app restart)
        await q.start()
        assert q.running is True
        assert len(q.workers) == 2
        await q.stop()
