#!/usr/bin/env python3
"""
QENEX Model Versioning and Rollback System
Advanced model lifecycle management with zero-downtime updates
"""

import asyncio
import json
import pickle
import hashlib
import uuid
import time
import shutil
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import sqlite3
import git
import tarfile
import zipfile
import tempfile
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
import psutil
import numpy as np

# Configuration
VERSIONING_ROOT = "/opt/qenex-os/distributed-training/model-versioning"
MODEL_REPO = f"{VERSIONING_ROOT}/repository"
VERSION_DB = f"{VERSIONING_ROOT}/versions.db"
BACKUP_DIR = f"{VERSIONING_ROOT}/backups"
STAGING_DIR = f"{VERSIONING_ROOT}/staging"
LOGS_DIR = f"{VERSIONING_ROOT}/logs"
CONFIG_DIR = f"{VERSIONING_ROOT}/config"

# Create directories
for directory in [VERSIONING_ROOT, MODEL_REPO, BACKUP_DIR, STAGING_DIR, LOGS_DIR, CONFIG_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class ModelStatus(Enum):
    TRAINING = "training"
    VALIDATING = "validating"
    STAGING = "staging"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    FAILED = "failed"

class UpdateStrategy(Enum):
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"
    A_B_TESTING = "a_b_testing"
    SHADOW = "shadow"

class RollbackTrigger(Enum):
    MANUAL = "manual"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ERROR_RATE_THRESHOLD = "error_rate_threshold"
    ACCURACY_DROP = "accuracy_drop"
    TIMEOUT = "timeout"

@dataclass
class ModelVersion:
    version_id: str
    model_name: str
    version_number: str
    semantic_version: str  # e.g., "2.1.3"
    git_commit_hash: Optional[str]
    created_timestamp: str
    created_by: str
    status: ModelStatus
    file_path: str
    file_size_bytes: int
    checksum: str
    metadata: Dict[str, Any]
    performance_metrics: Dict[str, float]
    validation_results: Dict[str, Any]
    parent_version: Optional[str] = None
    tags: List[str] = None

@dataclass
class ModelDeployment:
    deployment_id: str
    model_name: str
    version_id: str
    strategy: UpdateStrategy
    target_nodes: List[str]
    start_time: str
    end_time: Optional[str] = None
    status: str = "in_progress"
    rollback_version: Optional[str] = None
    canary_percentage: float = 0.0
    metrics: Dict[str, Any] = None

@dataclass
class RollbackPlan:
    plan_id: str
    model_name: str
    from_version: str
    to_version: str
    trigger: RollbackTrigger
    created_time: str
    executed_time: Optional[str] = None
    affected_nodes: List[str] = None
    rollback_reason: str = ""

class ModelVersionManager:
    """Advanced model versioning and lifecycle management"""
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"version-mgr-{uuid.uuid4().hex[:8]}"
        
        # Configuration
        self.config = self.load_config()
        
        # Setup logging
        self.logger = self.setup_logging()
        
        # Database connection
        self.db_connection = None
        self.init_database()
        
        # Version tracking
        self.active_versions: Dict[str, str] = {}  # model_name -> version_id
        self.staging_versions: Dict[str, str] = {}
        self.version_history: Dict[str, List[ModelVersion]] = {}
        
        # Deployment tracking
        self.active_deployments: Dict[str, ModelDeployment] = {}
        self.deployment_history: List[ModelDeployment] = []
        
        # Rollback management
        self.rollback_plans: Dict[str, RollbackPlan] = {}
        self.auto_rollback_enabled = True
        
        # Git integration
        self.git_repo = None
        self.init_git_repository()
        
        # Performance monitoring
        self.performance_thresholds = {
            "accuracy_min": 0.8,
            "error_rate_max": 0.05,
            "response_time_max": 1000,  # milliseconds
            "memory_usage_max": 80  # percentage
        }
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.process_pool = ProcessPoolExecutor(max_workers=4)
        
        # Background services
        self.running = False
        self.background_tasks = []
        
        self.logger.info(f"Model Version Manager initialized: {self.manager_id}")
    
    def load_config(self) -> Dict:
        """Load versioning configuration"""
        default_config = {
            "versioning": {
                "semantic_versioning": True,
                "auto_increment": True,
                "max_versions_per_model": 50,
                "backup_retention_days": 90,
                "git_integration": True,
                "compression_enabled": True,
            },
            "deployment": {
                "default_strategy": "blue_green",
                "canary_default_percentage": 10.0,
                "deployment_timeout_minutes": 30,
                "validation_timeout_minutes": 10,
                "rollback_timeout_minutes": 5,
            },
            "monitoring": {
                "performance_check_interval": 60,
                "health_check_interval": 30,
                "metrics_retention_days": 30,
                "alert_thresholds": {
                    "accuracy_drop": 0.05,
                    "error_rate_increase": 0.02,
                    "response_time_increase": 500
                }
            },
            "storage": {
                "backend": "filesystem",  # filesystem, s3, gcs, azure
                "compression": "gzip",
                "replication_enabled": True,
                "replication_factor": 3,
            }
        }
        
        config_file = f"{CONFIG_DIR}/model_versioning.json"
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
        logger = logging.getLogger('ModelVersionManager')
        logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(f"{LOGS_DIR}/model_versioning.log")
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
    
    def init_database(self):
        """Initialize SQLite database for version tracking"""
        self.db_connection = sqlite3.connect(VERSION_DB, check_same_thread=False)
        self.db_connection.row_factory = sqlite3.Row
        
        cursor = self.db_connection.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_versions (
                version_id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                version_number TEXT NOT NULL,
                semantic_version TEXT NOT NULL,
                git_commit_hash TEXT,
                created_timestamp TEXT NOT NULL,
                created_by TEXT NOT NULL,
                status TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                metadata TEXT,
                performance_metrics TEXT,
                validation_results TEXT,
                parent_version TEXT,
                tags TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deployments (
                deployment_id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                version_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                target_nodes TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                rollback_version TEXT,
                canary_percentage REAL,
                metrics TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rollback_plans (
                plan_id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                from_version TEXT NOT NULL,
                to_version TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                created_time TEXT NOT NULL,
                executed_time TEXT,
                affected_nodes TEXT,
                rollback_reason TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_versions_name ON model_versions(model_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_versions_status ON model_versions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deployments_model ON deployments(model_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rollback_plans_model ON rollback_plans(model_name)')
        
        self.db_connection.commit()
        
        self.logger.info("Database initialized")
    
    def init_git_repository(self):
        """Initialize Git repository for model versioning"""
        if not self.config["versioning"]["git_integration"]:
            return
        
        git_dir = f"{MODEL_REPO}/.git"
        
        try:
            if os.path.exists(git_dir):
                self.git_repo = git.Repo(MODEL_REPO)
            else:
                self.git_repo = git.Repo.init(MODEL_REPO)
                
                # Initial commit
                with open(f"{MODEL_REPO}/README.md", 'w') as f:
                    f.write("# QENEX Model Repository\n\nThis repository contains versioned ML models.\n")
                
                self.git_repo.index.add(["README.md"])
                self.git_repo.index.commit("Initial commit - QENEX Model Repository")
            
            self.logger.info("Git repository initialized")
            
        except Exception as e:
            self.logger.warning(f"Git initialization failed: {e}")
            self.git_repo = None
    
    async def start(self):
        """Start the model version manager"""
        self.running = True
        
        # Start background services
        tasks = [
            self.performance_monitor(),
            self.deployment_monitor(),
            self.cleanup_service(),
            self.backup_service(),
            self.health_checker()
        ]
        
        self.background_tasks = [asyncio.create_task(task) for task in tasks]
        
        self.logger.info("Model version manager started")
    
    async def create_model_version(self, 
                                 model_name: str,
                                 model_data: bytes,
                                 created_by: str,
                                 metadata: Dict[str, Any] = None,
                                 parent_version: str = None,
                                 tags: List[str] = None) -> str:
        """Create a new model version"""
        
        version_id = f"v{uuid.uuid4().hex[:8]}"
        
        # Generate semantic version
        semantic_version = await self.generate_semantic_version(model_name, parent_version)
        version_number = semantic_version.split('.')[-1]  # Use patch number as version
        
        # Calculate checksum
        checksum = hashlib.sha256(model_data).hexdigest()
        
        # Save model file
        model_dir = f"{MODEL_REPO}/{model_name}"
        os.makedirs(model_dir, exist_ok=True)
        
        file_path = f"{model_dir}/{version_id}.model"
        
        # Compress if enabled
        if self.config["versioning"]["compression_enabled"]:
            compressed_path = f"{file_path}.gz"
            with open(compressed_path, 'wb') as f:
                import gzip
                f.write(gzip.compress(model_data))
            file_path = compressed_path
        else:
            with open(file_path, 'wb') as f:
                f.write(model_data)
        
        # Create version record
        version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            version_number=version_number,
            semantic_version=semantic_version,
            git_commit_hash=None,  # Will be set after Git commit
            created_timestamp=datetime.now().isoformat(),
            created_by=created_by,
            status=ModelStatus.STAGING,
            file_path=file_path,
            file_size_bytes=len(model_data),
            checksum=checksum,
            metadata=metadata or {},
            performance_metrics={},
            validation_results={},
            parent_version=parent_version,
            tags=tags or []
        )
        
        # Store in database
        await self.save_version_to_db(version)
        
        # Add to Git if enabled
        if self.git_repo:
            git_commit_hash = await self.commit_to_git(version)
            version.git_commit_hash = git_commit_hash
            await self.update_version_in_db(version)
        
        # Update in-memory tracking
        if model_name not in self.version_history:
            self.version_history[model_name] = []
        self.version_history[model_name].append(version)
        
        # Set as staging version
        self.staging_versions[model_name] = version_id
        
        self.logger.info(f"Created model version {version_id} for {model_name} ({semantic_version})")
        
        return version_id
    
    async def generate_semantic_version(self, model_name: str, parent_version: str = None) -> str:
        """Generate semantic version number (MAJOR.MINOR.PATCH)"""
        if not self.config["versioning"]["semantic_versioning"]:
            return str(int(time.time()))
        
        # Get latest version
        latest_version = await self.get_latest_version(model_name)
        
        if not latest_version:
            return "1.0.0"
        
        # Parse latest semantic version
        try:
            major, minor, patch = map(int, latest_version.semantic_version.split('.'))
        except (ValueError, AttributeError):
            return "1.0.0"
        
        # Auto-increment based on parent relationship
        if parent_version:
            parent = await self.get_version_by_id(parent_version)
            if parent and parent.semantic_version != latest_version.semantic_version:
                # Different branch, increment minor
                return f"{major}.{minor + 1}.0"
        
        # Default: increment patch version
        return f"{major}.{minor}.{patch + 1}"
    
    async def get_latest_version(self, model_name: str) -> Optional[ModelVersion]:
        """Get the latest version of a model"""
        cursor = self.db_connection.cursor()
        cursor.execute('''
            SELECT * FROM model_versions 
            WHERE model_name = ? 
            ORDER BY created_timestamp DESC 
            LIMIT 1
        ''', (model_name,))
        
        row = cursor.fetchone()
        if row:
            return self.row_to_model_version(row)
        return None
    
    async def get_version_by_id(self, version_id: str) -> Optional[ModelVersion]:
        """Get version by ID"""
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT * FROM model_versions WHERE version_id = ?', (version_id,))
        
        row = cursor.fetchone()
        if row:
            return self.row_to_model_version(row)
        return None
    
    def row_to_model_version(self, row) -> ModelVersion:
        """Convert database row to ModelVersion object"""
        return ModelVersion(
            version_id=row['version_id'],
            model_name=row['model_name'],
            version_number=row['version_number'],
            semantic_version=row['semantic_version'],
            git_commit_hash=row['git_commit_hash'],
            created_timestamp=row['created_timestamp'],
            created_by=row['created_by'],
            status=ModelStatus(row['status']),
            file_path=row['file_path'],
            file_size_bytes=row['file_size_bytes'],
            checksum=row['checksum'],
            metadata=json.loads(row['metadata'] or '{}'),
            performance_metrics=json.loads(row['performance_metrics'] or '{}'),
            validation_results=json.loads(row['validation_results'] or '{}'),
            parent_version=row['parent_version'],
            tags=json.loads(row['tags'] or '[]')
        )
    
    async def save_version_to_db(self, version: ModelVersion):
        """Save version to database"""
        cursor = self.db_connection.cursor()
        cursor.execute('''
            INSERT INTO model_versions (
                version_id, model_name, version_number, semantic_version, 
                git_commit_hash, created_timestamp, created_by, status,
                file_path, file_size_bytes, checksum, metadata,
                performance_metrics, validation_results, parent_version, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            version.version_id, version.model_name, version.version_number,
            version.semantic_version, version.git_commit_hash, version.created_timestamp,
            version.created_by, version.status.value, version.file_path,
            version.file_size_bytes, version.checksum, json.dumps(version.metadata),
            json.dumps(version.performance_metrics), json.dumps(version.validation_results),
            version.parent_version, json.dumps(version.tags or [])
        ))
        self.db_connection.commit()
    
    async def update_version_in_db(self, version: ModelVersion):
        """Update version in database"""
        cursor = self.db_connection.cursor()
        cursor.execute('''
            UPDATE model_versions SET
                status = ?, performance_metrics = ?, validation_results = ?,
                git_commit_hash = ?, metadata = ?, tags = ?
            WHERE version_id = ?
        ''', (
            version.status.value, json.dumps(version.performance_metrics),
            json.dumps(version.validation_results), version.git_commit_hash,
            json.dumps(version.metadata), json.dumps(version.tags or []),
            version.version_id
        ))
        self.db_connection.commit()
    
    async def commit_to_git(self, version: ModelVersion) -> str:
        """Commit model version to Git repository"""
        if not self.git_repo:
            return ""
        
        try:
            # Add model file to Git
            relative_path = os.path.relpath(version.file_path, MODEL_REPO)
            self.git_repo.index.add([relative_path])
            
            # Create version metadata file
            metadata_file = f"{version.model_name}_{version.version_id}_metadata.json"
            metadata_path = f"{MODEL_REPO}/{metadata_file}"
            
            with open(metadata_path, 'w') as f:
                json.dump(asdict(version), f, indent=2, default=str)
            
            self.git_repo.index.add([metadata_file])
            
            # Commit
            commit_message = f"Add model version {version.semantic_version} for {version.model_name}"
            commit = self.git_repo.index.commit(commit_message)
            
            # Create tag
            tag_name = f"{version.model_name}_v{version.semantic_version}"
            self.git_repo.create_tag(tag_name, ref=commit)
            
            return commit.hexsha
            
        except Exception as e:
            self.logger.error(f"Git commit failed: {e}")
            return ""
    
    async def validate_model_version(self, 
                                   version_id: str,
                                   validation_data: Any = None,
                                   validation_metrics: Dict[str, float] = None) -> Dict[str, Any]:
        """Validate a model version"""
        version = await self.get_version_by_id(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        self.logger.info(f"Validating model version {version_id}")
        
        # Update status to validating
        version.status = ModelStatus.VALIDATING
        await self.update_version_in_db(version)
        
        validation_results = {
            "validation_timestamp": datetime.now().isoformat(),
            "validation_passed": True,
            "validation_errors": [],
            "performance_metrics": validation_metrics or {},
            "data_integrity_check": True,
            "model_size_check": True,
            "compatibility_check": True
        }
        
        try:
            # Load and verify model
            model_data = await self.load_model_data(version)
            
            # Verify checksum
            actual_checksum = hashlib.sha256(model_data).hexdigest()
            if actual_checksum != version.checksum:
                validation_results["validation_passed"] = False
                validation_results["validation_errors"].append("Checksum mismatch")
                validation_results["data_integrity_check"] = False
            
            # Check model size
            if len(model_data) != version.file_size_bytes:
                validation_results["validation_passed"] = False
                validation_results["validation_errors"].append("File size mismatch")
                validation_results["model_size_check"] = False
            
            # Run custom validation if provided
            if validation_data is not None:
                custom_results = await self.run_custom_validation(model_data, validation_data)
                validation_results.update(custom_results)
            
            # Update version with validation results
            version.validation_results = validation_results
            if validation_metrics:
                version.performance_metrics.update(validation_metrics)
            
            # Update status based on validation
            if validation_results["validation_passed"]:
                version.status = ModelStatus.STAGING
                self.logger.info(f"Model version {version_id} validation passed")
            else:
                version.status = ModelStatus.FAILED
                self.logger.warning(f"Model version {version_id} validation failed")
            
            await self.update_version_in_db(version)
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Validation failed for version {version_id}: {e}")
            
            version.status = ModelStatus.FAILED
            validation_results["validation_passed"] = False
            validation_results["validation_errors"].append(str(e))
            version.validation_results = validation_results
            
            await self.update_version_in_db(version)
            
            return validation_results
    
    async def load_model_data(self, version: ModelVersion) -> bytes:
        """Load model data from storage"""
        file_path = version.file_path
        
        if file_path.endswith('.gz'):
            import gzip
            with open(file_path, 'rb') as f:
                return gzip.decompress(f.read())
        else:
            with open(file_path, 'rb') as f:
                return f.read()
    
    async def run_custom_validation(self, model_data: bytes, validation_data: Any) -> Dict[str, Any]:
        """Run custom model validation logic"""
        # Placeholder for custom validation logic
        # In practice, this would load the model and run inference tests
        return {
            "custom_validation_passed": True,
            "inference_test_passed": True,
            "accuracy_test_passed": True
        }
    
    async def deploy_model_version(self, 
                                 model_name: str,
                                 version_id: str,
                                 target_nodes: List[str],
                                 strategy: UpdateStrategy = UpdateStrategy.BLUE_GREEN,
                                 canary_percentage: float = 10.0) -> str:
        """Deploy a model version with specified strategy"""
        
        version = await self.get_version_by_id(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        if version.status != ModelStatus.STAGING:
            raise ValueError(f"Version {version_id} is not ready for deployment (status: {version.status.value})")
        
        deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"
        
        # Get current active version for rollback
        current_active = self.active_versions.get(model_name)
        
        deployment = ModelDeployment(
            deployment_id=deployment_id,
            model_name=model_name,
            version_id=version_id,
            strategy=strategy,
            target_nodes=target_nodes,
            start_time=datetime.now().isoformat(),
            rollback_version=current_active,
            canary_percentage=canary_percentage,
            metrics={}
        )
        
        self.active_deployments[deployment_id] = deployment
        
        self.logger.info(f"Starting deployment {deployment_id}: {model_name} {version.semantic_version} "
                        f"using {strategy.value} strategy")
        
        try:
            # Execute deployment based on strategy
            if strategy == UpdateStrategy.BLUE_GREEN:
                await self.blue_green_deployment(deployment)
            elif strategy == UpdateStrategy.ROLLING:
                await self.rolling_deployment(deployment)
            elif strategy == UpdateStrategy.CANARY:
                await self.canary_deployment(deployment)
            elif strategy == UpdateStrategy.A_B_TESTING:
                await self.ab_testing_deployment(deployment)
            elif strategy == UpdateStrategy.SHADOW:
                await self.shadow_deployment(deployment)
            
            # Update version status
            version.status = ModelStatus.ACTIVE
            await self.update_version_in_db(version)
            
            # Update active version
            self.active_versions[model_name] = version_id
            
            # Complete deployment
            deployment.status = "completed"
            deployment.end_time = datetime.now().isoformat()
            
            self.deployment_history.append(deployment)
            del self.active_deployments[deployment_id]
            
            self.logger.info(f"Deployment {deployment_id} completed successfully")
            
            return deployment_id
            
        except Exception as e:
            self.logger.error(f"Deployment {deployment_id} failed: {e}")
            
            deployment.status = "failed"
            deployment.end_time = datetime.now().isoformat()
            
            # Trigger rollback if needed
            if current_active:
                await self.initiate_rollback(model_name, version_id, current_active, 
                                           RollbackTrigger.MANUAL, f"Deployment failed: {e}")
            
            raise
    
    async def blue_green_deployment(self, deployment: ModelDeployment):
        """Blue-Green deployment strategy"""
        # In Blue-Green deployment, we maintain two identical production environments
        # Switch traffic from blue (current) to green (new) environment
        
        self.logger.info(f"Executing Blue-Green deployment for {deployment.deployment_id}")
        
        # Phase 1: Prepare Green environment
        await self.prepare_green_environment(deployment)
        
        # Phase 2: Validate Green environment
        await self.validate_green_environment(deployment)
        
        # Phase 3: Switch traffic to Green
        await self.switch_traffic_to_green(deployment)
        
        # Phase 4: Monitor and verify
        await self.monitor_deployment(deployment, duration_minutes=5)
    
    async def rolling_deployment(self, deployment: ModelDeployment):
        """Rolling deployment strategy"""
        # Rolling deployment gradually replaces instances of the old version
        
        self.logger.info(f"Executing Rolling deployment for {deployment.deployment_id}")
        
        nodes = deployment.target_nodes
        batch_size = max(1, len(nodes) // 4)  # Deploy to 25% of nodes at a time
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            
            # Deploy to current batch
            await self.deploy_to_nodes(deployment, batch)
            
            # Validate batch
            await self.validate_node_batch(deployment, batch)
            
            # Wait before next batch
            await asyncio.sleep(30)  # 30 seconds between batches
    
    async def canary_deployment(self, deployment: ModelDeployment):
        """Canary deployment strategy"""
        # Canary deployment routes a small percentage of traffic to new version
        
        self.logger.info(f"Executing Canary deployment for {deployment.deployment_id} "
                        f"({deployment.canary_percentage}% traffic)")
        
        # Phase 1: Deploy to canary nodes
        canary_node_count = max(1, int(len(deployment.target_nodes) * deployment.canary_percentage / 100))
        canary_nodes = deployment.target_nodes[:canary_node_count]
        
        await self.deploy_to_nodes(deployment, canary_nodes)
        
        # Phase 2: Monitor canary metrics
        canary_metrics = await self.monitor_canary_deployment(deployment, duration_minutes=10)
        
        # Phase 3: Decide based on metrics
        if await self.evaluate_canary_metrics(canary_metrics):
            # Canary successful, proceed with full deployment
            remaining_nodes = deployment.target_nodes[canary_node_count:]
            await self.deploy_to_nodes(deployment, remaining_nodes)
        else:
            # Canary failed, rollback
            raise Exception("Canary deployment failed metrics validation")
    
    async def ab_testing_deployment(self, deployment: ModelDeployment):
        """A/B testing deployment strategy"""
        # A/B testing routes traffic between old (A) and new (B) versions
        
        self.logger.info(f"Executing A/B testing deployment for {deployment.deployment_id}")
        
        # Split nodes between A and B groups
        mid_point = len(deployment.target_nodes) // 2
        a_nodes = deployment.target_nodes[:mid_point]
        b_nodes = deployment.target_nodes[mid_point:]
        
        # Deploy new version to B group
        await self.deploy_to_nodes(deployment, b_nodes)
        
        # Run A/B test
        await self.run_ab_test(deployment, a_nodes, b_nodes, duration_minutes=15)
    
    async def shadow_deployment(self, deployment: ModelDeployment):
        """Shadow deployment strategy"""
        # Shadow deployment runs new version alongside old version without affecting users
        
        self.logger.info(f"Executing Shadow deployment for {deployment.deployment_id}")
        
        # Deploy to shadow environment
        await self.deploy_to_shadow_environment(deployment)
        
        # Mirror traffic to shadow
        await self.mirror_traffic_to_shadow(deployment, duration_minutes=20)
        
        # Validate shadow performance
        await self.validate_shadow_performance(deployment)
    
    async def prepare_green_environment(self, deployment: ModelDeployment):
        """Prepare green environment for blue-green deployment"""
        # Placeholder for environment preparation logic
        self.logger.info(f"Preparing green environment for {deployment.deployment_id}")
        await asyncio.sleep(2)  # Simulate preparation time
    
    async def validate_green_environment(self, deployment: ModelDeployment):
        """Validate green environment"""
        # Placeholder for validation logic
        self.logger.info(f"Validating green environment for {deployment.deployment_id}")
        await asyncio.sleep(1)  # Simulate validation time
    
    async def switch_traffic_to_green(self, deployment: ModelDeployment):
        """Switch traffic to green environment"""
        # Placeholder for traffic switching logic
        self.logger.info(f"Switching traffic to green for {deployment.deployment_id}")
        await asyncio.sleep(1)  # Simulate switch time
    
    async def deploy_to_nodes(self, deployment: ModelDeployment, nodes: List[str]):
        """Deploy to specific nodes"""
        self.logger.info(f"Deploying {deployment.version_id} to {len(nodes)} nodes")
        
        # In a real implementation, this would:
        # 1. Load the model file
        # 2. Send it to target nodes via API/SSH
        # 3. Update node configurations
        # 4. Restart/reload model services
        
        # Simulate deployment time
        await asyncio.sleep(len(nodes) * 0.5)
    
    async def validate_node_batch(self, deployment: ModelDeployment, nodes: List[str]):
        """Validate a batch of nodes after deployment"""
        self.logger.info(f"Validating deployment on {len(nodes)} nodes")
        
        # Simulate validation checks
        await asyncio.sleep(1)
        
        # In practice, this would run health checks, performance tests, etc.
    
    async def monitor_deployment(self, deployment: ModelDeployment, duration_minutes: int):
        """Monitor deployment for specified duration"""
        self.logger.info(f"Monitoring deployment {deployment.deployment_id} for {duration_minutes} minutes")
        
        # Simulate monitoring
        await asyncio.sleep(duration_minutes * 6)  # 6 seconds = 1 minute for simulation
        
        # Collect metrics
        deployment.metrics = {
            "success_rate": 0.99,
            "average_response_time": 150,
            "error_rate": 0.01,
            "cpu_usage": 65,
            "memory_usage": 70
        }
    
    async def monitor_canary_deployment(self, deployment: ModelDeployment, duration_minutes: int) -> Dict[str, float]:
        """Monitor canary deployment and return metrics"""
        self.logger.info(f"Monitoring canary deployment for {duration_minutes} minutes")
        
        # Simulate canary monitoring
        await asyncio.sleep(duration_minutes * 3)  # Accelerated for simulation
        
        return {
            "canary_success_rate": 0.98,
            "canary_response_time": 140,
            "canary_error_rate": 0.02,
            "baseline_success_rate": 0.97,
            "baseline_response_time": 160,
            "baseline_error_rate": 0.03
        }
    
    async def evaluate_canary_metrics(self, metrics: Dict[str, float]) -> bool:
        """Evaluate if canary metrics are acceptable"""
        # Compare canary vs baseline
        success_rate_improvement = metrics["canary_success_rate"] - metrics["baseline_success_rate"]
        response_time_improvement = metrics["baseline_response_time"] - metrics["canary_response_time"]
        error_rate_improvement = metrics["baseline_error_rate"] - metrics["canary_error_rate"]
        
        # Canary is successful if it performs better than baseline
        canary_success = (
            success_rate_improvement >= -0.01 and  # Allow small degradation
            response_time_improvement >= -50 and  # Allow 50ms slower
            error_rate_improvement >= -0.01  # Allow small error rate increase
        )
        
        self.logger.info(f"Canary evaluation: {'PASSED' if canary_success else 'FAILED'}")
        return canary_success
    
    async def run_ab_test(self, deployment: ModelDeployment, a_nodes: List[str], b_nodes: List[str], duration_minutes: int):
        """Run A/B test between node groups"""
        self.logger.info(f"Running A/B test for {duration_minutes} minutes")
        
        # Simulate A/B test
        await asyncio.sleep(duration_minutes * 2)  # Accelerated for simulation
        
        # In practice, this would collect metrics from both groups and compare
        deployment.metrics = {
            "a_group_conversion": 0.15,
            "b_group_conversion": 0.18,
            "statistical_significance": 0.95,
            "winner": "B"
        }
    
    async def deploy_to_shadow_environment(self, deployment: ModelDeployment):
        """Deploy to shadow environment"""
        self.logger.info(f"Deploying to shadow environment for {deployment.deployment_id}")
        await asyncio.sleep(2)
    
    async def mirror_traffic_to_shadow(self, deployment: ModelDeployment, duration_minutes: int):
        """Mirror traffic to shadow environment"""
        self.logger.info(f"Mirroring traffic to shadow for {duration_minutes} minutes")
        await asyncio.sleep(duration_minutes * 1)  # Accelerated
    
    async def validate_shadow_performance(self, deployment: ModelDeployment):
        """Validate shadow environment performance"""
        self.logger.info(f"Validating shadow performance for {deployment.deployment_id}")
        await asyncio.sleep(1)
    
    async def initiate_rollback(self, 
                              model_name: str,
                              from_version: str,
                              to_version: str,
                              trigger: RollbackTrigger,
                              reason: str = "") -> str:
        """Initiate model rollback"""
        
        plan_id = f"rollback-{uuid.uuid4().hex[:8]}"
        
        rollback_plan = RollbackPlan(
            plan_id=plan_id,
            model_name=model_name,
            from_version=from_version,
            to_version=to_version,
            trigger=trigger,
            created_time=datetime.now().isoformat(),
            rollback_reason=reason
        )
        
        self.rollback_plans[plan_id] = rollback_plan
        
        self.logger.warning(f"Initiating rollback {plan_id}: {model_name} from {from_version} to {to_version}")
        self.logger.warning(f"Rollback reason: {reason}")
        
        try:
            # Execute rollback
            await self.execute_rollback(rollback_plan)
            
            rollback_plan.executed_time = datetime.now().isoformat()
            
            # Update active version
            self.active_versions[model_name] = to_version
            
            # Update version statuses
            from_version_obj = await self.get_version_by_id(from_version)
            to_version_obj = await self.get_version_by_id(to_version)
            
            if from_version_obj:
                from_version_obj.status = ModelStatus.DEPRECATED
                await self.update_version_in_db(from_version_obj)
            
            if to_version_obj:
                to_version_obj.status = ModelStatus.ACTIVE
                await self.update_version_in_db(to_version_obj)
            
            self.logger.info(f"Rollback {plan_id} completed successfully")
            
            return plan_id
            
        except Exception as e:
            self.logger.error(f"Rollback {plan_id} failed: {e}")
            raise
    
    async def execute_rollback(self, rollback_plan: RollbackPlan):
        """Execute rollback plan"""
        self.logger.info(f"Executing rollback plan {rollback_plan.plan_id}")
        
        # Get target nodes (in practice, get from current deployment)
        target_nodes = ["node1", "node2", "node3"]  # Placeholder
        rollback_plan.affected_nodes = target_nodes
        
        # Load rollback version
        rollback_version = await self.get_version_by_id(rollback_plan.to_version)
        if not rollback_version:
            raise ValueError(f"Rollback version {rollback_plan.to_version} not found")
        
        # Deploy rollback version
        # This is essentially a fast deployment using blue-green strategy
        deployment = ModelDeployment(
            deployment_id=f"rollback-deploy-{uuid.uuid4().hex[:8]}",
            model_name=rollback_plan.model_name,
            version_id=rollback_plan.to_version,
            strategy=UpdateStrategy.BLUE_GREEN,
            target_nodes=target_nodes,
            start_time=datetime.now().isoformat()
        )
        
        await self.blue_green_deployment(deployment)
        
        # Verify rollback
        await self.verify_rollback(rollback_plan)
    
    async def verify_rollback(self, rollback_plan: RollbackPlan):
        """Verify rollback was successful"""
        self.logger.info(f"Verifying rollback {rollback_plan.plan_id}")
        
        # In practice, this would:
        # 1. Check that all nodes are running the rollback version
        # 2. Verify system health metrics
        # 3. Run smoke tests
        
        # Simulate verification
        await asyncio.sleep(2)
        
        self.logger.info(f"Rollback {rollback_plan.plan_id} verification completed")
    
    async def performance_monitor(self):
        """Background performance monitoring"""
        while self.running:
            try:
                for model_name, version_id in self.active_versions.items():
                    metrics = await self.collect_performance_metrics(model_name, version_id)
                    
                    # Check for performance degradation
                    if await self.check_performance_degradation(metrics):
                        # Consider auto-rollback
                        if self.auto_rollback_enabled:
                            await self.consider_auto_rollback(model_name, version_id, metrics)
                
                await asyncio.sleep(self.config["monitoring"]["performance_check_interval"])
                
            except Exception as e:
                self.logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(300)  # 5 minutes
    
    async def collect_performance_metrics(self, model_name: str, version_id: str) -> Dict[str, float]:
        """Collect performance metrics for a model version"""
        # Simulate metrics collection
        return {
            "accuracy": 0.85 + np.random.uniform(-0.05, 0.05),
            "response_time": 150 + np.random.uniform(-50, 50),
            "error_rate": 0.02 + np.random.uniform(-0.01, 0.01),
            "cpu_usage": 60 + np.random.uniform(-20, 20),
            "memory_usage": 70 + np.random.uniform(-10, 10)
        }
    
    async def check_performance_degradation(self, metrics: Dict[str, float]) -> bool:
        """Check if performance has degraded beyond thresholds"""
        return (
            metrics["accuracy"] < self.performance_thresholds["accuracy_min"] or
            metrics["error_rate"] > self.performance_thresholds["error_rate_max"] or
            metrics["response_time"] > self.performance_thresholds["response_time_max"] or
            metrics["memory_usage"] > self.performance_thresholds["memory_usage_max"]
        )
    
    async def consider_auto_rollback(self, model_name: str, version_id: str, metrics: Dict[str, float]):
        """Consider automatic rollback based on performance metrics"""
        # Get previous version for rollback
        version = await self.get_version_by_id(version_id)
        if not version or not version.parent_version:
            self.logger.warning(f"Cannot auto-rollback {version_id}: no parent version")
            return
        
        # Check if degradation is severe enough
        severity_score = 0
        if metrics["accuracy"] < self.performance_thresholds["accuracy_min"]:
            severity_score += 3
        if metrics["error_rate"] > self.performance_thresholds["error_rate_max"]:
            severity_score += 3
        if metrics["response_time"] > self.performance_thresholds["response_time_max"]:
            severity_score += 2
        if metrics["memory_usage"] > self.performance_thresholds["memory_usage_max"]:
            severity_score += 1
        
        if severity_score >= 4:  # High severity threshold
            reason = f"Auto-rollback triggered: severity={severity_score}, metrics={metrics}"
            await self.initiate_rollback(
                model_name, version_id, version.parent_version,
                RollbackTrigger.PERFORMANCE_DEGRADATION, reason
            )
    
    async def deployment_monitor(self):
        """Monitor active deployments"""
        while self.running:
            try:
                timeout_minutes = self.config["deployment"]["deployment_timeout_minutes"]
                current_time = datetime.now()
                
                timed_out_deployments = []
                
                for deployment_id, deployment in self.active_deployments.items():
                    start_time = datetime.fromisoformat(deployment.start_time)
                    if (current_time - start_time).seconds > timeout_minutes * 60:
                        timed_out_deployments.append(deployment_id)
                
                # Handle timed out deployments
                for deployment_id in timed_out_deployments:
                    deployment = self.active_deployments[deployment_id]
                    self.logger.warning(f"Deployment {deployment_id} timed out")
                    
                    deployment.status = "timed_out"
                    deployment.end_time = datetime.now().isoformat()
                    
                    # Trigger rollback if possible
                    if deployment.rollback_version:
                        await self.initiate_rollback(
                            deployment.model_name, deployment.version_id, 
                            deployment.rollback_version, RollbackTrigger.TIMEOUT,
                            f"Deployment {deployment_id} timed out"
                        )
                    
                    # Move to history
                    self.deployment_history.append(deployment)
                    del self.active_deployments[deployment_id]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Deployment monitor error: {e}")
                await asyncio.sleep(300)
    
    async def cleanup_service(self):
        """Background cleanup service"""
        while self.running:
            try:
                # Clean up old versions
                await self.cleanup_old_versions()
                
                # Clean up old backups
                await self.cleanup_old_backups()
                
                # Clean up temporary files
                await self.cleanup_temp_files()
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Cleanup service error: {e}")
                await asyncio.sleep(1800)  # 30 minutes
    
    async def cleanup_old_versions(self):
        """Clean up old model versions"""
        max_versions = self.config["versioning"]["max_versions_per_model"]
        
        for model_name in self.version_history:
            versions = sorted(
                self.version_history[model_name],
                key=lambda v: v.created_timestamp,
                reverse=True
            )
            
            if len(versions) > max_versions:
                old_versions = versions[max_versions:]
                
                for version in old_versions:
                    if version.status not in [ModelStatus.ACTIVE, ModelStatus.STAGING]:
                        await self.archive_version(version)
    
    async def archive_version(self, version: ModelVersion):
        """Archive old model version"""
        self.logger.info(f"Archiving version {version.version_id}")
        
        # Move to archive directory
        archive_dir = f"{VERSIONING_ROOT}/archive/{version.model_name}"
        os.makedirs(archive_dir, exist_ok=True)
        
        if os.path.exists(version.file_path):
            archive_path = f"{archive_dir}/{version.version_id}.model.gz"
            shutil.move(version.file_path, archive_path)
            
            # Update database
            version.status = ModelStatus.ARCHIVED
            version.file_path = archive_path
            await self.update_version_in_db(version)
    
    async def cleanup_old_backups(self):
        """Clean up old backup files"""
        retention_days = self.config["versioning"]["backup_retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for backup_file in Path(BACKUP_DIR).glob("*.backup"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                backup_file.unlink()
                self.logger.info(f"Deleted old backup: {backup_file}")
    
    async def cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_dirs = [STAGING_DIR, tempfile.gettempdir()]
        
        for temp_dir in temp_dirs:
            for temp_file in Path(temp_dir).glob("qenex_model_*"):
                try:
                    if temp_file.is_file():
                        # Delete files older than 1 hour
                        if time.time() - temp_file.stat().st_mtime > 3600:
                            temp_file.unlink()
                    elif temp_file.is_dir():
                        # Delete empty directories
                        if not any(temp_file.iterdir()):
                            temp_file.rmdir()
                except OSError:
                    pass  # Ignore permission errors
    
    async def backup_service(self):
        """Background backup service"""
        while self.running:
            try:
                await self.create_system_backup()
                await asyncio.sleep(86400)  # Daily backups
                
            except Exception as e:
                self.logger.error(f"Backup service error: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def create_system_backup(self):
        """Create system backup"""
        backup_id = f"backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = f"{BACKUP_DIR}/{backup_id}.tar.gz"
        
        self.logger.info(f"Creating system backup: {backup_id}")
        
        # Create tarball of model repository and database
        with tarfile.open(backup_path, 'w:gz') as tar:
            tar.add(MODEL_REPO, arcname='models')
            tar.add(VERSION_DB, arcname='versions.db')
            
            # Add configuration
            tar.add(CONFIG_DIR, arcname='config')
        
        self.logger.info(f"System backup created: {backup_path}")
    
    async def health_checker(self):
        """Background health checking"""
        while self.running:
            try:
                # Check database health
                await self.check_database_health()
                
                # Check storage health
                await self.check_storage_health()
                
                # Check Git repository health
                await self.check_git_health()
                
                await asyncio.sleep(self.config["monitoring"]["health_check_interval"])
                
            except Exception as e:
                self.logger.error(f"Health checker error: {e}")
                await asyncio.sleep(300)
    
    async def check_database_health(self):
        """Check database health"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM model_versions")
            cursor.fetchone()
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            # Could implement database recovery logic here
    
    async def check_storage_health(self):
        """Check storage health"""
        disk_usage = psutil.disk_usage(VERSIONING_ROOT)
        usage_percent = (disk_usage.used / disk_usage.total) * 100
        
        if usage_percent > 90:
            self.logger.warning(f"Storage usage high: {usage_percent:.1f}%")
            # Could trigger cleanup or alert
    
    async def check_git_health(self):
        """Check Git repository health"""
        if self.git_repo:
            try:
                # Check if repository is clean
                if self.git_repo.is_dirty():
                    self.logger.warning("Git repository has uncommitted changes")
                
                # Check for unpushed commits
                if self.git_repo.active_branch.commit != self.git_repo.heads.master.commit:
                    self.logger.info("Git repository has unpushed commits")
                    
            except Exception as e:
                self.logger.error(f"Git health check failed: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get model versioning system status"""
        total_versions = 0
        versions_by_status = {}
        
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM model_versions GROUP BY status")
        for row in cursor.fetchall():
            versions_by_status[row[0]] = row[1]
            total_versions += row[1]
        
        return {
            "manager_id": self.manager_id,
            "running": self.running,
            "models": {
                "total_versions": total_versions,
                "active_models": len(self.active_versions),
                "staging_models": len(self.staging_versions),
                "versions_by_status": versions_by_status
            },
            "deployments": {
                "active_deployments": len(self.active_deployments),
                "completed_deployments": len(self.deployment_history)
            },
            "rollbacks": {
                "pending_rollbacks": len(self.rollback_plans),
                "auto_rollback_enabled": self.auto_rollback_enabled
            },
            "storage": {
                "repository_size_mb": sum(
                    f.stat().st_size for f in Path(MODEL_REPO).rglob('*') if f.is_file()
                ) / 1024 / 1024,
                "backup_count": len(list(Path(BACKUP_DIR).glob("*.tar.gz")))
            },
            "git": {
                "enabled": self.git_repo is not None,
                "commits": len(list(self.git_repo.iter_commits())) if self.git_repo else 0,
                "tags": len(self.git_repo.tags) if self.git_repo else 0
            }
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down model version manager...")
        
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Close database connection
        if self.db_connection:
            self.db_connection.close()
        
        # Shutdown executors
        self.executor.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        self.logger.info("Model version manager shutdown complete")

async def main():
    """Main entry point"""
    version_manager = ModelVersionManager()
    
    try:
        await version_manager.start()
        
        # Example usage
        print("Creating sample model version...")
        
        # Create a sample model
        sample_model_data = pickle.dumps({"weights": np.random.random((100, 50))})
        
        version_id = await version_manager.create_model_version(
            model_name="security_detector",
            model_data=sample_model_data,
            created_by="system",
            metadata={"architecture": "neural_network", "layers": 3},
            tags=["security", "production"]
        )
        
        print(f"Created version: {version_id}")
        
        # Validate the version
        validation_results = await version_manager.validate_model_version(
            version_id, 
            validation_metrics={"accuracy": 0.92, "f1_score": 0.89}
        )
        
        print(f"Validation results: {validation_results['validation_passed']}")
        
        # Deploy the version
        deployment_id = await version_manager.deploy_model_version(
            "security_detector",
            version_id,
            ["node1", "node2", "node3"],
            UpdateStrategy.BLUE_GREEN
        )
        
        print(f"Deployment: {deployment_id}")
        
        # Get system status
        status = await version_manager.get_system_status()
        print("\nSystem Status:", json.dumps(status, indent=2))
        
        # Keep running for a while
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    finally:
        await version_manager.shutdown()

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║               QENEX Model Versioning System               ║
║              Zero-Downtime Model Lifecycle                ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())