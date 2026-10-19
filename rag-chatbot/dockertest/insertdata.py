from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import random

client = QdrantClient(url="http://localhost:6333")

vector = [random.random() for _ in range(1024)]

payload = {
    "document_id": "DOC001",
    "category_id": "CAT001",
    "category_name": "Peraturan Akademik",
    "document_title": "Peraturan Akademik 2026",
    "chunk_number": 1,
    "text": "Mahasiswa wajib melakukan registrasi akademik sesuai dengan ketentuan yang berlaku.",
    "metadata": {
        "source": "Peraturan Akademik 2026",
        "page": 1
    }
}

client.upsert(
    collection_name="academic_chunks",
    points=[
        PointStruct(
            id=1,
            vector=vector,
            payload=payload
        )
    ]
)

print("Point berhasil dimasukkan!")