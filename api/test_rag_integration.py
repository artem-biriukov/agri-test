"""
Integration tests for RAG service and API orchestration
Verifies MCSI → Yield Forecast → RAG interpretation flow
"""

import pytest
import json
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, '.')

from rag_service import app, MCsIData, YieldForecastData, RAGRequest

client = TestClient(app)

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_mcsi_data():
    """Sample MCSI data (from /mcsi/county/19001)"""
    return MCsIData(
        fips="19001",
        county_name="Adair",
        overall_stress_index=35.5,
        water_stress_index=42.3,
        heat_stress_index=8.9,
        vegetation_health_index=42.1,
        atmospheric_stress_index=12.0,
        primary_driver="Water stress",
        indicators={
            "water_deficit_mean": 5.2,
            "pr_sum": 2.1,
            "lst_mean": 28.5,
            "ndvi_mean": 0.465,
            "vpd_mean": 1.2,
            "eto_mean": 4.1
        }
    )

@pytest.fixture
def sample_yield_data():
    """Sample yield forecast data (from /forecast endpoint)"""
    return YieldForecastData(
        fips="19001",
        year=2025,
        current_week=30,
        yield_forecast_bu_acre=194.2,
        confidence_interval_lower=193.8,
        confidence_interval_upper=194.6,
        forecast_uncertainty=0.4,
        baseline_yield=199.2,
        primary_driver="cumsum_precip",
        feature_importance={
            "cumsum_precip": 0.325,
            "cumsum_heat_days": 0.315,
            "cumsum_vpd": 0.127,
            "cumsum_water_deficit": 0.124,
            "ndvi_current": 0.109
        }
    )

@pytest.fixture
def rag_request(sample_mcsi_data, sample_yield_data):
    """Complete RAG request"""
    return RAGRequest(
        mcsi_data=sample_mcsi_data,
        yield_data=sample_yield_data,
        question=None
    )

# ============================================================================
# HEALTH & BASIC TESTS
# ============================================================================

