from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
import chromadb
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", 8000))


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/query")
async def query_documents(request: QueryRequest):
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = client.get_collection("corn-stress-knowledge")
        results = collection.query(query_texts=[request.query], n_results=request.top_k)
        return {"results": results}
    except Exception:
        raise HTTPException(status_code=500, detail="Query failed")


@app.post("/chat")
async def chat(request: QueryRequest):
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = client.get_collection("corn-stress-knowledge")
        results = collection.query(query_texts=[request.query], n_results=request.top_k)

        context = "\n".join(results["documents"][0] if results["documents"] else [])

        response = {
            "answer": f"Based on the context: {context[:500]}...",
            "sources": results.get("metadatas", [[]])[0] if results.get("metadatas") else [],
        }
        return response
    except Exception:
        raise HTTPException(status_code=500, detail="Chat failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
