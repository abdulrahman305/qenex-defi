#!/usr/bin/env python3
"""
QENEX Zero-Downtime Model Update System
Real-time model updates without service interruption
"""

import asyncio
import json
import pickle
import hashlib
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import queue
import socket
import tempfile
import shutil
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
import psutil
import numpy as np
import aiohttp
import websockets
import redis.asyncio as aioredis

# Configuration
UPDATER_ROOT = "/opt/qenex-os/distributed-training/zero-downtime"
UPDATE_QUEUE = f"{UPDATER_ROOT}/queue"
STAGING_AREA = f"{UPDATER_ROOT}/staging"
ACTIVE_MODELS = f"{UPDATER_ROOT}/active"
BACKUP_MODELS = f"{UPDATER_ROOT}/backup"
UPDATE_LOGS = f"{UPDATER_ROOT}/logs"
CONFIG_DIR = f"{UPDATER_ROOT}/config"

# Create directories
for directory in [UPDATER_ROOT, UPDATE_QUEUE, STAGING_AREA, ACTIVE_MODELS, BACKUP_MODELS, UPDATE_LOGS, CONFIG_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class UpdateStatus(Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    STAGING = "staging"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    SWITCHING = "switching"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"

class UpdateStrategy(Enum):
    HOT_SWAP = "hot_swap"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    STAGED = "staged"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ModelUpdate:
    update_id: str
    model_name: str
    current_version: str
    target_version: str
    strategy: UpdateStrategy
    priority: int
    created_time: str
    scheduled_time: Optional[str] = None
    started_time: Optional[str] = None
    completed_time: Optional[str] = None
    status: UpdateStatus = UpdateStatus.QUEUED
    progress_percentage: float = 0.0
    affected_nodes: List[str] = None
    rollback_version: Optional[str] = None
    metadata: Dict[str, Any] = None
    health_checks: Dict[str, bool] = None

@dataclass
class NodeState:
    node_id: str
    model_name: str
    active_version: str
    staging_version: Optional[str]
    health_status: HealthStatus
    last_health_check: str
    update_in_progress: bool
    load_balancer_weight: float
    performance_metrics: Dict[str, float]

@dataclass
class LoadBalancerRule:
    rule_id: str
    model_name: str
    version: str
    weight: float
    active: bool
    created_time: str
    metadata: Dict[str, Any] = None

class HealthChecker:
    """Health checking and monitoring system"""
    
    def __init__(self, updater):
        self.updater = updater
        self.logger = updater.logger
        self.health_check_interval = 10  # seconds
        self.health_timeout = 5  # seconds
    
    async def check_node_health(self, node_id: str, model_name: str) -> Tuple[HealthStatus, Dict[str, Any]]:
        """Check health of a specific node"""
        try:
            # Simulate health check - in practice, this would call node API
            node_url = f"http://{node_id}:8080/health"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(node_url, timeout=aiohttp.ClientTimeout(total=self.health_timeout)) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            
                            # Evaluate health metrics
                            cpu_usage = health_data.get('cpu_usage', 0)
                            memory_usage = health_data.get('memory_usage', 0)
                            error_rate = health_data.get('error_rate', 0)
                            response_time = health_data.get('avg_response_time', 0)
                            
                            # Determine health status
                            if (cpu_usage > 90 or memory_usage > 90 or 
                                error_rate > 5 or response_time > 1000):
                                status = HealthStatus.UNHEALTHY
                            elif (cpu_usage > 80 or memory_usage > 80 or 
                                  error_rate > 2 or response_time > 500):
                                status = HealthStatus.DEGRADED
                            else:
                                status = HealthStatus.HEALTHY
                            
                            return status, health_data
                        else:
                            return HealthStatus.UNHEALTHY, {"error": f"HTTP {response.status}"}
                            
                except asyncio.TimeoutError:
                    return HealthStatus.UNHEALTHY, {"error": "Health check timeout"}
                except Exception as e:
                    return HealthStatus.UNHEALTHY, {"error": str(e)}
                    
        except Exception as e:
            self.logger.error(f"Health check failed for {node_id}: {e}")
            return HealthStatus.UNKNOWN, {"error": str(e)}
    
    async def perform_model_validation(self, node_id: str, model_name: str, version: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate model performance on a node"""
        try:
            # Simulate model validation
            validation_url = f"http://{node_id}:8080/validate/{model_name}/{version}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(validation_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        validation_data = await response.json()
                        
                        accuracy = validation_data.get('accuracy', 0)
                        latency = validation_data.get('avg_latency', 1000)
                        error_rate = validation_data.get('error_rate', 100)
                        
                        # Validation criteria
                        is_valid = (
                            accuracy >= 0.8 and 
                            latency <= 500 and 
                            error_rate <= 2.0
                        )
                        
                        return is_valid, validation_data
                    else:
                        return False, {"error": f"Validation failed with HTTP {response.status}"}
                        
        except Exception as e:
            self.logger.error(f"Model validation failed for {node_id}: {e}")
            return False, {"error": str(e)}
    
    async def run_smoke_tests(self, node_id: str, model_name: str, version: str) -> Tuple[bool, Dict[str, Any]]:
        """Run smoke tests on deployed model"""
        try:
            test_cases = [
                {"input": "test_case_1", "expected_type": "classification"},
                {"input": "test_case_2", "expected_type": "detection"},
                {"input": "test_case_3", "expected_type": "prediction"}
            ]
            
            results = {"passed": 0, "failed": 0, "details": []}
            
            for i, test_case in enumerate(test_cases):
                test_url = f"http://{node_id}:8080/predict/{model_name}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(test_url, json=test_case) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get('status') == 'success':
                                results["passed"] += 1
                                results["details"].append(f"Test {i+1}: PASSED")
                            else:
                                results["failed"] += 1
                                results["details"].append(f"Test {i+1}: FAILED - {result.get('error', 'Unknown error')}")
                        else:
                            results["failed"] += 1
                            results["details"].append(f"Test {i+1}: FAILED - HTTP {response.status}")
            
            success_rate = results["passed"] / len(test_cases)
            return success_rate >= 0.8, results
            
        except Exception as e:
            return False, {"error": str(e), "details": []}

class LoadBalancer:
    """Load balancer integration for zero-downtime updates"""
    
    def __init__(self, updater):
        self.updater = updater
        self.logger = updater.logger
        self.rules: Dict[str, LoadBalancerRule] = {}
        self.redis_client = None
    
    async def initialize(self):
        """Initialize load balancer connection"""
        try:
            self.redis_client = aioredis.Redis(host='localhost', port=6379)
            await self.redis_client.ping()
            self.logger.info("Load balancer Redis connection established")
        except Exception as e:
            self.logger.warning(f"Load balancer Redis connection failed: {e}")
    
    async def create_traffic_rule(self, model_name: str, version: str, weight: float) -> str:
        """Create traffic routing rule"""
        rule_id = f"rule-{uuid.uuid4().hex[:8]}"
        
        rule = LoadBalancerRule(
            rule_id=rule_id,
            model_name=model_name,
            version=version,
            weight=weight,
            active=False,
            created_time=datetime.now().isoformat()
        )
        
        self.rules[rule_id] = rule
        
        # Update load balancer configuration
        await self.update_load_balancer_config()
        
        self.logger.info(f"Created traffic rule {rule_id}: {model_name} v{version} weight={weight}")
        return rule_id
    
    async def activate_traffic_rule(self, rule_id: str):
        """Activate traffic routing rule"""
        if rule_id in self.rules:
            self.rules[rule_id].active = True
            await self.update_load_balancer_config()
            self.logger.info(f"Activated traffic rule {rule_id}")
    
    async def deactivate_traffic_rule(self, rule_id: str):
        """Deactivate traffic routing rule"""
        if rule_id in self.rules:
            self.rules[rule_id].active = False
            await self.update_load_balancer_config()
            self.logger.info(f"Deactivated traffic rule {rule_id}")
    
    async def update_rule_weight(self, rule_id: str, weight: float):
        """Update traffic weight for a rule"""
        if rule_id in self.rules:
            self.rules[rule_id].weight = weight
            await self.update_load_balancer_config()
            self.logger.info(f"Updated rule {rule_id} weight to {weight}")
    
    async def update_load_balancer_config(self):
        """Update load balancer configuration"""
        if not self.redis_client:
            return
        
        try:
            # Build configuration for each model
            config = {}
            
            for rule in self.rules.values():
                if rule.active:
                    model_key = f"model:{rule.model_name}"
                    if model_key not in config:
                        config[model_key] = {"versions": {}}
                    
                    config[model_key]["versions"][rule.version] = {
                        "weight": rule.weight,
                        "rule_id": rule.rule_id
                    }
            
            # Update Redis configuration
            for model_key, model_config in config.items():
                await self.redis_client.set(model_key, json.dumps(model_config))
            
            self.logger.debug(f"Updated load balancer configuration for {len(config)} models")
            
        except Exception as e:
            self.logger.error(f"Failed to update load balancer config: {e}")
    
    async def gradual_traffic_shift(self, model_name: str, from_version: str, to_version: str, duration_minutes: int = 10):
        """Gradually shift traffic from one version to another"""
        steps = 20  # Number of gradual steps
        step_duration = (duration_minutes * 60) / steps
        
        # Find existing rules
        from_rule = None
        to_rule = None
        
        for rule in self.rules.values():
            if rule.model_name == model_name and rule.version == from_version:
                from_rule = rule
            elif rule.model_name == model_name and rule.version == to_version:
                to_rule = rule
        
        if not from_rule or not to_rule:
            raise ValueError("Cannot find traffic rules for version shift")
        
        self.logger.info(f"Starting gradual traffic shift: {from_version} -> {to_version} over {duration_minutes} minutes")
        
        for step in range(steps + 1):
            progress = step / steps
            
            # Calculate weights
            from_weight = 100 * (1 - progress)
            to_weight = 100 * progress
            
            # Update weights
            await self.update_rule_weight(from_rule.rule_id, from_weight)
            await self.update_rule_weight(to_rule.rule_id, to_weight)
            
            self.logger.info(f"Traffic shift step {step}/{steps}: {from_version}={from_weight:.1f}% {to_version}={to_weight:.1f}%")
            
            if step < steps:
                await asyncio.sleep(step_duration)
        
        # Deactivate old version rule
        await self.deactivate_traffic_rule(from_rule.rule_id)
        
        self.logger.info(f"Traffic shift completed: 100% traffic now on {to_version}")

class ZeroDowntimeUpdater:
    """Main zero-downtime model update system"""
    
    def __init__(self, updater_id: str = None):
        self.updater_id = updater_id or f"updater-{uuid.uuid4().hex[:8]}"
        
        # Configuration
        self.config = self.load_config()
        
        # Setup logging
        self.logger = self.setup_logging()
        
        # Component initialization
        self.health_checker = HealthChecker(self)
        self.load_balancer = LoadBalancer(self)
        
        # State management
        self.update_queue = asyncio.PriorityQueue()
        self.active_updates: Dict[str, ModelUpdate] = {}
        self.node_states: Dict[str, NodeState] = {}
        
        # Update history
        self.completed_updates: List[ModelUpdate] = []
        self.failed_updates: List[ModelUpdate] = []
        
        # Redis for coordination
        self.redis_client = None
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=12)
        self.process_pool = ProcessPoolExecutor(max_workers=4)
        
        # Background services
        self.running = False
        self.background_tasks = []
        
        # Update callbacks
        self.update_callbacks: Dict[str, List[Callable]] = {
            'pre_update': [],
            'post_update': [],
            'rollback': [],
            'failure': []
        }
        
        self.logger.info(f"Zero-Downtime Updater initialized: {self.updater_id}")
    
    def load_config(self) -> Dict:
        """Load updater configuration"""
        default_config = {
            "updater": {
                "max_concurrent_updates": 3,
                "update_timeout_minutes": 30,
                "health_check_interval": 10,
                "validation_timeout_minutes": 5,
                "rollback_timeout_minutes": 5,
                "default_strategy": "hot_swap",
            },
            "strategies": {
                "hot_swap": {
                    "enabled": True,
                    "validation_required": True,
                    "smoke_tests_required": True,
                    "health_check_threshold": 3,
                },
                "blue_green": {
                    "enabled": True,
                    "traffic_shift_duration": 10,
                    "validation_duration": 5,
                    "rollback_threshold": 0.95,
                },
                "canary": {
                    "enabled": True,
                    "canary_percentage": 10.0,
                    "canary_duration": 15,
                    "success_threshold": 0.98,
                },
                "rolling": {
                    "enabled": True,
                    "batch_size": 2,
                    "batch_delay_seconds": 30,
                    "failure_threshold": 0.1,
                },
            },
            "health_checks": {
                "enabled": True,
                "interval_seconds": 10,
                "timeout_seconds": 5,
                "failure_threshold": 3,
                "recovery_threshold": 2,
            },
            "load_balancer": {
                "enabled": True,
                "redis_host": "localhost",
                "redis_port": 6379,
                "gradual_shift": True,
                "shift_duration_minutes": 10,
            },
            "monitoring": {
                "metrics_retention_hours": 24,
                "alert_on_failure": True,
                "performance_tracking": True,
            }
        }
        
        config_file = f"{CONFIG_DIR}/zero_downtime.json"
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
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
        
        return default_config
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('ZeroDowntimeUpdater')
        logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(f"{UPDATE_LOGS}/zero_downtime.log")
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
        """Start the zero-downtime updater"""
        self.running = True
        
        # Initialize Redis
        try:
            self.redis_client = aioredis.Redis(
                host=self.config["load_balancer"]["redis_host"],
                port=self.config["load_balancer"]["redis_port"]
            )
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}")
        
        # Initialize load balancer
        await self.load_balancer.initialize()
        
        # Start background services
        self.background_tasks = [
            asyncio.create_task(self.update_processor()),
            asyncio.create_task(self.health_monitor()),
            asyncio.create_task(self.node_state_monitor()),
            asyncio.create_task(self.cleanup_service()),
            asyncio.create_task(self.metrics_collector())
        ]
        
        self.logger.info("Zero-downtime updater started")
    
    async def schedule_model_update(self, 
                                  model_name: str,
                                  target_version: str,
                                  nodes: List[str],
                                  strategy: UpdateStrategy = None,
                                  priority: int = 1,
                                  scheduled_time: str = None,
                                  metadata: Dict[str, Any] = None) -> str:
        """Schedule a model update"""
        
        update_id = f"update-{uuid.uuid4().hex[:8]}"
        
        # Get current version from first node (assuming all nodes have same version)
        current_version = "unknown"
        if nodes and nodes[0] in self.node_states:
            current_version = self.node_states[nodes[0]].active_version
        
        update = ModelUpdate(
            update_id=update_id,
            model_name=model_name,
            current_version=current_version,
            target_version=target_version,
            strategy=strategy or UpdateStrategy(self.config["updater"]["default_strategy"]),
            priority=priority,
            created_time=datetime.now().isoformat(),
            scheduled_time=scheduled_time,
            affected_nodes=nodes,
            metadata=metadata or {},
            health_checks={}
        )
        
        # Add to queue (priority queue sorts by priority)
        await self.update_queue.put((-priority, update))  # Negative for highest priority first
        
        self.logger.info(f"Scheduled model update {update_id}: {model_name} -> {target_version} "
                        f"using {update.strategy.value} strategy")
        
        return update_id
    
    async def update_processor(self):
        """Background update processing service"""
        max_concurrent = self.config["updater"]["max_concurrent_updates"]
        
        while self.running:
            try:
                # Check if we can process more updates
                if len(self.active_updates) >= max_concurrent:
                    await asyncio.sleep(5)
                    continue
                
                # Get next update from queue
                try:
                    priority, update = await asyncio.wait_for(self.update_queue.get(), timeout=5.0)
                    
                    # Check if scheduled for future
                    if update.scheduled_time:
                        scheduled_dt = datetime.fromisoformat(update.scheduled_time)
                        if scheduled_dt > datetime.now():
                            # Put back in queue and wait
                            await self.update_queue.put((priority, update))
                            await asyncio.sleep(60)  # Check again in 1 minute
                            continue
                    
                    # Process update
                    update.status = UpdateStatus.PREPARING
                    update.started_time = datetime.now().isoformat()
                    self.active_updates[update.update_id] = update
                    
                    # Process asynchronously
                    asyncio.create_task(self.process_single_update(update))
                    
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                self.logger.error(f"Update processor error: {e}")
                await asyncio.sleep(30)
    
    async def process_single_update(self, update: ModelUpdate):
        """Process a single model update"""
        try:
            self.logger.info(f"Processing update {update.update_id}: {update.model_name} "
                           f"{update.current_version} -> {update.target_version}")
            
            # Execute pre-update callbacks
            await self.execute_callbacks('pre_update', update)
            
            # Execute update based on strategy
            if update.strategy == UpdateStrategy.HOT_SWAP:
                await self.hot_swap_update(update)
            elif update.strategy == UpdateStrategy.BLUE_GREEN:
                await self.blue_green_update(update)
            elif update.strategy == UpdateStrategy.CANARY:
                await self.canary_update(update)
            elif update.strategy == UpdateStrategy.ROLLING:
                await self.rolling_update(update)
            elif update.strategy == UpdateStrategy.STAGED:
                await self.staged_update(update)
            else:
                raise ValueError(f"Unknown update strategy: {update.strategy}")
            
            # Mark as completed
            update.status = UpdateStatus.COMPLETED
            update.completed_time = datetime.now().isoformat()
            update.progress_percentage = 100.0
            
            # Execute post-update callbacks
            await self.execute_callbacks('post_update', update)
            
            # Move to completed list
            self.completed_updates.append(update)
            del self.active_updates[update.update_id]
            
            self.logger.info(f"Update {update.update_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Update {update.update_id} failed: {e}")
            
            update.status = UpdateStatus.FAILED
            update.completed_time = datetime.now().isoformat()
            
            # Execute failure callbacks
            await self.execute_callbacks('failure', update)
            
            # Attempt rollback
            try:
                await self.rollback_update(update)
            except Exception as rollback_error:
                self.logger.error(f"Rollback failed for update {update.update_id}: {rollback_error}")
            
            # Move to failed list
            self.failed_updates.append(update)
            del self.active_updates[update.update_id]
    
    async def hot_swap_update(self, update: ModelUpdate):
        """Hot swap update strategy - fastest with minimal validation"""
        self.logger.info(f"Executing hot swap update for {update.update_id}")
        
        update.status = UpdateStatus.STAGING
        update.progress_percentage = 10.0
        
        # Stage new model on all nodes
        for node_id in update.affected_nodes:
            await self.stage_model_on_node(node_id, update.model_name, update.target_version)
            update.progress_percentage += 30.0 / len(update.affected_nodes)
        
        update.status = UpdateStatus.VALIDATING
        
        # Quick validation
        if self.config["strategies"]["hot_swap"]["validation_required"]:
            for node_id in update.affected_nodes:
                is_valid, validation_data = await self.health_checker.perform_model_validation(
                    node_id, update.model_name, update.target_version
                )
                
                if not is_valid:
                    raise Exception(f"Model validation failed on {node_id}: {validation_data}")
                
                update.progress_percentage += 20.0 / len(update.affected_nodes)
        
        update.status = UpdateStatus.SWITCHING
        
        # Atomic swap
        for node_id in update.affected_nodes:
            await self.swap_model_on_node(node_id, update.model_name, update.target_version)
            update.progress_percentage += 30.0 / len(update.affected_nodes)
        
        update.status = UpdateStatus.VERIFYING
        
        # Smoke tests
        if self.config["strategies"]["hot_swap"]["smoke_tests_required"]:
            for node_id in update.affected_nodes:
                success, test_results = await self.health_checker.run_smoke_tests(
                    node_id, update.model_name, update.target_version
                )
                
                if not success:
                    raise Exception(f"Smoke tests failed on {node_id}: {test_results}")
                
                update.progress_percentage += 10.0 / len(update.affected_nodes)
    
    async def blue_green_update(self, update: ModelUpdate):
        """Blue-green update strategy with traffic shifting"""
        self.logger.info(f"Executing blue-green update for {update.update_id}")
        
        update.status = UpdateStatus.STAGING
        update.progress_percentage = 5.0
        
        # Create green environment
        green_nodes = []
        for node_id in update.affected_nodes:
            green_node_id = f"{node_id}_green"
            await self.create_green_environment(node_id, green_node_id, update.model_name, update.target_version)
            green_nodes.append(green_node_id)
            update.progress_percentage += 20.0 / len(update.affected_nodes)
        
        update.status = UpdateStatus.VALIDATING
        
        # Validate green environment
        for green_node_id in green_nodes:
            is_valid, validation_data = await self.health_checker.perform_model_validation(
                green_node_id, update.model_name, update.target_version
            )
            
            if not is_valid:
                raise Exception(f"Green environment validation failed on {green_node_id}")
            
            update.progress_percentage += 30.0 / len(green_nodes)
        
        update.status = UpdateStatus.SWITCHING
        
        # Create traffic rules for gradual shift
        old_rule_id = await self.load_balancer.create_traffic_rule(
            update.model_name, update.current_version, 100.0
        )
        new_rule_id = await self.load_balancer.create_traffic_rule(
            update.model_name, update.target_version, 0.0
        )
        
        await self.load_balancer.activate_traffic_rule(old_rule_id)
        await self.load_balancer.activate_traffic_rule(new_rule_id)
        
        # Gradual traffic shift
        shift_duration = self.config["strategies"]["blue_green"]["traffic_shift_duration"]
        await self.load_balancer.gradual_traffic_shift(
            update.model_name, update.current_version, update.target_version, shift_duration
        )
        
        update.progress_percentage = 90.0
        update.status = UpdateStatus.VERIFYING
        
        # Final verification
        await asyncio.sleep(self.config["strategies"]["blue_green"]["validation_duration"] * 60)
        
        # Check final health
        for node_id in update.affected_nodes:
            health_status, health_data = await self.health_checker.check_node_health(
                node_id, update.model_name
            )
            
            if health_status not in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                raise Exception(f"Final health check failed on {node_id}: {health_data}")
        
        update.progress_percentage = 100.0
    
    async def canary_update(self, update: ModelUpdate):
        """Canary update strategy with gradual rollout"""
        self.logger.info(f"Executing canary update for {update.update_id}")
        
        canary_percentage = self.config["strategies"]["canary"]["canary_percentage"]
        canary_count = max(1, int(len(update.affected_nodes) * canary_percentage / 100))
        canary_nodes = update.affected_nodes[:canary_count]
        remaining_nodes = update.affected_nodes[canary_count:]
        
        update.status = UpdateStatus.STAGING
        update.progress_percentage = 10.0
        
        # Deploy to canary nodes
        for node_id in canary_nodes:
            await self.deploy_model_to_node(node_id, update.model_name, update.target_version)
            update.progress_percentage += 30.0 / len(canary_nodes)
        
        update.status = UpdateStatus.VALIDATING
        
        # Monitor canary for specified duration
        canary_duration = self.config["strategies"]["canary"]["canary_duration"]
        success_threshold = self.config["strategies"]["canary"]["success_threshold"]
        
        await self.monitor_canary_deployment(
            canary_nodes, update.model_name, update.target_version, 
            canary_duration, success_threshold
        )
        
        update.progress_percentage = 50.0
        update.status = UpdateStatus.DEPLOYING
        
        # Deploy to remaining nodes
        for node_id in remaining_nodes:
            await self.deploy_model_to_node(node_id, update.model_name, update.target_version)
            update.progress_percentage += 40.0 / len(remaining_nodes)
        
        update.status = UpdateStatus.VERIFYING
        update.progress_percentage = 100.0
    
    async def rolling_update(self, update: ModelUpdate):
        """Rolling update strategy with batched deployment"""
        self.logger.info(f"Executing rolling update for {update.update_id}")
        
        batch_size = self.config["strategies"]["rolling"]["batch_size"]
        batch_delay = self.config["strategies"]["rolling"]["batch_delay_seconds"]
        failure_threshold = self.config["strategies"]["rolling"]["failure_threshold"]
        
        update.status = UpdateStatus.DEPLOYING
        
        # Process nodes in batches
        nodes = update.affected_nodes
        total_batches = (len(nodes) + batch_size - 1) // batch_size
        failed_count = 0
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches}: {batch}")
            
            # Deploy to batch
            for node_id in batch:
                try:
                    await self.deploy_model_to_node(node_id, update.model_name, update.target_version)
                except Exception as e:
                    self.logger.error(f"Deployment failed on {node_id}: {e}")
                    failed_count += 1
                    
                    if failed_count / len(nodes) > failure_threshold:
                        raise Exception(f"Rolling update failed: {failed_count}/{len(nodes)} nodes failed")
            
            # Validate batch
            for node_id in batch:
                health_status, _ = await self.health_checker.check_node_health(
                    node_id, update.model_name
                )
                
                if health_status == HealthStatus.UNHEALTHY:
                    failed_count += 1
                    if failed_count / len(nodes) > failure_threshold:
                        raise Exception(f"Rolling update failed: too many unhealthy nodes")
            
            update.progress_percentage = (batch_num / total_batches) * 90.0
            
            # Wait before next batch (except for last batch)
            if i + batch_size < len(nodes):
                await asyncio.sleep(batch_delay)
        
        update.progress_percentage = 100.0
    
    async def staged_update(self, update: ModelUpdate):
        """Staged update strategy with manual approval points"""
        self.logger.info(f"Executing staged update for {update.update_id}")
        
        stages = [
            ("staging", 0.2),      # Stage to 20% of nodes
            ("validation", 0.5),   # Validate and expand to 50%
            ("production", 1.0)    # Full production deployment
        ]
        
        for stage_name, node_percentage in stages:
            node_count = int(len(update.affected_nodes) * node_percentage)
            stage_nodes = update.affected_nodes[:node_count]
            
            update.status = UpdateStatus.DEPLOYING
            self.logger.info(f"Executing stage '{stage_name}' on {len(stage_nodes)} nodes")
            
            # Deploy to stage nodes
            for node_id in stage_nodes:
                await self.deploy_model_to_node(node_id, update.model_name, update.target_version)
            
            # Validate stage
            await self.validate_stage(stage_nodes, update.model_name, update.target_version)
            
            # Wait for manual approval (in practice, this would be an API call or UI interaction)
            if stage_name != "production":  # Skip approval for final stage
                self.logger.info(f"Stage '{stage_name}' completed. Waiting for approval...")
                await asyncio.sleep(30)  # Simulate approval wait
            
            update.progress_percentage = node_percentage * 100.0
    
    async def stage_model_on_node(self, node_id: str, model_name: str, version: str):
        """Stage model on a specific node"""
        # Simulate staging model file
        staging_path = f"{STAGING_AREA}/{node_id}_{model_name}_{version}.model"
        
        # In practice, this would:
        # 1. Download model file from repository
        # 2. Transfer to node
        # 3. Validate checksum
        # 4. Prepare for deployment
        
        await asyncio.sleep(1)  # Simulate staging time
        
        # Create staging marker
        with open(staging_path, 'w') as f:
            json.dump({
                "node_id": node_id,
                "model_name": model_name,
                "version": version,
                "staged_time": datetime.now().isoformat()
            }, f)
        
        self.logger.debug(f"Staged model {model_name} v{version} on {node_id}")
    
    async def swap_model_on_node(self, node_id: str, model_name: str, version: str):
        """Atomically swap model on node"""
        # Simulate atomic swap
        await asyncio.sleep(0.5)  # Simulate swap time
        
        # Update node state
        if node_id in self.node_states:
            self.node_states[node_id].active_version = version
            self.node_states[node_id].staging_version = None
        
        self.logger.debug(f"Swapped model {model_name} to v{version} on {node_id}")
    
    async def deploy_model_to_node(self, node_id: str, model_name: str, version: str):
        """Deploy model to node (combined stage and swap)"""
        await self.stage_model_on_node(node_id, model_name, version)
        await self.swap_model_on_node(node_id, model_name, version)
    
    async def create_green_environment(self, blue_node_id: str, green_node_id: str, model_name: str, version: str):
        """Create green environment for blue-green deployment"""
        # In practice, this would create a new container/VM/process
        await asyncio.sleep(2)  # Simulate environment creation
        
        # Register green node
        self.node_states[green_node_id] = NodeState(
            node_id=green_node_id,
            model_name=model_name,
            active_version=version,
            staging_version=None,
            health_status=HealthStatus.HEALTHY,
            last_health_check=datetime.now().isoformat(),
            update_in_progress=True,
            load_balancer_weight=0.0,
            performance_metrics={}
        )
        
        self.logger.debug(f"Created green environment {green_node_id} for {blue_node_id}")
    
    async def monitor_canary_deployment(self, canary_nodes: List[str], model_name: str, version: str, 
                                      duration_minutes: int, success_threshold: float):
        """Monitor canary deployment"""
        self.logger.info(f"Monitoring canary deployment for {duration_minutes} minutes")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        success_count = 0
        total_checks = 0
        
        while time.time() < end_time:
            for node_id in canary_nodes:
                health_status, health_data = await self.health_checker.check_node_health(
                    node_id, model_name
                )
                
                total_checks += 1
                if health_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                    success_count += 1
            
            # Check if success rate is acceptable
            if total_checks > 0:
                success_rate = success_count / total_checks
                if success_rate < success_threshold:
                    raise Exception(f"Canary success rate ({success_rate:.2f}) below threshold ({success_threshold})")
            
            await asyncio.sleep(30)  # Check every 30 seconds
        
        final_success_rate = success_count / total_checks if total_checks > 0 else 0
        self.logger.info(f"Canary monitoring completed: {final_success_rate:.2f} success rate")
    
    async def validate_stage(self, nodes: List[str], model_name: str, version: str):
        """Validate a deployment stage"""
        for node_id in nodes:
            # Health check
            health_status, health_data = await self.health_checker.check_node_health(
                node_id, model_name
            )
            
            if health_status == HealthStatus.UNHEALTHY:
                raise Exception(f"Stage validation failed: {node_id} is unhealthy")
            
            # Smoke tests
            success, test_results = await self.health_checker.run_smoke_tests(
                node_id, model_name, version
            )
            
            if not success:
                raise Exception(f"Stage validation failed: smoke tests failed on {node_id}")
    
    async def rollback_update(self, update: ModelUpdate):
        """Rollback a failed update"""
        self.logger.warning(f"Rolling back update {update.update_id}")
        
        update.status = UpdateStatus.ROLLING_BACK
        
        # Execute rollback callbacks
        await self.execute_callbacks('rollback', update)
        
        if not update.rollback_version:
            self.logger.error(f"No rollback version specified for update {update.update_id}")
            return
        
        # Rollback each affected node
        for node_id in update.affected_nodes:
            try:
                await self.deploy_model_to_node(node_id, update.model_name, update.rollback_version)
                self.logger.info(f"Rolled back {node_id} to version {update.rollback_version}")
            except Exception as e:
                self.logger.error(f"Rollback failed on {node_id}: {e}")
        
        # Update load balancer if needed
        if update.strategy == UpdateStrategy.BLUE_GREEN:
            # Restore traffic to original version
            await self.load_balancer.create_traffic_rule(
                update.model_name, update.rollback_version, 100.0
            )
    
    async def execute_callbacks(self, callback_type: str, update: ModelUpdate):
        """Execute registered callbacks"""
        for callback in self.update_callbacks.get(callback_type, []):
            try:
                await callback(update)
            except Exception as e:
                self.logger.error(f"Callback {callback_type} failed: {e}")
    
    def register_callback(self, callback_type: str, callback: Callable):
        """Register update callback"""
        if callback_type in self.update_callbacks:
            self.update_callbacks[callback_type].append(callback)
    
    async def health_monitor(self):
        """Background health monitoring"""
        interval = self.config["health_checks"]["interval_seconds"]
        
        while self.running:
            try:
                for node_id, node_state in self.node_states.items():
                    health_status, health_data = await self.health_checker.check_node_health(
                        node_id, node_state.model_name
                    )
                    
                    node_state.health_status = health_status
                    node_state.last_health_check = datetime.now().isoformat()
                    node_state.performance_metrics = health_data
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(interval * 2)
    
    async def node_state_monitor(self):
        """Monitor and sync node states"""
        while self.running:
            try:
                # Sync node states with Redis
                if self.redis_client:
                    for node_id, node_state in self.node_states.items():
                        state_key = f"node_state:{node_id}"
                        await self.redis_client.set(state_key, json.dumps(asdict(node_state), default=str))
                
                await asyncio.sleep(30)  # Sync every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Node state monitor error: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_service(self):
        """Background cleanup service"""
        while self.running:
            try:
                # Clean up old staging files
                cutoff_time = time.time() - (3600 * 24)  # 24 hours
                
                for staging_file in Path(STAGING_AREA).glob("*.model"):
                    if staging_file.stat().st_mtime < cutoff_time:
                        staging_file.unlink()
                
                # Clean up completed updates older than 7 days
                cutoff_date = datetime.now() - timedelta(days=7)
                self.completed_updates = [
                    update for update in self.completed_updates
                    if datetime.fromisoformat(update.completed_time or update.created_time) > cutoff_date
                ]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Cleanup service error: {e}")
                await asyncio.sleep(1800)
    
    async def metrics_collector(self):
        """Collect and store metrics"""
        while self.running:
            try:
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "updater_id": self.updater_id,
                    "active_updates": len(self.active_updates),
                    "completed_updates": len(self.completed_updates),
                    "failed_updates": len(self.failed_updates),
                    "healthy_nodes": len([
                        node for node in self.node_states.values()
                        if node.health_status == HealthStatus.HEALTHY
                    ]),
                    "total_nodes": len(self.node_states),
                    "queue_size": self.update_queue.qsize()
                }
                
                # Store in Redis
                if self.redis_client:
                    metrics_key = f"updater_metrics:{int(time.time())}"
                    await self.redis_client.set(metrics_key, json.dumps(metrics), ex=86400)  # 24h TTL
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                self.logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(300)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "updater_id": self.updater_id,
            "running": self.running,
            "updates": {
                "active": len(self.active_updates),
                "completed": len(self.completed_updates),
                "failed": len(self.failed_updates),
                "queued": self.update_queue.qsize()
            },
            "nodes": {
                "total": len(self.node_states),
                "healthy": len([n for n in self.node_states.values() if n.health_status == HealthStatus.HEALTHY]),
                "degraded": len([n for n in self.node_states.values() if n.health_status == HealthStatus.DEGRADED]),
                "unhealthy": len([n for n in self.node_states.values() if n.health_status == HealthStatus.UNHEALTHY])
            },
            "strategies_enabled": {
                strategy: config["enabled"] 
                for strategy, config in self.config["strategies"].items()
            },
            "load_balancer": {
                "enabled": self.config["load_balancer"]["enabled"],
                "rules_active": len([r for r in self.load_balancer.rules.values() if r.active])
            }
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down zero-downtime updater...")
        
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        # Shutdown executors
        self.executor.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        self.logger.info("Zero-downtime updater shutdown complete")

async def main():
    """Main entry point"""
    updater = ZeroDowntimeUpdater()
    
    try:
        await updater.start()
        
        # Register some sample nodes
        for i in range(3):
            node_id = f"qenex-node-{i}"
            updater.node_states[node_id] = NodeState(
                node_id=node_id,
                model_name="security_detector",
                active_version="v1.0.0",
                staging_version=None,
                health_status=HealthStatus.HEALTHY,
                last_health_check=datetime.now().isoformat(),
                update_in_progress=False,
                load_balancer_weight=33.33,
                performance_metrics={"cpu_usage": 60, "memory_usage": 70, "error_rate": 0.01}
            )
        
        # Schedule a sample update
        update_id = await updater.schedule_model_update(
            model_name="security_detector",
            target_version="v2.0.0",
            nodes=list(updater.node_states.keys()),
            strategy=UpdateStrategy.BLUE_GREEN,
            priority=1,
            metadata={"update_type": "model_improvement", "expected_accuracy": 0.95}
        )
        
        print(f"Scheduled update: {update_id}")
        
        # Get system status
        status = await updater.get_system_status()
        print("System Status:", json.dumps(status, indent=2))
        
        # Keep running to see the update process
        await asyncio.sleep(60)
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    finally:
        await updater.shutdown()

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║              QENEX Zero-Downtime Updater                  ║
║                Real-time Model Updates                     ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())