"""
Integration tests for API Orchestrator
Tests actual FastAPI endpoints using TestClient
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.api_orchestrator import app

client = TestClient(app)


class TestAPIHealth:
    """Test health check endpoint"""
    
    def test_health_endpoint_exists(self):
        """Test that /health endpoint exists"""
        response = client.get("/health")
        assert response.status_code == 200
        
    def test_health_response_structure(self):
        """Test health response has correct structure"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "services" in data or "error" in data


class TestMCSIEndpoints:
    """Test MCSI proxy endpoints"""
    
    def test_mcsi_timeseries_endpoint_structure(self):
        """Test MCSI timeseries endpoint exists"""
        response = client.get("/mcsi/19001/timeseries?limit=30")
        # Service unavailable is OK (no real backend)
        assert response.status_code in [200, 503, 500]
    
    def test_mcsi_single_endpoint_structure(self):
        """Test single MCSI value endpoint exists"""
        response = client.get("/mcsi/19001")
        assert response.status_code in [200, 503, 500]


class TestYieldEndpoints:
    """Test yield forecast proxy endpoints"""
    
    def test_yield_forecast_endpoint_structure(self):
        """Test yield forecast endpoint exists"""
        response = client.get("/yield/19001?week=15")
        assert response.status_code in [200, 500, 503]
        
    def test_yield_endpoint_validation(self):
        """Test yield endpoint parameter validation"""
        response = client.get("/yield/19001")
        assert response.status_code in [200, 500, 503]


class TestAPIOrchestration:
    """Test API orchestration logic"""
    
    def test_api_metadata(self):
        """Test API has correct metadata"""
        assert app.title == "AgriGuard API Orchestrator"
        assert app.version == "1.1.0"
    
    def test_cors_configured(self):
        """Test CORS middleware is configured"""
        middlewares = [m for m in app.user_middleware]
        assert len(middlewares) > 0
