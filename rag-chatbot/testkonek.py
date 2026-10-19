import os
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
client = QdrantClient(url=QDRANT_URL)

def check_all_documents():
    print("=" * 60)
    print("DAFTAR DOKUMEN DI KNOWLEDGE_DOCUMENTS")
    print("=" * 60)

    records, _ = client.scroll(
        collection_name="knowledge_documents",
        limit=100
    )

    print(f"Total Dokumen Tersimpan: {len(records)}\n")

    for idx, point in enumerate(records, 1):
        p = point.payload or {}
        print(f"[{idx}] Document ID : {p.get('document_id')}")
        print(f"    Judul       : {p.get('title')}")
        print(f"    File Name   : {p.get('file_name')}")
        print(f"    URL Download: {p.get('download_url')}")
        print(f"    Status      : {p.get('status')}")
        print("-" * 60)

if __name__ == "__main__":
    check_all_documents()