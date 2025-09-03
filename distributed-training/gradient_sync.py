#!/usr/bin/env python3
"""
QENEX Gradient Synchronization System
High-performance gradient synchronization for distributed training
"""

import asyncio
import json
import numpy as np
import pickle
import hashlib
import uuid
import time
import threading
import multiprocessing as mp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import queue
import socket
import struct
import zlib
import lz4.frame
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import redis
import zmq
import mpi4py.MPI as MPI
import torch
import torch.distributed as dist
import horovod.torch as hvd

# Configuration
SYNC_ROOT = "/opt/qenex-os/distributed-training/gradient-sync"
SYNC_BUFFER = f"{SYNC_ROOT}/buffer"
SYNC_CHECKPOINTS = f"{SYNC_ROOT}/checkpoints"
SYNC_LOGS = f"{SYNC_ROOT}/logs"
SYNC_CONFIG = f"{SYNC_ROOT}/config"

# Create directories
for directory in [SYNC_ROOT, SYNC_BUFFER, SYNC_CHECKPOINTS, SYNC_LOGS, SYNC_CONFIG]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class SyncStrategy(Enum):
    ALLREDUCE = "allreduce"
    PARAMETER_SERVER = "parameter_server"
    GOSSIP = "gossip"
    HIERARCHICAL = "hierarchical"
    RING_ALLREDUCE = "ring_allreduce"
    BUTTERFLY_ALLREDUCE = "butterfly_allreduce"

class CompressionType(Enum):
    NONE = "none"
    QUANTIZATION = "quantization"
    SPARSIFICATION = "sparsification"
    HUFFMAN = "huffman"
    GRADIENT_COMPRESSION = "gradient_compression"

class SyncTopology(Enum):
    FLAT = "flat"
    HIERARCHICAL = "hierarchical"
    RING = "ring"
    MESH = "mesh"
    TREE = "tree"

@dataclass
class GradientUpdate:
    update_id: str
    node_id: str
    model_name: str
    layer_name: str
    gradients: np.ndarray
    metadata: Dict[str, Any]
    timestamp: str
    sequence_number: int
    checksum: str
    compressed: bool = False
    compression_ratio: float = 1.0

@dataclass
class SyncNode:
    node_id: str
    ip_address: str
    port: int
    rank: int
    world_size: int
    device_type: str  # cpu, cuda, mps
    compute_capability: float
    bandwidth_mbps: float
    latency_ms: float
    last_sync: str
    gradient_buffer_size: int
    is_coordinator: bool = False

@dataclass
class SyncRound:
    round_id: str
    model_name: str
    participating_nodes: List[str]
    strategy: SyncStrategy
    topology: SyncTopology
    compression: CompressionType
    start_time: str
    end_time: Optional[str] = None
    total_gradients: int = 0
    bytes_transferred: int = 0
    sync_time_ms: float = 0.0

