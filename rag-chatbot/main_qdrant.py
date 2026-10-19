from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from rag_qdrantpt2 import run_rag


# ============================================================
# INIT APP
# ============================================================

app = FastAPI(
    title="Academic RAG API - Qdrant"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):
    message: str


# ============================================================
# TEST ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Qdrant RAG API jalan 🔥"
    }


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post("/chat")
def chat(req: ChatRequest):

    return run_rag(
        req.message
    )