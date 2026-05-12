from sentence_transformers import SentenceTransformer
import torch
import time

# SAFE DEVICE CHECK
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
elif torch.backends.mps.is_available():
    print("Using Apple GPU (MPS)")
else:
    print("Using CPU")

# BETTER MODEL (lighter & faster)
model = SentenceTransformer("all-MiniLM-L6-v2")

texts = [
    "query: apa itu machine learning?",
    "passage: machine learning adalah cabang AI yang mempelajari pola dari data"
] * 100

start = time.time()

embeddings = model.encode(
    texts,
    batch_size=64,   # safe value
    show_progress_bar=True,
    convert_to_tensor=False
)

end = time.time()

print("Selesai!")
print("Total embeddings:", len(embeddings))
print("Time:", end - start)
