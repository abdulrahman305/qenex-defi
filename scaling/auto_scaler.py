#!/usr/bin/env python3
"""
QENEX Auto-Scaler - Automatic scaling based on load and demand
"""

import asyncio
import psutil
import docker
import kubernetes
import logging
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScalingPolicy:
    min_instances: int = 1
    max_instances: int = 10
    cpu_threshold_up: float = 80.0
    cpu_threshold_down: float = 20.0
    memory_threshold_up: float = 80.0
    memory_threshold_down: float = 30.0
    queue_threshold: int = 5
    scale_up_cooldown: int = 300  # seconds
    scale_down_cooldown: int = 600  # seconds
    scale_increment: int = 1

@dataclass
class WorkerNode:
    node_id: str
    hostname: str
    ip_address: str
    cpu_cores: int
    memory_gb: float
    status: str
    workload: int
    created_at: datetime
    last_heartbeat: datetime

class AutoScaler:
    def __init__(self, scaling_policy: ScalingPolicy = None):
        self.policy = scaling_policy or ScalingPolicy()
        self.workers: Dict[str, WorkerNode] = {}
        self.last_scale_up = datetime.min
        self.last_scale_down = datetime.min
        self.metrics_history = []
        self.docker_client = None
        self.k8s_client = None
        self.scaling_mode = 'docker'  # 'docker', 'kubernetes', or 'cloud'
        
        # Initialize clients
        self.init_clients()
    
    def init_clients(self):
        """Initialize container orchestration clients"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except:
            logger.warning("Docker not available")
        
        try:
            kubernetes.config.load_incluster_config()
            self.k8s_client = kubernetes.client.CoreV1Api()
            self.scaling_mode = 'kubernetes'
            logger.info("Kubernetes client initialized")
        except:
            try:
                kubernetes.config.load_kube_config()
                self.k8s_client = kubernetes.client.CoreV1Api()
                self.scaling_mode = 'kubernetes'
                logger.info("Kubernetes client initialized from kubeconfig")
            except:
                logger.warning("Kubernetes not available")
    
    def collect_metrics(self) -> Dict[str, float]:
        """Collect current system metrics"""
        metrics = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'load_average': os.getloadavg()[0],
            'network_connections': len(psutil.net_connections()),
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': time.time()
        }
        
        # Get queue size from QENEX system
        try:
            with open('/opt/qenex-os/dashboard/api.json', 'r') as f:
                api_data = json.load(f)
                metrics['queue_size'] = api_data.get('pipelines', 0)
                metrics['qenex_processes'] = api_data.get('qenex_processes', 0)
        except:
            metrics['queue_size'] = 0
            metrics['qenex_processes'] = 0
        
        # Store in history (keep last hour)
        self.metrics_history.append(metrics)
        cutoff_time = time.time() - 3600
        self.metrics_history = [m for m in self.metrics_history if m['timestamp'] > cutoff_time]
        
        return metrics
    
    def calculate_scaling_decision(self, metrics: Dict[str, float]) -> str:
        """Determine if scaling is needed"""
        current_workers = len([w for w in self.workers.values() if w.status == 'running'])
        
        # Check if we need to scale up
        scale_up_needed = False
        if metrics['cpu_percent'] > self.policy.cpu_threshold_up:
            scale_up_needed = True
            logger.info(f"CPU threshold exceeded: {metrics['cpu_percent']:.1f}%")
        
        if metrics['memory_percent'] > self.policy.memory_threshold_up:
            scale_up_needed = True
            logger.info(f"Memory threshold exceeded: {metrics['memory_percent']:.1f}%")
        
        if metrics['queue_size'] > self.policy.queue_threshold:
            scale_up_needed = True
            logger.info(f"Queue threshold exceeded: {metrics['queue_size']} tasks")
        
        # Check cooldown period
        if scale_up_needed:
            time_since_scale = (datetime.now() - self.last_scale_up).seconds
            if time_since_scale < self.policy.scale_up_cooldown:
                logger.info(f"Scale up cooldown active: {self.policy.scale_up_cooldown - time_since_scale}s remaining")
                return 'wait'
            
            if current_workers < self.policy.max_instances:
                return 'scale_up'
            else:
                logger.warning(f"Max instances reached: {self.policy.max_instances}")
                return 'max_reached'
        
        # Check if we need to scale down
        scale_down_needed = False
        if (metrics['cpu_percent'] < self.policy.cpu_threshold_down and 
            metrics['memory_percent'] < self.policy.memory_threshold_down and
            metrics['queue_size'] == 0):
            scale_down_needed = True
        
        if scale_down_needed:
            time_since_scale = (datetime.now() - self.last_scale_down).seconds
            if time_since_scale < self.policy.scale_down_cooldown:
                logger.info(f"Scale down cooldown active: {self.policy.scale_down_cooldown - time_since_scale}s remaining")
                return 'wait'
            
            if current_workers > self.policy.min_instances:
                return 'scale_down'
        
        return 'maintain'
    
    def predict_future_load(self) -> float:
        """Predict future load based on historical metrics"""
        if len(self.metrics_history) < 10:
            return 0
        
        # Simple moving average prediction
        recent_cpu = [m['cpu_percent'] for m in self.metrics_history[-10:]]
        recent_memory = [m['memory_percent'] for m in self.metrics_history[-10:]]
        
        avg_cpu = sum(recent_cpu) / len(recent_cpu)
        avg_memory = sum(recent_memory) / len(recent_memory)
        
        # Calculate trend
        cpu_trend = recent_cpu[-1] - recent_cpu[0]
        memory_trend = recent_memory[-1] - recent_memory[0]
        
        # Predict next value
        predicted_cpu = avg_cpu + (cpu_trend * 0.3)
        predicted_memory = avg_memory + (memory_trend * 0.3)
        
        return max(predicted_cpu, predicted_memory)
    
    async def spawn_worker_docker(self) -> Optional[WorkerNode]:
        """Spawn a new worker using Docker"""
        if not self.docker_client:
            logger.error("Docker client not available")
            return None
        
        try:
            worker_id = f"qenex-worker-{int(time.time())}"
            
            # Create worker container
            container = self.docker_client.containers.run(
                image='qenex/worker:latest',
                name=worker_id,
                detach=True,
                environment={
                    'WORKER_ID': worker_id,
                    'MASTER_HOST': 'localhost',
                    'MASTER_PORT': '8000'
                },
                network_mode='host',
                restart_policy={'Name': 'unless-stopped'},
                labels={'qenex': 'worker', 'worker_id': worker_id}
            )
            
            # Get container info
            container.reload()
            
            worker = WorkerNode(
                node_id=worker_id,
                hostname=container.name,
                ip_address=container.attrs['NetworkSettings']['IPAddress'] or 'localhost',
                cpu_cores=psutil.cpu_count(),
                memory_gb=psutil.virtual_memory().total / (1024**3),
                status='running',
                workload=0,
                created_at=datetime.now(),
                last_heartbeat=datetime.now()
            )
            
            self.workers[worker_id] = worker
            logger.info(f"Spawned Docker worker: {worker_id}")
            
            return worker
            
        except Exception as e:
            logger.error(f"Failed to spawn Docker worker: {e}")
            return None
    
    async def spawn_worker_kubernetes(self) -> Optional[WorkerNode]:
        """Spawn a new worker using Kubernetes"""
        if not self.k8s_client:
            logger.error("Kubernetes client not available")
            return None
        
        try:
            worker_id = f"qenex-worker-{int(time.time())}"
            
            # Define pod spec
            pod_manifest = {
                'apiVersion': 'v1',
                'kind': 'Pod',
                'metadata': {
                    'name': worker_id,
                    'labels': {
                        'app': 'qenex-worker',
                        'worker-id': worker_id
                    }
                },
                'spec': {
                    'containers': [{
                        'name': 'worker',
                        'image': 'qenex/worker:latest',
                        'env': [
                            {'name': 'WORKER_ID', 'value': worker_id},
                            {'name': 'MASTER_HOST', 'value': 'qenex-master'},
                            {'name': 'MASTER_PORT', 'value': '8000'}
                        ],
                        'resources': {
                            'requests': {
                                'memory': '512Mi',
                                'cpu': '500m'
                            },
                            'limits': {
                                'memory': '2Gi',
                                'cpu': '2000m'
                            }
                        }
                    }]
                }
            }
            
            # Create pod
            resp = self.k8s_client.create_namespaced_pod(
                body=pod_manifest,
                namespace='default'
            )
            
            worker = WorkerNode(
                node_id=worker_id,
                hostname=resp.metadata.name,
                ip_address=resp.status.pod_ip or 'pending',
                cpu_cores=2,
                memory_gb=2,
                status='running',
                workload=0,
                created_at=datetime.now(),
                last_heartbeat=datetime.now()
            )
            
            self.workers[worker_id] = worker
            logger.info(f"Spawned Kubernetes worker: {worker_id}")
            
            return worker
            
        except Exception as e:
            logger.error(f"Failed to spawn Kubernetes worker: {e}")
            return None
    
    async def spawn_worker_cloud(self) -> Optional[WorkerNode]:
        """Spawn a new worker in cloud (AWS/GCP/Azure)"""
        # This would integrate with cloud providers' APIs
        # For now, simulate with local process
        try:
            worker_id = f"qenex-worker-{int(time.time())}"
            
            # Start worker process
            process = subprocess.Popen([
                'python3', '/opt/qenex-os/workers/worker.py',
                '--id', worker_id,
                '--port', str(8100 + len(self.workers))
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            worker = WorkerNode(
                node_id=worker_id,
                hostname=f"worker-{len(self.workers)}",
                ip_address='127.0.0.1',
                cpu_cores=psutil.cpu_count(),
                memory_gb=psutil.virtual_memory().total / (1024**3),
                status='running',
                workload=0,
                created_at=datetime.now(),
                last_heartbeat=datetime.now()
            )
            
            self.workers[worker_id] = worker
            logger.info(f"Spawned cloud worker: {worker_id}")
            
            return worker
            
        except Exception as e:
            logger.error(f"Failed to spawn cloud worker: {e}")
            return None
    
    async def terminate_worker(self, worker_id: str):
        """Terminate a worker"""
        if worker_id not in self.workers:
            return
        
        worker = self.workers[worker_id]
        
        try:
            if self.scaling_mode == 'docker' and self.docker_client:
                containers = self.docker_client.containers.list(
                    filters={'label': f'worker_id={worker_id}'}
                )
                for container in containers:
                    container.stop()
                    container.remove()
                    
            elif self.scaling_mode == 'kubernetes' and self.k8s_client:
                self.k8s_client.delete_namespaced_pod(
                    name=worker_id,
                    namespace='default'
                )
            
            worker.status = 'terminated'
            del self.workers[worker_id]
            logger.info(f"Terminated worker: {worker_id}")
            
        except Exception as e:
            logger.error(f"Failed to terminate worker {worker_id}: {e}")
    
    async def scale_up(self, count: int = None):
        """Scale up by spawning new workers"""
        count = count or self.policy.scale_increment
        current_workers = len([w for w in self.workers.values() if w.status == 'running'])
        
        # Don't exceed max instances
        count = min(count, self.policy.max_instances - current_workers)
        
        logger.info(f"Scaling up by {count} workers")
        
        for i in range(count):
            if self.scaling_mode == 'docker':
                await self.spawn_worker_docker()
            elif self.scaling_mode == 'kubernetes':
                await self.spawn_worker_kubernetes()
            else:
                await self.spawn_worker_cloud()
        
        self.last_scale_up = datetime.now()
    
    async def scale_down(self, count: int = None):
        """Scale down by terminating workers"""
        count = count or self.policy.scale_increment
        current_workers = [w for w in self.workers.values() if w.status == 'running']
        
        # Don't go below min instances
        count = min(count, len(current_workers) - self.policy.min_instances)
        
        if count <= 0:
            return
        
        logger.info(f"Scaling down by {count} workers")
        
        # Terminate workers with lowest workload
        workers_to_terminate = sorted(current_workers, key=lambda w: w.workload)[:count]
        
        for worker in workers_to_terminate:
            await self.terminate_worker(worker.node_id)
        
        self.last_scale_down = datetime.now()
    
    async def rebalance_workload(self):
        """Rebalance workload across workers"""
        active_workers = [w for w in self.workers.values() if w.status == 'running']
        
        if len(active_workers) < 2:
            return
        
        total_workload = sum(w.workload for w in active_workers)
        avg_workload = total_workload / len(active_workers)
        
        # Find overloaded and underloaded workers
        overloaded = [w for w in active_workers if w.workload > avg_workload * 1.5]
        underloaded = [w for w in active_workers if w.workload < avg_workload * 0.5]
        
        if overloaded and underloaded:
            logger.info(f"Rebalancing workload: {len(overloaded)} overloaded, {len(underloaded)} underloaded")
            # Implement workload migration logic here
    
    async def health_check(self):
        """Check health of all workers"""
        for worker in list(self.workers.values()):
            if worker.status != 'running':
                continue
            
            # Check if worker is responsive
            time_since_heartbeat = (datetime.now() - worker.last_heartbeat).seconds
            
            if time_since_heartbeat > 60:
                logger.warning(f"Worker {worker.node_id} is unresponsive")
                worker.status = 'unhealthy'
                
                # Try to restart unhealthy worker
                await self.terminate_worker(worker.node_id)
                
                if self.scaling_mode == 'docker':
                    await self.spawn_worker_docker()
                elif self.scaling_mode == 'kubernetes':
                    await self.spawn_worker_kubernetes()
                else:
                    await self.spawn_worker_cloud()
    
    async def auto_scale_loop(self):
        """Main auto-scaling loop"""
        logger.info("Auto-scaler started")
        
        # Ensure minimum instances
        current_workers = len(self.workers)
        if current_workers < self.policy.min_instances:
            await self.scale_up(self.policy.min_instances - current_workers)
        
        while True:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                
                # Make scaling decision
                decision = self.calculate_scaling_decision(metrics)
                
                # Execute scaling action
                if decision == 'scale_up':
                    await self.scale_up()
                elif decision == 'scale_down':
                    await self.scale_down()
                
                # Perform health checks
                await self.health_check()
                
                # Rebalance workload periodically
                if len(self.metrics_history) % 10 == 0:
                    await self.rebalance_workload()
                
                # Log status
                active_workers = len([w for w in self.workers.values() if w.status == 'running'])
                logger.info(f"Auto-scaler status: {active_workers} workers, "
                          f"CPU: {metrics['cpu_percent']:.1f}%, "
                          f"Memory: {metrics['memory_percent']:.1f}%, "
                          f"Queue: {metrics['queue_size']}")
                
            except Exception as e:
                logger.error(f"Auto-scaler error: {e}")
            
            # Check every 30 seconds
            await asyncio.sleep(30)
    
    def get_status(self) -> Dict[str, Any]:
        """Get auto-scaler status"""
        active_workers = [w for w in self.workers.values() if w.status == 'running']
        
        return {
            'scaling_mode': self.scaling_mode,
            'active_workers': len(active_workers),
            'total_workers': len(self.workers),
            'min_instances': self.policy.min_instances,
            'max_instances': self.policy.max_instances,
            'last_scale_up': self.last_scale_up.isoformat() if self.last_scale_up != datetime.min else None,
            'last_scale_down': self.last_scale_down.isoformat() if self.last_scale_down != datetime.min else None,
            'workers': [
                {
                    'id': w.node_id,
                    'hostname': w.hostname,
                    'status': w.status,
                    'workload': w.workload,
                    'uptime': (datetime.now() - w.created_at).seconds
                }
                for w in active_workers
            ]
        }

import os

async def main():
    """Main auto-scaler entry point"""
    # Configure scaling policy
    policy = ScalingPolicy(
        min_instances=1,
        max_instances=5,
        cpu_threshold_up=70.0,
        cpu_threshold_down=30.0,
        memory_threshold_up=75.0,
        memory_threshold_down=35.0
    )
    
    # Create auto-scaler
    scaler = AutoScaler(policy)
    
    # Start auto-scaling loop
    await scaler.auto_scale_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Auto-scaler stopped")