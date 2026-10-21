"""
semantic_cache.py
Thesis: Comparative Analysis of Distributed Semantic Caching Algorithms
        for Mitigating Denial of Wallet in LLM APIs.

Contains:
- Step 2: FastEmbed 384-dim Vector Generation (all-MiniLM-L6-v2)
- Step 3: NumPy L2 Vector Normalization
- Step 4: Redis Vector Search (KNN 1) & Distance-to-Similarity Conversion
- Step 7: Redis Cache Persistence with TTL (Memory Exhaustion Protection)
"""

import os

# Disable Xet chunker and increase HTTPS timeout for one-time model download
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"
os.environ["HF_HUB_ETAG_TIMEOUT"] = "60"

import time
import uuid
import logging
import numpy as np
import redis
from fastembed import TextEmbedding
from redis.commands.search.query import Query

logger = logging.getLogger("DoW-Defense-Gateway")

# =====================================================================
# CONFIGURATION
# =====================================================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

INDEX_NAME = "idx:semantic_cache"
DOC_PREFIX = "cache:faq:"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.80"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour TTL

# Global singletons (loaded once)
_embed_model: TextEmbedding | None = None
_redis_client: redis.Redis | None = None


def get_embed_model() -> TextEmbedding:
    """Loads the FastEmbed ONNX model once into memory."""
    global _embed_model
    if _embed_model is None:
        logger.info(f"Loading FastEmbed model: {EMBEDDING_MODEL_NAME} ...")
        _embed_model = TextEmbedding(
            model_name=EMBEDDING_MODEL_NAME,
            cache_dir="./model_cache",
        )
    return _embed_model


