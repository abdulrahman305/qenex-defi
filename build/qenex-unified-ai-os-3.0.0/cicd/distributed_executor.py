#!/usr/bin/env python3
"""
QENEX Distributed Pipeline Execution System
High-performance distributed CI/CD pipeline executor with load balancing
Version: 1.0.0
"""

import os
import sys
import json
import asyncio
import hashlib
import pickle
import time
import logging
import threading
import subprocess
import tempfile
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import queue
import uuid

try:
    import redis
except ImportError:
    redis = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import docker
except ImportError:
    docker = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QENEX-DistributedExecutor')

class WorkerType(Enum):
    DOCKER = "docker"
    NATIVE = "native"
    KUBERNETES = "kubernetes"
    REMOTE = "remote"

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class WorkerStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class ExecutionTask:
    """Represents a single execution task"""
    id: str
    pipeline_id: str
    stage_name: str
    command: str
    environment: Dict[str, str]
    working_directory: str
    timeout: int = 3600
    priority: int = 5
    dependencies: List[str] = None
    resources: Dict[str, Any] = None
    created_at: datetime = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    logs: List[str] = None
    artifacts: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.dependencies is None:
            self.dependencies = []
        if self.resources is None:
            self.resources = {"cpu": 1, "memory": "1G", "disk": "10G"}
        if self.logs is None:
            self.logs = []
        if self.artifacts is None:
            self.artifacts = []

@dataclass
class WorkerNode:
    """Represents a worker node in the cluster"""
    id: str
    hostname: str
    ip_address: str
    port: int
    worker_type: WorkerType
    capacity: Dict[str, Any]
    current_load: Dict[str, Any]
    status: WorkerStatus
    last_heartbeat: datetime
    current_tasks: List[str]
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_runtime: float = 0.0
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.current_tasks is None:
            self.current_tasks = []

    @property
    def load_percentage(self) -> float:
        """Calculate current load percentage"""
        if not self.capacity.get('cpu', 0):
            return 100.0
        return (self.current_load.get('cpu', 0) / self.capacity.get('cpu', 1)) * 100

    @property
    def is_available(self) -> bool:
        """Check if worker is available for new tasks"""
        return (self.status == WorkerStatus.IDLE and 
                len(self.current_tasks) < self.capacity.get('max_concurrent_tasks', 1))

