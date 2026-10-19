import os
import logging
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
VECTOR_DIMENSION = 1024 # Dimensi untuk intfloat/multilingual-e5-large

COLLECTION_DOCS = "knowledge_documents"
COLLECTION_CHUNKS = "knowledge_chunks"

def init_qdrant_collections():
    logger.info(f"Menghubungkan ke Qdrant di {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)

    # 1. Inisiasi knowledge_documents (Tanpa Vektor)
    logger.info(f"Memeriksa koleksi '{COLLECTION_DOCS}'...")
    if not client.collection_exists(COLLECTION_DOCS):
        logger.info(f"Membuat koleksi '{COLLECTION_DOCS}'...")
        client.create_collection(
            collection_name=COLLECTION_DOCS,
            # Qdrant memerlukan definisi vektor, jika tidak dipakai, kita set size kecil atau kosong
            vectors_config={}, 
        )
        logger.info(f"Koleksi '{COLLECTION_DOCS}' berhasil dibuat.")
    else:
        logger.info(f"Koleksi '{COLLECTION_DOCS}' sudah ada.")

    # 2. Inisiasi knowledge_chunks (Dengan Vektor 1024)
    logger.info(f"Memeriksa koleksi '{COLLECTION_CHUNKS}'...")
    if not client.collection_exists(COLLECTION_CHUNKS):
        logger.info(f"Membuat koleksi '{COLLECTION_CHUNKS}' dengan dimensi vektor {VECTOR_DIMENSION}...")
        client.create_collection(
            collection_name=COLLECTION_CHUNKS,
            vectors_config=VectorParams(
                size=VECTOR_DIMENSION, 
                distance=Distance.COSINE
            ),
        )
        logger.info(f"Koleksi '{COLLECTION_CHUNKS}' berhasil dibuat.")
    else:
        logger.info(f"Koleksi '{COLLECTION_CHUNKS}' sudah ada.")

    logger.info("Inisiasi database Qdrant selesai.")

if __name__ == "__main__":
    init_qdrant_collections()