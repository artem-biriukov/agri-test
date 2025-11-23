import os
import logging
from typing import Optional, List
from datetime import datetime
import chromadb
import google.generativeai as genai
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))
RAG_COLLECTION_NAME = os.environ.get("RAG_COLLECTION_NAME", "corn-stress-knowledge")

class ChatMessage(BaseModel):
    query: str
    county: Optional[str] = None
    week: Optional[int] = None
    agri_context: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    retrieved_contexts: List[dict] = []
    model: str
    timestamp: str

app = FastAPI(title="AgriGuard RAG Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured")

try:
    chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    collection = chroma_client.get_or_create_collection(
        name=RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    logger.info(f"Connected to ChromaDB: {RAG_COLLECTION_NAME}")
except Exception as e:
    logger.error(f"ChromaDB error: {e}")
    collection = None

SYSTEM_PROMPT = """You are AgriBot, an expert in Iowa corn farming and stress analysis.
Answer questions about corn stress, yields, and farming practices based on retrieved knowledge.
Keep responses concise and actionable."""

@app.get("/health")
async def health():
    return {
        "status": "healthy" if (collection and GEMINI_API_KEY) else "degraded",
        "chroma_connected": collection is not None,
        "gemini_configured": GEMINI_API_KEY is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    if not collection or not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Query ChromaDB for relevant documents
        results = collection.query(query_texts=[message.query], n_results=5)
        
        contexts = []
        if results['documents'] and results['documents'][0]:
            for doc, dist in zip(results['documents'][0], results['distances'][0]):
                contexts.append({
                    "text": doc[:500],
                    "score": float(1 - dist)
                })
        
        # Build prompt with context
        context_str = "\n".join([f"- {c['text']}" for c in contexts]) if contexts else "No context found"
        
        agri_data = message.agri_context or {}
        county_info = f"\nCounty: {message.county}, Week: {message.week}" if message.county else ""
        stress_info = ""
        if agri_data:
            stress_info = f"\nCurrent stress data: CSI={agri_data.get('csi_overall')}, Water={agri_data.get('water_stress')}, Heat={agri_data.get('heat_stress')}"
        
        prompt = f"""{SYSTEM_PROMPT}

Question: {message.query}{county_info}{stress_info}

Knowledge base context:
{context_str}

Answer:"""
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.3,
            )
        )
        
        return ChatResponse(
            response=response.text,
            retrieved_contexts=contexts,
            model=GEMINI_MODEL,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"service": "AgriGuard RAG", "version": "1.0.0", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
