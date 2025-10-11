from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import emotion_face
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()

# API configuration
API_PROVIDER = os.getenv("API_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Conditional imports
if API_PROVIDER == "openai":
    import openai
    openai.api_key = OPENAI_API_KEY
elif API_PROVIDER == "ollama":
    import ollama

app = FastAPI(title="Emotion-Aware Coding Assistant")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(emotion_face.router)

@app.get("/")
def read_root():
    return {"message": f"Backend active using {API_PROVIDER.title()} API"}


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/api/voice")
async def voice_endpoint(audio: UploadFile = File(...)):
    # TODO: implement voice-to-text processing
    return {"text": "Voice received successfully!"}


@app.post("/api/chat")
async def chat_endpoint(data: ChatRequest):
    try:
        # --- OPENAI ---
        if API_PROVIDER == "openai":
            messages = [{"role": "system", "content": "You are a helpful and empathetic coding assistant."}]
            messages += data.history + [{"role": "user", "content": data.message}]
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )
            reply = response.choices[0].message.content
            return {"response": reply}

        # --- HUGGINGFACE ---
        elif API_PROVIDER == "huggingface":
            headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
            payload = {
                "inputs": data.message,
                "parameters": {"max_new_tokens": 150, "temperature": 0.7},
            }
            response = requests.post(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            output = response.json()
            # Hugging Face sometimes returns list or dict
            text = output[0]["generated_text"] if isinstance(output, list) else str(output)
            return {"response": text}

        # --- OLLAMA ---
        elif API_PROVIDER == "ollama":
            response = ollama.chat(
                model="llama3",
                messages=[
                    {"role": "system", "content": "You are a helpful coding assistant."},
                    {"role": "user", "content": data.message},
                ],
            )
            reply = response["message"]["content"]
            return {"response": reply}

        else:
            return {"response": "Invalid API_PROVIDER setting."}

    except Exception as e:
        return {"response": f"{API_PROVIDER.title()} Error: {str(e)}"}
