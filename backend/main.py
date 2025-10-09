from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import emotion_face
from pydantic import BaseModel
import os
import openai

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")  # Make sure this is set

app = FastAPI(title="Emotion-Aware Coding Assistant")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emotion_face.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Emotion-Aware Coding Assistant"}


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat_endpoint(data: ChatRequest):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if available
            messages=[
                {"role": "system", "content": "You are a helpful and empathetic coding assistant."},
                {"role": "user", "content": data.message},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        reply = response.choices[0].message.content
        return {"response": reply}

    except Exception as e:
        return {"response": f"OpenAI Error: {str(e)}"}
