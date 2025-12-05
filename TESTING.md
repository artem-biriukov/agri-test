# AgriGuard Testing Documentation

## Overview

AgriGuard uses a comprehensive testing strategy with automated CI/CD pipelines to ensure code quality and reliability.

## Test Coverage

**Current Coverage: 68.97%** (Target: 60% ✅)

### Coverage by Module
- `api/api_orchestrator.py`: 67.92%
- `rag/rag_service.py`: 71.79%

## Test Suite

### Total Tests: 60 passing, 9 skipped

### Test Categories

#### 1. API Integration Tests (`tests/test_api_integration.py`)
- Health endpoint validation
- MCSI endpoint structure
- Yield forecast endpoint structure
- API metadata and CORS configuration

#### 2. API Orchestrator Tests (`tests/test_api_orchestrator.py`)
- Request routing
- Error handling
- Data integration
- Request validation

#### 3. Data Processing Tests (`tests/test_data_processing.py`)
- Data validation (NDVI, LST, FIPS codes)
- MCSI calculations
- Yield feature engineering
- Data quality checks

#### 4. RAG Service Tests (`tests/test_rag_service.py`)
- Document loading and chunking
- Vector search functionality
- Chat generation
- RAG configuration

#### 5. Integration Tests
- MCSI service integration (`tests/test_mcsi_integration.py`)
- Yield service integration (`tests/test_yield_integration.py`)
- RAG service integration (`tests/test_rag_integration.py`)

## Running Tests Locally

### Run All Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ -v --cov --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_api_integration.py -v
```

### Run Specific Test
```bash
pytest tests/test_api_integration.py::TestAPIHealth::test_health_endpoint_exists -v
```

## CI/CD Pipeline

### Automated Testing
Tests run automatically on:
- Push to `master` or `main` branches
- Pull requests to `master` or `main`
- Manual workflow dispatch

### Pipeline Jobs

1. **Test and Coverage**
   - Runs all 60 tests
   - Generates coverage reports
   - Enforces 60% coverage threshold
   - Uploads results to Codecov

2. **Code Quality**
   - Flake8 linting
   - Black code formatting checks

3. **Security Scan**
   - Trivy vulnerability scanning
   - Security report upload to GitHub

### Viewing Results
- GitHub Actions: https://github.com/artem-biriukov/agri-test/actions
- Coverage Reports: Available as workflow artifacts

## Test Requirements

### Dependencies
All test dependencies are listed in `requirements-test.txt`:
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
coverage>=7.4.0
httpx>=0.27.0
fastapi>=0.109.0
```

### Installation
```bash
pip install -r requirements-test.txt
```

## Coverage Configuration

Coverage settings are defined in `pyproject.toml`:
- **Target:** 60% minimum coverage
- **Scope:** `api/`, `rag/` modules
- **Excluded:** Test files, cache, utility scripts

## Best Practices

1. **Write tests for new features** before implementation (TDD)
2. **Maintain 60%+ coverage** on all code changes
3. **Run tests locally** before pushing
4. **Fix failing tests immediately** - don't merge broken code
5. **Update test documentation** when adding new test categories

## Troubleshooting

### Tests Failing Locally
```bash
# Clear cache
rm -rf .pytest_cache __pycache__

# Reinstall dependencies
pip install -r requirements-test.txt --force-reinstall
```

### Coverage Not Measuring
```bash
# Check coverage configuration
cat pyproject.toml

# Run with debug
pytest tests/ -v --cov --cov-report=term --cov-config=pyproject.toml
```

## Future Improvements

- [ ] Add integration tests for MCSI/Yield services when models available
- [ ] Increase coverage to 80%+
- [ ] Add performance testing
- [ ] Add end-to-end tests with real GKE deployment
- [ ] Add load testing for API endpoints

---

**Last Updated:** December 5, 2025  
**Test Coverage:** 68.97%  
**Tests Passing:** 60/60
