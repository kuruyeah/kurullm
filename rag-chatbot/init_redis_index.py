"""
init_redis_index.py
Thesis: Comparative Analysis of Distributed Semantic Caching Algorithms
        for Mitigating Denial of Wallet in LLM APIs.

Purpose:
Initializes (or resets) the RediSearch Vector Index for storing 384-dimensional
L2-normalized embeddings from `sentence-transformers/all-MiniLM-L6-v2`.
"""

import os
import redis
from redis.commands.search.field import TextField, VectorField, NumericField
from redis.commands.search.index_definition import IndexDefinition, IndexType


# =====================================================================
# 1. THESIS EXPERIMENT CONFIGURATION (THE "KNOBS")
# =====================================================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

INDEX_NAME = "idx:semantic_cache"
DOC_PREFIX = "cache:faq:"
VECTOR_DIM = 384  # Output dimension of all-MiniLM-L6-v2

# Switch Distance Metric: "COSINE", "IP" (Inner Product), or "L2" (Euclidean)
DISTANCE_METRIC = os.getenv("DISTANCE_METRIC", "COSINE").upper()

# Switch Index Algorithm: "HNSW" (Approximate Graph) or "FLAT" (Exact Brute-Force)
INDEX_ALGORITHM = os.getenv("INDEX_ALGORITHM", "HNSW").upper()


def create_semantic_cache_index(drop_existing: bool = True) -> None:
    """
    Creates the Redis Stack vector index with the specified algorithm and metric.
    """
    if DISTANCE_METRIC not in {"COSINE", "IP", "L2"}:
        raise ValueError(f"Unsupported DISTANCE_METRIC: {DISTANCE_METRIC}. Choose COSINE, IP, or L2.")

    if INDEX_ALGORITHM not in {"HNSW", "FLAT"}:
        raise ValueError(f"Unsupported INDEX_ALGORITHM: {INDEX_ALGORITHM}. Choose HNSW or FLAT.")

    # 2. Connect to Redis Stack (decode_responses=False is required for binary float32 vectors)
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    r.ping()
    print(f"[*] Connected to Redis Stack at {REDIS_HOST}:{REDIS_PORT}")

    # 3. Drop existing index & cached data so every benchmark run starts clean
    if drop_existing:
        try:
            r.ft(INDEX_NAME).dropindex(delete_documents=True)
            print(f"[!] Dropped old index '{INDEX_NAME}' and cleared previous cached documents.")
        except redis.exceptions.ResponseError:
            print(f"[*] No existing index '{INDEX_NAME}' found. Creating fresh index...")

    # 4. Configure Vector Field parameters
    vector_params = {
        "TYPE": "FLOAT32",
        "DIM": VECTOR_DIM,
        "DISTANCE_METRIC": DISTANCE_METRIC,
    }

    # Add HNSW graph parameters only if using HNSW
    if INDEX_ALGORITHM == "HNSW":
        vector_params.update({
            "M": 16,                 # Max outgoing edges per node in each graph layer
            "EF_CONSTRUCTION": 200,  # Candidate list size when building the index
            "EF_RUNTIME": 10,        # Candidate list size when searching (KNN query)
        })

    # 5. Define the 4 columns/fields of each cached entry
    schema = (
        TextField("original_query"),
        TextField("response"),
        NumericField("created_at"),
        VectorField(
            "embedding",
            INDEX_ALGORITHM,
            vector_params,
        ),
    )

    # Watch all Redis Hash keys starting with "cache:faq:"
    definition = IndexDefinition(prefix=[DOC_PREFIX], index_type=IndexType.HASH)

    # 6. Create the Vector Index in Redis
    r.ft(INDEX_NAME).create_index(fields=schema, definition=definition)

    # 7. Save active config metadata in Redis so FastAPI knows which formula is active
    r.set("config:active_distance_metric", DISTANCE_METRIC.encode("utf-8"))
    r.set("config:active_algorithm", INDEX_ALGORITHM.encode("utf-8"))

    print("=" * 65)
    print("[+] SUCCESS: Semantic Cache Vector Index Initialized!")
    print(f"    - Index Name      : {INDEX_NAME}")
    print(f"    - Key Prefix      : {DOC_PREFIX}")
    print(f"    - Vector Dimension: {VECTOR_DIM} (FLOAT32)")
    print(f"    - Algorithm       : {INDEX_ALGORITHM}")
    print(f"    - Distance Metric : {DISTANCE_METRIC}")
    print("=" * 65)


if __name__ == "__main__":
    create_semantic_cache_index(drop_existing=True)