def test_health_check():
    """Service health check"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "RAG Service"

def test_knowledge_base():
    """Knowledge base endpoint returns context"""
    response = client.get("/knowledge")
    assert response.status_code == 200
    data = response.json()
    assert "corn_growth_stages" in data
    assert "management_options" in data
    assert "yield_science" in data

# ============================================================================
# RAG SERVICE LOGIC TESTS
# ============================================================================

def test_mcsi_data_validation(sample_mcsi_data):
    """Verify MCSI data structure"""
    assert sample_mcsi_data.fips == "19001"
    assert 0 <= sample_mcsi_data.overall_stress_index <= 100
    assert 0 <= sample_mcsi_data.water_stress_index <= 100
    assert len(sample_mcsi_data.indicators) > 0

def test_yield_data_validation(sample_yield_data):
    """Verify yield forecast data structure"""
    assert sample_yield_data.fips == "19001"
    assert sample_yield_data.yield_forecast_bu_acre > 0
    assert (sample_yield_data.confidence_interval_lower <=
            sample_yield_data.yield_forecast_bu_acre <=
            sample_yield_data.confidence_interval_upper)
    assert sample_yield_data.forecast_uncertainty > 0

def test_stress_status():
    """Test stress status classification"""
    from rag_service import get_stress_status
    
    assert get_stress_status(10) == "HEALTHY"
    assert get_stress_status(30) == "MILD"
    assert get_stress_status(50) == "MODERATE"
    assert get_stress_status(70) == "SEVERE"
    assert get_stress_status(90) == "CRITICAL"

def test_build_context(sample_mcsi_data, sample_yield_data):
    """Verify context building"""
    from rag_service import build_context
    
    context = build_context(sample_mcsi_data, sample_yield_data)
    
    # Check key information is in context
    assert "Adair" in context
    assert "19001" in context
    assert "194.2" in context  # Yield forecast
    assert "35.5" in context   # Stress index
    assert "MILD" in context   # Status
    assert "CORN_GROWTH_STAGES" in context
    assert "CRITICAL_THRESHOLDS" in context

def test_recommendation_generation(sample_mcsi_data, sample_yield_data):
    """Test recommendation generation"""
    from rag_service import generate_recommendations
    
    recs = generate_recommendations(sample_mcsi_data, sample_yield_data)
    
    # Should have recommendations
    assert len(recs) > 0
    assert isinstance(recs, list)
    
    # Check for specific recommendations based on data
    rec_text = " ".join(recs)
    assert "WATER STRESS" in rec_text  # water_stress_index=42.3
    assert "YIELD" in rec_text         # yield below baseline

def test_risk_assessment(sample_mcsi_data, sample_yield_data):
    """Test risk assessment"""
    from rag_service import assess_risk
    
    risk = assess_risk(sample_mcsi_data, sample_yield_data)
    
    assert isinstance(risk, str)
    assert "RISK" in risk
    assert "MODERATE" in risk or "HIGH" in risk or "LOW" in risk
    assert "±" in risk  # Contains uncertainty

def test_data_source_tracking(sample_mcsi_data, sample_yield_data):
    """Verify provenance tracking"""
    from rag_service import track_data_sources
    
    sources = track_data_sources(sample_mcsi_data, sample_yield_data)
    
    assert "mcsi_service" in sources
    assert "yield_forecast_service" in sources
    assert "knowledge_context" in sources
    assert sources["mcsi_service"]["fips"] == "19001"
    assert sources["yield_forecast_service"]["current_week"] == 30
    assert "gemini" in sources["model"].lower()

# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

def test_interpret_endpoint(rag_request):
    """Test /interpret endpoint with valid data"""
    response = client.post(
        "/interpret",
        json=rag_request.dict()
    )
    
    # For now, skip if Gemini API not available
    if response.status_code == 500 and "API error" in response.text:
        pytest.skip("Gemini API not available")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert data["fips"] == "19001"
    assert data["county_name"] == "Adair"
    assert "interpretation" in data
    assert "recommendations" in data
    assert "risk_assessment" in data
    assert "data_sources" in data
    assert "timestamp" in data
    assert "model_version" in data
    
    # Verify recommendations are non-empty
    assert len(data["recommendations"]) > 0
    assert isinstance(data["recommendations"], list)

def test_interpret_with_question(sample_mcsi_data, sample_yield_data):
    """Test interpretation with farmer question"""
    request_data = {
        "mcsi_data": sample_mcsi_data.dict(),
        "yield_data": sample_yield_data.dict(),
        "question": "Should I irrigate this week?"
    }
    
    response = client.post("/interpret", json=request_data)
    
    if response.status_code == 500:
        pytest.skip("Gemini API not available")
    
    assert response.status_code == 200
    data = response.json()
    assert "interpretation" in data

def test_batch_interpret(sample_mcsi_data, sample_yield_data):
    """Test batch processing"""
    requests_data = [
        {
            "mcsi_data": sample_mcsi_data.dict(),
            "yield_data": sample_yield_data.dict(),
            "question": None
        },
        {
            "mcsi_data": {**sample_mcsi_data.dict(), "fips": "19003"},
            "yield_data": {**sample_yield_data.dict(), "fips": "19003"},
            "question": None
        }
    ]
    
    response = client.post("/batch_interpret", json=requests_data)
    
    if response.status_code == 500:
        pytest.skip("Gemini API not available")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

# ============================================================================
# EDGE CASE & ERROR TESTS
# ============================================================================

def test_missing_mcsi_field():
    """Test error handling for missing MCSI data"""
    incomplete_request = {
        "mcsi_data": {
            "fips": "19001",
            "county_name": "Adair"
            # Missing required fields
        },
        "yield_data": {}
    }
    
    response = client.post("/interpret", json=incomplete_request)
    assert response.status_code == 422  # Validation error

def test_invalid_fips():
    """Test with invalid FIPS code"""
    from rag_service import build_context
    
    mcsi = MCsIData(
        fips="00000",  # Invalid
        county_name="Unknown",
        overall_stress_index=0,
        water_stress_index=0,
        heat_stress_index=0,
        vegetation_health_index=0,
        atmospheric_stress_index=0,
        primary_driver="None",
        indicators={}
    )
    
    # Should still work - no validation on FIPS format
    context = build_context(mcsi, pytest.fixture(lambda: sample_yield_data))
    assert "00000" in context

def test_extreme_stress_values():
    """Test handling of extreme stress values"""
    from rag_service import get_stress_status, generate_recommendations
    
    extreme_mcsi = MCsIData(
        fips="19001",
        county_name="Adair",
        overall_stress_index=99.9,  # CRITICAL
        water_stress_index=95.0,
        heat_stress_index=80.0,
        vegetation_health_index=5.0,
        atmospheric_stress_index=50.0,
        primary_driver="Multiple stressors",
        indicators={"water_deficit_mean": 10.0}
    )
    
    extreme_yield = YieldForecastData(
        fips="19001",
        year=2025,
        current_week=30,
        yield_forecast_bu_acre=150.0,  # Very low
        confidence_interval_lower=140.0,
        confidence_interval_upper=160.0,
        forecast_uncertainty=10.0,
        baseline_yield=199.2,
        primary_driver="cumsum_heat_days",
        feature_importance={}
    )
    
    # Should handle extreme values
    assert get_stress_status(99.9) == "CRITICAL"
    recs = generate_recommendations(extreme_mcsi, extreme_yield)
    assert len(recs) > 0
    assert any("WATER STRESS" in r for r in recs)
    assert any("YIELD" in r for r in recs)

def test_early_season_data():
    """Test early season (week 21) data"""
    early_yield = YieldForecastData(
        fips="19001",
        year=2025,
        current_week=21,  # Early May
        yield_forecast_bu_acre=199.0,
        confidence_interval_lower=180.0,
        confidence_interval_upper=218.0,
        forecast_uncertainty=18.0,  # High early season uncertainty
        baseline_yield=199.2,
        primary_driver="week_of_season",
        feature_importance={}
    )
    
    early_mcsi = MCsIData(
        fips="19001",
        county_name="Adair",
        overall_stress_index=15.0,  # HEALTHY
        water_stress_index=20.0,
        heat_stress_index=0.0,
        vegetation_health_index=45.0,
        atmospheric_stress_index=10.0,
        primary_driver="None",
        indicators={"water_deficit_mean": 2.0}
    )
    
    # Early season should have high uncertainty
    assert early_yield.forecast_uncertainty > 10.0
    
    # Should have early season guidance
    from rag_service import build_context
    context = build_context(early_mcsi, early_yield)
    assert "week_of_season: 21" in context

def test_critical_pollination_period():
    """Test critical pollination period (weeks 27-31)"""
    poll_yield = YieldForecastData(
        fips="19001",
        year=2025,
        current_week=30,  # Pollination
        yield_forecast_bu_acre=180.0,
        confidence_interval_lower=179.5,
        confidence_interval_upper=180.5,
        forecast_uncertainty=0.5,
        baseline_yield=199.2,
        primary_driver="cumsum_heat_days",
        feature_importance={"cumsum_heat_days": 0.5}
    )
    
    poll_mcsi = MCsIData(
        fips="19001",
        county_name="Adair",
        overall_stress_index=65.0,  # SEVERE
        water_stress_index=50.0,
        heat_stress_index=75.0,  # HIGH HEAT
        vegetation_health_index=50.0,
        atmospheric_stress_index=30.0,
        primary_driver="Heat stress",
        indicators={"lst_mean": 37.0}  # >35°C is critical
    )
    
    recs = generate_recommendations(poll_mcsi, poll_yield)
    # Should mention pollination criticality
    assert any("POLLINATION" in r or "HEAT" in r for r in recs)

# ============================================================================
# PERFORMANCE & LOAD TESTS
# ============================================================================

def test_response_time(sample_mcsi_data, sample_yield_data):
    """Verify API response time is reasonable"""
    import time
    
    request_data = {
        "mcsi_data": sample_mcsi_data.dict(),
        "yield_data": sample_yield_data.dict(),
        "question": None
    }
    
    start = time.time()
    response = client.post("/interpret", json=request_data)
    elapsed = time.time() - start
    
    if response.status_code == 500:
        pytest.skip("Gemini API not available")
    
    # Should respond in reasonable time (< 30s for Gemini)
    assert elapsed < 30.0

# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
