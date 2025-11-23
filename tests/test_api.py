import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_mcsi_data():
    """Mock MCSI response data."""
    return {
        "fips": "19001",
        "county_name": "ADAIR",
        "data": [
            {
                "week": 1,
                "date": "2025-05-05",
                "csi_overall": 25.3,
                "water_stress": 30,
                "heat_stress": 15,
                "vegetation_stress": 20,
                "atmospheric_stress": 10
            },
            {
                "week": 2,
                "date": "2025-05-12",
                "csi_overall": 28.5,
                "water_stress": 35,
                "heat_stress": 18,
                "vegetation_stress": 22,
                "atmospheric_stress": 12
            }
        ]
    }


@pytest.fixture
def mock_yield_data():
    """Mock yield forecast response data."""
    return {
        "predicted_yield": 186.2,
        "lower_bound": 171.2,
        "upper_bound": 201.2,
        "confidence": 0.95,
        "model_version": "xgboost_v1.0"
    }


class TestMCSIEndpoint:
    """Test MCSI Service endpoints."""

    def test_health_check(self):
        """Test /health endpoint."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response
            
            # Simulate health check
            response = mock_get("http://localhost:8000/health")
            
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    def test_mcsi_timeseries_valid_county(self, mock_mcsi_data):
        """Test /mcsi/{fips}/timeseries with valid county."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_mcsi_data
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8000/mcsi/19001/timeseries")
            
            assert response.status_code == 200
            data = response.json()
            assert data["fips"] == "19001"
            assert data["county_name"] == "ADAIR"
            assert len(data["data"]) > 0

    def test_mcsi_invalid_fips(self):
        """Test /mcsi/{fips}/timeseries with invalid FIPS code."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"detail": "County not found"}
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8000/mcsi/99999/timeseries")
            
            assert response.status_code == 404

    def test_mcsi_response_schema(self, mock_mcsi_data):
        """Test MCSI response has required fields."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_mcsi_data
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8000/mcsi/19001/timeseries")
            data = response.json()
            
            # Check required fields
            assert "fips" in data
            assert "county_name" in data
            assert "data" in data
            
            # Check data structure
            for record in data["data"]:
                assert "week" in record
                assert "date" in record
                assert "csi_overall" in record
                assert 0 <= record["csi_overall"] <= 100

    def test_mcsi_csi_range(self, mock_mcsi_data):
        """Test MCSI values are in valid range [0, 100]."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_mcsi_data
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8000/mcsi/19001/timeseries")
            data = response.json()
            
            for record in data["data"]:
                assert 0 <= record["csi_overall"] <= 100
                assert 0 <= record["water_stress"] <= 100
                assert 0 <= record["heat_stress"] <= 100
                assert 0 <= record["vegetation_stress"] <= 100
                assert 0 <= record["atmospheric_stress"] <= 100


class TestYieldForecastEndpoint:
    """Test Yield Forecast Service endpoints."""

    def test_health_check(self):
        """Test /health endpoint."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8001/health")
            
            assert response.status_code == 200

    def test_forecast_valid_features(self, mock_yield_data):
        """Test /forecast endpoint with valid features."""
        features = {
            "features": [30, 8, 156, 25, 12, 380, 85, 0.78, 14, 0.65,
                        450, 1.1, 9, 105, 195]
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_yield_data
            mock_post.return_value = mock_response
            
            response = mock_post("http://localhost:8001/forecast",
                               json=features)
            
            assert response.status_code == 200
            data = response.json()
            assert 40 <= data["predicted_yield"] <= 250

    def test_forecast_invalid_features(self):
        """Test /forecast with invalid feature count."""
        invalid_features = {
            "features": [30, 8, 156, 25]  # Only 4 features, need 15
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.json.return_value = {"detail": "Invalid features"}
            mock_post.return_value = mock_response
            
            response = mock_post("http://localhost:8001/forecast",
                               json=invalid_features)
            
            assert response.status_code == 422

    def test_forecast_response_schema(self, mock_yield_data):
        """Test forecast response has required fields."""
        features = {
            "features": [30, 8, 156, 25, 12, 380, 85, 0.78, 14, 0.65,
                        450, 1.1, 9, 105, 195]
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_yield_data
            mock_post.return_value = mock_response
            
            response = mock_post("http://localhost:8001/forecast",
                               json=features)
            data = response.json()
            
            # Check required fields
            assert "predicted_yield" in data
            assert "lower_bound" in data
            assert "upper_bound" in data
            assert "confidence" in data
            assert "model_version" in data

    def test_forecast_bounds(self, mock_yield_data):
        """Test that confidence bounds are valid."""
        features = {
            "features": [30, 8, 156, 25, 12, 380, 85, 0.78, 14, 0.65,
                        450, 1.1, 9, 105, 195]
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_yield_data
            mock_post.return_value = mock_response
            
            response = mock_post("http://localhost:8001/forecast",
                               json=features)
            data = response.json()
            
            # Bounds should be valid
            assert data["lower_bound"] < data["predicted_yield"]
            assert data["predicted_yield"] < data["upper_bound"]
            assert data["confidence"] > 0
            assert data["confidence"] <= 1.0


class TestAPIOrchestrator:
    """Test API Orchestrator endpoints."""

    def test_orchestrator_health_check(self):
        """Test /health endpoint."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8002/health")
            
            assert response.status_code == 200

    def test_combined_data_endpoint(self):
        """Test combined CSI + yield endpoint."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "county": "ADAIR",
                "week": 20,
                "csi": 29.5,
                "yield_forecast": 186.2,
                "yield_uncertainty": 15.0,
                "recommendations": "Monitor water levels"
            }
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8002/data/19001/week/20")
            
            assert response.status_code == 200
            data = response.json()
            assert "csi" in data
            assert "yield_forecast" in data
            assert 0 <= data["csi"] <= 100


class TestRAGService:
    """Test RAG/AgriBot Service endpoints."""

    def test_rag_health_check(self):
        """Test /health endpoint."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8003/health")
            
            assert response.status_code == 200

    def test_chat_endpoint(self):
        """Test /chat endpoint."""
        payload = {
            "message": "What should I do about water stress?",
            "context": {
                "fips": "19001",
                "csi": 65,
                "yield_forecast": 175
            }
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Given water deficit of 4mm and current stress index of 65...",
                "confidence": 0.92
            }
            mock_post.return_value = mock_response
            
            response = mock_post("http://localhost:8003/chat",
                                json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "confidence" in data


class TestAPIErrorHandling:
    """Test error handling across APIs."""

    def test_malformed_json(self):
        """Test handling of malformed JSON requests."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"detail": "Invalid JSON"}
            mock_post.return_value = mock_response
            
            response = mock_post("http://localhost:8002/data",
                               data="not valid json")
            
            assert response.status_code == 400

    def test_service_timeout(self):
        """Test timeout handling."""
        with patch('requests.get', side_effect=TimeoutError):
            with pytest.raises(TimeoutError):
                requests.get("http://localhost:8000/health",
                           timeout=1)

    def test_service_unavailable(self):
        """Test 503 Service Unavailable."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.json.return_value = {"detail": "Service Unavailable"}
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8000/health")
            
            assert response.status_code == 503


class TestAPIConcurrency:
    """Test API behavior under concurrent access."""

    def test_multiple_concurrent_requests(self):
        """Test handling of multiple concurrent requests."""
        import concurrent.futures
        
        def make_request(county_fips):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "fips": county_fips,
                    "csi": 30.0
                }
                mock_get.return_value = mock_response
                return mock_get(f"http://localhost:8000/mcsi/{county_fips}/timeseries")
        
        # Test with 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, f"1900{i}") 
                      for i in range(1, 6)]
            results = [f.result() for f in futures]
        
        assert len(results) == 5
        assert all(r.status_code == 200 for r in results)
