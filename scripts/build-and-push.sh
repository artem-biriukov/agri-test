#!/bin/bash
set -e

# Configuration
PROJECT_ID="agriguard-ac215"
REGION="us-central1"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/agriguard"

echo "Authenticating to Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

echo "Building MCSI..."
docker build -t ${REGISTRY}/mcsi:latest -f ml-models/mcsi/Dockerfile ml-models/mcsi
docker push ${REGISTRY}/mcsi:latest

echo "Building Yield..."
docker build -t ${REGISTRY}/yield:latest -f ml-models/yield_forecast/Dockerfile.yield ml-models/yield_forecast
docker push ${REGISTRY}/yield:latest

echo "Building API..."
docker build -t ${REGISTRY}/api:latest -f deployment/Dockerfile.api .
docker push ${REGISTRY}/api:latest

echo "Building RAG..."
docker build -t ${REGISTRY}/rag:latest -f rag/Dockerfile.rag rag
docker push ${REGISTRY}/rag:latest

echo "Pushing ChromaDB..."
docker pull chromadb/chroma:0.4.24
docker tag chromadb/chroma:0.4.24 ${REGISTRY}/chromadb:0.4.24
docker push ${REGISTRY}/chromadb:0.4.24

echo "Building Frontend..."
docker build -t ${REGISTRY}/frontend:latest -f frontend/Dockerfile frontend
docker push ${REGISTRY}/frontend:latest

echo "✅ All images pushed successfully!"
echo "Registry: ${REGISTRY}"