class GradientCompressor:
    """Advanced gradient compression techniques"""
    
    def __init__(self):
        self.quantization_bits = 8
        self.sparsity_threshold = 0.001
        
    def compress_gradients(self, gradients: np.ndarray, method: CompressionType) -> Tuple[bytes, Dict[str, Any]]:
        """Compress gradients using specified method"""
        
        if method == CompressionType.NONE:
            return pickle.dumps(gradients), {"original_shape": gradients.shape}
            
        elif method == CompressionType.QUANTIZATION:
            return self.quantize_gradients(gradients)
            
        elif method == CompressionType.SPARSIFICATION:
            return self.sparsify_gradients(gradients)
            
        elif method == CompressionType.HUFFMAN:
            return self.huffman_compress(gradients)
            
        elif method == CompressionType.GRADIENT_COMPRESSION:
            return self.advanced_gradient_compression(gradients)
            
        else:
            return pickle.dumps(gradients), {"original_shape": gradients.shape}
    
    def decompress_gradients(self, compressed_data: bytes, metadata: Dict[str, Any], method: CompressionType) -> np.ndarray:
        """Decompress gradients"""
        
        if method == CompressionType.NONE:
            return pickle.loads(compressed_data)
            
        elif method == CompressionType.QUANTIZATION:
            return self.dequantize_gradients(compressed_data, metadata)
            
        elif method == CompressionType.SPARSIFICATION:
            return self.desparsify_gradients(compressed_data, metadata)
            
        elif method == CompressionType.HUFFMAN:
            return self.huffman_decompress(compressed_data, metadata)
            
        elif method == CompressionType.GRADIENT_COMPRESSION:
            return self.advanced_gradient_decompression(compressed_data, metadata)
            
        else:
            return pickle.loads(compressed_data)
    
    def quantize_gradients(self, gradients: np.ndarray) -> Tuple[bytes, Dict[str, Any]]:
        """8-bit quantization of gradients"""
        # Find min and max values
        min_val = np.min(gradients)
        max_val = np.max(gradients)
        
        # Quantize to 8-bit
        scale = (max_val - min_val) / 255.0
        quantized = np.round((gradients - min_val) / scale).astype(np.uint8)
        
        # Compress quantized data
        compressed = lz4.frame.compress(quantized.tobytes())
        
        metadata = {
            "original_shape": gradients.shape,
            "min_val": float(min_val),
            "max_val": float(max_val),
            "scale": float(scale),
            "dtype": str(gradients.dtype)
        }
        
        return compressed, metadata
    
    def dequantize_gradients(self, compressed_data: bytes, metadata: Dict[str, Any]) -> np.ndarray:
        """Dequantize compressed gradients"""
        # Decompress
        decompressed = lz4.frame.decompress(compressed_data)
        quantized = np.frombuffer(decompressed, dtype=np.uint8)
        quantized = quantized.reshape(metadata["original_shape"])
        
        # Dequantize
        min_val = metadata["min_val"]
        scale = metadata["scale"]
        
        gradients = quantized.astype(np.float32) * scale + min_val
        return gradients.astype(np.dtype(metadata["dtype"]))
    
    def sparsify_gradients(self, gradients: np.ndarray) -> Tuple[bytes, Dict[str, Any]]:
        """Gradient sparsification - keep only significant values"""
        # Find significant gradients
        abs_gradients = np.abs(gradients)
        threshold = np.percentile(abs_gradients, 95)  # Keep top 5%
        
        # Create sparse representation
        mask = abs_gradients >= threshold
        indices = np.where(mask)
        values = gradients[mask]
        
        # Serialize sparse data
        sparse_data = {
            "indices": indices,
            "values": values,
            "shape": gradients.shape,
            "threshold": threshold,
            "sparsity": 1.0 - (len(values) / gradients.size)
        }
        
        compressed = lz4.frame.compress(pickle.dumps(sparse_data))
        
        metadata = {
            "original_shape": gradients.shape,
            "sparsity_ratio": sparse_data["sparsity"],
            "num_nonzero": len(values)
        }
        
        return compressed, metadata
    
    def desparsify_gradients(self, compressed_data: bytes, metadata: Dict[str, Any]) -> np.ndarray:
        """Reconstruct gradients from sparse representation"""
        # Decompress
        decompressed = lz4.frame.decompress(compressed_data)
        sparse_data = pickle.loads(decompressed)
        
        # Reconstruct dense gradients
        gradients = np.zeros(sparse_data["shape"], dtype=np.float32)
        gradients[sparse_data["indices"]] = sparse_data["values"]
        
        return gradients
    
    def huffman_compress(self, gradients: np.ndarray) -> Tuple[bytes, Dict[str, Any]]:
        """Huffman encoding compression"""
        # Simple approach using zlib (which uses Huffman internally)
        serialized = pickle.dumps(gradients)
        compressed = zlib.compress(serialized, level=9)
        
        metadata = {
            "original_shape": gradients.shape,
            "compression_ratio": len(serialized) / len(compressed)
        }
        
        return compressed, metadata
    
    def huffman_decompress(self, compressed_data: bytes, metadata: Dict[str, Any]) -> np.ndarray:
        """Huffman decoding decompression"""
        decompressed = zlib.decompress(compressed_data)
        return pickle.loads(decompressed)
    
    def advanced_gradient_compression(self, gradients: np.ndarray) -> Tuple[bytes, Dict[str, Any]]:
        """Advanced gradient compression combining multiple techniques"""
        # 1. Error feedback and momentum
        # 2. Top-K sparsification
        # 3. Quantization
        
        # For now, use combination of sparsification and quantization
        # First sparsify
        sparse_compressed, sparse_meta = self.sparsify_gradients(gradients)
        sparse_gradients = self.desparsify_gradients(sparse_compressed, sparse_meta)
        
        # Then quantize the sparse gradients
        final_compressed, quant_meta = self.quantize_gradients(sparse_gradients)
        
        metadata = {
            "original_shape": gradients.shape,
            "sparse_meta": sparse_meta,
            "quant_meta": quant_meta,
            "compression_stages": ["sparsify", "quantize"]
        }
        
        return final_compressed, metadata
    
    def advanced_gradient_decompression(self, compressed_data: bytes, metadata: Dict[str, Any]) -> np.ndarray:
        """Advanced gradient decompression"""
        # Reverse the compression stages
        stages = metadata["compression_stages"]
        
        if "quantize" in stages and "sparsify" in stages:
            # First dequantize
            gradients = self.dequantize_gradients(compressed_data, metadata["quant_meta"])
            # Already sparse, no need to desparsify again
            return gradients
        
        return self.dequantize_gradients(compressed_data, metadata)

