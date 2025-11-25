#!/bin/bash
# Run tests in Docker container with all dependencies

echo "Installing test dependencies..."
docker-compose exec rag pip install pytest pytest-cov pytest-asyncio --break-system-packages

echo "Running tests..."
docker-compose exec rag pytest /app/tests/ -v \
    --cov=/app \
    --cov-report=term-missing \
    --cov-report=html:/app/htmlcov

echo "Coverage report generated in htmlcov/"
