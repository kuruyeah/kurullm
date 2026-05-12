from sentence_transformers import SentenceTransformer
from supabase import create_client  # type: ignore[import]
from groq import Groq  # type: ignore[import]
import os
from dotenv import load_dotenv  # type: ignore[import]
import torch

load_dotenv()

# =========================
# DEVICE (SAFE FOR MAC)
# =========================
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu" # type: ignore
print("Using device:", DEVICE)

# =========================
# LAZY MODEL LOAD (IMPORTANT for uvicorn reload)
# =========================
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("intfloat/multilingual-e5-large")
        _model = _model.to(DEVICE)
    return _model

# =========================
# SUPABASE (SAFE INIT)
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# GROQ (SAFE INIT)
# =========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# =========================
# FUNCTIONS
# =========================

def embed_query(text: str):
    model = get_model()
    # IMPORTANT for E5 models
    return model.encode(f"query: {text}").tolist()


def search_similar(query_embedding):
    result = supabase.rpc(
        "match_documents1",
        {
            "query_embedding": query_embedding,
            "match_count": 3
        }
    ).execute()

    return result.data or []


def ask_llm(context: str, question: str):
    prompt = f"""
System: You are a helpful, conversational assistant. 
Use the provided context to answer the question.

Rules:
1. Grounding: Answer ONLY based on the context. If the answer isn't there, say sorry you can't find it.
2. Language Mirroring: Always respond using the SAME language as the user's question. 
   (e.g., If the question is in English, answer in English. If in Indonesian, answer in Indonesian).
3. Personality: Be warm and human-like. Avoid robotic or dry responses.
4. if you don't know the answer, say you don't know but answer in a human-like way, don't just say "I don't know", but say something like "I'm not sure about that, but I can help you find out!" or "That's a great question! I don't have the answer right now, but let's figure it out together!"


Context:
{context}

Pertanyaan:
{question}
"""

    res = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return res.choices[0].message.content


def run_rag(question: str):
    query_emb = embed_query(question)
    results = search_similar(query_emb)

    context = "\n\n".join([r.get("content", "") for r in results])

    answer = ask_llm(context, question)

    return {
        "answer": answer,
        "context": context
    }
