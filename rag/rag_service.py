import os, logging
from typing import Optional, List
from datetime import datetime
import google.generativeai as genai
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

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

app = FastAPI(title="AgriGuard RAG")
app.add_middleware(__import__('fastapi').middleware.cors.CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.get("/health")
async def health():
    return {"status": "healthy", "chroma_connected": True, "gemini_configured": bool(GEMINI_API_KEY), "timestamp": datetime.now().isoformat()}

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini not configured")
    
    agri_data = message.agri_context or {}
    county_info = f"County: {message.county}, Week {message.week}\n" if message.county else ""
    stress_info = f"CSI={agri_data.get('csi_overall')}, Water stress={agri_data.get('water_stress')}%, Heat stress={agri_data.get('heat_stress')}°C\n" if agri_data else ""
    
    prompt = f"""You are AgriBot, Iowa corn farming expert. Answer concisely and actionably about stress, yields, and management.

{county_info}{stress_info}
Question: {message.query}

Answer:"""
    
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=1024, temperature=0.3))
    
    return ChatResponse(response=response.text, retrieved_contexts=[], model=GEMINI_MODEL, timestamp=datetime.now().isoformat())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
