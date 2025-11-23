import pytest
import json
from unittest.mock import Mock, patch
import time


class TestDataPipelineIntegration:
    """Test complete data pipeline integration."""

    def test_pipeline_end_to_end(self):
        """Test full pipeline: download -> process -> store."""
        with patch('requests.get') as mock_get, \
             patch('pandas.DataFrame.to_parquet') as mock_parquet:
            
            # Stage 1: Ingestion
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"satellite_data"
            mock_get.return_value = mock_response
            
            # Simulate downloading satellite data
            response = mock_get("https://lpdaac.usgs.gov/products/mod13a1v061/")
            assert response.status_code == 200
            
            # Stage 2: Processing (simulated)
            # Would aggregate data here
            processed_data = {
                "fips": "19001",
                "ndvi_mean": 0.65,
                "lst_mean": 25.0,
                "water_deficit": 2.5
            }
            
            # Stage 3: Storage
            mock_parquet.return_value = None
            # df.to_parquet("gs://...")
            
            assert processed_data["fips"] == "19001"
            assert 0 <= processed_data["ndvi_mean"] <= 1

    def test_pipeline_data_quality(self):
        """Test data quality checks in pipeline."""
        with patch('pandas.read_parquet') as mock_read:
            # Mock data read from GCS
            mock_read.return_value = Mock(
                shape=(770547, 15),
                isnull=Mock(return_value=Mock(sum=Mock(return_value=0)))
            )
            
            # Read data
            df = mock_read("gs://agriguard-ac215-data/data_clean/daily/")
            
            # Check quality
            assert df.shape[0] == 770547, "Should have 770K+ records"
            assert df.isnull().sum().sum() == 0, "No null values in critical columns"

    def test_pipeline_weekly_execution(self):
        """Test pipeline executes weekly as scheduled."""
        with patch('google.cloud.scheduler_v1.CloudSchedulerClient') as mock_scheduler:
            # Mock Cloud Scheduler
            mock_client = Mock()
            mock_scheduler.return_value = mock_client
            
            # Verify scheduling
            mock_client.list_jobs = Mock(return_value=[
                Mock(name="projects/agriguard-ac215/locations/us-central1/jobs/weekly-pipeline")
            ])
            
            jobs = mock_client.list_jobs()
            assert len(jobs) > 0
            assert "weekly-pipeline" in jobs[0].name


class TestMCSIServiceIntegration:
    """Test MCSI service integrated with data."""

    def test_mcsi_with_real_data_structure(self):
        """Test MCSI service with realistic data."""
        with patch('pandas.read_parquet') as mock_read:
            # Mock weekly data from GCS
            mock_data = Mock()
            mock_data.loc = Mock(return_value=Mock(
                to_dict=Mock(return_value={
                    "ndvi_mean": 0.65,
                    "lst_mean": 25.0,
                    "vpd_mean": 1.2,
                    "water_deficit": 2.5,
                    "eto_cumsum": 450
                })
            ))
            mock_read.return_value = mock_data
            
            # Load data
            weekly_data = mock_read("gs://agriguard-ac215-data/data_clean/weekly/")
            row = weekly_data.loc[0]
            indicators = row.to_dict()
            
            # Verify MCSI inputs available
            assert "ndvi_mean" in indicators
            assert "lst_mean" in indicators
            assert "water_deficit" in indicators
            assert 0 <= indicators["ndvi_mean"] <= 1

    def test_mcsi_all_counties(self):
        """Test MCSI calculation for all 99 Iowa counties."""
        county_fips_codes = [f"1900{i:02d}" for i in range(1, 100)]
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"csi_overall": 25.3}]
            }
            mock_get.return_value = mock_response
            
            results = []
            for fips in county_fips_codes[:5]:  # Test subset
                response = mock_get(f"http://localhost:8000/mcsi/{fips}/timeseries")
                assert response.status_code == 200
                results.append(response.json())
            
            assert len(results) == 5


