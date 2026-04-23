from sentence_transformers import SentenceTransformer
import torch
import time

print("GPU:", torch.cuda.get_device_name(0))

model = SentenceTransformer("intfloat/e5-large", device="cuda")

texts = [
    "query: apa itu machine learning?",
    "passage: machine learning adalah cabang AI yang mempelajari pola dari data"
] * 100  # biar agak berat

start = time.time()

embeddings = model.encode(
    texts,
    batch_size=1024,  # naikkan dari 32
    show_progress_bar=True,
    convert_to_tensor=True
)

end = time.time()

print("Selesai!")
print("Shape:", embeddings.shape)
print("Time:", end - start)