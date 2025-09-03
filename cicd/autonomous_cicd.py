#!/usr/bin/env python3
"""
QENEX Autonomous CI/CD Engine
Self-managing continuous integration and deployment system
Version: 1.0.0
"""

import os
import sys
import json
import yaml
import subprocess
import threading
import asyncio
import hashlib
import shutil
import tempfile
# Handle imports gracefully
try:
    import docker
except ImportError:
    docker = None

try:
    import git
except ImportError:
    git = None

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

try:
    import requests
except ImportError:
    requests = None

try:
    import schedule
except ImportError:
    schedule = None
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QENEX-CICD')

# CI/CD Configuration
CICD_ROOT = "/opt/qenex-os/cicd"
PIPELINES_DIR = f"{CICD_ROOT}/pipelines"
ARTIFACTS_DIR = f"{CICD_ROOT}/artifacts"
LOGS_DIR = f"{CICD_ROOT}/logs"
CACHE_DIR = f"{CICD_ROOT}/cache"
WORKSPACE_DIR = f"{CICD_ROOT}/workspace"

# Create directories
for directory in [CICD_ROOT, PIPELINES_DIR, ARTIFACTS_DIR, LOGS_DIR, CACHE_DIR, WORKSPACE_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class DeploymentStrategy(Enum):
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"
    A_B_TESTING = "a_b_testing"

@dataclass
class Pipeline:
    id: str
    name: str
    source: str
    branch: str
    status: PipelineStatus
    stages: List[Dict]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    artifacts: List[str] = None
    metrics: Dict = None

@dataclass
class BuildConfig:
    language: str
    version: str
    dependencies: List[str]
    build_commands: List[str]
    test_commands: List[str]
    artifacts: List[str]
    cache_paths: List[str]
    environment: Dict[str, str]

class AutonomousCICD:
    """Autonomous CI/CD orchestration engine"""
    
    def __init__(self):
        self.pipelines = {}
        self.active_deployments = {}
        self.docker_client = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.monitoring_thread = None
        self.auto_fix_enabled = True
        self.learning_mode = True
        self.deployment_history = []
        self.performance_metrics = {}
        
        # Initialize Docker client
        try:
            if docker:
                self.docker_client = docker.from_env()
            else:
                self.docker_client = None
                logger.warning("Docker module not available, using local execution")
        except Exception as e:
            logger.warning(f"Docker not available, using local execution: {e}")
            self.docker_client = None
        
        # Load saved pipelines
        self._load_pipelines()
        
        # Start monitoring
        self._start_monitoring()
    
    def create_pipeline(self, config: Dict) -> Pipeline:
        """Create a new CI/CD pipeline"""
        pipeline_id = hashlib.md5(f"{config['name']}{datetime.now()}".encode()).hexdigest()[:8]
        
        pipeline = Pipeline(
            id=pipeline_id,
            name=config['name'],
            source=config.get('source', ''),
            branch=config.get('branch', 'main'),
            status=PipelineStatus.PENDING,
            stages=config.get('stages', self._default_stages()),
            created_at=datetime.now(),
            artifacts=[],
            metrics={}
        )
        
        self.pipelines[pipeline_id] = pipeline
        self._save_pipeline(pipeline)
        
        # Start pipeline execution
        self.executor.submit(self._execute_pipeline, pipeline_id)
        
        return pipeline
    
    def _default_stages(self) -> List[Dict]:
        """Default pipeline stages"""
        return [
            {
                'name': 'checkout',
                'type': 'source',
                'parallel': False
            },
            {
                'name': 'dependencies',
                'type': 'setup',
                'parallel': False
            },
            {
                'name': 'build',
                'type': 'build',
                'parallel': False
            },
            {
                'name': 'test',
                'type': 'test',
                'parallel': True
            },
            {
                'name': 'security_scan',
                'type': 'security',
                'parallel': True
            },
            {
                'name': 'package',
                'type': 'package',
                'parallel': False
            },
            {
                'name': 'deploy',
                'type': 'deploy',
                'parallel': False
            }
        ]
    
    async def _execute_pipeline(self, pipeline_id: str):
        """Execute a pipeline autonomously"""
        pipeline = self.pipelines[pipeline_id]
        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = datetime.now()
        
        workspace = f"{WORKSPACE_DIR}/{pipeline_id}"
        Path(workspace).mkdir(parents=True, exist_ok=True)
        
        try:
            for stage in pipeline.stages:
                logger.info(f"Executing stage: {stage['name']} for pipeline {pipeline_id}")
                
                if stage['type'] == 'source':
                    await self._checkout_source(pipeline, workspace)
                elif stage['type'] == 'setup':
                    await self._setup_dependencies(pipeline, workspace)
                elif stage['type'] == 'build':
                    await self._build_project(pipeline, workspace)
                elif stage['type'] == 'test':
                    await self._run_tests(pipeline, workspace)
                elif stage['type'] == 'security':
                    await self._security_scan(pipeline, workspace)
                elif stage['type'] == 'package':
                    await self._package_artifacts(pipeline, workspace)
                elif stage['type'] == 'deploy':
                    await self._deploy(pipeline, workspace)
            
            pipeline.status = PipelineStatus.SUCCESS
            pipeline.completed_at = datetime.now()
            
            # Learn from successful pipeline
            if self.learning_mode:
                self._learn_from_pipeline(pipeline)
            
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
            pipeline.status = PipelineStatus.FAILED
            pipeline.completed_at = datetime.now()
            
            # Attempt auto-fix
            if self.auto_fix_enabled:
                self._attempt_auto_fix(pipeline, str(e))
        
        finally:
            self._save_pipeline(pipeline)
            self._cleanup_workspace(workspace)
    
    async def _checkout_source(self, pipeline: Pipeline, workspace: str):
        """Checkout source code"""
        if pipeline.source.startswith('git'):
            if git:
                repo = git.Repo.clone_from(pipeline.source, workspace)
                repo.git.checkout(pipeline.branch)
            else:
                # Fallback to system git command
                try:
                    subprocess.run(['git', 'clone', '--branch', pipeline.branch, pipeline.source, workspace], check=True)
                    logger.info(f"Cloned {pipeline.source} using system git")
                except subprocess.CalledProcessError as e:
                    # If git command fails, try without branch specification
                    subprocess.run(['git', 'clone', pipeline.source, workspace], check=True)
                    os.chdir(workspace)
                    subprocess.run(['git', 'checkout', pipeline.branch], check=False)
                    logger.info(f"Cloned {pipeline.source} and attempted checkout to {pipeline.branch}")
        elif os.path.exists(pipeline.source):
            # Local directory
            shutil.copytree(pipeline.source, workspace, dirs_exist_ok=True)
        else:
            raise ValueError(f"Invalid source: {pipeline.source}")
    
    async def _setup_dependencies(self, pipeline: Pipeline, workspace: str):
        """Setup project dependencies"""
        os.chdir(workspace)
        
        # Detect project type and install dependencies
        if os.path.exists('package.json'):
            subprocess.run(['npm', 'install'], check=True)
        elif os.path.exists('requirements.txt'):
            subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
        elif os.path.exists('Gemfile'):
            subprocess.run(['bundle', 'install'], check=True)
        elif os.path.exists('pom.xml'):
            subprocess.run(['mvn', 'dependency:resolve'], check=True)
        elif os.path.exists('go.mod'):
            subprocess.run(['go', 'mod', 'download'], check=True)
    
    async def _build_project(self, pipeline: Pipeline, workspace: str):
        """Build the project"""
        os.chdir(workspace)
        
        # Detect build system
        if os.path.exists('package.json'):
            subprocess.run(['npm', 'run', 'build'], check=False)
        elif os.path.exists('Makefile'):
            subprocess.run(['make'], check=True)
        elif os.path.exists('pom.xml'):
            subprocess.run(['mvn', 'package'], check=True)
        elif os.path.exists('build.gradle'):
            subprocess.run(['gradle', 'build'], check=True)
        elif os.path.exists('cargo.toml'):
            subprocess.run(['cargo', 'build', '--release'], check=True)
        elif os.path.exists('setup.py'):
            subprocess.run(['python', 'setup.py', 'build'], check=True)
    
    async def _run_tests(self, pipeline: Pipeline, workspace: str):
        """Run automated tests"""
        os.chdir(workspace)
        test_results = {}
        
        # Run different test types
        if os.path.exists('package.json'):
            result = subprocess.run(['npm', 'test'], capture_output=True, text=True)
            test_results['unit'] = result.returncode == 0
        
        if os.path.exists('pytest.ini') or os.path.exists('tests'):
            result = subprocess.run(['pytest', '--tb=short'], capture_output=True, text=True)
            test_results['pytest'] = result.returncode == 0
        
        # Store test metrics
        pipeline.metrics['tests'] = test_results
        pipeline.metrics['test_coverage'] = self._calculate_coverage(workspace)
    
    async def _security_scan(self, pipeline: Pipeline, workspace: str):
        """Perform security scanning"""
        os.chdir(workspace)
        vulnerabilities = []
        
        # Run security tools
        security_tools = [
            (['bandit', '-r', '.'], 'python'),
            (['npm', 'audit'], 'node'),
            (['safety', 'check'], 'python'),
            (['trivy', 'fs', '.'], 'container')
        ]
        
        for cmd, tool_type in security_tools:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    vulnerabilities.append({
                        'tool': cmd[0],
                        'type': tool_type,
                        'issues': result.stdout
                    })
            except:
                pass
        
        pipeline.metrics['vulnerabilities'] = vulnerabilities
        
        # Auto-fix critical vulnerabilities
        if vulnerabilities and self.auto_fix_enabled:
            self._fix_vulnerabilities(workspace, vulnerabilities)
    
    async def _package_artifacts(self, pipeline: Pipeline, workspace: str):
        """Package build artifacts"""
        os.chdir(workspace)
        artifacts = []
        
        # Create artifact archive
        artifact_name = f"{pipeline.name}-{pipeline.id}.tar.gz"
        artifact_path = f"{ARTIFACTS_DIR}/{artifact_name}"
        
        # Determine what to package
        if os.path.exists('dist'):
            subprocess.run(['tar', '-czf', artifact_path, 'dist'])
            artifacts.append(artifact_path)
        elif os.path.exists('build'):
            subprocess.run(['tar', '-czf', artifact_path, 'build'])
            artifacts.append(artifact_path)
        elif os.path.exists('target'):
            subprocess.run(['tar', '-czf', artifact_path, 'target'])
            artifacts.append(artifact_path)
        
        pipeline.artifacts = artifacts
    
    async def _deploy(self, pipeline: Pipeline, workspace: str):
        """Deploy application using intelligent strategies"""
        deployment_config = self._analyze_deployment_needs(pipeline)
        strategy = deployment_config['strategy']
        
        if strategy == DeploymentStrategy.ROLLING:
            await self._rolling_deployment(pipeline, deployment_config)
        elif strategy == DeploymentStrategy.BLUE_GREEN:
            await self._blue_green_deployment(pipeline, deployment_config)
        elif strategy == DeploymentStrategy.CANARY:
            await self._canary_deployment(pipeline, deployment_config)
        else:
            await self._simple_deployment(pipeline, deployment_config)
        
        # Monitor deployment health
        self._monitor_deployment_health(pipeline)
    
    def _analyze_deployment_needs(self, pipeline: Pipeline) -> Dict:
        """Analyze and determine best deployment strategy"""
        config = {
            'strategy': DeploymentStrategy.ROLLING,
            'replicas': 3,
            'health_check_url': '/health',
            'rollback_on_failure': True
        }
        
        # Analyze pipeline metrics to determine strategy
        if pipeline.metrics.get('test_coverage', 0) > 80:
            config['strategy'] = DeploymentStrategy.BLUE_GREEN
        elif pipeline.metrics.get('vulnerabilities'):
            config['strategy'] = DeploymentStrategy.CANARY
            config['canary_percentage'] = 10
        
        return config
    
    async def _rolling_deployment(self, pipeline: Pipeline, config: Dict):
        """Perform rolling deployment"""
        logger.info(f"Starting rolling deployment for {pipeline.name}")
        
        # Deploy to each replica gradually
        for i in range(config['replicas']):
            logger.info(f"Deploying to replica {i+1}/{config['replicas']}")
            
            # Deploy to replica
            await self._deploy_to_instance(pipeline, f"instance-{i}")
            
            # Health check
            if not self._health_check(f"instance-{i}", config['health_check_url']):
                logger.error(f"Health check failed for instance-{i}")
                if config['rollback_on_failure']:
                    await self._rollback_deployment(pipeline)
                    break
            
            # Wait before next replica
            await asyncio.sleep(5)
    
    async def _blue_green_deployment(self, pipeline: Pipeline, config: Dict):
        """Perform blue-green deployment"""
        logger.info(f"Starting blue-green deployment for {pipeline.name}")
        
        # Deploy to green environment
        await self._deploy_to_environment(pipeline, 'green')
        
        # Run smoke tests
        if self._smoke_test('green'):
            # Switch traffic to green
            self._switch_traffic('blue', 'green')
            logger.info("Successfully switched to green environment")
        else:
            logger.error("Smoke tests failed, keeping blue environment")
    
    async def _canary_deployment(self, pipeline: Pipeline, config: Dict):
        """Perform canary deployment"""
        logger.info(f"Starting canary deployment for {pipeline.name}")
        
        canary_percentage = config.get('canary_percentage', 10)
        
        # Deploy canary version
        await self._deploy_canary(pipeline, canary_percentage)
        
        # Monitor canary metrics
        await asyncio.sleep(60)  # Monitor for 1 minute
        
        if self._analyze_canary_metrics():
            # Gradually increase traffic
            for percentage in [25, 50, 75, 100]:
                await self._update_canary_traffic(percentage)
                await asyncio.sleep(30)
                
                if not self._analyze_canary_metrics():
                    await self._rollback_canary()
                    break
        else:
            await self._rollback_canary()
    
    def _monitor_deployment_health(self, pipeline: Pipeline):
        """Monitor deployment health and auto-heal if needed"""
        def monitor():
            while pipeline.id in self.active_deployments:
                health_status = self._check_deployment_health(pipeline)
                
                if not health_status['healthy']:
                    logger.warning(f"Deployment {pipeline.id} unhealthy: {health_status['reason']}")
                    
                    if self.auto_fix_enabled:
                        self._auto_heal_deployment(pipeline, health_status)
                
                time.sleep(30)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _auto_heal_deployment(self, pipeline: Pipeline, health_status: Dict):
        """Automatically heal unhealthy deployments"""
        reason = health_status['reason']
        
        if 'memory' in reason.lower():
            # Scale up if memory issues
            self._scale_deployment(pipeline, scale_up=True)
        elif 'cpu' in reason.lower():
            # Optimize CPU usage
            self._optimize_cpu_usage(pipeline)
        elif 'error_rate' in reason.lower():
            # Rollback if high error rate
            asyncio.run(self._rollback_deployment(pipeline))
        else:
            # Restart unhealthy instances
            self._restart_unhealthy_instances(pipeline)
    
    def _learn_from_pipeline(self, pipeline: Pipeline):
        """Learn from pipeline execution to improve future runs"""
        # Store successful patterns
        success_pattern = {
            'duration': (pipeline.completed_at - pipeline.started_at).total_seconds(),
            'stages': pipeline.stages,
            'metrics': pipeline.metrics
        }
        
        # Update learning model
        if pipeline.name not in self.performance_metrics:
            self.performance_metrics[pipeline.name] = []
        
        self.performance_metrics[pipeline.name].append(success_pattern)
        
        # Optimize future pipelines based on learning
        self._optimize_pipeline_config(pipeline.name)
    
    def _attempt_auto_fix(self, pipeline: Pipeline, error: str):
        """Attempt to automatically fix pipeline failures"""
        logger.info(f"Attempting auto-fix for pipeline {pipeline.id}")
        
        fixes_attempted = []
        
        # Common fixes based on error patterns
        if 'permission denied' in error.lower():
            fixes_attempted.append('permissions')
            subprocess.run(['chmod', '-R', '755', f"{WORKSPACE_DIR}/{pipeline.id}"])
        
        if 'no such file' in error.lower():
            fixes_attempted.append('missing_files')
            self._restore_missing_files(pipeline)
        
        if 'timeout' in error.lower():
            fixes_attempted.append('timeout')
            # Increase timeout and retry
            pipeline.status = PipelineStatus.RETRYING
            self.executor.submit(self._execute_pipeline, pipeline.id)
        
        if 'out of memory' in error.lower():
            fixes_attempted.append('memory')
            self._optimize_memory_usage(pipeline)
            pipeline.status = PipelineStatus.RETRYING
            self.executor.submit(self._execute_pipeline, pipeline.id)
        
        logger.info(f"Auto-fix attempted: {fixes_attempted}")
    
    def get_pipeline_status(self, pipeline_id: str) -> Dict:
        """Get detailed pipeline status"""
        if pipeline_id not in self.pipelines:
            return {'error': 'Pipeline not found'}
        
        pipeline = self.pipelines[pipeline_id]
        return {
            'id': pipeline.id,
            'name': pipeline.name,
            'status': pipeline.status.value,
            'started_at': pipeline.started_at.isoformat() if pipeline.started_at else None,
            'completed_at': pipeline.completed_at.isoformat() if pipeline.completed_at else None,
            'duration': self._calculate_duration(pipeline),
            'stages': pipeline.stages,
            'artifacts': pipeline.artifacts,
            'metrics': pipeline.metrics
        }
    
    def list_pipelines(self) -> List[Dict]:
        """List all pipelines"""
        return [self.get_pipeline_status(pid) for pid in self.pipelines]
    
    def trigger_pipeline(self, name: str, source: str, branch: str = 'main') -> str:
        """Manually trigger a pipeline"""
        config = {
            'name': name,
            'source': source,
            'branch': branch
        }
        
        pipeline = self.create_pipeline(config)
        return pipeline.id
    
    def cancel_pipeline(self, pipeline_id: str) -> bool:
        """Cancel a running pipeline"""
        if pipeline_id in self.pipelines:
            pipeline = self.pipelines[pipeline_id]
            pipeline.status = PipelineStatus.CANCELLED
            pipeline.completed_at = datetime.now()
            self._save_pipeline(pipeline)
            return True
        return False
    
    def _calculate_duration(self, pipeline: Pipeline) -> float:
        """Calculate pipeline duration"""
        if pipeline.started_at and pipeline.completed_at:
            return (pipeline.completed_at - pipeline.started_at).total_seconds()
        elif pipeline.started_at:
            return (datetime.now() - pipeline.started_at).total_seconds()
        return 0
    
    def _save_pipeline(self, pipeline: Pipeline):
        """Save pipeline state"""
        pipeline_file = f"{PIPELINES_DIR}/{pipeline.id}.json"
        with open(pipeline_file, 'w') as f:
            data = asdict(pipeline)
            # Convert datetime objects to strings
            for key in ['created_at', 'started_at', 'completed_at']:
                if data[key]:
                    data[key] = data[key].isoformat()
            # Convert enum to string
            if isinstance(data.get('status'), PipelineStatus):
                data['status'] = data['status'].value
            elif hasattr(data.get('status'), 'value'):
                data['status'] = data['status'].value
            json.dump(data, f, indent=2)
    
    def _load_pipelines(self):
        """Load saved pipelines"""
        for pipeline_file in Path(PIPELINES_DIR).glob('*.json'):
            with open(pipeline_file, 'r') as f:
                data = json.load(f)
                # Convert strings back to datetime
                for key in ['created_at', 'started_at', 'completed_at']:
                    if data[key]:
                        data[key] = datetime.fromisoformat(data[key])
                # Convert status string to enum
                data['status'] = PipelineStatus(data['status'])
                
                pipeline = Pipeline(**data)
                self.pipelines[pipeline.id] = pipeline
    
    def _start_monitoring(self):
        """Start background monitoring"""
        def monitor():
            while True:
                # Clean old artifacts
                self._cleanup_old_artifacts()
                
                # Check pipeline health
                for pipeline_id, pipeline in self.pipelines.items():
                    if pipeline.status == PipelineStatus.RUNNING:
                        # Check for stuck pipelines
                        if pipeline.started_at:
                            duration = (datetime.now() - pipeline.started_at).total_seconds()
                            if duration > 3600:  # 1 hour timeout
                                logger.warning(f"Pipeline {pipeline_id} exceeded timeout")
                                pipeline.status = PipelineStatus.FAILED
                                self._save_pipeline(pipeline)
                
                time.sleep(60)
        
        self.monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self.monitoring_thread.start()
    
    def _cleanup_old_artifacts(self):
        """Clean up old artifacts"""
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for artifact_file in Path(ARTIFACTS_DIR).glob('*'):
            if artifact_file.stat().st_mtime < cutoff_date.timestamp():
                artifact_file.unlink()
    
    def _cleanup_workspace(self, workspace: str):
        """Clean up pipeline workspace"""
        try:
            shutil.rmtree(workspace)
        except:
            pass
    
    # Placeholder methods for additional functionality
    def _calculate_coverage(self, workspace: str) -> float:
        return 85.0  # Placeholder
    
    def _fix_vulnerabilities(self, workspace: str, vulnerabilities: List):
        pass  # Placeholder
    
    def _deploy_to_instance(self, pipeline: Pipeline, instance: str):
        pass  # Placeholder
    
    def _health_check(self, instance: str, url: str) -> bool:
        return True  # Placeholder
    
    def _rollback_deployment(self, pipeline: Pipeline):
        pass  # Placeholder
    
    def _deploy_to_environment(self, pipeline: Pipeline, env: str):
        pass  # Placeholder
    
    def _smoke_test(self, env: str) -> bool:
        return True  # Placeholder
    
    def _switch_traffic(self, from_env: str, to_env: str):
        pass  # Placeholder
    
    def _deploy_canary(self, pipeline: Pipeline, percentage: int):
        pass  # Placeholder
    
    def _analyze_canary_metrics(self) -> bool:
        return True  # Placeholder
    
    def _update_canary_traffic(self, percentage: int):
        pass  # Placeholder
    
    def _rollback_canary(self):
        pass  # Placeholder
    
    def _check_deployment_health(self, pipeline: Pipeline) -> Dict:
        return {'healthy': True, 'reason': ''}  # Placeholder
    
    def _scale_deployment(self, pipeline: Pipeline, scale_up: bool):
        pass  # Placeholder
    
    def _optimize_cpu_usage(self, pipeline: Pipeline):
        pass  # Placeholder
    
    def _restart_unhealthy_instances(self, pipeline: Pipeline):
        pass  # Placeholder
    
    def _optimize_pipeline_config(self, name: str):
        pass  # Placeholder
    
    def _restore_missing_files(self, pipeline: Pipeline):
        pass  # Placeholder
    
    def _optimize_memory_usage(self, pipeline: Pipeline):
        pass  # Placeholder
    
    def _simple_deployment(self, pipeline: Pipeline, config: Dict):
        pass  # Placeholder

# Global CI/CD instance
cicd_engine = None

def get_cicd_engine():
    """Get or create CI/CD engine instance"""
    global cicd_engine
    if cicd_engine is None:
        cicd_engine = AutonomousCICD()
    return cicd_engine

if __name__ == '__main__':
    # Start CI/CD engine
    engine = get_cicd_engine()
    logger.info("QENEX Autonomous CI/CD Engine started")