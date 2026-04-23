import os
from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

# ambil dari environment variable
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class Req(BaseModel):
    message: str

@app.post("/chat")
def chat(req: Req):
    user_input = req.message

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input}
        ]
    )

    reply = response.choices[0].message.content

    return {"reply": reply}