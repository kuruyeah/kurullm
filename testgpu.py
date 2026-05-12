from sentence_transformers import SentenceTransformer
import torch
import time
import gc

# ========================
# DEVICE CHECK (SAFE)
# ========================
if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

print("Using device:", device)

# ========================
# LOAD MODEL (LIGHTWEIGHT)
# ========================
model = SentenceTransformer("all-MiniLM-L6-v2")
model = model.to(device)

# ========================
# DATA
# ========================
texts = [
    "query: apa itu machine learning?",
    "passage: machine learning adalah cabang AI yang mempelajari pola dari data"
] * 1000   # smaller first

print("Total texts:", len(texts))

# ========================
# BENCHMARK FUNCTION
# ========================
def benchmark(batch_size):
    try:
        gc.collect()

        start = time.time()

        with torch.no_grad():
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_tensor=False
            )

        end = time.time()

        total_time = end - start
        throughput = len(texts) / total_time

        print(f"\n=== BATCH {batch_size} ===")
        print("Time:", total_time)
        print("Throughput:", throughput, "texts/sec")

        return total_time, throughput

    except RuntimeError as e:
        print(f"\n❌ BATCH {batch_size} FAILED:", e)
        return None, None


# ========================
# RUN TEST
# ========================
results = {}

for bs in [32, 64, 128, 256]:
    t, th = benchmark(bs)
    if t is None:
        break
    results[bs] = (t, th)


# ========================
# SUMMARY
# ========================
print("\n=== SUMMARY ===")
for bs, (t, th) in results.items():
    print(f"Batch {bs}: {t:.3f}s | {th:.2f} texts/sec")

if results:
    best = max(results.items(), key=lambda x: x[1][1])
    print(f"\n🔥 BEST BATCH: {best[0]} (Throughput: {best[1][1]:.2f} texts/sec)")