class TaskQueue:
    """Priority-based task queue with dependency resolution"""
    
    def __init__(self):
        self.tasks = {}
        self.pending_queue = queue.PriorityQueue()
        self.running_tasks = {}
        self.completed_tasks = {}
        self.failed_tasks = {}
        self.task_dependencies = {}
        self.lock = threading.RLock()
    
    def add_task(self, task: ExecutionTask):
        """Add a task to the queue"""
        with self.lock:
            self.tasks[task.id] = task
            
            # Check if dependencies are met
            if self._dependencies_met(task):
                # Priority queue uses negative priority for max-heap behavior
                priority = -task.priority if task.priority else -5
                self.pending_queue.put((priority, task.created_at, task.id))
                logger.info(f"Task {task.id} added to pending queue")
            else:
                # Store in dependency wait list
                for dep_id in task.dependencies:
                    if dep_id not in self.task_dependencies:
                        self.task_dependencies[dep_id] = []
                    self.task_dependencies[dep_id].append(task.id)
                logger.info(f"Task {task.id} waiting for dependencies: {task.dependencies}")
    
    def get_next_task(self) -> Optional[ExecutionTask]:
        """Get the next available task"""
        try:
            priority, created_at, task_id = self.pending_queue.get_nowait()
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.ASSIGNED
                    return task
        except queue.Empty:
            pass
        return None
    
    def mark_running(self, task_id: str, worker_id: str):
        """Mark task as running"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.RUNNING
                task.worker_id = worker_id
                task.started_at = datetime.now()
                self.running_tasks[task_id] = task
                logger.info(f"Task {task_id} marked as running on worker {worker_id}")
    
    def mark_completed(self, task_id: str, result: Dict):
        """Mark task as completed and check for dependent tasks"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result
                self.completed_tasks[task_id] = task
                
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
                
                # Check for dependent tasks
                self._check_dependent_tasks(task_id)
                logger.info(f"Task {task_id} completed successfully")
    
    def mark_failed(self, task_id: str, error: str):
        """Mark task as failed"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.result = {"error": error}
                self.failed_tasks[task_id] = task
                
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
                
                logger.error(f"Task {task_id} failed: {error}")
    
    def _dependencies_met(self, task: ExecutionTask) -> bool:
        """Check if all dependencies are met"""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True
    
    def _check_dependent_tasks(self, completed_task_id: str):
        """Check and queue tasks that were waiting for this dependency"""
        if completed_task_id in self.task_dependencies:
            for dependent_task_id in self.task_dependencies[completed_task_id]:
                if dependent_task_id in self.tasks:
                    task = self.tasks[dependent_task_id]
                    if self._dependencies_met(task):
                        priority = -task.priority if task.priority else -5
                        self.pending_queue.put((priority, task.created_at, task.id))
                        logger.info(f"Dependent task {dependent_task_id} now queued")
            del self.task_dependencies[completed_task_id]

class WorkerManager:
    """Manages worker nodes and load balancing"""
    
    def __init__(self):
        self.workers = {}
        self.lock = threading.RLock()
        self.heartbeat_timeout = 60  # seconds
    
    def register_worker(self, worker: WorkerNode):
        """Register a new worker node"""
        with self.lock:
            self.workers[worker.id] = worker
            logger.info(f"Worker {worker.id} ({worker.hostname}) registered")
    
    def unregister_worker(self, worker_id: str):
        """Unregister a worker node"""
        with self.lock:
            if worker_id in self.workers:
                del self.workers[worker_id]
                logger.info(f"Worker {worker_id} unregistered")
    
    def update_worker_heartbeat(self, worker_id: str, load_info: Dict):
        """Update worker heartbeat and load information"""
        with self.lock:
            if worker_id in self.workers:
                worker = self.workers[worker_id]
                worker.last_heartbeat = datetime.now()
                worker.current_load = load_info
                
                # Update status based on load
                if worker.load_percentage > 90:
                    worker.status = WorkerStatus.BUSY
                else:
                    worker.status = WorkerStatus.IDLE
    
    def get_best_worker(self, task: ExecutionTask) -> Optional[WorkerNode]:
        """Find the best available worker for a task"""
        with self.lock:
            available_workers = [
                worker for worker in self.workers.values()
                if worker.is_available and self._worker_supports_task(worker, task)
            ]
            
            if not available_workers:
                return None
            
            # Sort by load percentage (ascending) and then by completed tasks (descending)
            available_workers.sort(key=lambda w: (w.load_percentage, -w.completed_tasks))
            return available_workers[0]
    
    def _worker_supports_task(self, worker: WorkerNode, task: ExecutionTask) -> bool:
        """Check if worker supports the task requirements"""
        # Check resource requirements
        task_cpu = task.resources.get('cpu', 1)
        task_memory = self._parse_memory(task.resources.get('memory', '1G'))
        
        worker_cpu = worker.capacity.get('cpu', 0)
        worker_memory = self._parse_memory(worker.capacity.get('memory', '0G'))
        
        if task_cpu > worker_cpu or task_memory > worker_memory:
            return False
        
        # Check worker type compatibility
        # Add more sophisticated matching logic here
        
        return True
    
    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to bytes"""
        if isinstance(memory_str, int):
            return memory_str
        
        memory_str = memory_str.upper()
        if memory_str.endswith('G'):
            return int(memory_str[:-1]) * 1024 * 1024 * 1024
        elif memory_str.endswith('M'):
            return int(memory_str[:-1]) * 1024 * 1024
        elif memory_str.endswith('K'):
            return int(memory_str[:-1]) * 1024
        else:
            return int(memory_str)
    
    def cleanup_stale_workers(self):
        """Remove workers that haven't sent heartbeat recently"""
        with self.lock:
            current_time = datetime.now()
            stale_workers = []
            
            for worker_id, worker in self.workers.items():
                time_since_heartbeat = (current_time - worker.last_heartbeat).total_seconds()
                if time_since_heartbeat > self.heartbeat_timeout:
                    stale_workers.append(worker_id)
            
            for worker_id in stale_workers:
                self.unregister_worker(worker_id)
                logger.warning(f"Worker {worker_id} removed due to stale heartbeat")

