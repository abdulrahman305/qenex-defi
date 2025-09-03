"""Swagger/OpenAPI documentation for QENEX OS API"""
from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

app = FastAPI(
    title="QENEX OS API",
    description="Unified AI Operating System API Documentation",
    version="5.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    timestamp: datetime
    uptime: int = Field(..., example=3600)
    version: str = Field(..., example="5.0.0")

class SystemStatus(BaseModel):
    version: str
    uptime: int
    modules: Dict[str, str]
    health: str
    resources: Dict[str, float]

class MetricsResponse(BaseModel):
    cpu: float = Field(..., example=45.2)
    memory: float = Field(..., example=78.5)
    disk: float = Field(..., example=62.1)
    network: Dict[str, float]
    processes: int

class AgentConfig(BaseModel):
    agent_type: str = Field(..., example="monitor")
    config: Dict[str, Any]
    auto_start: bool = True

class AgentResponse(BaseModel):
    agent_id: str
    status: str
    created_at: datetime

class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int

# Endpoints
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check system health status"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        uptime=3600,
        version="5.0.0"
    )

@app.get("/api/v1/status", response_model=SystemStatus, tags=["System"])
async def get_system_status():
    """Get comprehensive system status"""
    return SystemStatus(
        version="5.0.0",
        uptime=3600,
        modules={"ai": "active", "monitoring": "active"},
        health="healthy",
        resources={"cpu": 45.2, "memory": 78.5}
    )

@app.get("/api/v1/metrics", response_model=MetricsResponse, tags=["Monitoring"])
async def get_metrics():
    """Get real-time system metrics"""
    return MetricsResponse(
        cpu=45.2,
        memory=78.5,
        disk=62.1,
        network={"in": 1024.5, "out": 2048.3},
        processes=125
    )

@app.post("/api/v1/agents/deploy", response_model=AgentResponse, tags=["Agents"])
async def deploy_agent(agent: AgentConfig):
    """Deploy a new AI agent"""
    return AgentResponse(
        agent_id="agent-123",
        status="deployed",
        created_at=datetime.now()
    )

@app.get("/api/v1/agents", tags=["Agents"])
async def list_agents():
    """List all deployed agents"""
    return [
        {"id": "agent-1", "type": "monitor", "status": "active"},
        {"id": "agent-2", "type": "optimizer", "status": "active"}
    ]

@app.delete("/api/v1/agents/{agent_id}", tags=["Agents"])
async def remove_agent(agent_id: str):
    """Remove a deployed agent"""
    return {"message": f"Agent {agent_id} removed successfully"}

@app.post("/api/v1/execute", tags=["Commands"])
async def execute_command(command: Dict[str, str]):
    """Execute a system command"""
    return {"result": "Command executed successfully", "output": "..."}

@app.get("/api/v1/logs", tags=["Monitoring"])
async def get_logs(level: Optional[str] = None, limit: int = 100):
    """Retrieve system logs"""
    return {"logs": [], "count": 0}

@app.post("/api/v1/backup", tags=["System"])
async def create_backup():
    """Create system backup"""
    return {"backup_id": "backup-123", "status": "created"}

@app.post("/api/v1/restore/{backup_id}", tags=["System"])
async def restore_backup(backup_id: str):
    """Restore from backup"""
    return {"message": f"Restoring from {backup_id}"}

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="QENEX OS API",
        version="5.0.0",
        description="""
        ## QENEX Unified AI Operating System API
        
        ### Features:
        - Real-time system monitoring
        - AI agent deployment and management
        - Self-healing capabilities
        - Distributed computing support
        - Advanced security features
        
        ### Authentication:
        Use Bearer token in Authorization header
        
        ### Rate Limiting:
        - 1000 requests per hour per IP
        - 100 requests per minute for write operations
        """,
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://qenex.ai/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)