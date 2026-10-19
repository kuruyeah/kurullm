import json
import torch
from sentence_transformers import SentenceTransformer

# =========================================================
# CONFIG
# =========================================================

INPUT_FILE = r"test_mineru\parsed_chunks_v4_2.json"

MODEL_NAME = "intfloat/multilingual-e5-large"

BATCH_SIZE = 16

# =========================================================
# DEVICE
# =========================================================

device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("EMBEDDING CHUNKS")
print("=" * 60)

print(f"Device : {device}")

if device == "cuda":
    print(f"GPU    : {torch.cuda.get_device_name(0)}")
    print(f"CUDA   : {torch.version.cuda}")

# =========================================================
# LOAD JSON
# =========================================================

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    chunks = json.load(f)

print(f"Chunks : {len(chunks)}")

# =========================================================
# LOAD MODEL
# =========================================================

print("\nLoading model...")

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

    text = chunk.get("text", "").strip()

    if not text:
        text = "[EMPTY]"

    # E5 document embedding
    texts.append(
        "passage: " + text
    )

# =========================================================
# EMBEDDING
# =========================================================

print("\nGenerating embeddings...")

embeddings = model.encode(
    texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    normalize_embeddings=True,
    convert_to_numpy=True
)

# =========================================================
# CHECK RESULT
# =========================================================

print("\n" + "=" * 60)
print("RESULT")
print("=" * 60)

print(f"Embedding shape : {embeddings.shape}")
print(f"Expected dim    : 1024")

if embeddings.shape[1] != 1024:

    raise ValueError(
        f"Embedding dimension salah: {embeddings.shape[1]}"
    )

print("Dimension       : OK")
print("Normalization   : OK")

# =========================================================
# SAMPLE
# =========================================================

print("\nSample:")

print(f"Chunk ID : {chunks[0]['chunk_id']}")
print(f"Text     : {chunks[0]['text'][:200]}")
print(
    f"Vector   : {embeddings[0][:10]}"
)

print("\nEmbedding selesai.")