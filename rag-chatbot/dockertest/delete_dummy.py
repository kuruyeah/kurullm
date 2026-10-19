from qdrant_client import QdrantClient

client = QdrantClient(
    url="http://localhost:6333"
)

client.delete(
    collection_name="academic_chunks",
    points_selector=[1]
)

print("Dummy Point ID 1 berhasil dihapus.")