def get_redis_client() -> redis.Redis:
    """Creates or returns the Redis Stack client connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=False,  # Must be False for binary FLOAT32 vectors
        )
        _redis_client.ping()
    return _redis_client


# =====================================================================
# STEP 2 & STEP 3: EMBEDDING GENERATION + L2 NORMALIZATION
# =====================================================================
def generate_normalized_embedding(text: str) -> bytes:
    """
    [STEP 2]: Generates a 384-dimensional vector using FastEmbed (all-MiniLM-L6-v2).
    [STEP 3]: Applies explicit L2 normalization via NumPy so ||v||_2 = 1.0.
              This guarantees mathematical comparability across COSINE, IP, and L2.
    """
    model = get_embed_model()

    # Step 2: Generate raw 384-dim embedding vector
    raw_vector = next(model.embed([text]))
    vec = np.asarray(raw_vector, dtype=np.float32)

    # Step 3: Explicit L2 Normalization: v_norm = v / ||v||_2
    l2_norm = np.linalg.norm(vec)
    if l2_norm > 0:
        normalized_vec = vec / l2_norm
    else:
        normalized_vec = vec

    # Convert to raw FLOAT32 bytes for Redis storage & search
    return normalized_vec.astype(np.float32).tobytes()


# =====================================================================
# STEP 4: REDIS VECTOR SEARCH & SIMILARITY CALCULATION
# =====================================================================
def search_semantic_cache(embedding_bytes: bytes) -> dict:
    """
    [STEP 4]: Queries the Redis index for the closest cached question vector (KNN 1)
    and converts Redis's raw distance into a normalized similarity score [0.0 - 1.0].
    """
    r = get_redis_client()

    # Read active metric & algorithm set by init_redis_index.py
    raw_metric = r.get("config:active_distance_metric")
    active_metric = raw_metric.decode("utf-8") if raw_metric else "COSINE"

    raw_algo = r.get("config:active_algorithm")
    active_algo = raw_algo.decode("utf-8") if raw_algo else "HNSW"

    # Build RediSearch KNN=1 query
    redis_query = (
        Query("*=>[KNN 1 @embedding $vec_param AS vector_distance]")
        .sort_by("vector_distance")
        .return_fields("original_query", "response", "vector_distance")
        .dialect(2)
    )

    search_results = r.ft(INDEX_NAME).search(
        redis_query,
        query_params={"vec_param": embedding_bytes},
    )

    best_similarity = 0.0
    cached_response = None
    matched_query = None

    if search_results.docs:
        top_doc = search_results.docs[0]
        vector_distance = float(top_doc.vector_distance)

        # Convert Redis Distance -> Similarity [0.0 to 1.0]
        if active_metric == "L2":
            # On unit vectors: d_L2^2 = 2 * (1 - cosine_similarity)
            best_similarity = round(1.0 - (vector_distance / 2.0), 4)
        else:
            # On unit vectors for COSINE and IP: distance = 1 - similarity
            best_similarity = round(1.0 - vector_distance, 4)

        raw_resp = getattr(top_doc, "response", None)
        if isinstance(raw_resp, bytes):
            cached_response = raw_resp.decode("utf-8")
        elif isinstance(raw_resp, str):
            cached_response = raw_resp

        raw_orig = getattr(top_doc, "original_query", None)
        if isinstance(raw_orig, bytes):
            matched_query = raw_orig.decode("utf-8")
        elif isinstance(raw_orig, str):
            matched_query = raw_orig

    is_hit = cached_response is not None and best_similarity >= SIMILARITY_THRESHOLD

    return {
        "is_hit": is_hit,
        "similarity_score": best_similarity,
        "cached_response": cached_response if is_hit else None,
        "matched_query": matched_query,
        "distance_metric": active_metric,
        "index_algorithm": active_algo,
    }


# =====================================================================
# STEP 7: REDIS CACHE UPDATE (WITH TTL FOR OOM PROTECTION)
# =====================================================================
def save_to_redis_cache(query_text: str, embedding_bytes: bytes, llm_response: str) -> str:
    """
    [STEP 7]: Saves the normalized question vector and plain-text LLM answer
    into Redis Stack with a TTL (CACHE_TTL_SECONDS) to prevent memory exhaustion.
    """
    r = get_redis_client()
    doc_key = f"{DOC_PREFIX}{uuid.uuid4().hex}"

    pipe = r.pipeline()
    pipe.hset(
        doc_key,
        mapping={
            "original_query": query_text.encode("utf-8"),
            "response": llm_response.encode("utf-8"),
            "embedding": embedding_bytes,
            "created_at": int(time.time()),
        },
    )
    # [DoW MITIGATION]: Auto-expire entry after 1 hour so RAM never overflows
    pipe.expire(doc_key, CACHE_TTL_SECONDS)
    pipe.execute()

    logger.info(f"[Cache Write] Stored key={doc_key} for query='{query_text[:45]}'")
    return doc_key


# =====================================================================
# QUICK SELF-TEST (RUN DIRECTLY IN TERMINAL TO VERIFY)
# =====================================================================
if __name__ == "__main__":
    print("1. Loading FastEmbed & generating normalized vector for Query 1...")
    q1 = "How do I pay my semester tuition fee at the university?"
    vec1 = generate_normalized_embedding(q1)

    # Verify L2 Norm == 1.0
    arr1 = np.frombuffer(vec1, dtype=np.float32)
    print(f"   Vector shape: {arr1.shape} | L2 Norm: {np.linalg.norm(arr1):.6f}")

    print("\n2. Saving Query 1 + Dummy Answer into Redis...")
    key = save_to_redis_cache(
        query_text=q1,
        embedding_bytes=vec1,
        llm_response="You can pay your semester tuition fee (UKT) via the student portal Virtual Account.",
    )
    print(f"   Saved under Redis key: {key}")

    print("\n3. Testing Semantic Search with a PARAPHRASED Query 2...")
    q2 = "What is the procedure for paying university tuition fees?"
    vec2 = generate_normalized_embedding(q2)
    result = search_semantic_cache(vec2)

    print("   Search Result:")
    print(f"   - Input Query     : {q2}")
    print(f"   - Matched in Cache: {result['matched_query']}")
    print(f"   - Algorithm/Metric: {result['index_algorithm']} / {result['distance_metric']}")
    print(f"   - Similarity Score: {result['similarity_score']} (Threshold: {SIMILARITY_THRESHOLD})")
    print(f"   - Cache Status    : {'HIT' if result['is_hit'] else 'MISS'}")
    print(f"   - Returned Answer : {result['cached_response']}")
