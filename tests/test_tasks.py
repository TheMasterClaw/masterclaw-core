"""Tests for the task queue module

Comprehensive test coverage for TaskQueue including:
- Basic task execution
- Error handling and retry logic
- Concurrent task processing
- Queue lifecycle management
- Edge cases and timeouts
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from masterclaw_core.tasks import TaskQueue, task_queue


class TestTaskQueueBasic:
    """Basic task queue functionality"""
    
    @pytest.fixture
    async def queue(self):
        """Create and start a task queue for testing"""
        q = TaskQueue(max_workers=2)
        await q.start()
        yield q
        await q.stop()
    
    @pytest.mark.asyncio
    async def test_submit_simple_task(self):
        """Test submitting a simple synchronous task"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            result = []
            
            def simple_task():
                result.append("executed")
            
            task_id = await q.submit(simple_task)
            
            # Wait for task to complete
            await asyncio.sleep(0.1)
            
            assert len(result) == 1
            assert result[0] == "executed"
            assert task_id.startswith("task_")
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_submit_async_task(self):
        """Test submitting an async task"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            result = []
            
            async def async_task():
                await asyncio.sleep(0.01)
                result.append("async_executed")
            
            await q.submit(async_task)
            await asyncio.sleep(0.15)
            
            assert len(result) == 1
            assert result[0] == "async_executed"
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_task_with_args_and_kwargs(self):
        """Test task with positional and keyword arguments"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            result = {}
            
            def task_with_args(a, b, c=None, d=None):
                result['a'] = a
                result['b'] = b
                result['c'] = c
                result['d'] = d
            
            await q.submit(task_with_args, 1, 2, c=3, d=4)
            await asyncio.sleep(0.1)
            
            assert result == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_tasks_sequential(self):
        """Test submitting multiple tasks that run sequentially"""
        q = TaskQueue(max_workers=1)  # Single worker = sequential
        await q.start()
        
        try:
            results = []
            
            def task(n):
                results.append(n)
            
            for i in range(5):
                await q.submit(task, i)
            
            await asyncio.sleep(0.3)
            
            assert len(results) == 5
            assert results == [0, 1, 2, 3, 4]
        finally:
            await q.stop()


class TestTaskQueueConcurrency:
    """Test concurrent task processing"""
    
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self):
        """Test that multiple workers process tasks concurrently"""
        q = TaskQueue(max_workers=3)
        await q.start()
        
        try:
            start_times = {}
            end_times = {}
            
            async def timed_task(task_id):
                start_times[task_id] = datetime.now(timezone.utc)
                await asyncio.sleep(0.1)  # Simulate work
                end_times[task_id] = datetime.now(timezone.utc)
            
            # Submit 3 tasks simultaneously
            tasks = []
            for i in range(3):
                task_id = await q.submit(timed_task, f"task_{i}")
                tasks.append(task_id)
            
            # Wait for all to complete
            await asyncio.sleep(0.2)
            
            # With 3 workers, all should start around the same time
            # Check that tasks ran concurrently (overlap in execution)
            assert len(start_times) == 3
            assert len(end_times) == 3
            
            # All start times should be within 50ms of each other
            start_times_list = [start_times[f"task_{i}"] for i in range(3)]
            time_spread = max(start_times_list) - min(start_times_list)
            assert time_spread.total_seconds() < 0.05  # Should start almost simultaneously
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_queue_size_tracking(self):
        """Test queue size is tracked correctly"""
        q = TaskQueue(max_workers=1)  # Single worker to create backlog
        await q.start()
        
        try:
            completed = []
            
            async def trackable_task():
                await asyncio.sleep(0.05)
                completed.append(True)
            
            # Queue should start empty
            initial_size = q.get_queue_size()
            assert initial_size == 0
            
            # Submit multiple tasks
            for _ in range(5):
                await q.submit(trackable_task)
            
            # Queue should have tasks (may be 4-5 depending on timing)
            size_after_submit = q.get_queue_size()
            assert size_after_submit >= 3  # Most should be queued
            
            # Wait for all tasks to complete using join
            await q.queue.join()
            
            # All tasks should have completed
            assert len(completed) == 5
        finally:
            await q.stop()


