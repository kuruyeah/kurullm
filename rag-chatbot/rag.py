from sentence_transformers import SentenceTransformer
from supabase import create_client  # type: ignore[import]
from groq import Groq  # type: ignore[import]
import os
from dotenv import load_dotenv  # type: ignore[import]

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
System: You are a helpful, conversational assistant. 
Use the provided context to answer the question.

Rules:
1. Grounding: Answer ONLY based on the context. If the answer isn't there, say sorry you can't find it.
2. Language Mirroring: Always respond using the SAME language as the user's question. 
   (e.g., If the question is in English, answer in English. If in Indonesian, answer in Indonesian).
3. Personality: Be warm and human-like. Avoid robotic or dry responses.
4. if you don't know the answer, say you don't know but answer in a human-like way, don't just say "I don't know", but say something like "I'm not sure about that, but I can help you find out!" or "That's a great question! I don't have the answer right now, but let's figure it out together!"


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