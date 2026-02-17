"""Background task queue for MasterClaw"""

import asyncio
from typing import Callable, Any
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger("masterclaw")


class TaskQueue:
    """Simple async task queue for background processing"""
    
    def __init__(self, max_workers: int = 5):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers = []
        self.running = False
    
    async def start(self):
        """Start the task queue workers"""
        self.running = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.workers.append(worker)
        logger.info(f"Task queue started with {self.max_workers} workers")
    
    async def stop(self):
        """Stop the task queue"""
        self.running = False
        # Wait for all workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()  # Clear workers list after stopping
        logger.info("Task queue stopped")
    
    async def _worker_loop(self, worker_id: str):
        """Worker loop to process tasks"""
        while self.running:
            try:
                # Wait for task with timeout
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._execute_task(task)
                self.queue.task_done()  # Mark task as done
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    async def _execute_task(self, task: dict):
        """Execute a single task"""
        try:
            func = task['func']
            args = task.get('args', [])
            kwargs = task.get('kwargs', {})
            
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
            
            logger.debug(f"Task completed: {task.get('name', 'unnamed')}")
        except Exception as e:
            logger.error(f"Task failed: {e}")
    
    async def submit(self, func: Callable, *args, **kwargs) -> str:
        """Submit a task to the queue"""
        task_id = f"task_{datetime.now(timezone.utc).timestamp()}_{uuid.uuid4().hex[:8]}"
        await self.queue.put({
            'id': task_id,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'name': func.__name__,
        })
        return task_id
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()


# Global task queue
task_queue = TaskQueue()
