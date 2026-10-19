from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from groq import Groq
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

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

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_chunks")

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
        match_count = int(os.getenv("RAG_MATCH_COUNT", "5"))

    result = get_qdrant().query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_embedding,
        limit=match_count,
        with_payload=True,
        with_vectors=False,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="is_active",
                    match=MatchValue(value=True) # Memastikan hanya membaca chunk dokumen aktif
                )
            ]
        )
    )

    return result.points


def get_document_metadata(doc_id):
    """
    Mencari metadata dokumen (seperti Judul dan URL) 
    dari koleksi knowledge_documents berdasarkan document_id.
    """
    try:
        records, _ = get_qdrant().scroll(
            collection_name="knowledge_documents",
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id", 
                        match=MatchValue(value=doc_id)
                    )
                ]
            ),
            limit=1
        )
        if records:
            return records[0].payload
    except Exception as e:
        logger.error(f"Gagal mengambil metadata untuk {doc_id}: {e}")
    
    return {}

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

# ============================================================
# CONTEXT BUILDER (Perbarui bagian ini)
# ============================================================
def build_context(results):
    contexts = []

    for point in results:
        payload = point.payload or {}
        text = str(payload.get("text", "")).strip()

        if not text:
            continue

        section = payload.get("section", "")
        subsections = payload.get("subsections", []) # Ambil subsections
        page_start = payload.get("page_start", "")
        page_end = payload.get("page_end", "")
        chunk_id = payload.get("chunk_id", "")

        metadata = []

        if section:
            metadata.append(f"Section: {section}")
            
        # Tambahkan subsections ke dalam konteks LLM
        if subsections:
            metadata.append(f"Subsections: {', '.join(subsections)}")

        if page_start:
            if page_end and page_end != page_start:
                metadata.append(f"Page: {page_start}-{page_end}")
            else:
                metadata.append(f"Page: {page_start}")

        header = "\n".join(metadata)

        if header:
            context_item = f"[{header}]\n{text}"
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
                "referenced_docs": []
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

        # 8. Return & Ambil Metadata Dokumen
        logger.info("[RAG 7/8] Menyiapkan hasil dan mengambil metadata dokumen")

        matches = []
        unique_doc_ids = set() 
        referenced_docs = []

        # 1. Simpan semua matches untuk logging/debug
        for point in results:
            payload = point.payload or {}
            matches.append({
                "score": point.score,
                "chunk_id": payload.get("chunk_id"),
                "document_id": payload.get("document_id"),
                "section": payload.get("section"),
                "page_start": payload.get("page_start"),
                "text": payload.get("text"),
            })

        # 2. Logika Penentuan Referensi Dominan
        if results:
            top_doc_id = results[0].payload.get("document_id")
            top_score = results[0].score

            # Wajib masukkan dokumen dari chunk peringkat #1
            if top_doc_id:
                unique_doc_ids.add(top_doc_id)

            # Dokumen lain HANYA masuk jika skornya hampir identik dengan peringkat #1 (margin <= 0.01)
            for point in results[1:3]:
                payload = point.payload or {}
                doc_id = payload.get("document_id")
                score = point.score

                if doc_id and doc_id != top_doc_id:
                    if (top_score - score) <= 0.01:  # Memperketat filter dari 0.03 menjadi 0.01
                        unique_doc_ids.add(doc_id)

        # 3. Ambil metadata dari knowledge_documents
        for doc_id in unique_doc_ids:
            doc_meta = get_document_metadata(doc_id)
            if doc_meta:
                referenced_docs.append({
                    "title": doc_meta.get("title", "Dokumen Akademik"),
                    "download_url": doc_meta.get("download_url", ""),
                    "file_name": doc_meta.get("file_name", "")
                })

        logger.info("[RAG 8/8] Selesai tanpa error")

        return {
            "answer": answer,
            "context": context,
            "result_count": len(results),
            "rewritten_query": rewritten_query,
            "matches": matches,
            "referenced_docs": referenced_docs
        }

    except Exception:
        logger.exception("[RAG ERROR] Gagal memproses pertanyaan")
        raise