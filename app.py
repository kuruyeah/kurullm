import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
from groq import Groq
from langdetect import detect, DetectorFactory
from dotenv import load_dotenv
import os

load_dotenv()

# biar stabil
DetectorFactory.seed = 0

# ========================
# CONFIG (pakai env lebih aman)
# ========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ========================
# INIT
# ========================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer('all-MiniLM-L6-v2')
client = Groq(api_key=GROQ_API_KEY)

# ========================
# UI
# ========================
st.title("🎓 Chatbot Regulasi Akademik")

query = st.text_input("💬 Tanyakan sesuatu tentang regulasi kampus:")

if st.button("Kirim") and query:

    # ========================
    # DETECT LANGUAGE (FIX)
    # ========================
    try:
        lang = detect(query)
    except:
        lang = "id"

    # fallback buat teks pendek Indo
    if len(query) < 15:
        lang = "id"

    # ========================
    # EMBEDDING
    # ========================
    query_embedding = model.encode(query, normalize_embeddings=True).tolist()

    # ========================
    # SEARCH
    # ========================
    response = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "match_count": 3
        }
    ).execute()

    contexts = []
    if response.data:
        contexts = [doc["content"] for doc in response.data]

    context_text = "\n".join(contexts)

    # ========================
    # PROMPT
    # ========================
    prompt = f"""
Jawablah HANYA berdasarkan konteks berikut.
Jika tidak ditemukan, katakan sesuai bahasa user:

- Indonesia: Tidak ditemukan dalam regulasi
- English: Not found in the regulations

Konteks:
{context_text if context_text else "Tidak ada konteks"}

Pertanyaan:
{query}
"""

    # ========================
    # LLM
    # ========================
    chat = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": f"""
You are a helpful AI assistant.

Rules:
- ALWAYS respond in this language: {lang}
- Match user's tone (formal/casual)
- Keep answers clear and natural
- ONLY use provided context
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    answer = chat.choices[0].message.content

    # ========================
    # OUTPUT
    # ========================
    st.subheader("🤖 Jawaban:")
    st.write(answer)

    # DEBUG
    with st.expander("🔍 Lihat sumber"):
        if contexts:
            for c in contexts:
                st.write("- ", c)
        else:
            st.write("Tidak ada sumber ditemukan")