import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

MODEL_NAME = "intfloat/multilingual-e5-large"
COLLECTION_NAME = "academic_chunks"

# =========================
# 1. Load model
# =========================
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Device: {device}")

model = SentenceTransformer(
    MODEL_NAME,
    device=device
)

# =========================
# 2. Text
# =========================
text = "Mahasiswa wajib melakukan registrasi akademik sesuai dengan ketentuan yang berlaku."

# E5 menggunakan prefix passage:
embedding = model.encode(
    "passage: " + text,
    normalize_embeddings=True
)

print(f"Embedding dimension: {len(embedding)}")

# =========================
# 3. Connect Qdrant
# =========================
client = QdrantClient(
    url="http://localhost:6333"
)

# =========================
# 4. Insert point
# =========================
payload = {
    "document_id": "DOC001",
    "category_id": "CAT001",
    "category_name": "Peraturan Akademik",
    "document_title": "Peraturan Akademik 2026",

    "file_id": "FILE001",
    "file_name": "peraturan_akademik_2026.pdf",

    "chunk_number": 1,

    "text": text,

    "metadata": {
        "page": 1,
        "source": "Peraturan Akademik 2026"
    }
}

client.upsert(
    collection_name=COLLECTION_NAME,
    points=[
        PointStruct(
            id=2,
            vector=embedding.tolist(),
            payload=payload
        )
    ]
)

print("Embedding berhasil dimasukkan ke Qdrant!")