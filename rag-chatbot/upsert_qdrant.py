import json
import uuid
import torch

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


# =========================================================
# CONFIG
# =========================================================

INPUT_FILE = r"test_mineru\parsed_chunks_v4_2.json"

MODEL_NAME = "intfloat/multilingual-e5-large"

QDRANT_URL = "http://localhost:6333"

COLLECTION_NAME = "academic_chunks"

BATCH_SIZE = 16


# =========================================================
# DEVICE
# =========================================================

device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("UPSERT EMBEDDINGS TO QDRANT")
print("=" * 60)

print(f"Device     : {device}")

if device == "cuda":
    print(
        f"GPU        : {torch.cuda.get_device_name(0)}"
    )

# =========================================================
# LOAD CHUNKS
# =========================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    chunks = json.load(f)

print(f"Chunks     : {len(chunks)}")


# =========================================================
# LOAD MODEL
# =========================================================

print("\nLoading embedding model...")

model = SentenceTransformer(
    MODEL_NAME,
    device=device
)

print("Model loaded.")


# =========================================================
# PREPARE TEXT
# =========================================================

texts = []

for chunk in chunks:

    text = chunk.get(
        "text",
        ""
    ).strip()

    texts.append(
        "passage: " + text
    )


# =========================================================
# GENERATE EMBEDDINGS
# =========================================================

print("\nGenerating embeddings...")

embeddings = model.encode(
    texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    normalize_embeddings=True,
    convert_to_numpy=True
)

print(
    f"Embedding shape : {embeddings.shape}"
)


# =========================================================
# CONNECT QDRANT
# =========================================================

print("\nConnecting to Qdrant...")

client = QdrantClient(
    url=QDRANT_URL
)

print("Connected.")


# =========================================================
# CHECK COLLECTION
# =========================================================

collections = client.get_collections()

collection_names = [
    collection.name
    for collection in collections.collections
]

if COLLECTION_NAME not in collection_names:

    raise RuntimeError(
        f"Collection '{COLLECTION_NAME}' "
        "tidak ditemukan."
    )

print(
    f"Collection    : {COLLECTION_NAME}"
)


# =========================================================
# CREATE POINTS
# =========================================================

points = []

for index, chunk in enumerate(chunks):

    # UUID deterministik berdasarkan chunk_id
    point_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            chunk["chunk_id"]
        )
    )

    payload = {
        "chunk_id": chunk.get("chunk_id"),
        "document_id": chunk.get("document_id"),
        "file_id": chunk.get("file_id"),
        "category_id": chunk.get("category_id"),
        "category_name": chunk.get("category_name"),
        "document_title": chunk.get("document_title"),
        "section": chunk.get("section"),
        "subsections": chunk.get("subsections", []),
        "page_start": chunk.get("page_start"),
        "page_end": chunk.get("page_end"),
        "chunk_number": chunk.get("chunk_number"),
        "token_count": chunk.get("token_count"),
        "text": chunk.get("text")
    }

    points.append(
        PointStruct(
            id=point_id,
            vector=embeddings[index].tolist(),
            payload=payload
        )
    )


# =========================================================
# UPSERT
# =========================================================

print(
    f"\nUploading {len(points)} points..."
)

client.upsert(
    collection_name=COLLECTION_NAME,
    points=points
)

print("\n" + "=" * 60)
print("UPLOAD SELESAI")
print("=" * 60)

print(
    f"Points uploaded : {len(points)}"
)

print(
    f"Collection      : {COLLECTION_NAME}"
)


# =========================================================
# VERIFY
# =========================================================

info = client.get_collection(
    COLLECTION_NAME
)

print(
    f"Points in Qdrant: {info.points_count}"
)

print("=" * 60)