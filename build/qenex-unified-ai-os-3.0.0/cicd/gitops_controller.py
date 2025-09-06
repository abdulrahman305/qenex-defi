#!/usr/bin/env python3
"""
QENEX GitOps Controller
Git-driven infrastructure and application deployment
Version: 1.0.0
"""

import os
import sys
import json
import yaml
import git
import asyncio
import hashlib
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import kubernetes
from kubernetes import client, config, watch
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QENEX-GitOps')

# GitOps Configuration
GITOPS_ROOT = "/opt/qenex-os/gitops"
REPOS_DIR = f"{GITOPS_ROOT}/repos"
MANIFESTS_DIR = f"{GITOPS_ROOT}/manifests"
STATE_DIR = f"{GITOPS_ROOT}/state"
SYNC_DIR = f"{GITOPS_ROOT}/sync"

for directory in [GITOPS_ROOT, REPOS_DIR, MANIFESTS_DIR, STATE_DIR, SYNC_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

class SyncStatus(Enum):
    IN_SYNC = "in_sync"
    OUT_OF_SYNC = "out_of_sync"
    SYNCING = "syncing"
    UNKNOWN = "unknown"
    ERROR = "error"

class ReconciliationMode(Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SEMI_AUTO = "semi_auto"

@dataclass
class GitOpsRepository:
    name: str
    url: str
    branch: str
    path: str
    target_namespace: str
    sync_policy: Dict
    credentials: Optional[Dict] = None
    webhook_secret: Optional[str] = None

@dataclass
class Application:
    name: str
    namespace: str
    repository: GitOpsRepository
    manifests: List[str]
    sync_status: SyncStatus
    health_status: str
    last_sync: Optional[datetime] = None
    revision: Optional[str] = None

class GitOpsController:
    """GitOps controller for autonomous deployments"""
    
    def __init__(self):
        self.repositories = {}
        self.applications = {}
        self.sync_threads = {}
        self.reconciliation_mode = ReconciliationMode.AUTOMATIC
        self.sync_interval = 300  # 5 minutes
        self.drift_detection_enabled = True
        self.auto_rollback_enabled = True
        self.k8s_client = None
        
        # Initialize Kubernetes client
        self._init_k8s_client()
        
        # Load existing repositories
        self._load_repositories()
        
        # Start reconciliation loop
        self._start_reconciliation_loop()
    
    def _init_k8s_client(self):
        """Initialize Kubernetes client"""
        try:
            # Try in-cluster config first
            config.load_incluster_config()
        except:
            try:
                # Fall back to kubeconfig
                config.load_kube_config()
            except:
                logger.warning("Kubernetes not available, using mock mode")
                return
        
        self.k8s_client = client.ApiClient()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
    
    def add_repository(self, repo_config: Dict) -> GitOpsRepository:
        """Add a GitOps repository"""
        repo = GitOpsRepository(
            name=repo_config['name'],
            url=repo_config['url'],
            branch=repo_config.get('branch', 'main'),
            path=repo_config.get('path', '/'),
            target_namespace=repo_config.get('namespace', 'default'),
            sync_policy=repo_config.get('sync_policy', {
                'automated': True,
                'prune': True,
                'self_heal': True
            }),
            credentials=repo_config.get('credentials'),
            webhook_secret=hashlib.sha256(os.urandom(32)).hexdigest()
        )
        
        self.repositories[repo.name] = repo
        
        # Clone repository
        self._clone_repository(repo)
        
        # Discover applications
        self._discover_applications(repo)
        
        # Start watching repository
        self._watch_repository(repo)
        
        return repo
    
    def _clone_repository(self, repo: GitOpsRepository):
        """Clone or update GitOps repository"""
        repo_path = f"{REPOS_DIR}/{repo.name}"
        
        try:
            if os.path.exists(repo_path):
                # Pull latest changes
                git_repo = git.Repo(repo_path)
                git_repo.remotes.origin.pull(repo.branch)
            else:
                # Clone repository
                if repo.credentials:
                    # Use credentials if provided
                    url_with_auth = self._add_git_credentials(repo.url, repo.credentials)
                    git.Repo.clone_from(url_with_auth, repo_path, branch=repo.branch)
                else:
                    git.Repo.clone_from(repo.url, repo_path, branch=repo.branch)
            
            logger.info(f"Repository {repo.name} synced successfully")
        except Exception as e:
            logger.error(f"Failed to sync repository {repo.name}: {e}")
    
    def _discover_applications(self, repo: GitOpsRepository):
        """Discover applications in repository"""
        repo_path = f"{REPOS_DIR}/{repo.name}"
        base_path = f"{repo_path}{repo.path}"
        
        # Look for application manifests
        for root, dirs, files in os.walk(base_path):
            # Skip .git directory
            if '.git' in root:
                continue
            
            yaml_files = [f for f in files if f.endswith(('.yaml', '.yml'))]
            
            if yaml_files:
                app_name = os.path.basename(root)
                if app_name == os.path.basename(base_path):
                    app_name = repo.name
                
                app = Application(
                    name=app_name,
                    namespace=repo.target_namespace,
                    repository=repo,
                    manifests=[os.path.join(root, f) for f in yaml_files],
                    sync_status=SyncStatus.UNKNOWN,
                    health_status="Unknown"
                )
                
                self.applications[app_name] = app
                logger.info(f"Discovered application: {app_name}")
    
    def _watch_repository(self, repo: GitOpsRepository):
        """Watch repository for changes"""
        repo_path = f"{REPOS_DIR}/{repo.name}"
        
        class GitChangeHandler(FileSystemEventHandler):
            def __init__(self, controller, repo):
                self.controller = controller
                self.repo = repo
            
            def on_modified(self, event):
                if not event.is_directory and '.git' not in event.src_path:
                    logger.info(f"Change detected in {event.src_path}")
                    self.controller._handle_repository_change(self.repo)
        
        handler = GitChangeHandler(self, repo)
        observer = Observer()
        observer.schedule(handler, repo_path, recursive=True)
        observer.start()
        
        self.sync_threads[repo.name] = observer
    
    def _handle_repository_change(self, repo: GitOpsRepository):
        """Handle repository changes"""
        # Pull latest changes
        self._clone_repository(repo)
        
        # Rediscover applications
        self._discover_applications(repo)
        
        # Sync applications if automatic
        if repo.sync_policy.get('automated', False):
            for app_name, app in self.applications.items():
                if app.repository.name == repo.name:
                    self.sync_application(app_name)
    
    def sync_application(self, app_name: str) -> Dict:
        """Sync application with Git state"""
        if app_name not in self.applications:
            return {'error': 'Application not found'}
        
        app = self.applications[app_name]
        app.sync_status = SyncStatus.SYNCING
        
        try:
            # Read manifests
            manifests = []
            for manifest_file in app.manifests:
                with open(manifest_file, 'r') as f:
                    docs = yaml.safe_load_all(f)
                    manifests.extend([d for d in docs if d])
            
            # Apply manifests to cluster
            results = []
            for manifest in manifests:
                result = self._apply_manifest(manifest, app.namespace)
                results.append(result)
            
            app.sync_status = SyncStatus.IN_SYNC
            app.last_sync = datetime.now()
            
            # Get current revision
            repo_path = f"{REPOS_DIR}/{app.repository.name}"
            git_repo = git.Repo(repo_path)
            app.revision = git_repo.head.commit.hexsha[:7]
            
            # Check application health
            app.health_status = self._check_application_health(app)
            
            return {
                'status': 'success',
                'app': app_name,
                'sync_status': app.sync_status.value,
                'health_status': app.health_status,
                'revision': app.revision,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Failed to sync application {app_name}: {e}")
            app.sync_status = SyncStatus.ERROR
            
            # Auto-rollback if enabled
            if self.auto_rollback_enabled:
                self._rollback_application(app)
            
            return {
                'status': 'error',
                'app': app_name,
                'error': str(e)
            }
    
    def _apply_manifest(self, manifest: Dict, namespace: str) -> Dict:
        """Apply Kubernetes manifest"""
        if not self.k8s_client:
            # Mock mode
            return {'action': 'mock_applied', 'resource': manifest.get('metadata', {}).get('name')}
        
        kind = manifest.get('kind')
        metadata = manifest.get('metadata', {})
        name = metadata.get('name')
        
        # Ensure namespace
        metadata['namespace'] = namespace
        
        try:
            if kind == 'Deployment':
                return self._apply_deployment(manifest)
            elif kind == 'Service':
                return self._apply_service(manifest)
            elif kind == 'ConfigMap':
                return self._apply_configmap(manifest)
            elif kind == 'Secret':
                return self._apply_secret(manifest)
            else:
                # Generic apply using kubectl
                return self._kubectl_apply(manifest)
        except Exception as e:
            return {'action': 'error', 'resource': name, 'error': str(e)}
    
    def _apply_deployment(self, manifest: Dict) -> Dict:
        """Apply deployment manifest"""
        name = manifest['metadata']['name']
        namespace = manifest['metadata']['namespace']
        
        try:
            # Check if deployment exists
            self.apps_v1.read_namespaced_deployment(name, namespace)
            # Update existing
            self.apps_v1.patch_namespaced_deployment(name, namespace, manifest)
            return {'action': 'updated', 'resource': f'deployment/{name}'}
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                # Create new
                self.apps_v1.create_namespaced_deployment(namespace, manifest)
                return {'action': 'created', 'resource': f'deployment/{name}'}
            raise
    
    def _apply_service(self, manifest: Dict) -> Dict:
        """Apply service manifest"""
        name = manifest['metadata']['name']
        namespace = manifest['metadata']['namespace']
        
        try:
            self.v1.read_namespaced_service(name, namespace)
            self.v1.patch_namespaced_service(name, namespace, manifest)
            return {'action': 'updated', 'resource': f'service/{name}'}
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                self.v1.create_namespaced_service(namespace, manifest)
                return {'action': 'created', 'resource': f'service/{name}'}
            raise
    
    def _apply_configmap(self, manifest: Dict) -> Dict:
        """Apply configmap manifest"""
        name = manifest['metadata']['name']
        namespace = manifest['metadata']['namespace']
        
        try:
            self.v1.read_namespaced_config_map(name, namespace)
            self.v1.patch_namespaced_config_map(name, namespace, manifest)
            return {'action': 'updated', 'resource': f'configmap/{name}'}
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                self.v1.create_namespaced_config_map(namespace, manifest)
                return {'action': 'created', 'resource': f'configmap/{name}'}
            raise
    
    def _apply_secret(self, manifest: Dict) -> Dict:
        """Apply secret manifest"""
        name = manifest['metadata']['name']
        namespace = manifest['metadata']['namespace']
        
        try:
            self.v1.read_namespaced_secret(name, namespace)
            self.v1.patch_namespaced_secret(name, namespace, manifest)
            return {'action': 'updated', 'resource': f'secret/{name}'}
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                self.v1.create_namespaced_secret(namespace, manifest)
                return {'action': 'created', 'resource': f'secret/{name}'}
            raise
    
    def _kubectl_apply(self, manifest: Dict) -> Dict:
        """Apply manifest using kubectl"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(manifest, f)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ['kubectl', 'apply', '-f', temp_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {'action': 'applied', 'output': result.stdout}
            else:
                return {'action': 'error', 'error': result.stderr}
        finally:
            os.unlink(temp_file)
    
    def _check_application_health(self, app: Application) -> str:
        """Check application health status"""
        if not self.k8s_client:
            return "Unknown"
        
        try:
            # Check deployments
            for manifest_file in app.manifests:
                with open(manifest_file, 'r') as f:
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        if doc and doc.get('kind') == 'Deployment':
                            name = doc['metadata']['name']
                            deployment = self.apps_v1.read_namespaced_deployment(
                                name, app.namespace
                            )
                            
                            if deployment.status.replicas != deployment.status.ready_replicas:
                                return "Degraded"
            
            return "Healthy"
        except:
            return "Unknown"
    
    def _rollback_application(self, app: Application):
        """Rollback application to previous version"""
        logger.info(f"Rolling back application {app.name}")
        
        # Get previous commit
        repo_path = f"{REPOS_DIR}/{app.repository.name}"
        git_repo = git.Repo(repo_path)
        
        # Checkout previous commit
        git_repo.git.checkout('HEAD~1')
        
        # Reapply manifests
        self.sync_application(app.name)
        
        # Restore HEAD
        git_repo.git.checkout(app.repository.branch)
    
    def _start_reconciliation_loop(self):
        """Start automatic reconciliation loop"""
        def reconcile():
            while True:
                if self.reconciliation_mode == ReconciliationMode.AUTOMATIC:
                    for app_name, app in self.applications.items():
                        # Check drift
                        if self.drift_detection_enabled:
                            if self._detect_drift(app):
                                logger.info(f"Drift detected in {app_name}, syncing...")
                                self.sync_application(app_name)
                        
                        # Auto-sync if policy enabled
                        if app.repository.sync_policy.get('automated'):
                            # Check if sync needed
                            if app.sync_status == SyncStatus.OUT_OF_SYNC:
                                self.sync_application(app_name)
                
                # Wait for next cycle
                asyncio.run(asyncio.sleep(self.sync_interval))
        
        threading.Thread(target=reconcile, daemon=True).start()
    
    def _detect_drift(self, app: Application) -> bool:
        """Detect configuration drift"""
        if not self.k8s_client:
            return False
        
        try:
            # Compare Git state with cluster state
            for manifest_file in app.manifests:
                with open(manifest_file, 'r') as f:
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        if doc:
                            if self._has_drift(doc, app.namespace):
                                return True
            return False
        except:
            return False
    
    def _has_drift(self, manifest: Dict, namespace: str) -> bool:
        """Check if resource has drifted"""
        kind = manifest.get('kind')
        name = manifest['metadata']['name']
        
        try:
            if kind == 'Deployment':
                current = self.apps_v1.read_namespaced_deployment(name, namespace)
                # Compare specs
                return current.spec != manifest['spec']
            # Add more resource types as needed
        except:
            return True
        
        return False
    
    def get_application_status(self, app_name: str) -> Dict:
        """Get application status"""
        if app_name not in self.applications:
            return {'error': 'Application not found'}
        
        app = self.applications[app_name]
        return {
            'name': app.name,
            'namespace': app.namespace,
            'repository': app.repository.name,
            'sync_status': app.sync_status.value,
            'health_status': app.health_status,
            'last_sync': app.last_sync.isoformat() if app.last_sync else None,
            'revision': app.revision,
            'manifests': len(app.manifests)
        }
    
    def list_applications(self) -> List[Dict]:
        """List all applications"""
        return [self.get_application_status(name) for name in self.applications]
    
    def refresh_application(self, app_name: str):
        """Refresh application from Git"""
        if app_name in self.applications:
            app = self.applications[app_name]
            self._clone_repository(app.repository)
            self._discover_applications(app.repository)
    
    def _add_git_credentials(self, url: str, credentials: Dict) -> str:
        """Add credentials to Git URL"""
        if 'username' in credentials and 'password' in credentials:
            # Parse URL and add credentials
            if url.startswith('https://'):
                return url.replace('https://', 
                    f"https://{credentials['username']}:{credentials['password']}@")
        return url
    
    def _load_repositories(self):
        """Load saved repositories"""
        state_file = f"{STATE_DIR}/repositories.json"
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                repos = json.load(f)
                for repo_config in repos:
                    self.add_repository(repo_config)
    
    def save_state(self):
        """Save current state"""
        state_file = f"{STATE_DIR}/repositories.json"
        repos = []
        
        for repo in self.repositories.values():
            repos.append({
                'name': repo.name,
                'url': repo.url,
                'branch': repo.branch,
                'path': repo.path,
                'namespace': repo.target_namespace,
                'sync_policy': repo.sync_policy
            })
        
        with open(state_file, 'w') as f:
            json.dump(repos, f, indent=2)

# Global GitOps controller
gitops_controller = None

def get_gitops_controller():
    """Get or create GitOps controller"""
    global gitops_controller
    if gitops_controller is None:
        gitops_controller = GitOpsController()
    return gitops_controller

if __name__ == '__main__':
    controller = get_gitops_controller()
    logger.info("QENEX GitOps Controller started")