class ExecutionEngine:
    """Core execution engine for running tasks on workers"""
    
    def __init__(self, worker: WorkerNode):
        self.worker = worker
        self.docker_client = None
        if docker:
            try:
                self.docker_client = docker.from_env()
            except Exception as e:
                logger.warning(f"Docker client initialization failed: {e}")
    
    async def execute_task(self, task: ExecutionTask) -> Dict:
        """Execute a task and return results"""
        logger.info(f"Executing task {task.id} on worker {self.worker.id}")
        
        try:
            if self.worker.worker_type == WorkerType.DOCKER:
                return await self._execute_docker_task(task)
            elif self.worker.worker_type == WorkerType.NATIVE:
                return await self._execute_native_task(task)
            else:
                raise Exception(f"Unsupported worker type: {self.worker.worker_type}")
        
        except Exception as e:
            logger.error(f"Task {task.id} execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    async def _execute_docker_task(self, task: ExecutionTask) -> Dict:
        """Execute task in Docker container"""
        if not self.docker_client:
            raise Exception("Docker client not available")
        
        # Create temporary directory for task
        task_dir = f"/tmp/qenex-task-{task.id}"
        os.makedirs(task_dir, exist_ok=True)
        
        try:
            # Prepare environment
            env_vars = task.environment.copy()
            env_vars.update({
                'QENEX_TASK_ID': task.id,
                'QENEX_PIPELINE_ID': task.pipeline_id,
                'QENEX_STAGE': task.stage_name
            })
            
            # Create container
            container = self.docker_client.containers.run(
                image="ubuntu:22.04",
                command=f"bash -c '{task.command}'",
                environment=env_vars,
                working_dir="/workspace",
                volumes={
                    task.working_directory: {'bind': '/workspace', 'mode': 'rw'},
                    task_dir: {'bind': '/tmp/task', 'mode': 'rw'}
                },
                detach=True,
                remove=False,
                mem_limit=task.resources.get('memory', '1G'),
                cpu_count=task.resources.get('cpu', 1)
            )
            
            # Wait for completion with timeout
            result = container.wait(timeout=task.timeout)
            
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
            
            # Collect artifacts
            artifacts = self._collect_artifacts(task_dir, task.artifacts)
            
            # Cleanup
            container.remove()
            
            return {
                "success": result['StatusCode'] == 0,
                "exit_code": result['StatusCode'],
                "stdout": stdout,
                "stderr": stderr,
                "artifacts": artifacts,
                "execution_time": (datetime.now() - task.started_at).total_seconds()
            }
            
        finally:
            # Cleanup task directory
            if os.path.exists(task_dir):
                import shutil
                shutil.rmtree(task_dir, ignore_errors=True)
    
    async def _execute_native_task(self, task: ExecutionTask) -> Dict:
        """Execute task natively on the system"""
        # Create temporary directory for task
        task_dir = f"/tmp/qenex-task-{task.id}"
        os.makedirs(task_dir, exist_ok=True)
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(task.environment)
            env.update({
                'QENEX_TASK_ID': task.id,
                'QENEX_PIPELINE_ID': task.pipeline_id,
                'QENEX_STAGE': task.stage_name,
                'QENEX_TASK_DIR': task_dir
            })
            
            # Execute command
            start_time = datetime.now()
            process = subprocess.Popen(
                task.command,
                shell=True,
                cwd=task.working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait with timeout
            try:
                stdout, stderr = process.communicate(timeout=task.timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                exit_code = -1
                stderr += "\nTask killed due to timeout"
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Collect artifacts
            artifacts = self._collect_artifacts(task_dir, task.artifacts)
            
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "artifacts": artifacts,
                "execution_time": execution_time
            }
            
        finally:
            # Cleanup task directory
            if os.path.exists(task_dir):
                import shutil
                shutil.rmtree(task_dir, ignore_errors=True)
    
    def _collect_artifacts(self, task_dir: str, artifact_patterns: List[str]) -> List[str]:
        """Collect task artifacts"""
        artifacts = []
        
        if not artifact_patterns:
            return artifacts
        
        import glob
        for pattern in artifact_patterns:
            pattern_path = os.path.join(task_dir, pattern)
            matching_files = glob.glob(pattern_path, recursive=True)
            artifacts.extend(matching_files)
        
        return artifacts

class DistributedExecutor:
    """Main distributed execution coordinator"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.task_queue = TaskQueue()
        self.worker_manager = WorkerManager()
        self.execution_engines = {}
        self.running = False
        self.coordinator_thread = None
        self.heartbeat_thread = None
        
        # Redis connection for distributed coordination (optional)
        self.redis_client = None
        if redis and self.config.get('redis_url'):
            try:
                self.redis_client = redis.from_url(self.config['redis_url'])
                logger.info("Connected to Redis for distributed coordination")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
    
    def start(self):
        """Start the distributed executor"""
        if self.running:
            return
        
        self.running = True
        
        # Start coordinator thread
        self.coordinator_thread = threading.Thread(target=self._coordinator_loop, daemon=True)
        self.coordinator_thread.start()
        
        # Start heartbeat cleanup thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        logger.info("Distributed executor started")
    
    def stop(self):
        """Stop the distributed executor"""
        self.running = False
        
        if self.coordinator_thread:
            self.coordinator_thread.join(timeout=5)
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        logger.info("Distributed executor stopped")
    
    def submit_task(self, task: ExecutionTask) -> str:
        """Submit a task for execution"""
        self.task_queue.add_task(task)
        logger.info(f"Task {task.id} submitted for execution")
        return task.id
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status"""
        if task_id in self.task_queue.tasks:
            return self.task_queue.tasks[task_id].status
        return None
    
    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """Get task result"""
        if task_id in self.task_queue.tasks:
            return self.task_queue.tasks[task_id].result
        return None
    
    def register_worker(self, worker: WorkerNode):
        """Register a worker node"""
        self.worker_manager.register_worker(worker)
        
        # Create execution engine for worker
        if worker.id not in self.execution_engines:
            self.execution_engines[worker.id] = ExecutionEngine(worker)
    
    def _coordinator_loop(self):
        """Main coordinator loop for task assignment"""
        while self.running:
            try:
                # Get next task
                task = self.task_queue.get_next_task()
                if not task:
                    time.sleep(1)
                    continue
                
                # Find best worker
                worker = self.worker_manager.get_best_worker(task)
                if not worker:
                    # No available workers, put task back in queue
                    self.task_queue.pending_queue.put((-task.priority, task.created_at, task.id))
                    time.sleep(5)
                    continue
                
                # Assign task to worker
                self.task_queue.mark_running(task.id, worker.id)
                worker.current_tasks.append(task.id)
                
                # Execute task asynchronously
                asyncio.run_coroutine_threadsafe(
                    self._execute_task_async(task, worker),
                    asyncio.new_event_loop()
                )
                
            except Exception as e:
                logger.error(f"Coordinator loop error: {e}")
                time.sleep(1)
    
    async def _execute_task_async(self, task: ExecutionTask, worker: WorkerNode):
        """Execute task asynchronously"""
        try:
            engine = self.execution_engines[worker.id]
            result = await engine.execute_task(task)
            
            # Update task result
            if result.get('success', False):
                self.task_queue.mark_completed(task.id, result)
                worker.completed_tasks += 1
            else:
                self.task_queue.mark_failed(task.id, result.get('error', 'Unknown error'))
                worker.failed_tasks += 1
            
            # Update worker stats
            worker.total_runtime += result.get('execution_time', 0)
            if task.id in worker.current_tasks:
                worker.current_tasks.remove(task.id)
            
        except Exception as e:
            self.task_queue.mark_failed(task.id, str(e))
            if task.id in worker.current_tasks:
                worker.current_tasks.remove(task.id)
    
    def _heartbeat_loop(self):
        """Cleanup stale workers periodically"""
        while self.running:
            try:
                self.worker_manager.cleanup_stale_workers()
                time.sleep(30)
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                time.sleep(30)
    
    def get_cluster_status(self) -> Dict:
        """Get cluster status information"""
        return {
            "workers": len(self.worker_manager.workers),
            "pending_tasks": self.task_queue.pending_queue.qsize(),
            "running_tasks": len(self.task_queue.running_tasks),
            "completed_tasks": len(self.task_queue.completed_tasks),
            "failed_tasks": len(self.task_queue.failed_tasks),
            "worker_details": [asdict(worker) for worker in self.worker_manager.workers.values()]
        }

# Worker node implementation
class WorkerNodeService:
    """Service for running worker nodes"""
    
    def __init__(self, coordinator_url: str, worker_config: Dict = None):
        self.coordinator_url = coordinator_url
        self.worker_config = worker_config or {}
        self.worker_id = str(uuid.uuid4())
        self.running = False
        
        # Initialize worker node
        self.worker_node = WorkerNode(
            id=self.worker_id,
            hostname=socket.gethostname(),
            ip_address=self._get_local_ip(),
            port=self.worker_config.get('port', 8080),
            worker_type=WorkerType(self.worker_config.get('type', 'native')),
            capacity=self._get_system_capacity(),
            current_load={},
            status=WorkerStatus.IDLE,
            last_heartbeat=datetime.now(),
            current_tasks=[]
        )
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _get_system_capacity(self) -> Dict:
        """Get system resource capacity"""
        capacity = {
            "cpu": 2,
            "memory": "4G",
            "disk": "100G",
            "max_concurrent_tasks": 4
        }
        
        if psutil:
            capacity.update({
                "cpu": psutil.cpu_count(),
                "memory": f"{psutil.virtual_memory().total // (1024**3)}G",
                "disk": f"{psutil.disk_usage('/').total // (1024**3)}G"
            })
        
        return capacity
    
    def start(self):
        """Start worker node service"""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")
        
        # Send heartbeat periodically
        while self.running:
            try:
                self._send_heartbeat()
                time.sleep(30)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                time.sleep(30)
    
    def _send_heartbeat(self):
        """Send heartbeat to coordinator"""
        load_info = self._get_current_load()
        # In a real implementation, send this to the coordinator via HTTP/gRPC
        logger.debug(f"Heartbeat from worker {self.worker_id}: {load_info}")
    
    def _get_current_load(self) -> Dict:
        """Get current system load"""
        load = {
            "cpu": 0.5,
            "memory": 0.3,
            "disk": 0.2
        }
        
        if psutil:
            load.update({
                "cpu": psutil.cpu_percent(interval=1) / 100,
                "memory": psutil.virtual_memory().percent / 100,
                "disk": psutil.disk_usage('/').percent / 100
            })
        
        return load

# Example usage and testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='QENEX Distributed Executor')
    parser.add_argument('--mode', choices=['coordinator', 'worker'], default='coordinator',
                        help='Run as coordinator or worker')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    if args.mode == 'coordinator':
        # Start coordinator
        executor = DistributedExecutor()
        
        # Register a local worker for testing
        local_worker = WorkerNode(
            id="local-worker-1",
            hostname="localhost",
            ip_address="127.0.0.1",
            port=8080,
            worker_type=WorkerType.NATIVE,
            capacity={"cpu": 4, "memory": "8G", "disk": "100G", "max_concurrent_tasks": 2},
            current_load={"cpu": 0.1, "memory": 0.2, "disk": 0.1},
            status=WorkerStatus.IDLE,
            last_heartbeat=datetime.now(),
            current_tasks=[]
        )
        
        executor.register_worker(local_worker)
        executor.start()
        
        # Submit test tasks
        test_task = ExecutionTask(
            id="test-task-1",
            pipeline_id="test-pipeline",
            stage_name="build",
            command="echo 'Hello from distributed executor!' && sleep 5",
            environment={"TEST_VAR": "test_value"},
            working_directory="/tmp",
            timeout=60
        )
        
        executor.submit_task(test_task)
        
        try:
            # Keep running
            while True:
                status = executor.get_cluster_status()
                logger.info(f"Cluster status: {status}")
                time.sleep(10)
        except KeyboardInterrupt:
            executor.stop()
    
    else:
        # Start worker
        worker = WorkerNodeService("http://coordinator:8080")
        try:
            worker.start()
        except KeyboardInterrupt:
            worker.running = False
            logger.info("Worker stopped")