class GradientSynchronizer:
    """Main gradient synchronization coordinator"""
    
    def __init__(self, node_id: str = None, config_path: str = None):
        self.node_id = node_id or f"sync-node-{uuid.uuid4().hex[:8]}"
        self.rank = 0
        self.world_size = 1
        
        # Configuration
        self.config = self.load_config(config_path)
        
        # Setup logging
        self.logger = self.setup_logging()
        
        # Node management
        self.nodes: Dict[str, SyncNode] = {}
        self.topology: SyncTopology = SyncTopology.FLAT
        
        # Gradient management
        self.gradient_buffer: Dict[str, List[GradientUpdate]] = {}
        self.pending_syncs: Dict[str, SyncRound] = {}
        self.completed_syncs: List[SyncRound] = []
        
        # Communication backends
        self.redis_client = None
        self.zmq_context = None
        self.zmq_sockets = {}
        self.mpi_comm = None
        
        # Compression
        self.compressor = GradientCompressor()
        
        # Performance tracking
        self.sync_stats = {
            "total_syncs": 0,
            "total_bytes_transferred": 0,
            "average_sync_time_ms": 0.0,
            "compression_ratios": []
        }
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=16)
        self.process_pool = ProcessPoolExecutor(max_workers=mp.cpu_count())
        
        # Event loop
        self.running = False
        self.sync_tasks = []
        
        self.logger.info(f"Gradient Synchronizer initialized: {self.node_id}")
    
    def load_config(self, config_path: str = None) -> Dict:
        """Load synchronizer configuration"""
        default_config = {
            "sync": {
                "strategy": "allreduce",
                "topology": "flat",
                "compression": "quantization",
                "batch_size": 1000000,  # 1M parameters per batch
                "timeout_seconds": 30,
                "max_retries": 3,
                "heartbeat_interval": 5,
            },
            "communication": {
                "backend": "redis",  # redis, zmq, mpi, nccl
                "redis_host": "localhost",
                "redis_port": 6379,
                "zmq_port_base": 5555,
                "buffer_size": 1048576,  # 1MB
                "compression_enabled": True,
            },
            "performance": {
                "gradient_compression": True,
                "async_communication": True,
                "pipeline_parallelism": True,
                "memory_optimization": True,
                "bandwidth_monitoring": True,
            },
            "fault_tolerance": {
                "checkpoint_interval": 300,  # 5 minutes
                "node_failure_timeout": 60,
                "automatic_recovery": True,
                "backup_nodes": 2,
            }
        }
        
        config_file = config_path or f"{SYNC_CONFIG}/gradient_sync.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # Merge configurations
                for section, values in user_config.items():
                    if section in default_config:
                        default_config[section].update(values)
                    else:
                        default_config[section] = values
        else:
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        
        return default_config
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('GradientSynchronizer')
        logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(f"{SYNC_LOGS}/gradient_sync.log")
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
    
    async def initialize(self):
        """Initialize synchronization system"""
        self.logger.info("Initializing gradient synchronization system...")
        
        # Initialize communication backend
        backend = self.config["communication"]["backend"]
        
        if backend == "redis":
            await self.init_redis_backend()
        elif backend == "zmq":
            await self.init_zmq_backend()
        elif backend == "mpi":
            await self.init_mpi_backend()
        elif backend == "nccl":
            await self.init_nccl_backend()
        
        # Start background services
        await self.start_background_services()
        
        self.running = True
        self.logger.info("Gradient synchronization system initialized")
    
    async def init_redis_backend(self):
        """Initialize Redis communication backend"""
        try:
            import redis.asyncio as aioredis
            self.redis_client = aioredis.Redis(
                host=self.config["communication"]["redis_host"],
                port=self.config["communication"]["redis_port"],
                decode_responses=False  # Keep binary data
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis backend initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis backend: {e}")
            raise
    
    async def init_zmq_backend(self):
        """Initialize ZeroMQ communication backend"""
        try:
            import zmq.asyncio
            self.zmq_context = zmq.asyncio.Context()
            
            # Create sockets for different communication patterns
            base_port = self.config["communication"]["zmq_port_base"]
            
            # Publisher socket for broadcasting
            self.zmq_sockets["pub"] = self.zmq_context.socket(zmq.PUB)
            self.zmq_sockets["pub"].bind(f"tcp://*:{base_port}")
            
            # Router socket for point-to-point communication
            self.zmq_sockets["router"] = self.zmq_context.socket(zmq.ROUTER)
            self.zmq_sockets["router"].bind(f"tcp://*:{base_port + 1}")
            
            self.logger.info("ZeroMQ backend initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ZeroMQ backend: {e}")
            raise
    
    async def init_mpi_backend(self):
        """Initialize MPI communication backend"""
        try:
            self.mpi_comm = MPI.COMM_WORLD
            self.rank = self.mpi_comm.Get_rank()
            self.world_size = self.mpi_comm.Get_size()
            
            self.logger.info(f"MPI backend initialized - Rank: {self.rank}/{self.world_size}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MPI backend: {e}")
            raise
    
    async def init_nccl_backend(self):
        """Initialize NCCL backend for GPU communication"""
        try:
            # Initialize PyTorch distributed with NCCL backend
            if not dist.is_initialized():
                dist.init_process_group(backend='nccl', init_method='tcp://localhost:23456')
                self.rank = dist.get_rank()
                self.world_size = dist.get_world_size()
            
            self.logger.info(f"NCCL backend initialized - Rank: {self.rank}/{self.world_size}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NCCL backend: {e}")
            raise
    
    async def start_background_services(self):
        """Start background services"""
        # Heartbeat service
        heartbeat_task = asyncio.create_task(self.heartbeat_service())
        self.sync_tasks.append(heartbeat_task)
        
        # Gradient buffer manager
        buffer_task = asyncio.create_task(self.gradient_buffer_manager())
        self.sync_tasks.append(buffer_task)
        
        # Performance monitor
        perf_task = asyncio.create_task(self.performance_monitor())
        self.sync_tasks.append(perf_task)
        
        # Failure detector
        failure_task = asyncio.create_task(self.failure_detector())
        self.sync_tasks.append(failure_task)
    
    async def register_node(self, node_info: Dict[str, Any]) -> str:
        """Register a node for gradient synchronization"""
        node_id = node_info.get("node_id") or f"node-{uuid.uuid4().hex[:8]}"
        
        node = SyncNode(
            node_id=node_id,
            ip_address=node_info.get("ip_address", "unknown"),
            port=node_info.get("port", 8080),
            rank=len(self.nodes),
            world_size=len(self.nodes) + 1,
            device_type=node_info.get("device_type", "cpu"),
            compute_capability=node_info.get("compute_capability", 1.0),
            bandwidth_mbps=node_info.get("bandwidth_mbps", 100.0),
            latency_ms=node_info.get("latency_ms", 10.0),
            last_sync=datetime.now().isoformat(),
            gradient_buffer_size=node_info.get("buffer_size", 1000),
            is_coordinator=node_info.get("is_coordinator", False)
        )
        
        self.nodes[node_id] = node
        
        # Update world size for all nodes
        for existing_node in self.nodes.values():
            existing_node.world_size = len(self.nodes)
        
        self.logger.info(f"Registered sync node: {node_id} (rank {node.rank})")
        return node_id
    
    async def submit_gradients(self, 
                             node_id: str,
                             model_name: str,
                             layer_name: str,
                             gradients: np.ndarray,
                             metadata: Dict[str, Any] = None) -> str:
        """Submit gradients for synchronization"""
        
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not registered")
        
        # Create gradient update
        update_id = f"grad-{uuid.uuid4().hex[:8]}"
        
        # Compress gradients if enabled
        compressed = self.config["communication"]["compression_enabled"]
        compression_method = CompressionType(self.config["sync"]["compression"])
        
        if compressed:
            compressed_data, comp_metadata = self.compressor.compress_gradients(
                gradients, compression_method
            )
            # Calculate checksum of compressed data
            checksum = hashlib.sha256(compressed_data).hexdigest()
            gradient_data = compressed_data
            comp_ratio = len(pickle.dumps(gradients)) / len(compressed_data)
        else:
            gradient_data = gradients
            checksum = hashlib.sha256(pickle.dumps(gradients)).hexdigest()
            comp_metadata = {}
            comp_ratio = 1.0
        
        update = GradientUpdate(
            update_id=update_id,
            node_id=node_id,
            model_name=model_name,
            layer_name=layer_name,
            gradients=gradient_data,
            metadata={**(metadata or {}), **comp_metadata},
            timestamp=datetime.now().isoformat(),
            sequence_number=self.get_next_sequence_number(node_id),
            checksum=checksum,
            compressed=compressed,
            compression_ratio=comp_ratio
        )
        
        # Add to buffer
        buffer_key = f"{model_name}_{layer_name}"
        if buffer_key not in self.gradient_buffer:
            self.gradient_buffer[buffer_key] = []
        
        self.gradient_buffer[buffer_key].append(update)
        
        # Update stats
        self.sync_stats["compression_ratios"].append(comp_ratio)
        
        self.logger.debug(f"Submitted gradients from {node_id} for {model_name}:{layer_name}")
        
        # Check if ready for synchronization
        await self.check_sync_readiness(buffer_key)
        
        return update_id
    
    def get_next_sequence_number(self, node_id: str) -> int:
        """Get next sequence number for node"""
        # Simple implementation - in practice, maintain per-node counters
        return int(time.time() * 1000) % 1000000
    
    async def check_sync_readiness(self, buffer_key: str):
        """Check if buffer is ready for synchronization"""
        updates = self.gradient_buffer.get(buffer_key, [])
        
        # Check if we have updates from enough nodes
        participating_nodes = set(update.node_id for update in updates)
        min_nodes = max(1, len(self.nodes) // 2)  # At least half the nodes
        
        if len(participating_nodes) >= min_nodes:
            await self.trigger_synchronization(buffer_key)
    
    async def trigger_synchronization(self, buffer_key: str):
        """Trigger gradient synchronization"""
        updates = self.gradient_buffer[buffer_key]
        if not updates:
            return
        
        # Create sync round
        round_id = f"sync-{uuid.uuid4().hex[:8]}"
        model_name, layer_name = buffer_key.split("_", 1)
        
        participating_nodes = list(set(update.node_id for update in updates))
        strategy = SyncStrategy(self.config["sync"]["strategy"])
        topology = SyncTopology(self.config["sync"]["topology"])
        compression = CompressionType(self.config["sync"]["compression"])
        
        sync_round = SyncRound(
            round_id=round_id,
            model_name=f"{model_name}_{layer_name}",
            participating_nodes=participating_nodes,
            strategy=strategy,
            topology=topology,
            compression=compression,
            start_time=datetime.now().isoformat(),
            total_gradients=len(updates)
        )
        
        self.pending_syncs[round_id] = sync_round
        
        self.logger.info(f"Starting sync round {round_id} with {len(participating_nodes)} nodes")
        
        # Perform synchronization based on strategy
        try:
            start_time = time.time()
            
            if strategy == SyncStrategy.ALLREDUCE:
                aggregated_gradients = await self.allreduce_synchronization(updates)
            elif strategy == SyncStrategy.PARAMETER_SERVER:
                aggregated_gradients = await self.parameter_server_synchronization(updates)
            elif strategy == SyncStrategy.RING_ALLREDUCE:
                aggregated_gradients = await self.ring_allreduce_synchronization(updates)
            else:
                aggregated_gradients = await self.allreduce_synchronization(updates)
            
            sync_time = (time.time() - start_time) * 1000  # milliseconds
            
            # Complete sync round
            sync_round.end_time = datetime.now().isoformat()
            sync_round.sync_time_ms = sync_time
            sync_round.bytes_transferred = sum(
                len(pickle.dumps(update.gradients)) for update in updates
            )
            
            # Move to completed
            self.completed_syncs.append(sync_round)
            del self.pending_syncs[round_id]
            
            # Clear buffer
            self.gradient_buffer[buffer_key] = []
            
            # Update statistics
            self.update_sync_statistics(sync_round)
            
            # Broadcast aggregated gradients
            await self.broadcast_aggregated_gradients(
                round_id, model_name, layer_name, aggregated_gradients, participating_nodes
            )
            
            self.logger.info(f"Completed sync round {round_id} in {sync_time:.2f}ms")
            
        except Exception as e:
            self.logger.error(f"Synchronization failed for round {round_id}: {e}")
            # Handle failure - could implement retry logic here
    
    async def allreduce_synchronization(self, updates: List[GradientUpdate]) -> np.ndarray:
        """AllReduce gradient synchronization"""
        # Decompress gradients if needed
        gradients_list = []
        for update in updates:
            if update.compressed:
                compression_method = CompressionType(self.config["sync"]["compression"])
                gradients = self.compressor.decompress_gradients(
                    update.gradients, update.metadata, compression_method
                )
            else:
                gradients = update.gradients
            
            gradients_list.append(gradients)
        
        # Average all gradients
        if gradients_list:
            stacked = np.stack(gradients_list, axis=0)
            return np.mean(stacked, axis=0)
        
        return np.array([])
    
    async def parameter_server_synchronization(self, updates: List[GradientUpdate]) -> np.ndarray:
        """Parameter server synchronization"""
        # In parameter server mode, one node acts as the server
        coordinator_node = None
        for node_id in updates[0].node_id:  # Get a node ID from updates
            if self.nodes[node_id].is_coordinator:
                coordinator_node = node_id
                break
        
        if not coordinator_node:
            # Use first node as coordinator
            coordinator_node = updates[0].node_id
        
        # Coordinator aggregates gradients
        if self.node_id == coordinator_node:
            return await self.allreduce_synchronization(updates)
        else:
            # Non-coordinator nodes wait for aggregated result
            # This would involve more complex communication in real implementation
            return await self.allreduce_synchronization(updates)
    
    async def ring_allreduce_synchronization(self, updates: List[GradientUpdate]) -> np.ndarray:
        """Ring AllReduce synchronization"""
        # Simplified ring allreduce - in practice, this would implement
        # the actual ring topology with proper scatter-reduce and all-gather phases
        
        # For now, fallback to standard allreduce
        return await self.allreduce_synchronization(updates)
    
    async def broadcast_aggregated_gradients(self, 
                                           round_id: str,
                                           model_name: str,
                                           layer_name: str,
                                           aggregated_gradients: np.ndarray,
                                           participating_nodes: List[str]):
        """Broadcast aggregated gradients to all participating nodes"""
        
        # Compress aggregated gradients
        compression_method = CompressionType(self.config["sync"]["compression"])
        compressed_data, metadata = self.compressor.compress_gradients(
            aggregated_gradients, compression_method
        )
        
        broadcast_message = {
            "type": "aggregated_gradients",
            "round_id": round_id,
            "model_name": model_name,
            "layer_name": layer_name,
            "gradients": compressed_data.hex(),  # Convert to hex for JSON serialization
            "metadata": metadata,
            "compression": compression_method.value,
            "timestamp": datetime.now().isoformat(),
            "participating_nodes": participating_nodes
        }
        
        # Broadcast using configured backend
        backend = self.config["communication"]["backend"]
        
        if backend == "redis" and self.redis_client:
            await self.redis_broadcast(broadcast_message)
        elif backend == "zmq" and self.zmq_sockets.get("pub"):
            await self.zmq_broadcast(broadcast_message)
        
        self.logger.info(f"Broadcasted aggregated gradients for round {round_id}")
    
    async def redis_broadcast(self, message: Dict[str, Any]):
        """Broadcast message via Redis"""
        try:
            channel = "qenex_gradient_sync"
            message_json = json.dumps(message)
            await self.redis_client.publish(channel, message_json)
        except Exception as e:
            self.logger.error(f"Redis broadcast failed: {e}")
    
    async def zmq_broadcast(self, message: Dict[str, Any]):
        """Broadcast message via ZeroMQ"""
        try:
            topic = "gradient_sync"
            message_json = json.dumps(message)
            await self.zmq_sockets["pub"].send_multipart([
                topic.encode(), message_json.encode()
            ])
        except Exception as e:
            self.logger.error(f"ZeroMQ broadcast failed: {e}")
    
    def update_sync_statistics(self, sync_round: SyncRound):
        """Update synchronization statistics"""
        self.sync_stats["total_syncs"] += 1
        self.sync_stats["total_bytes_transferred"] += sync_round.bytes_transferred
        
        # Update average sync time
        total_time = (self.sync_stats["average_sync_time_ms"] * 
                     (self.sync_stats["total_syncs"] - 1) + sync_round.sync_time_ms)
        self.sync_stats["average_sync_time_ms"] = total_time / self.sync_stats["total_syncs"]
    
    async def heartbeat_service(self):
        """Background heartbeat service"""
        interval = self.config["sync"]["heartbeat_interval"]
        
        while self.running:
            try:
                # Send heartbeat to all nodes
                heartbeat = {
                    "type": "heartbeat",
                    "node_id": self.node_id,
                    "timestamp": datetime.now().isoformat(),
                    "status": "active",
                    "pending_syncs": len(self.pending_syncs),
                    "buffer_size": sum(len(updates) for updates in self.gradient_buffer.values())
                }
                
                # Broadcast heartbeat
                if self.config["communication"]["backend"] == "redis" and self.redis_client:
                    await self.redis_client.publish("qenex_heartbeat", json.dumps(heartbeat))
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Heartbeat service error: {e}")
                await asyncio.sleep(interval)
    
    async def gradient_buffer_manager(self):
        """Background gradient buffer management"""
        while self.running:
            try:
                # Clean up old gradient updates
                cutoff_time = datetime.now() - timedelta(minutes=5)
                
                for buffer_key in list(self.gradient_buffer.keys()):
                    updates = self.gradient_buffer[buffer_key]
                    
                    # Remove old updates
                    fresh_updates = [
                        update for update in updates
                        if datetime.fromisoformat(update.timestamp) > cutoff_time
                    ]
                    
                    self.gradient_buffer[buffer_key] = fresh_updates
                
                # Save buffer checkpoint
                if datetime.now().minute % 5 == 0:  # Every 5 minutes
                    await self.save_buffer_checkpoint()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Buffer manager error: {e}")
                await asyncio.sleep(60)
    
    async def performance_monitor(self):
        """Background performance monitoring"""
        while self.running:
            try:
                # Collect performance metrics
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "node_id": self.node_id,
                    "sync_stats": self.sync_stats.copy(),
                    "active_nodes": len(self.nodes),
                    "pending_syncs": len(self.pending_syncs),
                    "buffer_sizes": {
                        key: len(updates) for key, updates in self.gradient_buffer.items()
                    },
                    "memory_usage": {
                        "buffer_mb": sum(
                            len(pickle.dumps(update)) for updates in self.gradient_buffer.values()
                            for update in updates
                        ) / 1024 / 1024,
                        "system_mb": psutil.virtual_memory().used / 1024 / 1024
                    }
                }
                
                # Save metrics
                metrics_file = f"{SYNC_LOGS}/performance_metrics_{datetime.now().strftime('%Y%m%d')}.json"
                with open(metrics_file, 'a') as f:
                    json.dump(metrics, f)
                    f.write('\n')
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                self.logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(300)
    
    async def failure_detector(self):
        """Background failure detection"""
        timeout_seconds = self.config["fault_tolerance"]["node_failure_timeout"]
        
        while self.running:
            try:
                current_time = datetime.now()
                failed_nodes = []
                
                for node_id, node in self.nodes.items():
                    last_sync = datetime.fromisoformat(node.last_sync)
                    if (current_time - last_sync).seconds > timeout_seconds:
                        failed_nodes.append(node_id)
                
                # Handle failed nodes
                for node_id in failed_nodes:
                    await self.handle_node_failure(node_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Failure detector error: {e}")
                await asyncio.sleep(60)
    
    async def handle_node_failure(self, node_id: str):
        """Handle node failure"""
        self.logger.warning(f"Node failure detected: {node_id}")
        
        # Remove from active nodes
        if node_id in self.nodes:
            del self.nodes[node_id]
        
        # Update world size for remaining nodes
        for node in self.nodes.values():
            node.world_size = len(self.nodes)
        
        # Clean up pending syncs involving the failed node
        failed_syncs = []
        for round_id, sync_round in self.pending_syncs.items():
            if node_id in sync_round.participating_nodes:
                sync_round.participating_nodes.remove(node_id)
                
                # If not enough nodes left, cancel sync
                if len(sync_round.participating_nodes) < 2:
                    failed_syncs.append(round_id)
        
        for round_id in failed_syncs:
            del self.pending_syncs[round_id]
            self.logger.warning(f"Cancelled sync round {round_id} due to insufficient nodes")
    
    async def save_buffer_checkpoint(self):
        """Save gradient buffer checkpoint"""
        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "node_id": self.node_id,
            "gradient_buffer": {
                key: [asdict(update) for update in updates]
                for key, updates in self.gradient_buffer.items()
            },
            "nodes": {node_id: asdict(node) for node_id, node in self.nodes.items()},
            "sync_stats": self.sync_stats
        }
        
        checkpoint_file = f"{SYNC_CHECKPOINTS}/buffer_checkpoint_{int(time.time())}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
        
        self.logger.debug(f"Saved buffer checkpoint: {checkpoint_file}")
        
        # Cleanup old checkpoints
        await self.cleanup_old_checkpoints()
    
    async def cleanup_old_checkpoints(self):
        """Clean up old checkpoint files"""
        checkpoint_files = sorted(
            Path(SYNC_CHECKPOINTS).glob("buffer_checkpoint_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Keep only the 5 most recent checkpoints
        for old_checkpoint in checkpoint_files[5:]:
            old_checkpoint.unlink()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get gradient synchronization system status"""
        return {
            "node_id": self.node_id,
            "rank": self.rank,
            "world_size": self.world_size,
            "running": self.running,
            "nodes": {
                "total": len(self.nodes),
                "active": len([n for n in self.nodes.values() 
                              if (datetime.now() - datetime.fromisoformat(n.last_sync)).seconds < 60]),
                "coordinators": len([n for n in self.nodes.values() if n.is_coordinator])
            },
            "synchronization": {
                "pending_rounds": len(self.pending_syncs),
                "completed_rounds": len(self.completed_syncs),
                "total_gradients_in_buffer": sum(len(updates) for updates in self.gradient_buffer.values()),
                "sync_statistics": self.sync_stats
            },
            "performance": {
                "average_compression_ratio": np.mean(self.sync_stats["compression_ratios"]) if self.sync_stats["compression_ratios"] else 1.0,
                "communication_backend": self.config["communication"]["backend"],
                "topology": self.topology.value
            }
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down gradient synchronization system...")
        
        self.running = False
        
        # Cancel background tasks
        for task in self.sync_tasks:
            task.cancel()
        
        # Close communication backends
        if self.redis_client:
            await self.redis_client.close()
        
        if self.zmq_context:
            self.zmq_context.destroy()
        
        # Save final checkpoint
        await self.save_buffer_checkpoint()
        
        # Shutdown thread pools
        self.executor.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        self.logger.info("Gradient synchronization system shutdown complete")

async def main():
    """Main entry point"""
    synchronizer = GradientSynchronizer()
    
    try:
        await synchronizer.initialize()
        
        # Example usage - register some nodes and simulate gradient synchronization
        for i in range(3):
            await synchronizer.register_node({
                "node_id": f"qenex-node-{i}",
                "ip_address": f"192.168.1.{100+i}",
                "port": 8080,
                "device_type": "cuda" if i == 0 else "cpu",
                "compute_capability": 2.0,
                "bandwidth_mbps": 1000.0,
                "latency_ms": 5.0,
                "buffer_size": 5000,
                "is_coordinator": i == 0
            })
        
        # Simulate gradient submissions
        for i in range(3):
            gradients = np.random.normal(0, 1, (1000, 512))
            await synchronizer.submit_gradients(
                f"qenex-node-{i}",
                "security_model",
                "dense_layer_1",
                gradients,
                {"accuracy": 0.85 + i * 0.02, "loss": 0.3 - i * 0.01}
            )
        
        # Get status
        status = await synchronizer.get_system_status()
        print("System Status:", json.dumps(status, indent=2))
        
        # Keep running for a while to see synchronization
        await asyncio.sleep(10)
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    finally:
        await synchronizer.shutdown()

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║              QENEX Gradient Synchronization               ║
║                High-Performance Distributed Sync          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    import os
    asyncio.run(main())