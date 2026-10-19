from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

collection_name = "academic_chunks"

client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE
    )
)

print(f"Collection '{collection_name}' berhasil dibuat!")

print(client.get_collections())