#!/usr/bin/env python3
"""
QENEX Distributed System
High-performance distributed processing with intelligent load balancing
"""

import asyncio
import json
import time
import socket
import hashlib
import logging
import random
import redis
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Callable, Any
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import uvloop
from aiohttp import web, ClientSession
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

@dataclass
class NodeInfo:
    """Information about a distributed node"""
    node_id: str
    host: str
    port: int
    status: str  # active, inactive, maintenance
    load: float  # 0.0 to 1.0
    capabilities: List[str]
    last_heartbeat: float
    version: str
    region: str = "default"
    
@dataclass
class Task:
    """Distributed task definition"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 5  # 1-10, higher = more priority
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    created_at: float = 0
    assigned_node: Optional[str] = None
    status: str = "pending"  # pending, assigned, running, completed, failed

class QenexDistributedSystem:
    """Advanced distributed processing system"""
    
    def __init__(self, config_path: str = "/opt/qenex-os/config/distributed.json"):
        self.config_path = config_path
        self.node_id = self.generate_node_id()
        self.nodes: Dict[str, NodeInfo] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.load_balancer = None
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/qenex-os/logs/distributed.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QenexDistributedSystem')
        
        # Load configuration
        self.load_config()
        self.init_redis()
        self.init_crypto()
        
    def load_config(self):
        """Load distributed system configuration"""
        default_config = {
            "enabled": True,
            "node": {
                "host": "0.0.0.0",
                "port": 8002,
                "capabilities": ["general", "ai-processing", "data-analysis"],
                "max_concurrent_tasks": 10,
                "region": "default"
            },
            "cluster": {
                "discovery_method": "redis",  # redis, consul, etcd
                "heartbeat_interval": 30,
                "node_timeout": 90,
                "auto_discovery": True,
                "bootstrap_nodes": []
            },
            "load_balancing": {
                "algorithm": "weighted_round_robin",  # round_robin, least_connections, weighted
                "health_check_interval": 10,
                "failure_threshold": 3
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None
            },
            "security": {
                "encryption_enabled": True,
                "node_authentication": True,
                "secure_communication": True
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            self.config = default_config
            
    def save_config(self):
        """Save current configuration"""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def generate_node_id(self) -> str:
        """Generate unique node ID"""
        hostname = socket.gethostname()
        timestamp = str(int(time.time()))
        random_suffix = str(random.randint(1000, 9999))
        
        node_string = f"{hostname}-{timestamp}-{random_suffix}"
        return hashlib.sha256(node_string.encode()).hexdigest()[:16]
        
    def init_redis(self):
        """Initialize Redis connection for coordination"""
        try:
            redis_config = self.config.get("redis", {})
            self.redis_client = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password"),
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            self.logger.info("Connected to Redis for coordination")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            
    def init_crypto(self):
        """Initialize cryptographic components"""
        try:
            # Generate RSA key pair for node authentication
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
            
            # Serialize public key for sharing
            self.public_key_bytes = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize crypto: {e}")
            self.private_key = None
            self.public_key = None
            
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a handler for specific task type"""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Registered handler for task type: {task_type}")
        
    def get_current_load(self) -> float:
        """Calculate current node load"""
        try:
            import psutil
            
            # Weighted load calculation
            cpu_load = psutil.cpu_percent(interval=1) / 100.0
            memory_load = psutil.virtual_memory().percent / 100.0
            
            # Task queue load
            active_tasks = len([t for t in self.tasks.values() if t.status == "running"])
            max_tasks = self.config["node"]["max_concurrent_tasks"]
            task_load = active_tasks / max_tasks
            
            # Combined load (weighted)
            total_load = (cpu_load * 0.4 + memory_load * 0.3 + task_load * 0.3)
            return min(total_load, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating load: {e}")
            return 0.5  # Default moderate load
            
    async def register_node(self):
        """Register this node with the cluster"""
        if not self.redis_client:
            return
            
        try:
            node_info = NodeInfo(
                node_id=self.node_id,
                host=self.config["node"]["host"],
                port=self.config["node"]["port"],
                status="active",
                load=self.get_current_load(),
                capabilities=self.config["node"]["capabilities"],
                last_heartbeat=time.time(),
                version="1.0.0",
                region=self.config["node"]["region"]
            )
            
            # Store node info in Redis
            node_key = f"qenex:nodes:{self.node_id}"
            self.redis_client.hset(node_key, mapping=asdict(node_info))
            self.redis_client.expire(node_key, self.config["cluster"]["node_timeout"])
            
            # Add to active nodes set
            self.redis_client.sadd("qenex:active_nodes", self.node_id)
            
            self.logger.info(f"Registered node {self.node_id} with cluster")
            
        except Exception as e:
            self.logger.error(f"Failed to register node: {e}")
            
    async def heartbeat_loop(self):
        """Send periodic heartbeats to maintain node registration"""
        while self.config.get("enabled", True):
            try:
                await self.register_node()
                await self.discover_nodes()
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                
            await asyncio.sleep(self.config["cluster"]["heartbeat_interval"])
            
    async def discover_nodes(self):
        """Discover other nodes in the cluster"""
        if not self.redis_client:
            return
            
        try:
            # Get all active nodes
            active_node_ids = self.redis_client.smembers("qenex:active_nodes")
            current_nodes = {}
            
            for node_id in active_node_ids:
                if node_id == self.node_id:
                    continue
                    
                node_key = f"qenex:nodes:{node_id}"
                node_data = self.redis_client.hgetall(node_key)
                
                if node_data:
                    node_info = NodeInfo(
                        node_id=node_data["node_id"],
                        host=node_data["host"],
                        port=int(node_data["port"]),
                        status=node_data["status"],
                        load=float(node_data["load"]),
                        capabilities=json.loads(node_data["capabilities"]),
                        last_heartbeat=float(node_data["last_heartbeat"]),
                        version=node_data["version"],
                        region=node_data.get("region", "default")
                    )
                    
                    # Check if node is still alive
                    if time.time() - node_info.last_heartbeat < self.config["cluster"]["node_timeout"]:
                        current_nodes[node_id] = node_info
                    else:
                        # Remove expired node
                        self.redis_client.srem("qenex:active_nodes", node_id)
                        self.redis_client.delete(node_key)
                        
            # Update node registry
            self.nodes = current_nodes
            
        except Exception as e:
            self.logger.error(f"Error discovering nodes: {e}")
            
    def select_node_for_task(self, task: Task) -> Optional[str]:
        """Select best node for task using load balancing algorithm"""
        eligible_nodes = []
        
        # Filter nodes by capabilities
        for node_id, node_info in self.nodes.items():
            if (node_info.status == "active" and 
                any(cap in node_info.capabilities for cap in ["general", task.task_type])):
                eligible_nodes.append((node_id, node_info))
                
        if not eligible_nodes:
            return None
            
        # Apply load balancing algorithm
        algorithm = self.config["load_balancing"]["algorithm"]
        
        if algorithm == "round_robin":
            # Simple round-robin
            return eligible_nodes[len(self.tasks) % len(eligible_nodes)][0]
            
        elif algorithm == "least_connections":
            # Select node with least running tasks
            min_load = float('inf')
            best_node = None
            
            for node_id, node_info in eligible_nodes:
                if node_info.load < min_load:
                    min_load = node_info.load
                    best_node = node_id
                    
            return best_node
            
        elif algorithm == "weighted_round_robin":
            # Weighted selection based on inverse load
            weights = []
            nodes = []
            
            for node_id, node_info in eligible_nodes:
                # Higher weight for lower load
                weight = max(0.1, 1.0 - node_info.load)
                weights.append(weight)
                nodes.append(node_id)
                
            # Weighted random selection
            total_weight = sum(weights)
            random_value = random.random() * total_weight
            
            current_weight = 0
            for i, weight in enumerate(weights):
                current_weight += weight
                if random_value <= current_weight:
                    return nodes[i]
                    
        return eligible_nodes[0][0]  # Fallback
        
    async def submit_task(self, task: Task) -> str:
        """Submit a task for distributed processing"""
        try:
            task.created_at = time.time()
            
            # Select node for task
            selected_node = self.select_node_for_task(task)
            
            if selected_node == self.node_id or selected_node is None:
                # Execute locally
                task.assigned_node = self.node_id
                self.tasks[task.task_id] = task
                asyncio.create_task(self.execute_task_locally(task))
                
            else:
                # Send to remote node
                task.assigned_node = selected_node
                await self.send_task_to_node(task, selected_node)
                
            # Store task in Redis for tracking
            if self.redis_client:
                task_key = f"qenex:tasks:{task.task_id}"
                self.redis_client.hset(task_key, mapping=asdict(task))
                self.redis_client.expire(task_key, 3600)  # 1 hour TTL
                
            self.logger.info(f"Submitted task {task.task_id} to node {selected_node}")
            return task.task_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit task: {e}")
            raise
            
    async def execute_task_locally(self, task: Task):
        """Execute a task on the local node"""
        try:
            task.status = "running"
            start_time = time.time()
            
            self.logger.info(f"Executing task {task.task_id} locally")
            
            # Get task handler
            handler = self.task_handlers.get(task.task_type)
            
            if not handler:
                raise ValueError(f"No handler registered for task type: {task.task_type}")
                
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(task.payload),
                timeout=task.timeout_seconds
            )
            
            task.status = "completed"
            execution_time = time.time() - start_time
            
            # Store result
            if self.redis_client:
                result_key = f"qenex:results:{task.task_id}"
                self.redis_client.hset(result_key, {
                    "result": json.dumps(result),
                    "execution_time": execution_time,
                    "node_id": self.node_id
                })
                self.redis_client.expire(result_key, 3600)
                
            self.logger.info(f"Completed task {task.task_id} in {execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            task.status = "failed"
            self.logger.error(f"Task {task.task_id} timed out")
            await self.handle_task_failure(task, "timeout")
            
        except Exception as e:
            task.status = "failed"
            self.logger.error(f"Task {task.task_id} failed: {e}")
            await self.handle_task_failure(task, str(e))
            
        finally:
            # Update task status
            if self.redis_client:
                task_key = f"qenex:tasks:{task.task_id}"
                self.redis_client.hset(task_key, "status", task.status)
                
    async def send_task_to_node(self, task: Task, node_id: str):
        """Send task to remote node for execution"""
        try:
            node_info = self.nodes.get(node_id)
            if not node_info:
                raise ValueError(f"Node {node_id} not found")
                
            url = f"http://{node_info.host}:{node_info.port}/api/tasks"
            
            async with ClientSession() as session:
                async with session.post(url, json=asdict(task)) as response:
                    if response.status == 200:
                        self.logger.info(f"Task {task.task_id} sent to node {node_id}")
                    else:
                        raise Exception(f"Failed to send task: HTTP {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to send task to node {node_id}: {e}")
            # Fallback to local execution
            await self.execute_task_locally(task)
            
    async def handle_task_failure(self, task: Task, error_message: str):
        """Handle task failure and retry logic"""
        task.retry_count += 1
        
        if task.retry_count < task.max_retries:
            # Retry task
            self.logger.info(f"Retrying task {task.task_id} ({task.retry_count}/{task.max_retries})")
            
            # Wait before retry (exponential backoff)
            wait_time = min(60, 2 ** task.retry_count)
            await asyncio.sleep(wait_time)
            
            task.status = "pending"
            await self.submit_task(task)
            
        else:
            # Max retries exceeded
            self.logger.error(f"Task {task.task_id} failed permanently after {task.retry_count} retries")
            
            if self.redis_client:
                error_key = f"qenex:errors:{task.task_id}"
                self.redis_client.hset(error_key, {
                    "error_message": error_message,
                    "retry_count": task.retry_count,
                    "timestamp": time.time()
                })
                self.redis_client.expire(error_key, 86400)  # 24 hours
                
    async def get_task_result(self, task_id: str) -> Optional[Dict]:
        """Get result of completed task"""
        if not self.redis_client:
            return None
            
        try:
            result_key = f"qenex:results:{task_id}"
            result_data = self.redis_client.hgetall(result_key)
            
            if result_data:
                return {
                    "result": json.loads(result_data["result"]),
                    "execution_time": float(result_data["execution_time"]),
                    "node_id": result_data["node_id"]
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get task result: {e}")
            
        return None
        
    async def get_system_status(self) -> Dict:
        """Get distributed system status"""
        try:
            active_nodes = len(self.nodes) + 1  # +1 for current node
            total_load = sum(node.load for node in self.nodes.values()) + self.get_current_load()
            avg_load = total_load / active_nodes if active_nodes > 0 else 0
            
            # Task statistics
            if self.redis_client:
                total_tasks = len(self.redis_client.keys("qenex:tasks:*"))
                completed_tasks = 0
                failed_tasks = 0
                
                for task_key in self.redis_client.keys("qenex:tasks:*"):
                    task_status = self.redis_client.hget(task_key, "status")
                    if task_status == "completed":
                        completed_tasks += 1
                    elif task_status == "failed":
                        failed_tasks += 1
            else:
                total_tasks = len(self.tasks)
                completed_tasks = len([t for t in self.tasks.values() if t.status == "completed"])
                failed_tasks = len([t for t in self.tasks.values() if t.status == "failed"])
                
            return {
                "cluster": {
                    "active_nodes": active_nodes,
                    "average_load": round(avg_load, 3),
                    "regions": list(set(node.region for node in self.nodes.values()))
                },
                "tasks": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "failed": failed_tasks,
                    "success_rate": round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0
                },
                "current_node": {
                    "node_id": self.node_id,
                    "load": round(self.get_current_load(), 3),
                    "capabilities": self.config["node"]["capabilities"],
                    "running_tasks": len([t for t in self.tasks.values() if t.status == "running"])
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {"error": str(e)}
            
    async def create_web_server(self):
        """Create web server for node communication"""
        app = web.Application()
        
        # Task submission endpoint
        async def handle_task_submission(request):
            try:
                task_data = await request.json()
                task = Task(**task_data)
                
                # Execute task locally
                self.tasks[task.task_id] = task
                asyncio.create_task(self.execute_task_locally(task))
                
                return web.json_response({"status": "accepted", "task_id": task.task_id})
                
            except Exception as e:
                return web.json_response({"error": str(e)}, status=400)
                
        # Status endpoint
        async def handle_status(request):
            status = await self.get_system_status()
            return web.json_response(status)
            
        # Node info endpoint
        async def handle_node_info(request):
            node_info = {
                "node_id": self.node_id,
                "load": self.get_current_load(),
                "capabilities": self.config["node"]["capabilities"],
                "version": "1.0.0",
                "uptime": time.time() - getattr(self, 'start_time', time.time())
            }
            return web.json_response(node_info)
            
        app.router.add_post('/api/tasks', handle_task_submission)
        app.router.add_get('/api/status', handle_status)
        app.router.add_get('/api/node', handle_node_info)
        
        return app
        
    async def start(self):
        """Start the distributed system"""
        self.start_time = time.time()
        self.logger.info(f"Starting QENEX Distributed System - Node: {self.node_id}")
        
        # Register default task handlers
        self.register_default_handlers()
        
        # Create web server
        app = await self.create_web_server()
        
        # Start web server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            self.config["node"]["host"],
            self.config["node"]["port"]
        )
        await site.start()
        
        self.logger.info(f"Node API server started on {self.config['node']['host']}:{self.config['node']['port']}")
        
        # Start heartbeat loop
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        
        # Wait for shutdown
        try:
            await asyncio.gather(heartbeat_task)
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
            
    def register_default_handlers(self):
        """Register default task handlers"""
        
        async def handle_data_processing(payload):
            """Handle data processing tasks"""
            await asyncio.sleep(payload.get('processing_time', 1))
            return {
                'processed_items': payload.get('items', 0),
                'timestamp': time.time(),
                'node_id': self.node_id
            }
            
        async def handle_ai_inference(payload):
            """Handle AI inference tasks"""
            model_name = payload.get('model', 'default')
            input_data = payload.get('input', {})
            
            # Simulate AI processing
            await asyncio.sleep(payload.get('inference_time', 0.5))
            
            return {
                'model': model_name,
                'prediction': f"prediction_for_{hash(str(input_data))}",
                'confidence': random.uniform(0.8, 0.99),
                'processing_node': self.node_id
            }
            
        async def handle_pipeline_execution(payload):
            """Handle pipeline execution tasks"""
            pipeline_id = payload.get('pipeline_id')
            steps = payload.get('steps', [])
            
            results = []
            for i, step in enumerate(steps):
                await asyncio.sleep(0.1)  # Simulate step execution
                results.append(f"step_{i}_completed")
                
            return {
                'pipeline_id': pipeline_id,
                'steps_completed': len(steps),
                'results': results,
                'execution_node': self.node_id
            }
            
        # Register handlers
        self.register_task_handler('data_processing', handle_data_processing)
        self.register_task_handler('ai_inference', handle_ai_inference)
        self.register_task_handler('pipeline_execution', handle_pipeline_execution)
        
    def stop(self):
        """Stop the distributed system"""
        self.logger.info("Stopping QENEX Distributed System")
        self.config['enabled'] = False

# Example usage functions
async def submit_sample_tasks(distributed_system):
    """Submit sample tasks for testing"""
    
    # Data processing task
    task1 = Task(
        task_id="data_proc_001",
        task_type="data_processing",
        payload={"items": 1000, "processing_time": 2},
        priority=7
    )
    
    # AI inference task  
    task2 = Task(
        task_id="ai_inf_001",
        task_type="ai_inference",
        payload={
            "model": "qenex-classifier-v1",
            "input": {"text": "Sample input for classification"},
            "inference_time": 1
        },
        priority=9
    )
    
    # Pipeline task
    task3 = Task(
        task_id="pipeline_001",
        task_type="pipeline_execution",
        payload={
            "pipeline_id": "data_pipeline_v1",
            "steps": ["extract", "transform", "load", "validate"]
        },
        priority=5
    )
    
    # Submit tasks
    for task in [task1, task2, task3]:
        task_id = await distributed_system.submit_task(task)
        print(f"Submitted task: {task_id}")

async def main():
    """Main entry point"""
    # Use uvloop for better performance
    if hasattr(asyncio, 'set_event_loop_policy'):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    distributed_system = QenexDistributedSystem()
    
    try:
        await distributed_system.start()
    except KeyboardInterrupt:
        distributed_system.stop()
        print("\nDistributed system stopped")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())