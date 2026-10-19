import time
import pandas as pd

from rag import (
    embed_query,
    search_similar,
    ask_llm,
)

TEST_QUESTIONS = [
    "Apa itu MBKM?",
    "Bagaimana prosedur cuti akademik?",
    "Bagaimana prosedur mengulang mata kuliah?",
    "kapan ujian akhir semester",
]

TOP_KS = [5, 10, 15, 20]

results = []

for question in TEST_QUESTIONS:

    print("\n" + "=" * 100)
    print(f"QUESTION : {question}")
    print("=" * 100)

    embedding = embed_query(question)

    for topk in TOP_KS:

        print(f"\nTOP-K = {topk}")

        # -------------------------
        # Retrieval
        # -------------------------
        retrieval_start = time.perf_counter()

        docs = search_similar(
            embedding,
            match_count=topk
        )
        print("Jumlah docs:", len(docs))

        retrieval_time = time.perf_counter() - retrieval_start

        context = "\n\n".join(
            d["content"]
            for d in docs
            if d["content"]
        )

        # -------------------------
        # Context Statistics
        # -------------------------
        context_length = len(context)

        print(f"Context Characters : {context_length}")

        

        # -------------------------
        # LLM
        # -------------------------
        llm_start = time.perf_counter()

        answer = ask_llm(context, question)

        llm_time = time.perf_counter() - llm_start

        total_time = retrieval_time + llm_time

        # -------------------------
        # Similarity
        # -------------------------
        similarities = [
            d["similarity"]
            for d in docs
            if d.get("similarity") is not None
        ]

        avg_similarity = (
            sum(similarities) / len(similarities)
            if similarities else 0
        )

        print(f"Retrieval : {retrieval_time:.3f} s")
        print(f"LLM       : {llm_time:.3f} s")
        print(f"Total     : {total_time:.3f} s")
        print(f"Average Similarity : {avg_similarity:.4f}")

        print("\nRetrieved Chunks")
        print("-" * 100)

        print("\nRetrieved Chunks")
        print("-" * 100)

        chunk_info = []

        for rank, doc in enumerate(docs, start=1):

            similarity = doc["similarity"]

            preview = doc["content"][:300].replace("\n", " ")

            chunk_info.append({
                "rank": rank,
                "similarity": similarity,
                "preview": preview
            })

            print(f"[{rank}] Similarity = {similarity:.4f}")
            print(preview)
            print("-" * 100)
        print("\nANSWER")
        print(answer)

        results.append({

    "question": question,

    "top_k": topk,

    "retrieval_time": retrieval_time,

    "llm_time": llm_time,

    "total_time": total_time,

    "avg_similarity": avg_similarity,

    "context_length": context_length,

    "chunks": str(chunk_info),

    "answer": answer
})

df = pd.DataFrame(results)

df.to_csv("topk_evaluation.csv", index=False)

print("\n\n==============================")
print("Evaluation Finished")
print("==============================")

print(df)