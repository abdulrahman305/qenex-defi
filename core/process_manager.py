#!/usr/bin/env python3
"""
QENEX Process Manager - Controls system load and process pooling
"""

import os
import signal
import psutil
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from queue import PriorityQueue
from dataclasses import dataclass
from typing import Optional, Callable
import json
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Task:
    priority: int
    func: Callable
    args: tuple
    kwargs: dict
    task_id: str
    
    def __lt__(self, other):
        return self.priority < other.priority

class ProcessManager:
    def __init__(self, max_workers=10, max_load=4.0, max_memory=80):
        self.max_workers = max_workers
        self.max_load = max_load
        self.max_memory_percent = max_memory
        self.task_queue = PriorityQueue()
        self.process_pool = ProcessPoolExecutor(max_workers=max_workers)
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers * 2)
        self.active_tasks = {}
        self.completed_tasks = []
        self.running = True
        
    def check_system_resources(self):
        """Check if system resources allow new tasks"""
        load_avg = os.getloadavg()[0]
        memory_percent = psutil.virtual_memory().percent
        
        if load_avg > self.max_load:
            logger.warning(f"High load: {load_avg:.2f} > {self.max_load}")
            return False
            
        if memory_percent > self.max_memory_percent:
            logger.warning(f"High memory: {memory_percent:.1f}% > {self.max_memory_percent}%")
            return False
            
        return True
    
    def submit_task(self, func, args=(), kwargs=None, priority=5, task_id=None):
        """Submit a task to the queue"""
        if kwargs is None:
            kwargs = {}
        if task_id is None:
            task_id = f"task_{time.time()}"
            
        task = Task(priority, func, args, kwargs, task_id)
        self.task_queue.put(task)
        logger.info(f"Task {task_id} queued with priority {priority}")
        return task_id
    
    async def process_queue(self):
        """Process tasks from queue based on system resources"""
        while self.running:
            if not self.task_queue.empty() and self.check_system_resources():
                task = self.task_queue.get()
                
                # Check active worker count
                active_count = len(self.active_tasks)
                if active_count < self.max_workers:
                    self.active_tasks[task.task_id] = task
                    
                    try:
                        # Execute task in process pool
                        future = self.process_pool.submit(task.func, *task.args, **task.kwargs)
                        result = await asyncio.get_event_loop().run_in_executor(
                            None, future.result, 30  # 30 second timeout
                        )
                        
                        self.completed_tasks.append({
                            'task_id': task.task_id,
                            'result': result,
                            'timestamp': time.time()
                        })
                        logger.info(f"Task {task.task_id} completed")
                        
                    except Exception as e:
                        logger.error(f"Task {task.task_id} failed: {e}")
                    finally:
                        del self.active_tasks[task.task_id]
                else:
                    # Put task back if too many active
                    self.task_queue.put(task)
                    await asyncio.sleep(1)
            else:
                await asyncio.sleep(2)
    
    def kill_high_resource_processes(self, cpu_threshold=80, memory_threshold=500):
        """Kill processes consuming too many resources"""
        killed = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                if proc.info['cpu_percent'] > cpu_threshold:
                    proc.kill()
                    killed.append(proc.info['name'])
                elif proc.info['memory_info'].rss > memory_threshold * 1024 * 1024:
                    proc.kill()
                    killed.append(proc.info['name'])
            except:
                pass
        return killed
    
    def get_status(self):
        """Get current status"""
        return {
            'active_tasks': len(self.active_tasks),
            'queued_tasks': self.task_queue.qsize(),
            'completed_tasks': len(self.completed_tasks),
            'load_average': os.getloadavg()[0],
            'memory_percent': psutil.virtual_memory().percent,
            'cpu_percent': psutil.cpu_percent(interval=1)
        }
    
    def shutdown(self):
        """Gracefully shutdown"""
        self.running = False
        self.process_pool.shutdown(wait=True)
        self.thread_pool.shutdown(wait=True)

# Global instance
manager = ProcessManager(max_workers=5, max_load=10.0, max_memory=85)

async def main():
    """Main process manager loop"""
    logger.info("QENEX Process Manager started")
    await manager.process_queue()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        manager.shutdown()
        logger.info("Process Manager shutdown")