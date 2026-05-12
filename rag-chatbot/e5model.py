from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "intfloat/multilingual-e5-large",
    device="cpu"
)

print(model.device)