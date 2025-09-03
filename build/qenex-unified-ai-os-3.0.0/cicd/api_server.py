#!/usr/bin/env python3
"""
QENEX CI/CD REST API Server
Comprehensive REST API for external integrations and CI/CD management
Version: 1.0.0
"""

import os
import sys
import json
import asyncio
import logging
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import threading
import tempfile
import subprocess

# Web framework
try:
    from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks, UploadFile, File
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

# Import QENEX CI/CD components
try:
    from autonomous_cicd import AutonomousCICD, Pipeline, PipelineStatus, DeploymentStrategy
    from distributed_executor import DistributedExecutor, ExecutionTask, WorkerNode, TaskStatus
    from secret_manager import SecretManager, SecretType, SecretScope
    from cache_manager import CacheManager, CacheType
    QENEX_COMPONENTS_AVAILABLE = True
except ImportError:
    QENEX_COMPONENTS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('QENEX-API')

# Pydantic models for API
class PipelineCreate(BaseModel):
    name: str = Field(..., description="Pipeline name")
    source: str = Field(..., description="Source repository URL")
    branch: str = Field(default="main", description="Branch to build")
    stages: List[Dict] = Field(default=[], description="Pipeline stages")
    environment: Dict[str, str] = Field(default={}, description="Environment variables")
    triggers: List[str] = Field(default=[], description="Trigger conditions")
    tags: List[str] = Field(default=[], description="Pipeline tags")

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    stages: Optional[List[Dict]] = None
    environment: Optional[Dict[str, str]] = None
    triggers: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class PipelineResponse(BaseModel):
    id: str
    name: str
    source: str
    branch: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    stages: List[Dict]
    metrics: Optional[Dict] = None
    tags: List[str] = []

class SecretCreate(BaseModel):
    name: str = Field(..., description="Secret name")
    value: str = Field(..., description="Secret value")
    secret_type: str = Field(default="custom", description="Secret type")
    scope: str = Field(default="global", description="Secret scope")
    scope_id: str = Field(default="default", description="Scope identifier")
    description: str = Field(default="", description="Secret description")
    expires_days: Optional[int] = Field(default=None, description="Expiration in days")
    tags: List[str] = Field(default=[], description="Secret tags")

class SecretResponse(BaseModel):
    id: str
    name: str
    type: str
    scope: str
    scope_id: str
    description: str
    created_at: str
    expires_at: Optional[str] = None
    tags: List[str]

class TaskCreate(BaseModel):
    pipeline_id: str = Field(..., description="Pipeline ID")
    stage_name: str = Field(..., description="Stage name")
    command: str = Field(..., description="Command to execute")
    environment: Dict[str, str] = Field(default={}, description="Environment variables")
    working_directory: str = Field(default="/tmp", description="Working directory")
    timeout: int = Field(default=3600, description="Timeout in seconds")
    priority: int = Field(default=5, description="Task priority (1-10)")
    dependencies: List[str] = Field(default=[], description="Task dependencies")

class TaskResponse(BaseModel):
    id: str
    pipeline_id: str
    stage_name: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    worker_id: Optional[str] = None
    result: Optional[Dict] = None

class WorkerRegister(BaseModel):
    hostname: str = Field(..., description="Worker hostname")
    ip_address: str = Field(..., description="Worker IP address")
    port: int = Field(default=8080, description="Worker port")
    worker_type: str = Field(default="native", description="Worker type")
    capacity: Dict[str, Any] = Field(..., description="Worker capacity")
    tags: List[str] = Field(default=[], description="Worker tags")

class APIKey(BaseModel):
    key: str
    name: str
    permissions: List[str]
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None

