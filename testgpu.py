from sentence_transformers import SentenceTransformer
import torch
import time
import gc

# ========================
# INFO GPU
# ========================
print("GPU:", torch.cuda.get_device_name(0))
print("VRAM:", torch.cuda.get_device_properties(0).total_memory / 1e9, "GB")

# ========================
# LOAD MODEL
# ========================
model = SentenceTransformer("intfloat/e5-large", device="cuda")

# optional: hemat VRAM + lebih cepat
model = model.half()

# ========================
# DATA (besar biar realistis)
# ========================
texts = [
    "query: apa itu machine learning?",
    "passage: machine learning adalah cabang AI yang mempelajari pola dari data"
] * 10000   # = 20.000 teks

print("Total texts:", len(texts))

# ========================
# BENCHMARK FUNCTION
# ========================
def benchmark(batch_size):
    try:
        torch.cuda.empty_cache()
        gc.collect()

        start = time.time()

        with torch.no_grad():
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_tensor=True
            )

        end = time.time()

        total_time = end - start
        throughput = len(texts) / total_time

        print(f"\n=== BATCH {batch_size} ===")
        print("Shape:", embeddings.shape)
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

for bs in [64, 128, 256, 512, 1024]:
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

best = max(results.items(), key=lambda x: x[1][1])
print(f"\n🔥 BEST BATCH: {best[0]} (Throughput: {best[1][1]:.2f} texts/sec)")