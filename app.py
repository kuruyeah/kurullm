import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformergit 
from langdetect import detect, DetectorFactory
import os
from dotenv import load_dotenv

# biar hasil langdetect stabil
DetectorFactory.seed = 0



# ========================
# CONFIG (lebih aman pakai st.secrets nanti)
# ========================

load_dotenv()
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
    # DETEKSI BAHASA
    # ========================
    try:
        lang = detect(query)
    except:
        lang = "id"  # fallback

    # ========================
    # EMBEDDING
    # ========================
    query_embedding = model.encode(query, normalize_embeddings=True).tolist()

    # ========================
    # SEARCH (RAG)
    # ========================
    response = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "match_count": 3
        }
    ).execute()

    contexts = [doc["content"] for doc in response.data]
    context_text = "\n".join(contexts)

    # ========================
    # PROMPT
    # ========================
    prompt = f"""
Jawablah HANYA berdasarkan konteks berikut.
Jika tidak ditemukan, katakan "Tidak ditemukan dalam regulasi".

Konteks:
{context_text}

Pertanyaan:
{query}
"""

    # ========================
    # LLM
    # ========================
    chat = client.chat.completions.create(
        model="openai/gpt-oss-120b",  # model Groq yang valid
        messages=[
            {
                "role": "system",
                "content": f"""
You are a helpful AI assistant.

Respond in this language: {lang}

Rules:
- Match user's tone (formal/casual)
- Keep answers clear and relevant
- Only answer based on provided context
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    answer = chat.choices[0].message.content

    # ========================
    # OUTPUT
    # ========================
    st.subheader("🤖 Jawaban:")
    st.write(answer)

    # DEBUG
    with st.expander("🔍 Lihat sumber"):
        for c in contexts:
            st.write("- ", c)