class QENEXAPIServer:
    """Main API server class"""
    
    def __init__(self, config: Dict = None):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for the API server")
        
        self.config = config or {}
        self.app = FastAPI(
            title="QENEX CI/CD API",
            description="Comprehensive REST API for QENEX CI/CD System",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Security
        self.security = HTTPBearer()
        self.jwt_secret = self.config.get('jwt_secret', 'qenex-secret-key')
        self.api_keys = {}  # In production, use database
        
        # Initialize components
        self.cicd = None
        self.executor = None
        self.secret_manager = None
        self.cache_manager = None
        
        if QENEX_COMPONENTS_AVAILABLE:
            self.cicd = AutonomousCICD()
            self.executor = DistributedExecutor()
            self.secret_manager = SecretManager()
            self.cache_manager = CacheManager()
            
            # Start services
            self.executor.start()
            self.cache_manager.start()
        
        self._setup_middleware()
        self._setup_routes()
        self._load_api_keys()
    
    def _setup_middleware(self):
        """Setup middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.middleware("http")
        async def log_requests(request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
            return response
    
    def _setup_routes(self):
        """Setup API routes"""
        # Health and status
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "services": {
                    "cicd": self.cicd is not None,
                    "executor": self.executor is not None,
                    "secrets": self.secret_manager is not None,
                    "cache": self.cache_manager is not None
                }
            }
        
        @self.app.get("/status")
        async def system_status(credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Get system status"""
            await self._verify_token(credentials)
            
            status = {
                "timestamp": datetime.now().isoformat(),
                "uptime": self._get_uptime(),
            }
            
            if self.cicd:
                status["pipelines"] = self.cicd.get_pipeline_stats()
            
            if self.executor:
                status["executor"] = self.executor.get_cluster_status()
            
            if self.secret_manager:
                status["secrets"] = self.secret_manager.health_check()
            
            if self.cache_manager:
                status["cache"] = self.cache_manager.get_statistics()
            
            return status
        
        # Authentication
        @self.app.post("/auth/login")
        async def login(username: str, password: str):
            """Login and get JWT token"""
            # Simple authentication - in production, use proper user management
            if username == "admin" and password == self.config.get('admin_password', 'admin'):
                token = self._generate_jwt_token(username)
                return {"access_token": token, "token_type": "bearer"}
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        @self.app.post("/auth/api-key")
        async def create_api_key(name: str, permissions: List[str], 
                               credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Create API key"""
            await self._verify_token(credentials)
            
            api_key = str(uuid.uuid4())
            self.api_keys[api_key] = APIKey(
                key=api_key,
                name=name,
                permissions=permissions,
                created_at=datetime.now()
            )
            
            return {"api_key": api_key, "name": name, "permissions": permissions}
        
        # Pipeline management
        @self.app.get("/pipelines")
        async def list_pipelines(credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """List all pipelines"""
            await self._verify_token(credentials)
            
            if not self.cicd:
                raise HTTPException(status_code=503, detail="CI/CD service not available")
            
            pipelines = self.cicd.list_pipelines()
            return [self._pipeline_to_response(pipeline) for pipeline in pipelines]
        
        @self.app.post("/pipelines", response_model=PipelineResponse)
        async def create_pipeline(pipeline: PipelineCreate,
                                credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Create a new pipeline"""
            await self._verify_token(credentials)
            
            if not self.cicd:
                raise HTTPException(status_code=503, detail="CI/CD service not available")
            
            pipeline_id = self.cicd.create_pipeline(
                name=pipeline.name,
                source=pipeline.source,
                branch=pipeline.branch,
                stages=pipeline.stages,
                environment=pipeline.environment,
                triggers=pipeline.triggers,
                tags=pipeline.tags
            )
            
            created_pipeline = self.cicd.get_pipeline(pipeline_id)
            return self._pipeline_to_response(created_pipeline)
        
        @self.app.get("/pipelines/{pipeline_id}")
        async def get_pipeline(pipeline_id: str,
                             credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Get pipeline details"""
            await self._verify_token(credentials)
            
            if not self.cicd:
                raise HTTPException(status_code=503, detail="CI/CD service not available")
            
            pipeline = self.cicd.get_pipeline(pipeline_id)
            if not pipeline:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            return self._pipeline_to_response(pipeline)
        
        @self.app.put("/pipelines/{pipeline_id}")
        async def update_pipeline(pipeline_id: str, update: PipelineUpdate,
                                credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Update pipeline"""
            await self._verify_token(credentials)
            
            if not self.cicd:
                raise HTTPException(status_code=503, detail="CI/CD service not available")
            
            success = self.cicd.update_pipeline(pipeline_id, **update.dict(exclude_none=True))
            if not success:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            pipeline = self.cicd.get_pipeline(pipeline_id)
            return self._pipeline_to_response(pipeline)
        
        @self.app.delete("/pipelines/{pipeline_id}")
        async def delete_pipeline(pipeline_id: str,
                                credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Delete pipeline"""
            await self._verify_token(credentials)
            
            if not self.cicd:
                raise HTTPException(status_code=503, detail="CI/CD service not available")
            
            success = self.cicd.delete_pipeline(pipeline_id)
            if not success:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            return {"message": "Pipeline deleted successfully"}
        
        @self.app.post("/pipelines/{pipeline_id}/trigger")
        async def trigger_pipeline(pipeline_id: str, parameters: Dict = None,
                                 credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Trigger pipeline execution"""
            await self._verify_token(credentials)
            
            if not self.cicd:
                raise HTTPException(status_code=503, detail="CI/CD service not available")
            
            execution_id = self.cicd.trigger_pipeline(pipeline_id, parameters or {})
            if not execution_id:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            return {"execution_id": execution_id, "status": "triggered"}
        
        @self.app.get("/pipelines/{pipeline_id}/logs")
        async def get_pipeline_logs(pipeline_id: str,
                                  credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Get pipeline execution logs"""
            await self._verify_token(credentials)
            
            if not self.cicd:
                raise HTTPException(status_code=503, detail="CI/CD service not available")
            
            logs = self.cicd.get_pipeline_logs(pipeline_id)
            return {"logs": logs}
        
        # Task management
        @self.app.post("/tasks", response_model=TaskResponse)
        async def create_task(task: TaskCreate,
                            credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Create a new execution task"""
            await self._verify_token(credentials)
            
            if not self.executor:
                raise HTTPException(status_code=503, detail="Executor service not available")
            
            from distributed_executor import ExecutionTask
            
            execution_task = ExecutionTask(
                id=str(uuid.uuid4()),
                pipeline_id=task.pipeline_id,
                stage_name=task.stage_name,
                command=task.command,
                environment=task.environment,
                working_directory=task.working_directory,
                timeout=task.timeout,
                priority=task.priority,
                dependencies=task.dependencies
            )
            
            task_id = self.executor.submit_task(execution_task)
            return self._task_to_response(execution_task)
        
        @self.app.get("/tasks/{task_id}")
        async def get_task(task_id: str,
                         credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Get task status and result"""
            await self._verify_token(credentials)
            
            if not self.executor:
                raise HTTPException(status_code=503, detail="Executor service not available")
            
            status = self.executor.get_task_status(task_id)
            result = self.executor.get_task_result(task_id)
            
            if status is None:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return {
                "id": task_id,
                "status": status.value,
                "result": result
            }
        
        # Worker management
        @self.app.post("/workers")
        async def register_worker(worker: WorkerRegister,
                                credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Register a new worker node"""
            await self._verify_token(credentials)
            
            if not self.executor:
                raise HTTPException(status_code=503, detail="Executor service not available")
            
            from distributed_executor import WorkerNode, WorkerType, WorkerStatus
            
            worker_node = WorkerNode(
                id=str(uuid.uuid4()),
                hostname=worker.hostname,
                ip_address=worker.ip_address,
                port=worker.port,
                worker_type=WorkerType(worker.worker_type),
                capacity=worker.capacity,
                current_load={},
                status=WorkerStatus.IDLE,
                last_heartbeat=datetime.now(),
                current_tasks=[],
                tags=worker.tags
            )
            
            self.executor.register_worker(worker_node)
            return {"worker_id": worker_node.id, "status": "registered"}
        
        @self.app.get("/workers")
        async def list_workers(credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """List all worker nodes"""
            await self._verify_token(credentials)
            
            if not self.executor:
                raise HTTPException(status_code=503, detail="Executor service not available")
            
            cluster_status = self.executor.get_cluster_status()
            return cluster_status.get("worker_details", [])
        
        # Secret management
        @self.app.post("/secrets", response_model=SecretResponse)
        async def create_secret(secret: SecretCreate,
                              credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Create a new secret"""
            await self._verify_token(credentials)
            
            if not self.secret_manager:
                raise HTTPException(status_code=503, detail="Secret service not available")
            
            expires_at = None
            if secret.expires_days:
                expires_at = datetime.now() + timedelta(days=secret.expires_days)
            
            secret_id = self.secret_manager.create_secret(
                name=secret.name,
                value=secret.value,
                secret_type=SecretType(secret.secret_type),
                scope=SecretScope(secret.scope),
                scope_id=secret.scope_id,
                description=secret.description,
                expires_at=expires_at,
                tags=secret.tags
            )
            
            secrets_list = self.secret_manager.list_secrets()
            created_secret = next((s for s in secrets_list if s["id"] == secret_id), None)
            
            if not created_secret:
                raise HTTPException(status_code=500, detail="Failed to create secret")
            
            return SecretResponse(**created_secret)
        
        @self.app.get("/secrets")
        async def list_secrets(scope: Optional[str] = None, scope_id: Optional[str] = None,
                             credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """List secrets (metadata only)"""
            await self._verify_token(credentials)
            
            if not self.secret_manager:
                raise HTTPException(status_code=503, detail="Secret service not available")
            
            scope_enum = SecretScope(scope) if scope else None
            secrets = self.secret_manager.list_secrets(scope_enum, scope_id)
            
            return [SecretResponse(**secret) for secret in secrets]
        
        @self.app.get("/secrets/{secret_id}/value")
        async def get_secret_value(secret_id: str,
                                 credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Get secret value (requires special permission)"""
            await self._verify_token(credentials, required_permissions=["secrets:read"])
            
            if not self.secret_manager:
                raise HTTPException(status_code=503, detail="Secret service not available")
            
            value = self.secret_manager.get_secret(secret_id)
            if value is None:
                raise HTTPException(status_code=404, detail="Secret not found or access denied")
            
            return {"value": value}
        
        @self.app.delete("/secrets/{secret_id}")
        async def delete_secret(secret_id: str,
                              credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Delete a secret"""
            await self._verify_token(credentials)
            
            if not self.secret_manager:
                raise HTTPException(status_code=503, detail="Secret service not available")
            
            success = self.secret_manager.delete_secret(secret_id)
            if not success:
                raise HTTPException(status_code=404, detail="Secret not found")
            
            return {"message": "Secret deleted successfully"}
        
        # Cache management
        @self.app.get("/cache/stats")
        async def get_cache_stats(credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Get cache statistics"""
            await self._verify_token(credentials)
            
            if not self.cache_manager:
                raise HTTPException(status_code=503, detail="Cache service not available")
            
            return self.cache_manager.get_statistics()
        
        @self.app.post("/cache/store")
        async def store_in_cache(key: str, pipeline_id: str, stage_name: str,
                               source_file: UploadFile = File(...),
                               cache_type: str = "custom", ttl_hours: int = 24,
                               credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Store content in cache"""
            await self._verify_token(credentials)
            
            if not self.cache_manager:
                raise HTTPException(status_code=503, detail="Cache service not available")
            
            # Save uploaded file temporarily
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            try:
                content = await source_file.read()
                temp_file.write(content)
                temp_file.close()
                
                success = self.cache_manager.store(
                    key, temp_file.name, pipeline_id, stage_name,
                    CacheType(cache_type), ttl_hours=ttl_hours
                )
                
                if success:
                    return {"message": "Content cached successfully", "key": key}
                else:
                    raise HTTPException(status_code=500, detail="Failed to cache content")
            
            finally:
                os.unlink(temp_file.name)
        
        @self.app.get("/cache/retrieve/{key}")
        async def retrieve_from_cache(key: str, pipeline_id: str, stage_name: str,
                                    credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Retrieve content from cache"""
            await self._verify_token(credentials)
            
            if not self.cache_manager:
                raise HTTPException(status_code=503, detail="Cache service not available")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()
            
            try:
                success = self.cache_manager.retrieve(key, temp_file.name, pipeline_id, stage_name)
                
                if success:
                    return FileResponse(
                        temp_file.name,
                        filename=f"cache_{key}",
                        media_type="application/octet-stream"
                    )
                else:
                    raise HTTPException(status_code=404, detail="Cache entry not found")
            
            except Exception as e:
                os.unlink(temp_file.name)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/cache/invalidate")
        async def invalidate_cache(key: Optional[str] = None, pipeline_id: Optional[str] = None,
                                 credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Invalidate cache entries"""
            await self._verify_token(credentials)
            
            if not self.cache_manager:
                raise HTTPException(status_code=503, detail="Cache service not available")
            
            count = self.cache_manager.invalidate(key=key, pipeline_id=pipeline_id)
            return {"message": f"Invalidated {count} cache entries"}
        
        # Webhook endpoints
        @self.app.post("/webhooks/github")
        async def github_webhook(request_body: dict, background_tasks: BackgroundTasks):
            """Handle GitHub webhook"""
            event_type = request_body.get("action", "unknown")
            repository = request_body.get("repository", {}).get("full_name", "unknown")
            
            logger.info(f"GitHub webhook received: {event_type} for {repository}")
            
            if event_type in ["push", "pull_request"]:
                background_tasks.add_task(self._handle_git_event, request_body)
            
            return {"message": "Webhook received", "event": event_type}
        
        @self.app.post("/webhooks/gitlab")
        async def gitlab_webhook(request_body: dict, background_tasks: BackgroundTasks):
            """Handle GitLab webhook"""
            event_type = request_body.get("object_kind", "unknown")
            project = request_body.get("project", {}).get("path_with_namespace", "unknown")
            
            logger.info(f"GitLab webhook received: {event_type} for {project}")
            
            if event_type in ["push", "merge_request"]:
                background_tasks.add_task(self._handle_git_event, request_body)
            
            return {"message": "Webhook received", "event": event_type}
        
        # File management
        @self.app.get("/files/artifacts/{pipeline_id}")
        async def list_artifacts(pipeline_id: str,
                                credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """List pipeline artifacts"""
            await self._verify_token(credentials)
            
            artifacts_dir = Path(f"/opt/qenex-os/cicd/artifacts/{pipeline_id}")
            if not artifacts_dir.exists():
                return {"artifacts": []}
            
            artifacts = []
            for file_path in artifacts_dir.rglob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    artifacts.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(artifacts_dir)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            return {"artifacts": artifacts}
        
        @self.app.get("/files/artifacts/{pipeline_id}/{file_path:path}")
        async def download_artifact(pipeline_id: str, file_path: str,
                                  credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Download pipeline artifact"""
            await self._verify_token(credentials)
            
            full_path = Path(f"/opt/qenex-os/cicd/artifacts/{pipeline_id}/{file_path}")
            
            if not full_path.exists() or not full_path.is_file():
                raise HTTPException(status_code=404, detail="Artifact not found")
            
            return FileResponse(
                str(full_path),
                filename=full_path.name,
                media_type="application/octet-stream"
            )
        
        # Metrics and monitoring
        @self.app.get("/metrics")
        async def get_metrics(credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Get system metrics"""
            await self._verify_token(credentials)
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "uptime": self._get_uptime()
            }
            
            if self.cicd:
                pipeline_stats = self.cicd.get_pipeline_stats()
                metrics["pipelines"] = pipeline_stats
            
            if self.executor:
                executor_stats = self.executor.get_cluster_status()
                metrics["executor"] = executor_stats
            
            if self.cache_manager:
                cache_stats = self.cache_manager.get_statistics()
                metrics["cache"] = cache_stats
            
            return metrics
        
        # System administration
        @self.app.post("/admin/maintenance")
        async def enable_maintenance_mode(enabled: bool = True,
                                        credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Enable/disable maintenance mode"""
            await self._verify_token(credentials, required_permissions=["admin"])
            
            # Implementation would set maintenance mode flag
            return {"maintenance_mode": enabled, "message": f"Maintenance mode {'enabled' if enabled else 'disabled'}"}
        
        @self.app.post("/admin/cleanup")
        async def cleanup_system(credentials: HTTPAuthorizationCredentials = Security(self.security)):
            """Perform system cleanup"""
            await self._verify_token(credentials, required_permissions=["admin"])
            
            cleanup_results = {}
            
            if self.cache_manager:
                expired_count = self.cache_manager.cleanup_expired()
                cleanup_results["cache_expired"] = expired_count
            
            if self.secret_manager:
                self.secret_manager.cleanup_expired_secrets()
                cleanup_results["secrets_cleaned"] = True
            
            # Clean old logs
            logs_cleaned = self._cleanup_old_logs()
            cleanup_results["logs_cleaned"] = logs_cleaned
            
            return {"message": "System cleanup completed", "results": cleanup_results}
    
    async def _verify_token(self, credentials: HTTPAuthorizationCredentials, 
                           required_permissions: List[str] = None):
        """Verify JWT token or API key"""
        token = credentials.credentials
        
        # Check if it's an API key
        if token in self.api_keys:
            api_key_obj = self.api_keys[token]
            api_key_obj.last_used_at = datetime.now()
            
            if required_permissions:
                for perm in required_permissions:
                    if perm not in api_key_obj.permissions:
                        raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
            return
        
        # Verify JWT token
        if not JWT_AVAILABLE:
            raise HTTPException(status_code=503, detail="JWT verification not available")
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            username = payload.get("sub")
            if not username:
                raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def _generate_jwt_token(self, username: str, expires_hours: int = 24) -> str:
        """Generate JWT token"""
        if not JWT_AVAILABLE:
            raise HTTPException(status_code=503, detail="JWT generation not available")
        
        expire = datetime.utcnow() + timedelta(hours=expires_hours)
        payload = {
            "sub": username,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def _pipeline_to_response(self, pipeline) -> PipelineResponse:
        """Convert pipeline object to response model"""
        return PipelineResponse(
            id=pipeline.id,
            name=pipeline.name,
            source=pipeline.source,
            branch=pipeline.branch,
            status=pipeline.status.value,
            created_at=pipeline.created_at.isoformat(),
            started_at=pipeline.started_at.isoformat() if pipeline.started_at else None,
            completed_at=pipeline.completed_at.isoformat() if pipeline.completed_at else None,
            stages=pipeline.stages,
            metrics=pipeline.metrics,
            tags=getattr(pipeline, 'tags', [])
        )
    
    def _task_to_response(self, task) -> TaskResponse:
        """Convert task object to response model"""
        return TaskResponse(
            id=task.id,
            pipeline_id=task.pipeline_id,
            stage_name=task.stage_name,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            worker_id=task.worker_id,
            result=task.result
        )
    
    async def _handle_git_event(self, event_data: dict):
        """Handle Git webhook events"""
        if not self.cicd:
            return
        
        # Extract relevant information
        repository_url = event_data.get("repository", {}).get("clone_url", "")
        branch = event_data.get("ref", "refs/heads/main").replace("refs/heads/", "")
        
        # Find matching pipelines
        pipelines = self.cicd.list_pipelines()
        for pipeline in pipelines:
            if pipeline.source == repository_url and pipeline.branch == branch:
                logger.info(f"Triggering pipeline {pipeline.id} for {repository_url}:{branch}")
                self.cicd.trigger_pipeline(pipeline.id, {"webhook_event": event_data})
    
    def _get_uptime(self) -> str:
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            return str(timedelta(seconds=int(uptime_seconds)))
        except:
            return "unknown"
    
    def _cleanup_old_logs(self) -> int:
        """Clean up old log files"""
        logs_dir = Path("/opt/qenex-os/cicd/logs")
        if not logs_dir.exists():
            return 0
        
        count = 0
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for log_file in logs_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    log_file.unlink()
                    count += 1
                except OSError:
                    pass
        
        return count
    
    def _load_api_keys(self):
        """Load API keys from configuration"""
        api_keys_file = Path("/opt/qenex-os/cicd/api_keys.json")
        if api_keys_file.exists():
            try:
                with open(api_keys_file) as f:
                    data = json.load(f)
                    for key_data in data:
                        self.api_keys[key_data["key"]] = APIKey(**key_data)
            except Exception as e:
                logger.warning(f"Failed to load API keys: {e}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
        """Run the API server"""
        logger.info(f"Starting QENEX API server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port, reload=reload)

# CLI interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='QENEX CI/CD API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)
    
    # Create and run server
    server = QENEXAPIServer(config)
    server.run(host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()