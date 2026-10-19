from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from groq import Groq

import torch
import os
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333"
)

QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "academic_chunks"
)

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

model = None
client = None
qdrant = None


NOT_FOUND_ANSWERS = {
    "tidak ditemukan",
    "tidak ditemukan.",
    "jawaban tidak ditemukan",
    "jawaban tidak ditemukan.",
}


# ============================================================
# INITIALIZATION
# ============================================================

def get_model():
    global model

    if model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info("Loading embedding model on %s", device)

        model = SentenceTransformer(
            EMBEDDING_MODEL,
            device=device
        )

    return model


def get_client():
    global client

    if client is None:
        client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

    return client


def get_qdrant():
    global qdrant

    if qdrant is None:
        logger.info(
            "Connecting to Qdrant: %s",
            QDRANT_URL
        )

        qdrant = QdrantClient(
            url=QDRANT_URL
        )

    return qdrant


# ============================================================
# QUERY REWRITING
# ============================================================

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
                "content": (
                    "You rewrite user questions into search "
                    "queries for a RAG system."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
    )

    return res.choices[0].message.content.strip()


# ============================================================
# EMBEDDING
# ============================================================

def embed_query(text):

    embedding = get_model().encode(
        f"query: {text}",
        normalize_embeddings=True
    )

    return embedding.tolist()


# ============================================================
# QDRANT SEARCH
# ============================================================

def search_similar(query_embedding, match_count=None):

    if match_count is None:
        match_count = int(
            os.getenv("RAG_MATCH_COUNT", "5")
        )

    result = get_qdrant().query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_embedding,
        limit=match_count,
        with_payload=True,
        with_vectors=False,
    )

    return result.points


# ============================================================
# UTILITIES
# ============================================================

def is_not_found_answer(answer):

    return answer.strip().lower() in NOT_FOUND_ANSWERS


def make_context_preview(context, max_length=1200):

    context = context.strip()

    if len(context) <= max_length:
        return context

    return f"{context[:max_length].strip()}..."


# ============================================================
# CONTEXT BUILDER
# ============================================================

def build_context(results):

    contexts = []

    for point in results:

        payload = point.payload or {}

        text = str(
            payload.get("text", "")
        ).strip()

        if not text:
            continue

        section = payload.get(
            "section",
            ""
        )

        page_start = payload.get(
            "page_start",
            ""
        )

        page_end = payload.get(
            "page_end",
            ""
        )

        chunk_id = payload.get(
            "chunk_id",
            ""
        )

        metadata = []

        if section:
            metadata.append(
                f"Section: {section}"
            )

        if page_start:
            if page_end and page_end != page_start:
                metadata.append(
                    f"Page: {page_start}-{page_end}"
                )
            else:
                metadata.append(
                    f"Page: {page_start}"
                )

        if chunk_id:
            metadata.append(
                f"Chunk: {chunk_id}"
            )

        header = "\n".join(metadata)

        if header:
            context_item = (
                f"[{header}]\n"
                f"{text}"
            )
        else:
            context_item = text

        contexts.append(context_item)

    return "\n\n".join(contexts)


# ============================================================
# LLM
# ============================================================

def ask_llm(context, question):

    prompt = f"""
System: You are a helpful, conversational assistant.

Use the provided context to answer the question.

Rules:

1. Grounding:
   Answer ONLY based on the provided context.
   Do not invent information.
   If the answer is not available in the context, say that
   you cannot find the answer from the available documents.

2. Language Mirroring:
   Always respond using the SAME language as the user's question.
   If the question is in English, answer in English.
   If the question is in Indonesian, answer in Indonesian.

3. Personality:
   Be warm and human-like.
   Avoid robotic or dry responses.

4. If you don't know the answer:
   Say you don't know in a natural and helpful way.
   For example:
   "Saya belum menemukan informasi tersebut di dokumen yang tersedia,
   tetapi saya bisa membantu mencari informasi terkait."

5. Do not mention that you are an AI unless necessary.

Context:
{context}

Pertanyaan:
{question}
"""

    res = get_client().chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return res.choices[0].message.content


# ============================================================
# MAIN RAG PIPELINE
# ============================================================

def run_rag(question):

    logger.info("[RAG 1/8] Mulai memproses pertanyaan")

    try:
        # 1. Rewrite pertanyaan
        logger.info("[RAG 2/8] Memulai rewrite_query")
        rewritten_query = rewrite_query(question)

        logger.info("Original Question : %s", question)
        logger.info("Rewritten Query   : %s", rewritten_query)

        # 2. Embedding query
        logger.info("[RAG 3/8] Memulai embed_query")
        query_emb = embed_query(rewritten_query)
        logger.info("[RAG 3/8] Embedding selesai")

        # 3. Search Qdrant
        logger.info("[RAG 4/8] Memulai search_similar")
        results = search_similar(query_emb)
        results = results or []
        logger.info(
            "[RAG 4/8] Qdrant mengembalikan %s points",
            len(results)
        )

        # 4. Build context
        logger.info("[RAG 5/8] Memulai build_context")
        context = build_context(results)

        # 5. No context
        if not context:
            logger.warning("[RAG 5/8] Context kosong")
            return {
                "answer": "tidak ditemukan",
                "context": "",
                "result_count": len(results),
                "matches": [],
            }

        # 6. Ask Groq
        logger.info("[RAG 6/8] Memulai ask_llm")
        answer = ask_llm(context, question)
        logger.info("[RAG 6/8] Jawaban LLM berhasil diterima")

        # 7. Fallback
        if is_not_found_answer(answer):
            answer = (
                "Berdasarkan konteks yang ditemukan, "
                "belum ada jawaban eksplisit untuk pertanyaan itu. "
                "Informasi terkait dari dokumen:\n\n"
                f"{make_context_preview(context)}"
            )

        # 8. Return
        logger.info("[RAG 7/8] Menyiapkan hasil")

        matches = []

        for point in results:
            payload = point.payload or {}

            matches.append({
                "score": point.score,
                "chunk_id": payload.get("chunk_id"),
                "document_id": payload.get("document_id"),
                "section": payload.get("section"),
                "page_start": payload.get("page_start"),
                "page_end": payload.get("page_end"),
                "text": payload.get("text"),
            })

        logger.info("[RAG 8/8] Selesai tanpa error")

        return {
            "answer": answer,
            "context": context,
            "result_count": len(results),
            "rewritten_query": rewritten_query,
            "matches": matches,
        }

    except Exception:
        logger.exception("[RAG ERROR] Gagal memproses pertanyaan")
        raise