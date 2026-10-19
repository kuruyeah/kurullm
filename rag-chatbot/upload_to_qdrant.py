import json
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================
JSON_PATH = Path(r".\test_mineru\knowledge_chunks_v1.json")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_CHUNKS = "knowledge_chunks"
COLLECTION_DOCS = "knowledge_documents"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

def main():
    if not JSON_PATH.exists():
        logger.error(f"File {JSON_PATH} tidak ditemukan.")
        return

    logger.info("Membaca file JSON...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    logger.info(f"Ditemukan {len(chunks)} chunks untuk diunggah.")

    logger.info("Memuat model embedding...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    logger.info("Menghubungkan ke Qdrant...")
    client = QdrantClient(url=QDRANT_URL)

    # ------------------------------------------------------------
    # 1. UPLOAD METADATA KE KNOWLEDGE_DOCUMENTS
    # ------------------------------------------------------------
    logger.info("Mengunggah metadata ke knowledge_documents...")
    
    # Ambil document_id dan version_id dari chunk pertama sebagai referensi
    doc_id = chunks[0]["document_id"]
    ver_id = chunks[0].get("version_id", "VER_001")
    
    # Generate UUID untuk dokumen induk
    doc_point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, doc_id))
    
    doc_point = PointStruct(
        id=doc_point_id,
        vector={}, # Kosong karena koleksi ini tidak memakai vektor
        payload={
            "document_id": doc_id,
            "version_id": ver_id,
            "title": "Panduan Penggunaan Web ULT", # Sesuaikan dengan judul aslinya
            "category_id": "CAT_PANDUAN",
            "file_name": "panduan_web_ult_v1.pdf",
            "download_url": "https://bit.ly/panduan-ult-v1",
            "status": "active",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
    )
    
    client.upsert(
        collection_name=COLLECTION_DOCS,
        wait=True,
        points=[doc_point]
    )
    logger.info("Metadata dokumen berhasil diunggah!")

    # ------------------------------------------------------------
    # 2. UPLOAD CHUNKS KE KNOWLEDGE_CHUNKS
    # ------------------------------------------------------------
    points = []
    logger.info("Memproses embedding untuk chunks...")
    for chunk in chunks:
        text_to_embed = f"passage: {chunk['text']}"
        embedding = model.encode(text_to_embed, normalize_embeddings=True).tolist()
        
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk["chunk_id"]))

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "version_id": chunk.get("version_id", "VER_001"),
                "section": chunk.get("section", ""),
                "subsections": chunk.get("subsections", []),
                "page_start": chunk.get("page_start", 0),
                "page_end": chunk.get("page_end", 0),
                "chunk_number": chunk.get("chunk_number", 0),
                "token_count": chunk.get("token_count", 0),
                "is_active": chunk.get("is_active", True),
                "text": chunk["text"]
            }
        )
        points.append(point)

    logger.info("Mengunggah chunks ke Qdrant...")
    operation_info = client.upsert(
        collection_name=COLLECTION_CHUNKS,
        wait=True,
        points=points
    )

    logger.info("Upload Chunks Selesai! Status:")
    logger.info(operation_info)

if __name__ == "__main__":
    main()