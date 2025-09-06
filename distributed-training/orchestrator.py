#!/usr/bin/env python3
"""
QENEX Distributed Training Orchestrator
Continuous distributed machine learning system for kernel optimization
"""

import asyncio
import json
import time
import uuid
import hashlib
import pickle
import threading
import multiprocessing as mp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import socket
import aiohttp
import websockets
import numpy as np
import queue
import signal
import os
import sys
import psutil
import docker
import kubernetes
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# Configuration
ORCHESTRATOR_VERSION = "1.0.0"
ORCHESTRATOR_ROOT = "/opt/qenex-os/distributed-training"
MODEL_REPO = f"{ORCHESTRATOR_ROOT}/models"
GRADIENT_STORE = f"{ORCHESTRATOR_ROOT}/gradients"
CHECKPOINT_DIR = f"{ORCHESTRATOR_ROOT}/checkpoints"
CONFIG_DIR = f"{ORCHESTRATOR_ROOT}/config"
LOGS_DIR = f"{ORCHESTRATOR_ROOT}/logs"

# Create directories
for directory in [ORCHESTRATOR_ROOT, MODEL_REPO, GRADIENT_STORE, CHECKPOINT_DIR, CONFIG_DIR, LOGS_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class NodeRole(Enum):
    ORCHESTRATOR = "orchestrator"
    TRAINER = "trainer"
    VALIDATOR = "validator"
    COORDINATOR = "coordinator"

class TrainingStatus(Enum):
    IDLE = "idle"
    TRAINING = "training"
    VALIDATING = "validating"
    SYNCHRONIZING = "synchronizing"
    UPDATING = "updating"
    FAILED = "failed"

class ModelVersion(Enum):
    STABLE = "stable"
    CANDIDATE = "candidate" 
    EXPERIMENTAL = "experimental"

@dataclass
class NodeInfo:
    node_id: str
    role: NodeRole
    ip_address: str
    port: int
    status: TrainingStatus
    cpu_cores: int
    memory_gb: int
    gpu_count: int
    last_heartbeat: str
    training_capacity: float
    current_model_version: str

@dataclass
class TrainingTask:
    task_id: str
    model_name: str
    dataset_id: str
    batch_size: int
    epochs: int
    learning_rate: float
    nodes_required: int
    priority: int
    created_time: str
    assigned_nodes: List[str]
    status: TrainingStatus

@dataclass
class ModelUpdate:
    model_id: str
    version: str
    gradients_hash: str
    accuracy: float
    loss: float
    node_id: str
    timestamp: str
    model_weights: bytes

class DistributedTrainingOrchestrator:
    """Main orchestrator for distributed training across QENEX instances"""
    
    def __init__(self, node_id: str = None, config_path: str = None):
        self.node_id = node_id or f"orchestrator-{uuid.uuid4().hex[:8]}"
        self.role = NodeRole.ORCHESTRATOR
        self.status = TrainingStatus.IDLE
        self.start_time = datetime.now()
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Set up logging
        self.logger = self.setup_logging()
        
        # Node management
        self.nodes: Dict[str, NodeInfo] = {}
        self.node_assignments: Dict[str, List[str]] = {}
        self.heartbeat_timeout = 30  # seconds
        
        # Training management
        self.training_queue = asyncio.Queue()
        self.active_tasks: Dict[str, TrainingTask] = {}
        self.model_versions: Dict[str, List[str]] = {}
        
        # Gradient aggregation
        self.gradient_buffer: Dict[str, List[bytes]] = {}
        self.model_updates: Dict[str, List[ModelUpdate]] = {}
        
        # Zero-downtime updates
        self.active_models: Dict[str, str] = {}  # model_name -> version
        self.staging_models: Dict[str, str] = {}
        
        # Performance monitoring
        self.performance_metrics = {}
        self.training_history = []
        
        # Communication
        self.websocket_server = None
        self.http_session = None
        
        # Threading pools
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.process_pool = ProcessPoolExecutor(max_workers=mp.cpu_count())
        
        # Kubernetes integration
        self.k8s_enabled = self.config.get("kubernetes", {}).get("enabled", False)
        if self.k8s_enabled:
            self.k8s_client = kubernetes.client.ApiClient()
        
        # Docker integration
        self.docker_enabled = self.config.get("docker", {}).get("enabled", False)
        if self.docker_enabled:
            self.docker_client = docker.from_env()
        
        self.logger.info(f"Distributed Training Orchestrator {ORCHESTRATOR_VERSION} initialized")
        self.logger.info(f"Node ID: {self.node_id}")
        self.logger.info(f"Role: {self.role.value}")
    
    def load_config(self, config_path: str = None) -> Dict:
        """Load orchestrator configuration"""
        default_config = {
            "orchestrator": {
                "port": 8080,
                "websocket_port": 8081,
                "max_nodes": 100,
                "heartbeat_interval": 10,
                "gradient_aggregation_method": "federated_averaging",
                "model_update_frequency": 3600,  # 1 hour
                "checkpoint_interval": 1800,  # 30 minutes
            },
            "training": {
                "batch_size": 32,
                "learning_rate": 0.001,
                "epochs": 10,
                "validation_split": 0.2,
                "early_stopping": True,
                "patience": 5,
            },
            "models": {
                "security_detection": {
                    "type": "neural_network",
                    "architecture": "transformer",
                    "input_size": 1024,
                    "hidden_size": 512,
                    "output_size": 10,
                },
                "anomaly_detection": {
                    "type": "autoencoder",
                    "architecture": "lstm",
                    "sequence_length": 100,
                    "encoding_dim": 64,
                },
                "threat_classification": {
                    "type": "cnn",
                    "architecture": "resnet",
                    "input_channels": 1,
                    "num_classes": 20,
                }
            },
            "federation": {
                "aggregation_strategy": "federated_averaging",
                "min_nodes_for_aggregation": 3,
                "consensus_threshold": 0.7,
                "privacy_preserving": True,
                "differential_privacy": {
                    "enabled": True,
                    "epsilon": 1.0,
                    "delta": 1e-5
                }
            },
            "kubernetes": {
                "enabled": False,
                "namespace": "qenex-training",
                "service_account": "qenex-orchestrator"
            },
            "docker": {
                "enabled": True,
                "registry": "qenex-registry:5000",
                "base_image": "qenex/training-node:latest"
            },
            "storage": {
                "type": "distributed",
                "backends": ["nfs", "ceph", "minio"],
                "replication_factor": 3
            }
        }
        
        config_file = config_path or f"{CONFIG_DIR}/orchestrator.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # Merge with defaults
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in default_config:
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
        else:
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        
        return default_config
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('DistributedTrainingOrchestrator')
        logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(f"{LOGS_DIR}/orchestrator.log")
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    async def start(self):
        """Start the distributed training orchestrator"""
        self.logger.info("Starting Distributed Training Orchestrator...")
        
        # Initialize HTTP session
        self.http_session = aiohttp.ClientSession()
        
        # Start core services
        tasks = [
            self.start_websocket_server(),
            self.start_node_discovery(),
            self.start_heartbeat_monitor(),
            self.start_gradient_aggregator(),
            self.start_model_updater(),
            self.start_performance_monitor(),
            self.start_training_scheduler(),
            self.start_checkpoint_manager(),
        ]
        
        # Start Kubernetes integration if enabled
        if self.k8s_enabled:
            tasks.append(self.start_kubernetes_integration())
        
        # Start Docker integration if enabled
        if self.docker_enabled:
            tasks.append(self.start_docker_integration())
        
        # Run all services concurrently
        await asyncio.gather(*tasks)
    
    async def start_websocket_server(self):
        """Start WebSocket server for node communication"""
        async def handle_client(websocket, path):
            try:
                node_id = await self.authenticate_node(websocket)
                if node_id:
                    await self.handle_node_connection(websocket, node_id)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
        
        port = self.config["orchestrator"]["websocket_port"]
        self.websocket_server = await websockets.serve(
            handle_client, "0.0.0.0", port
        )
        self.logger.info(f"WebSocket server started on port {port}")
        
        # Keep server running
        await self.websocket_server.wait_closed()
    
    async def authenticate_node(self, websocket) -> Optional[str]:
        """Authenticate connecting node"""
        try:
            # Wait for authentication message
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            auth_data = json.loads(auth_message)
            
            node_id = auth_data.get("node_id")
            token = auth_data.get("token")
            
            # Validate token (simplified - implement proper auth in production)
            expected_token = hashlib.sha256(f"{node_id}-qenex-training".encode()).hexdigest()
            
            if token == expected_token:
                await websocket.send(json.dumps({"status": "authenticated"}))
                self.logger.info(f"Node {node_id} authenticated successfully")
                return node_id
            else:
                await websocket.send(json.dumps({"status": "authentication_failed"}))
                return None
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return None
    
    async def handle_node_connection(self, websocket, node_id: str):
        """Handle WebSocket connection from a training node"""
        self.logger.info(f"Node {node_id} connected")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_node_message(websocket, node_id, data)
                except Exception as e:
                    self.logger.error(f"Error processing message from {node_id}: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Node {node_id} disconnected")
        finally:
            # Clean up node
            if node_id in self.nodes:
                del self.nodes[node_id]
    
    async def process_node_message(self, websocket, node_id: str, data: Dict):
        """Process message from training node"""
        message_type = data.get("type")
        
        if message_type == "heartbeat":
            await self.handle_heartbeat(node_id, data)
            
        elif message_type == "node_info":
            await self.handle_node_registration(websocket, node_id, data)
            
        elif message_type == "gradient_update":
            await self.handle_gradient_update(node_id, data)
            
        elif message_type == "training_complete":
            await self.handle_training_complete(node_id, data)
            
        elif message_type == "model_validation":
            await self.handle_model_validation(node_id, data)
            
        elif message_type == "performance_metrics":
            await self.handle_performance_metrics(node_id, data)
            
        else:
            self.logger.warning(f"Unknown message type from {node_id}: {message_type}")
    
    async def handle_heartbeat(self, node_id: str, data: Dict):
        """Handle heartbeat from training node"""
        if node_id in self.nodes:
            self.nodes[node_id].last_heartbeat = datetime.now().isoformat()
            self.nodes[node_id].status = TrainingStatus(data.get("status", "idle"))
    
    async def handle_node_registration(self, websocket, node_id: str, data: Dict):
        """Handle node registration"""
        node_info = NodeInfo(
            node_id=node_id,
            role=NodeRole(data.get("role", "trainer")),
            ip_address=data.get("ip_address", "unknown"),
            port=data.get("port", 8080),
            status=TrainingStatus.IDLE,
            cpu_cores=data.get("cpu_cores", 1),
            memory_gb=data.get("memory_gb", 1),
            gpu_count=data.get("gpu_count", 0),
            last_heartbeat=datetime.now().isoformat(),
            training_capacity=data.get("training_capacity", 1.0),
            current_model_version="none"
        )
        
        self.nodes[node_id] = node_info
        self.logger.info(f"Registered node {node_id} with role {node_info.role.value}")
        
        # Send initial configuration
        config_message = {
            "type": "configuration",
            "config": self.config["training"],
            "models": list(self.config["models"].keys())
        }
        await websocket.send(json.dumps(config_message))
    
    async def handle_gradient_update(self, node_id: str, data: Dict):
        """Handle gradient update from training node"""
        model_name = data.get("model_name")
        gradients = data.get("gradients")  # Base64 encoded
        metrics = data.get("metrics", {})
        
        if model_name not in self.gradient_buffer:
            self.gradient_buffer[model_name] = []
        
        # Decode gradients
        gradient_bytes = bytes.fromhex(gradients) if isinstance(gradients, str) else gradients
        
        # Create model update
        update = ModelUpdate(
            model_id=model_name,
            version=data.get("version", "unknown"),
            gradients_hash=hashlib.sha256(gradient_bytes).hexdigest(),
            accuracy=metrics.get("accuracy", 0.0),
            loss=metrics.get("loss", float('inf')),
            node_id=node_id,
            timestamp=datetime.now().isoformat(),
            model_weights=gradient_bytes
        )
        
        if model_name not in self.model_updates:
            self.model_updates[model_name] = []
        
        self.model_updates[model_name].append(update)
        
        self.logger.info(f"Received gradient update for {model_name} from {node_id}")
        
        # Check if we have enough updates for aggregation
        min_nodes = self.config["federation"]["min_nodes_for_aggregation"]
        if len(self.model_updates[model_name]) >= min_nodes:
            await self.trigger_gradient_aggregation(model_name)
    
    async def trigger_gradient_aggregation(self, model_name: str):
        """Trigger gradient aggregation for a model"""
        self.logger.info(f"Starting gradient aggregation for {model_name}")
        
        # Get recent updates
        recent_updates = self.model_updates[model_name][-10:]  # Last 10 updates
        
        # Aggregate using federated averaging
        aggregated_gradients = await self.federated_averaging(recent_updates)
        
        # Create new model version
        new_version = f"v{int(time.time())}"
        
        # Save aggregated model
        model_path = f"{MODEL_REPO}/{model_name}/{new_version}"
        os.makedirs(model_path, exist_ok=True)
        
        with open(f"{model_path}/model.pkl", "wb") as f:
            pickle.dump(aggregated_gradients, f)
        
        # Update model versions
        if model_name not in self.model_versions:
            self.model_versions[model_name] = []
        self.model_versions[model_name].append(new_version)
        
        # Prepare for zero-downtime update
        await self.prepare_model_update(model_name, new_version)
        
        self.logger.info(f"Gradient aggregation completed for {model_name} -> {new_version}")
    
    async def federated_averaging(self, updates: List[ModelUpdate]) -> bytes:
        """Perform federated averaging of model updates"""
        if not updates:
            return b""
        
        # Simple averaging implementation
        # In production, implement proper federated learning algorithms
        
        # For now, return the update from the node with highest accuracy
        best_update = max(updates, key=lambda x: x.accuracy)
        
        self.logger.info(f"Federated averaging: selected update from {best_update.node_id} "
                        f"with accuracy {best_update.accuracy}")
        
        return best_update.model_weights
    
    async def prepare_model_update(self, model_name: str, new_version: str):
        """Prepare zero-downtime model update"""
        # Stage the new model
        self.staging_models[model_name] = new_version
        
        # Validate the new model
        validation_results = await self.validate_model(model_name, new_version)
        
        if validation_results["is_valid"]:
            # Schedule update
            await self.schedule_model_update(model_name, new_version)
        else:
            self.logger.warning(f"Model validation failed for {model_name} {new_version}")
            # Rollback
            if model_name in self.staging_models:
                del self.staging_models[model_name]
    
    async def validate_model(self, model_name: str, version: str) -> Dict:
        """Validate model before deployment"""
        try:
            # Load model
            model_path = f"{MODEL_REPO}/{model_name}/{version}/model.pkl"
            
            if not os.path.exists(model_path):
                return {"is_valid": False, "error": "Model file not found"}
            
            # Basic validation checks
            file_size = os.path.getsize(model_path)
            if file_size == 0:
                return {"is_valid": False, "error": "Model file is empty"}
            
            # TODO: Add more sophisticated validation
            # - Check model architecture compatibility
            # - Validate model performance on test dataset
            # - Check for adversarial robustness
            
            return {
                "is_valid": True,
                "size_bytes": file_size,
                "validation_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"is_valid": False, "error": str(e)}
    
    async def schedule_model_update(self, model_name: str, new_version: str):
        """Schedule zero-downtime model update"""
        self.logger.info(f"Scheduling model update: {model_name} -> {new_version}")
        
        # Notify all nodes about the update
        update_message = {
            "type": "model_update",
            "model_name": model_name,
            "new_version": new_version,
            "update_strategy": "rolling",
            "rollback_version": self.active_models.get(model_name, "none")
        }
        
        await self.broadcast_to_nodes(update_message)
        
        # Update active model version after nodes confirm
        await asyncio.sleep(5)  # Wait for node confirmations
        self.active_models[model_name] = new_version
        
        # Clean up staging
        if model_name in self.staging_models:
            del self.staging_models[model_name]
    
    async def broadcast_to_nodes(self, message: Dict):
        """Broadcast message to all connected nodes"""
        # In a real implementation, maintain WebSocket connections to nodes
        # For now, log the broadcast
        self.logger.info(f"Broadcasting to {len(self.nodes)} nodes: {message['type']}")
    
    async def start_node_discovery(self):
        """Start node discovery service"""
        while True:
            try:
                # Kubernetes node discovery
                if self.k8s_enabled:
                    await self.discover_k8s_nodes()
                
                # Docker node discovery
                if self.docker_enabled:
                    await self.discover_docker_nodes()
                
                # Network node discovery
                await self.discover_network_nodes()
                
                await asyncio.sleep(30)  # Discovery every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Node discovery error: {e}")
                await asyncio.sleep(60)
    
    async def discover_k8s_nodes(self):
        """Discover training nodes in Kubernetes"""
        # TODO: Implement Kubernetes node discovery
        pass
    
    async def discover_docker_nodes(self):
        """Discover training nodes in Docker"""
        try:
            containers = self.docker_client.containers.list(
                filters={"label": "qenex.role=training-node"}
            )
            
            for container in containers:
                container_info = container.attrs
                node_id = container_info['Config']['Labels'].get('qenex.node_id')
                
                if node_id and node_id not in self.nodes:
                    # Register discovered node
                    self.logger.info(f"Discovered Docker node: {node_id}")
                    
        except Exception as e:
            self.logger.error(f"Docker node discovery error: {e}")
    
    async def discover_network_nodes(self):
        """Discover training nodes on network"""
        # TODO: Implement network-based node discovery
        # Could use multicast, service discovery, etc.
        pass
    
    async def start_heartbeat_monitor(self):
        """Monitor node heartbeats"""
        while True:
            try:
                current_time = datetime.now()
                stale_nodes = []
                
                for node_id, node_info in self.nodes.items():
                    last_heartbeat = datetime.fromisoformat(node_info.last_heartbeat)
                    if (current_time - last_heartbeat).seconds > self.heartbeat_timeout:
                        stale_nodes.append(node_id)
                
                # Remove stale nodes
                for node_id in stale_nodes:
                    self.logger.warning(f"Removing stale node: {node_id}")
                    del self.nodes[node_id]
                    
                    # Reassign tasks from failed node
                    await self.reassign_node_tasks(node_id)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(30)
    
    async def reassign_node_tasks(self, failed_node_id: str):
        """Reassign tasks from failed node"""
        reassigned_tasks = []
        
        for task_id, task in self.active_tasks.items():
            if failed_node_id in task.assigned_nodes:
                task.assigned_nodes.remove(failed_node_id)
                
                # Find replacement node
                replacement_node = await self.find_available_node(task)
                if replacement_node:
                    task.assigned_nodes.append(replacement_node)
                    reassigned_tasks.append(task_id)
        
        if reassigned_tasks:
            self.logger.info(f"Reassigned {len(reassigned_tasks)} tasks from failed node {failed_node_id}")
    
    async def find_available_node(self, task: TrainingTask) -> Optional[str]:
        """Find available node for task assignment"""
        available_nodes = [
            node_id for node_id, node_info in self.nodes.items()
            if node_info.status == TrainingStatus.IDLE and 
               node_info.role == NodeRole.TRAINER
        ]
        
        if available_nodes:
            # Simple round-robin assignment
            return available_nodes[0]
        
        return None
    
    async def start_gradient_aggregator(self):
        """Start gradient aggregation service"""
        while True:
            try:
                # Process gradient aggregation queue
                for model_name in list(self.model_updates.keys()):
                    updates = self.model_updates[model_name]
                    min_nodes = self.config["federation"]["min_nodes_for_aggregation"]
                    
                    if len(updates) >= min_nodes:
                        # Check if enough time has passed since last aggregation
                        last_update = max(updates, key=lambda x: x.timestamp)
                        time_since_update = (
                            datetime.now() - datetime.fromisoformat(last_update.timestamp)
                        ).seconds
                        
                        if time_since_update >= 60:  # Aggregate every minute
                            await self.trigger_gradient_aggregation(model_name)
                            # Clear processed updates
                            self.model_updates[model_name] = []
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Gradient aggregator error: {e}")
                await asyncio.sleep(60)
    
    async def start_model_updater(self):
        """Start model update service"""
        while True:
            try:
                # Check for scheduled model updates
                update_frequency = self.config["orchestrator"]["model_update_frequency"]
                
                for model_name in self.config["models"].keys():
                    if model_name in self.model_versions and self.model_versions[model_name]:
                        latest_version = self.model_versions[model_name][-1]
                        current_version = self.active_models.get(model_name)
                        
                        if latest_version != current_version:
                            await self.schedule_model_update(model_name, latest_version)
                
                await asyncio.sleep(update_frequency)
                
            except Exception as e:
                self.logger.error(f"Model updater error: {e}")
                await asyncio.sleep(300)  # 5 minutes
    
    async def start_performance_monitor(self):
        """Start performance monitoring service"""
        while True:
            try:
                # Collect performance metrics
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "orchestrator_id": self.node_id,
                    "active_nodes": len(self.nodes),
                    "active_tasks": len(self.active_tasks),
                    "models_trained": len(self.model_versions),
                    "total_gradients_processed": sum(
                        len(updates) for updates in self.model_updates.values()
                    ),
                    "system_resources": {
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_percent": psutil.virtual_memory().percent,
                        "disk_percent": psutil.disk_usage('/').percent,
                    }
                }
                
                self.performance_metrics[datetime.now().isoformat()] = metrics
                
                # Save metrics periodically
                if len(self.performance_metrics) % 10 == 0:
                    await self.save_performance_metrics()
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                self.logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(300)
    
    async def save_performance_metrics(self):
        """Save performance metrics to file"""
        metrics_file = f"{LOGS_DIR}/performance_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.performance_metrics, f, indent=2)
    
    async def start_training_scheduler(self):
        """Start training task scheduler"""
        while True:
            try:
                # Process training queue
                while not self.training_queue.empty():
                    task = await self.training_queue.get()
                    await self.schedule_training_task(task)
                
                await asyncio.sleep(10)  # Schedule every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Training scheduler error: {e}")
                await asyncio.sleep(30)
    
    async def schedule_training_task(self, task: TrainingTask):
        """Schedule training task on available nodes"""
        # Find available nodes
        available_nodes = [
            node_id for node_id, node_info in self.nodes.items()
            if node_info.status == TrainingStatus.IDLE and 
               node_info.role == NodeRole.TRAINER
        ]
        
        if len(available_nodes) >= task.nodes_required:
            # Assign nodes to task
            assigned_nodes = available_nodes[:task.nodes_required]
            task.assigned_nodes = assigned_nodes
            
            # Update node status
            for node_id in assigned_nodes:
                self.nodes[node_id].status = TrainingStatus.TRAINING
            
            # Add to active tasks
            self.active_tasks[task.task_id] = task
            
            self.logger.info(f"Scheduled training task {task.task_id} on {len(assigned_nodes)} nodes")
            
            # Notify nodes about training assignment
            training_message = {
                "type": "training_assignment",
                "task_id": task.task_id,
                "model_name": task.model_name,
                "dataset_id": task.dataset_id,
                "batch_size": task.batch_size,
                "epochs": task.epochs,
                "learning_rate": task.learning_rate
            }
            
            await self.broadcast_to_nodes(training_message)
        else:
            # Not enough nodes available, put back in queue
            await self.training_queue.put(task)
    
    async def start_checkpoint_manager(self):
        """Start checkpoint management service"""
        while True:
            try:
                checkpoint_interval = self.config["orchestrator"]["checkpoint_interval"]
                
                # Create checkpoint of current state
                checkpoint = {
                    "timestamp": datetime.now().isoformat(),
                    "orchestrator_id": self.node_id,
                    "nodes": {node_id: asdict(node_info) for node_id, node_info in self.nodes.items()},
                    "active_tasks": {task_id: asdict(task) for task_id, task in self.active_tasks.items()},
                    "model_versions": self.model_versions,
                    "active_models": self.active_models,
                    "performance_metrics": list(self.performance_metrics.values())[-100:]  # Last 100 entries
                }
                
                # Save checkpoint
                checkpoint_file = f"{CHECKPOINT_DIR}/checkpoint_{int(time.time())}.json"
                with open(checkpoint_file, 'w') as f:
                    json.dump(checkpoint, f, indent=2)
                
                # Clean up old checkpoints (keep last 10)
                await self.cleanup_old_checkpoints()
                
                self.logger.info(f"Created checkpoint: {checkpoint_file}")
                
                await asyncio.sleep(checkpoint_interval)
                
            except Exception as e:
                self.logger.error(f"Checkpoint manager error: {e}")
                await asyncio.sleep(1800)  # 30 minutes
    
    async def cleanup_old_checkpoints(self):
        """Clean up old checkpoint files"""
        checkpoint_files = sorted(
            Path(CHECKPOINT_DIR).glob("checkpoint_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Keep only the 10 most recent checkpoints
        for old_checkpoint in checkpoint_files[10:]:
            old_checkpoint.unlink()
    
    async def start_kubernetes_integration(self):
        """Start Kubernetes integration service"""
        while True:
            try:
                # TODO: Implement Kubernetes integration
                # - Deploy training pods
                # - Scale based on demand
                # - Manage persistent volumes
                # - Handle node failures
                
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Kubernetes integration error: {e}")
                await asyncio.sleep(300)
    
    async def start_docker_integration(self):
        """Start Docker integration service"""
        while True:
            try:
                # Monitor Docker containers
                containers = self.docker_client.containers.list(
                    filters={"label": "qenex.role=training-node"}
                )
                
                # Check container health
                unhealthy_containers = []
                for container in containers:
                    if container.status != 'running':
                        unhealthy_containers.append(container.id)
                
                # Restart unhealthy containers
                for container_id in unhealthy_containers:
                    try:
                        container = self.docker_client.containers.get(container_id)
                        container.restart()
                        self.logger.info(f"Restarted unhealthy container: {container_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to restart container {container_id}: {e}")
                
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Docker integration error: {e}")
                await asyncio.sleep(300)
    
    async def handle_training_complete(self, node_id: str, data: Dict):
        """Handle training completion from node"""
        task_id = data.get("task_id")
        metrics = data.get("metrics", {})
        
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            
            # Update node status
            if node_id in self.nodes:
                self.nodes[node_id].status = TrainingStatus.IDLE
            
            # Record training completion
            self.training_history.append({
                "task_id": task_id,
                "node_id": node_id,
                "completion_time": datetime.now().isoformat(),
                "metrics": metrics
            })
            
            self.logger.info(f"Training completed on node {node_id} for task {task_id}")
            
            # Check if all nodes completed for this task
            completed_nodes = [
                h["node_id"] for h in self.training_history 
                if h["task_id"] == task_id
            ]
            
            if len(completed_nodes) == len(task.assigned_nodes):
                # All nodes completed, remove task
                del self.active_tasks[task_id]
                self.logger.info(f"Task {task_id} fully completed")
    
    async def handle_model_validation(self, node_id: str, data: Dict):
        """Handle model validation results from node"""
        model_name = data.get("model_name")
        version = data.get("version")
        validation_results = data.get("results", {})
        
        self.logger.info(f"Received model validation for {model_name} {version} from {node_id}")
        self.logger.info(f"Validation results: {validation_results}")
    
    async def handle_performance_metrics(self, node_id: str, data: Dict):
        """Handle performance metrics from node"""
        metrics = data.get("metrics", {})
        timestamp = data.get("timestamp", datetime.now().isoformat())
        
        # Store node-specific metrics
        node_metrics_key = f"{node_id}_{timestamp}"
        self.performance_metrics[node_metrics_key] = {
            "node_id": node_id,
            "timestamp": timestamp,
            "metrics": metrics
        }
    
    async def create_training_task(self, model_name: str, **kwargs) -> str:
        """Create new training task"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        task = TrainingTask(
            task_id=task_id,
            model_name=model_name,
            dataset_id=kwargs.get("dataset_id", "default"),
            batch_size=kwargs.get("batch_size", self.config["training"]["batch_size"]),
            epochs=kwargs.get("epochs", self.config["training"]["epochs"]),
            learning_rate=kwargs.get("learning_rate", self.config["training"]["learning_rate"]),
            nodes_required=kwargs.get("nodes_required", 1),
            priority=kwargs.get("priority", 1),
            created_time=datetime.now().isoformat(),
            assigned_nodes=[],
            status=TrainingStatus.IDLE
        )
        
        await self.training_queue.put(task)
        self.logger.info(f"Created training task: {task_id} for model {model_name}")
        
        return task_id
    
    async def get_system_status(self) -> Dict:
        """Get current system status"""
        return {
            "orchestrator_id": self.node_id,
            "version": ORCHESTRATOR_VERSION,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "status": self.status.value,
            "nodes": {
                "total": len(self.nodes),
                "by_role": {
                    role.value: len([n for n in self.nodes.values() if n.role == role])
                    for role in NodeRole
                },
                "by_status": {
                    status.value: len([n for n in self.nodes.values() if n.status == status])
                    for status in TrainingStatus
                }
            },
            "training": {
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.training_history),
                "models_trained": len(self.model_versions)
            },
            "models": {
                "active": self.active_models,
                "versions": {k: len(v) for k, v in self.model_versions.items()}
            }
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Starting graceful shutdown...")
        
        # Stop WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
        
        # Shutdown executors
        self.executor.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        # Save final checkpoint
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "shutdown": True,
            "final_state": await self.get_system_status()
        }
        
        with open(f"{CHECKPOINT_DIR}/shutdown_checkpoint.json", 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        self.logger.info("Shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    # Set global shutdown flag
    global shutdown_requested
    shutdown_requested = True

async def main():
    """Main entry point"""
    global shutdown_requested
    shutdown_requested = False
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create orchestrator
    orchestrator = DistributedTrainingOrchestrator()
    
    try:
        # Start the orchestrator
        await orchestrator.start()
        
    except Exception as e:
        print(f"Fatal error: {e}")
        await orchestrator.shutdown()

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║            QENEX Distributed Training System              ║
║                    Orchestrator v1.0.0                    ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())