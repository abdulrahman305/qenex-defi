"""Unit tests for QENEX OS API endpoints"""
import pytest
import json
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.api_server import app

client = TestClient(app)

class TestAPIEndpoints:
    """Test suite for API endpoints"""
    
    def test_health_endpoint(self):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_status_endpoint(self):
        """Test /api/v1/status endpoint"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "uptime" in data
        assert "modules" in data
    
    def test_metrics_endpoint(self):
        """Test /api/v1/metrics endpoint"""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
    
    def test_deploy_agent(self):
        """Test agent deployment endpoint"""
        payload = {
            "agent_type": "monitor",
            "config": {
                "interval": 60,
                "targets": ["cpu", "memory"]
            }
        }
        response = client.post("/api/v1/agents/deploy", json=payload)
        assert response.status_code in [200, 201]
        assert "agent_id" in response.json()
    
    def test_invalid_endpoint(self):
        """Test 404 handling"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_authentication(self):
        """Test API authentication"""
        # Without token
        response = client.get("/api/v1/secure/data")
        assert response.status_code in [401, 403]
        
        # With token
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/api/v1/secure/data", headers=headers)
        # Should pass or return different error
        assert response.status_code != 401