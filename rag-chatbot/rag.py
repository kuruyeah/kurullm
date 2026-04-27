from sentence_transformers import SentenceTransformer
from supabase import create_client
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

# INIT
model = SentenceTransformer(
    "intfloat/multilingual-e5-large",
    device="cuda"
)

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# FUNCTIONS
def embed_query(text):
    return model.encode(f"query: {text}").tolist()

def search_similar(query_embedding):
    result = supabase.rpc("match_documents1", {
        "query_embedding": query_embedding,
        "match_count": 3
    }).execute()
    return result.data

def ask_llm(context, question):
    prompt = f"""
Jawab hanya berdasarkan konteks berikut.
Jika tidak ada, jawab tidak ditemukan.

Context:
{context}

Pertanyaan:
{question}
"""

    res = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return res.choices[0].message.content

def run_rag(question):
    query_emb = embed_query(question)
    results = search_similar(query_emb)

    context = "\n\n".join([r["content"] for r in results])

    answer = ask_llm(context, question)

    return {
        "answer": answer,
        "context": context
    }