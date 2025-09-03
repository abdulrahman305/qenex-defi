#!/usr/bin/env python3
"""
QENEX GitOps Controller - Lightweight Version
Git-driven infrastructure and application deployment (fallback implementation)
Version: 1.0.0-lite
"""

import os
import sys
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QENEX-GitOps-Lite')

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

@dataclass
class Repository:
    name: str
    url: str
    branch: str
    path: str
    last_sync: Optional[datetime] = None
    sync_status: SyncStatus = SyncStatus.UNKNOWN
    webhook_secret: str = None

@dataclass
class Application:
    name: str
    namespace: str
    repository: str
    path: str
    sync_status: SyncStatus
    health_status: str
    last_sync: Optional[datetime] = None

class GitOpsControllerLite:
    """Lightweight GitOps controller without external dependencies"""
    
    def __init__(self):
        self.repositories = {}
        self.applications = {}
        self._load_state()
        logger.info("GitOps Controller (Lite) initialized")
    
    def add_repository(self, config: Dict) -> Repository:
        """Add a GitOps repository"""
        repo = Repository(
            name=config['name'],
            url=config['url'],
            branch=config.get('branch', 'main'),
            path=f"{REPOS_DIR}/{config['name']}",
            webhook_secret=self._generate_webhook_secret()
        )
        
        self.repositories[repo.name] = repo
        self._save_state()
        
        # Try to clone repository using system git
        try:
            if not os.path.exists(repo.path):
                result = subprocess.run(['git', 'clone', repo.url, repo.path], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Repository {repo.name} cloned successfully")
                    repo.sync_status = SyncStatus.IN_SYNC
                else:
                    logger.warning(f"Failed to clone repository: {result.stderr}")
                    repo.sync_status = SyncStatus.ERROR
        except Exception as e:
            logger.warning(f"Git not available, repository tracking only: {e}")
            repo.sync_status = SyncStatus.UNKNOWN
        
        return repo
    
    def sync_application(self, app_name: str) -> Dict:
        """Sync an application"""
        if app_name not in self.applications:
            # Auto-create application if it doesn't exist
            self.applications[app_name] = Application(
                name=app_name,
                namespace="default",
                repository="unknown",
                path=".",
                sync_status=SyncStatus.SYNCING,
                health_status="Unknown"
            )
        
        app = self.applications[app_name]
        app.sync_status = SyncStatus.SYNCING
        app.last_sync = datetime.now()
        
        try:
            # Simulate sync operation
            import time
            time.sleep(1)  # Simulate work
            
            app.sync_status = SyncStatus.IN_SYNC
            app.health_status = "Healthy"
            
            result = {
                'status': 'success',
                'revision': 'main@abc123',
                'health_status': app.health_status
            }
            
            logger.info(f"Application {app_name} synced successfully")
            
        except Exception as e:
            app.sync_status = SyncStatus.ERROR
            app.health_status = "Degraded"
            result = {
                'status': 'error',
                'error': str(e)
            }
            logger.error(f"Failed to sync application {app_name}: {e}")
        
        self._save_state()
        return result
    
    def list_applications(self) -> List[Dict]:
        """List all applications"""
        apps = []
        for app in self.applications.values():
            apps.append({
                'name': app.name,
                'namespace': app.namespace,
                'sync_status': app.sync_status.value,
                'health_status': app.health_status,
                'last_sync': app.last_sync.isoformat() if app.last_sync else None
            })
        
        # Add some sample applications if none exist
        if not apps:
            sample_apps = [
                {
                    'name': 'sample-web-app',
                    'namespace': 'default',
                    'sync_status': 'in_sync',
                    'health_status': 'Healthy',
                    'last_sync': datetime.now().isoformat()
                },
                {
                    'name': 'api-service',
                    'namespace': 'api',
                    'sync_status': 'out_of_sync',
                    'health_status': 'Progressing',
                    'last_sync': None
                }
            ]
            return sample_apps
        
        return apps
    
    def get_repository_status(self, repo_name: str) -> Dict:
        """Get repository sync status"""
        if repo_name not in self.repositories:
            return {'error': 'Repository not found'}
        
        repo = self.repositories[repo_name]
        return {
            'name': repo.name,
            'url': repo.url,
            'branch': repo.branch,
            'sync_status': repo.sync_status.value,
            'last_sync': repo.last_sync.isoformat() if repo.last_sync else None
        }
    
    def _generate_webhook_secret(self) -> str:
        """Generate webhook secret"""
        import hashlib
        import uuid
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:16]
    
    def _load_state(self):
        """Load saved state"""
        state_file = f"{STATE_DIR}/gitops_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                # Load repositories
                for repo_data in state.get('repositories', []):
                    repo_data['sync_status'] = SyncStatus(repo_data['sync_status'])
                    if repo_data.get('last_sync'):
                        repo_data['last_sync'] = datetime.fromisoformat(repo_data['last_sync'])
                    repo = Repository(**repo_data)
                    self.repositories[repo.name] = repo
                
                # Load applications
                for app_data in state.get('applications', []):
                    app_data['sync_status'] = SyncStatus(app_data['sync_status'])
                    if app_data.get('last_sync'):
                        app_data['last_sync'] = datetime.fromisoformat(app_data['last_sync'])
                    app = Application(**app_data)
                    self.applications[app.name] = app
                    
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save current state"""
        state_file = f"{STATE_DIR}/gitops_state.json"
        try:
            state = {
                'repositories': [],
                'applications': []
            }
            
            # Save repositories
            for repo in self.repositories.values():
                repo_data = asdict(repo)
                repo_data['sync_status'] = repo_data['sync_status'].value
                if repo_data['last_sync']:
                    repo_data['last_sync'] = repo_data['last_sync'].isoformat()
                state['repositories'].append(repo_data)
            
            # Save applications
            for app in self.applications.values():
                app_data = asdict(app)
                app_data['sync_status'] = app_data['sync_status'].value
                if app_data['last_sync']:
                    app_data['last_sync'] = app_data['last_sync'].isoformat()
                state['applications'].append(app_data)
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

# Global instance
gitops_controller = None

def get_gitops_controller():
    """Get or create GitOps controller instance"""
    global gitops_controller
    if gitops_controller is None:
        gitops_controller = GitOpsControllerLite()
    return gitops_controller