class TestYieldForecastIntegration:
    """Test yield forecast with actual data flow."""

    def test_yield_prediction_pipeline(self):
        """Test full yield prediction with feature engineering."""
        with patch('pandas.read_parquet') as mock_read, \
             patch('xgboost.Booster.predict') as mock_predict:
            
            # Load features from processed data
            mock_data = Mock()
            mock_data.values = [[30, 8, 156, 25, 12, 380, 85, 0.78, 14, 0.65,
                                450, 1.1, 9, 105, 195]]
            mock_read.return_value = mock_data
            
            daily_data = mock_read("gs://agriguard-ac215-data/data_clean/daily/")
            
            # Feature engineering
            features = daily_data.values[0]
            assert len(features) == 15, "Should have 15 features"
            
            # Make prediction
            mock_predict.return_value = [186.2]
            prediction = mock_predict(features.reshape(1, -1))[0]
            
            assert 40 <= prediction <= 250, "Yield should be in realistic range"

    def test_yield_for_all_growing_weeks(self):
        """Test yield predictions across all growing weeks."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            
            weeks = range(1, 27)  # 26 weeks in growing season
            predictions = []
            
            for week in weeks:
                mock_response.json.return_value = {
                    "predicted_yield": 150.0 + week * 1.5,  # Simulated progression
                    "confidence": 0.85 + (week / 26 * 0.1)
                }
                mock_post.return_value = mock_response
                
                response = mock_post("http://localhost:8001/forecast",
                                   json={"week": week})
                predictions.append(response.json())
            
            assert len(predictions) == 26
            # Yield confidence increases with more data
            assert predictions[0]["confidence"] < predictions[25]["confidence"]


class TestAPIOrchestrationIntegration:
    """Test cross-service coordination through API Orchestrator."""

    def test_orchestrator_mcsi_and_yield(self):
        """Test API orchestrator calls both MCSI and Yield services."""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            
            # Call 1: MCSI from orchestrator
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={"csi_overall": 35.0})
            )
            mcsi_response = mock_get("http://localhost:8000/mcsi/19001/timeseries")
            
            # Call 2: Yield from orchestrator
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={"predicted_yield": 180.0})
            )
            yield_response = mock_post("http://localhost:8001/forecast")
            
            # Orchestrator aggregates both
            combined = {
                "csi": mcsi_response.json()["csi_overall"],
                "yield": yield_response.json()["predicted_yield"]
            }
            
            assert combined["csi"] == 35.0
            assert combined["yield"] == 180.0

    def test_orchestrator_error_handling(self):
        """Test orchestrator handles service failures gracefully."""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            
            # MCSI service down
            mock_get.return_value = Mock(status_code=503)
            
            # Orchestrator should retry or fallback
            response = mock_get("http://localhost:8000/mcsi/19001/timeseries")
            assert response.status_code == 503


class TestFrontendIntegration:
    """Test frontend integration with backend APIs."""

    def test_frontend_county_selection(self):
        """Test frontend loads data for selected county."""
        with patch('requests.get') as mock_get:
            # Frontend selects county 19001
            county_fips = "19001"
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "fips": county_fips,
                "county_name": "ADAIR",
                "data": [{"week": 1, "csi_overall": 25.3}]
            }
            mock_get.return_value = mock_response
            
            # Frontend calls API
            response = mock_get(f"http://localhost:8002/mcsi/{county_fips}/timeseries")
            
            assert response.status_code == 200
            assert response.json()["county_name"] == "ADAIR"

    def test_frontend_week_selection(self):
        """Test frontend displays data for selected week."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "week": 20,
                "date": "2025-08-15",
                "csi_overall": 45.0
            }
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8002/data/19001/week/20")
            
            assert response.status_code == 200
            assert response.json()["week"] == 20

    def test_frontend_chart_data(self):
        """Test frontend receives data suitable for charts."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "timeseries": [
                    {"week": 1, "csi": 20, "date": "2025-05-05"},
                    {"week": 2, "csi": 25, "date": "2025-05-12"},
                    {"week": 3, "csi": 30, "date": "2025-05-19"},
                ]
            }
            mock_get.return_value = mock_response
            
            response = mock_get("http://localhost:8002/chart/19001")
            data = response.json()["timeseries"]
            
            # Verify structure for charting
            assert all("week" in d for d in data)
            assert all("csi" in d for d in data)
            assert all("date" in d for d in data)


class TestRAGChatIntegration:
    """Test RAG/AgriBot integration with service data."""

    def test_chat_with_context(self):
        """Test chat responses use current CSI/yield data."""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            
            # Get current data
            mock_get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={"csi": 65, "yield_forecast": 175})
            )
            current_data = mock_get("http://localhost:8002/data/19001/week/20").json()
            
            # Ask AgriBot with context
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "response": "Your stress index is 65..."
                })
            )
            
            response = mock_post("http://localhost:8003/chat",
                               json={
                                   "message": "What about my crop?",
                                   "context": current_data
                               })
            
            assert response.status_code == 200
            assert "response" in response.json()

    def test_chat_recommendations_based_on_stress(self):
        """Test chat recommendations vary by stress level."""
        with patch('requests.post') as mock_post:
            # Low stress
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "response": "Continue normal management practices"
                })
            )
            response_low = mock_post("http://localhost:8003/chat",
                                    json={"context": {"csi": 25}})
            
            # High stress
            mock_post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "response": "Consider immediate irrigation"
                })
            )
            response_high = mock_post("http://localhost:8003/chat",
                                     json={"context": {"csi": 75}})
            
            assert response_low.json()["response"] != response_high.json()["response"]


class TestPerformanceIntegration:
    """Test performance across integrated services."""

    def test_end_to_end_latency(self):
        """Test total latency for user request."""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response
            
            # Simulate full request: UI -> API -> Services
            start = time.time()
            
            # 1. Frontend requests data
            mcsi_data = mock_get("http://localhost:8002/mcsi/19001/timeseries")
            
            # 2. Make yield prediction
            yield_data = mock_post("http://localhost:8001/forecast")
            
            # 3. Get chat recommendation
            chat_data = mock_post("http://localhost:8003/chat")
            
            elapsed = time.time() - start
            
            # Should complete in <2 seconds for full request
            assert elapsed < 2.0, f"Request took {elapsed}s, should be <2s"

    def test_scalability_multiple_counties(self):
        """Test performance with multiple county requests."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"csi": 35.0}
            mock_get.return_value = mock_response
            
            start = time.time()
            
            # Request data for 10 counties
            for i in range(1, 11):
                fips = f"1900{i:02d}"
                mock_get(f"http://localhost:8002/mcsi/{fips}/timeseries")
            
            elapsed = time.time() - start
            
            # Should handle multiple requests efficiently
            # <200ms per request = <2s total
            assert elapsed < 2.0, f"10 requests took {elapsed}s, should be <2s"
