from fastapi import FastAPI
from pydantic import BaseModel
from rag import run_rag

from fastapi.middleware.cors import CORSMiddleware

# INIT APP
app = FastAPI()

# CORS (biar React nanti bisa connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REQUEST MODEL
class ChatRequest(BaseModel):
    message: str

# TEST ROOT
@app.get("/")
def root():
    return {"message": "API jalan 🔥"}

# CHAT ENDPOINT (RAG)
@app.post("/chat")
def chat(req: ChatRequest):
    return run_rag(req.message)