class TestTaskQueueErrors:
    """Test error handling in task queue"""
    
    @pytest.mark.asyncio
    async def test_task_exception_handled(self):
        """Test that task exceptions don't crash the worker"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            error_triggered = []
            
            def failing_task():
                error_triggered.append(True)
                raise ValueError("Task failed intentionally")
            
            def successful_task():
                error_triggered.append(True)
                return "success"
            
            await q.submit(failing_task)
            await q.submit(successful_task)
            
            await asyncio.sleep(0.2)
            
            # Both should have been attempted
            assert len(error_triggered) == 2
            # Queue should still be running
            assert q.running is True
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_async_task_exception_handled(self):
        """Test that async task exceptions are handled"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            async def async_failing_task():
                await asyncio.sleep(0.01)
                raise RuntimeError("Async task failed")
            
            await q.submit(async_failing_task)
            await asyncio.sleep(0.1)
            
            # Queue should still be operational
            assert q.running is True
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_worker_restart_after_error(self):
        """Test that workers continue after task errors"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            results = []
            
            def fail_then_succeed():
                results.append("attempted")
                if len(results) == 1:
                    raise ValueError("First attempt fails")
            
            await q.submit(fail_then_succeed)
            await q.submit(fail_then_succeed)
            
            await asyncio.sleep(0.2)
            
            # Both tasks should have been attempted
            assert len(results) == 2
        finally:
            await q.stop()


class TestTaskQueueLifecycle:
    """Test task queue lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """Test starting and stopping the queue"""
        q = TaskQueue(max_workers=2)
        
        assert q.running is False
        assert len(q.workers) == 0
        
        await q.start()
        assert q.running is True
        assert len(q.workers) == 2
        
        await q.stop()
        assert q.running is False
    
    @pytest.mark.asyncio
    async def test_stop_clears_workers(self):
        """Test that stop clears the workers list"""
        q = TaskQueue(max_workers=3)
        await q.start()
        
        assert len(q.workers) == 3
        
        await q.stop()
        
        # Workers should be cleared
        assert len(q.workers) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_start_calls(self):
        """Test behavior when start is called multiple times"""
        q = TaskQueue(max_workers=2)
        
        await q.start()
        initial_workers = len(q.workers)
        
        # Calling start again should add more workers
        await q.start()
        assert len(q.workers) == initial_workers * 2
        
        await q.stop()
    
    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """Test that stop works even if start was never called"""
        q = TaskQueue(max_workers=2)
        
        # Should not raise
        await q.stop()
        
        assert q.running is False
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_pending_tasks(self):
        """Test graceful shutdown waits for pending tasks"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            completed = []
            
            async def slow_task():
                await asyncio.sleep(0.1)
                completed.append(True)
            
            # Submit task and immediately stop
            await q.submit(slow_task)
            
            # Give task time to start
            await asyncio.sleep(0.05)
            
            # Stop should wait for task to complete
            await q.stop()
            
            # Task should have completed
            assert len(completed) == 1
        finally:
            if q.running:
                await q.stop()


class TestTaskQueueEdgeCases:
    """Test edge cases and special scenarios"""
    
    @pytest.mark.asyncio
    async def test_empty_queue_behavior(self):
        """Test queue behavior when empty"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            # Queue should be empty
            assert q.get_queue_size() == 0
            
            # Workers should handle empty queue gracefully
            await asyncio.sleep(0.1)
            
            # Queue should still be running
            assert q.running is True
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_task_id_uniqueness(self):
        """Test that task IDs are unique"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            task_ids = []
            
            def dummy_task():
                pass
            
            # Submit many tasks rapidly
            for _ in range(10):
                task_id = await q.submit(dummy_task)
                task_ids.append(task_id)
            
            # All IDs should be unique
            assert len(task_ids) == len(set(task_ids))
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_nested_async_calls(self):
        """Test tasks with nested async operations"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            result = []
            
            async def inner():
                await asyncio.sleep(0.01)
                return "inner"
            
            async def outer():
                inner_result = await inner()
                result.append(inner_result)
            
            await q.submit(outer)
            await asyncio.sleep(0.1)
            
            assert result == ["inner"]
        finally:
            await q.stop()
    
    @pytest.mark.asyncio
    async def test_task_with_return_value(self):
        """Test that task return values don't break queue"""
        q = TaskQueue(max_workers=1)
        await q.start()
        
        try:
            def task_with_return():
                return "return_value"
            
            # Should not raise
            await q.submit(task_with_return)
            await asyncio.sleep(0.1)
            
            # Queue should still be running
            assert q.running is True
        finally:
            await q.stop()


class TestGlobalTaskQueue:
    """Tests for the global task_queue instance"""
    
    @pytest.mark.asyncio
    async def test_global_queue_singleton(self):
        """Test that global task_queue is a singleton"""
        from masterclaw_core.tasks import task_queue as global_queue
        
        # Should be same instance
        assert global_queue is task_queue
    
    @pytest.mark.asyncio  
    async def test_global_queue_default_workers(self):
        """Test global queue has default worker count"""
        from masterclaw_core.tasks import task_queue as global_queue
        
        # Default is 5 workers
        assert global_queue.max_workers == 5


class TestTaskQueueLogging:
    """Test logging behavior"""
    
    @pytest.mark.asyncio
    async def test_task_completion_logged(self, caplog):
        """Test that task completion is logged"""
        import logging
        
        with caplog.at_level(logging.DEBUG):
            q = TaskQueue(max_workers=1)
            await q.start()
            
            try:
                def simple_task():
                    pass
                
                await q.submit(simple_task)
                await asyncio.sleep(0.1)
                
                # Check for completion log
                assert any("Task completed" in record.message for record in caplog.records)
            finally:
                await q.stop()
    
    @pytest.mark.asyncio
    async def test_task_error_logged(self, caplog):
        """Test that task errors are logged"""
        import logging
        
        with caplog.at_level(logging.ERROR):
            q = TaskQueue(max_workers=1)
            await q.start()
            
            try:
                def failing_task():
                    raise ValueError("Test error")
                
                await q.submit(failing_task)
                await asyncio.sleep(0.1)
                
                # Check for error log
                assert any("Task failed" in record.message for record in caplog.records)
            finally:
                await q.stop()
    
    @pytest.mark.asyncio
    async def test_startup_logged(self, caplog):
        """Test that startup is logged"""
        import logging
        
        with caplog.at_level(logging.INFO):
            q = TaskQueue(max_workers=2)
            await q.start()
            
            try:
                assert any("Task queue started" in record.message for record in caplog.records)
                assert any("2 workers" in record.message for record in caplog.records)
            finally:
                await q.stop()
    
    @pytest.mark.asyncio
    async def test_shutdown_logged(self, caplog):
        """Test that shutdown is logged"""
        import logging
        
        with caplog.at_level(logging.INFO):
            q = TaskQueue(max_workers=1)
            await q.start()
            await q.stop()
            
            assert any("Task queue stopped" in record.message for record in caplog.records)
