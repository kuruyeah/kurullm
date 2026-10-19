from sentence_transformers import SentenceTransformer
from database import supabase
from groq import Groq
import torch
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

model = None
client = None
NOT_FOUND_ANSWERS = {
    "tidak ditemukan",
    "tidak ditemukan.",
    "jawaban tidak ditemukan",
    "jawaban tidak ditemukan.",
}


def get_model():
    global model
    if model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = SentenceTransformer(
            "intfloat/multilingual-e5-large",
            device=device
        )
    return model





def get_client():
    global client
    if client is None:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return client

def rewrite_query(question):
    prompt = f"""
You are an expert query rewriter for Retrieval-Augmented Generation (RAG).

DO NOT answer the question.

Your job is to rewrite the user's message into the best semantic search query.

Rules:
- Preserve all important information.
- Keep names, course names, regulations, entities, dates, semesters, etc.
- Remove greetings and unnecessary storytelling.
- Make the query concise but complete.
- Output ONLY the rewritten query.

User Question:
{question}
"""

    res = get_client().chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "You rewrite user questions into search queries for a RAG system."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
    )

    return res.choices[0].message.content.strip()

# FUNCTIONS
def embed_query(text):
    return get_model().encode(f"query: {text}").tolist()

def search_similar(query_embedding, match_count=None):

    if match_count is None:
        match_count = int(os.getenv("RAG_MATCH_COUNT", "5"))

    result = supabase.rpc(
        "match_documents1",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
        },
    ).execute()

    return result.data

def is_not_found_answer(answer):
    return answer.strip().lower() in NOT_FOUND_ANSWERS


def make_context_preview(context, max_length=1200):
    context = context.strip()
    if len(context) <= max_length:
        return context
    return f"{context[:max_length].strip()}..."


def ask_llm(context, question):
    prompt = f"""
System: You are a helpful, conversational assistant. 
Use the provided context to answer the question.
<<<<<<< HEAD

Rules:
1. Grounding: Answer ONLY based on the context. If the answer isn't there, say sorry you can't find it.
2. Language Mirroring: Always respond using the SAME language as the user's question. 
   (e.g., If the question is in English, answer in English. If in Indonesian, answer in Indonesian).
3. Personality: Be warm and human-like. Avoid robotic or dry responses.
4. if you don't know the answer, say you don't know but answer in a human-like way, don't just say "I don't know", but say something like "I'm not sure about that, but I can help you find out!" or "That's a great question! I don't have the answer right now, but let's figure it out together!"

=======
>>>>>>> ac83d25 (ini add local database)

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

    res = get_client().chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return res.choices[0].message.content

def run_rag(question):
    # 1. Rewrite pertanyaan agar lebih mudah dicari
    rewritten_query = rewrite_query(question)

    logger.info("Original Question : %s", question)
    logger.info("Rewritten Query   : %s", rewritten_query)

    # 2. Embedding menggunakan hasil rewrite
    query_emb = embed_query(rewritten_query)

    # 3. Search ke vector database
    results = search_similar(query_emb)
    results = results or []

    contexts = [
        str(r.get("content", "")).strip()
        for r in results
        if str(r.get("content", "")).strip()
    ]
    context = "\n\n".join(contexts)

    logger.info(
        "RAG search returned %s rows, %s non-empty contexts",
        len(results),
        len(contexts),
    )

    if not context:
        return {
            "answer": "tidak ditemukan",
            "context": "",
            "result_count": len(results),
            "matches": results,
        }

    answer = ask_llm(context, question)

    if is_not_found_answer(answer):
        answer = (
            "Berdasarkan konteks yang ditemukan, belum ada jawaban eksplisit untuk "
            "pertanyaan itu. Informasi terkait dari dokumen:\n\n"
            f"{make_context_preview(context)}"
        )

    return {
        "answer": answer,
        "context": context,
        "result_count": len(results),
        "matches": results,
    }

    