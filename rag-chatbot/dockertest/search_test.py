import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient


MODEL_NAME = "intfloat/multilingual-e5-large"
COLLECTION_NAME = "academic_chunks"


# =========================
# 1. Cek device
# =========================

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Device: {device}")

if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")


# =========================
# 2. Load embedding model
# =========================

print("\nLoading embedding model...")

model = SentenceTransformer(
    MODEL_NAME,
    device=device
)


# =========================
# 3. Connect Qdrant
# =========================

client = QdrantClient(
    url="http://localhost:6333"
)


# =========================
# 4. Query
# =========================

query = "Bagaimana mahasiswa melakukan registrasi?"

print(f"\nQuery: {query}")


# =========================
# 5. Generate query embedding
# =========================

query_embedding = model.encode(
    "query: " + query,
    normalize_embeddings=True
)


print(f"Embedding dimension: {len(query_embedding)}")


# =========================
# 6. Search Qdrant
# =========================

results = client.query_points(
    collection_name=COLLECTION_NAME,
    query=query_embedding.tolist(),
    limit=5,
    with_payload=True
).points


# =========================
# 7. Display results
# =========================

print("\n" + "=" * 60)
print("HASIL SEMANTIC RETRIEVAL")
print("=" * 60)

for i, result in enumerate(results, start=1):

    payload = result.payload

    print(f"\n[{i}]")
    print(f"Score       : {result.score}")
    print(f"Document ID : {payload.get('document_id')}")
    print(f"Document    : {payload.get('document_title')}")
    print(f"Chunk       : {payload.get('chunk_number')}")
    print(f"File        : {payload.get('file_name')}")
    print(f"Text        : {payload.get('text')}")