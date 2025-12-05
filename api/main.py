"""Main entry point - mounts API at /api prefix"""
from fastapi import FastAPI
from api.api_orchestrator import app as api_app

# Create parent app
app = FastAPI()

# Add root-level health check
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Mount the API orchestrator at /api
app.mount("/api", api_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
