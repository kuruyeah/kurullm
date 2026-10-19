import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient


# =========================================================
# CONFIG
# =========================================================

MODEL_NAME = "intfloat/multilingual-e5-large"

QDRANT_URL = "http://localhost:6333"

COLLECTION_NAME = "academic_chunks"

TOP_K = 3


# =========================================================
# DEVICE
# =========================================================

device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("QDRANT SEMANTIC SEARCH")
print("=" * 60)

print(f"Device : {device}")

if device == "cuda":
    print(
        f"GPU    : {torch.cuda.get_device_name(0)}"
    )


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
# CONNECT QDRANT
# =========================================================

client = QdrantClient(
    url=QDRANT_URL
)

print("Connected to Qdrant.")


# =========================================================
# QUERY
# =========================================================

query = input(
    "\nMasukkan pertanyaan: "
).strip()

if not query:
    print("Pertanyaan kosong.")
    exit()


# =========================================================
# QUERY EMBEDDING
# =========================================================

query_embedding = model.encode(
    "query: " + query,
    normalize_embeddings=True,
    convert_to_numpy=True
)


# =========================================================
# SEARCH
# =========================================================

results = client.query_points(
    collection_name=COLLECTION_NAME,
    query=query_embedding.tolist(),
    limit=TOP_K,
    with_payload=True
).points


# =========================================================
# DISPLAY
# =========================================================

print("\n" + "=" * 60)
print("HASIL SEMANTIC SEARCH")
print("=" * 60)

for i, result in enumerate(results, start=1):

    payload = result.payload

    print(f"\n[Result {i}]")
    print(f"Score       : {result.score}")
    print(
        f"Chunk ID    : {payload.get('chunk_id')}"
    )
    print(
        f"Section     : {payload.get('section')}"
    )
    print(
        f"Page        : "
        f"{payload.get('page_start')}-"
        f"{payload.get('page_end')}"
    )

    print(
        f"Text        : "
        f"{payload.get('text', '')[:500]}"
    )

print("\n" + "=" * 60)