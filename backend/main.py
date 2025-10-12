from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import emotion_face
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import time
from io import BytesIO
import asyncio
from concurrent.futures import ThreadPoolExecutor
import ssl
import logging
import httpx

# ---------------------------
# SSL workaround (Windows)
# ---------------------------
ssl._create_default_https_context = ssl._create_unverified_context

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv(dotenv_path="backend/.env")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 10))
TIMEOUT_GROQ = int(os.getenv("TIMEOUT_GROQ", 20))

# ---------------------------
# Logging setup
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

# ---------------------------
# Lazy-load clients
# ---------------------------
groq_client = None
def get_groq_client():
    global groq_client
    if not groq_client and GROQ_API_KEY:
        try:
            from groq import Groq
            groq_client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            logger.error(f"Groq init failed: {e}")
            groq_client = None
    return groq_client

try:
    import ollama
except Exception:
    ollama = None

# ---------------------------
# FastAPI setup
# ---------------------------
app = FastAPI(title="Emotion-Aware Coding Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(emotion_face.router)

@app.get("/")
def read_root():
    return {"message": "Backend active with Groq → HuggingFace → Ollama fallback"}

# ---------------------------
# Request models
# ---------------------------
class ChatRequest(BaseModel):
    message: str
    history: list = []

# ---------------------------
# Thread executor for Groq (sync API)
# ---------------------------
executor = ThreadPoolExecutor()
async def run_groq_chat(client, messages, model="llama-3.1-8b-instant", temperature=0.7):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            timeout=TIMEOUT_GROQ
        )
    )

# ---------------------------
# ASR / Voice endpoint
# ---------------------------
@app.post("/api/voice")
async def voice_endpoint(audio: UploadFile = File(...)):
    audio_content = await audio.read()

    # Try Groq
    try:
        client = get_groq_client()
        if client:
            transcription = client.audio.transcriptions.create(
                file=BytesIO(audio_content),
                model="whisper-large-v3",
            )
            return {"text": transcription.text}
    except Exception as e:
        logger.error(f"Groq ASR error: {e}")

    # Try Hugging Face
    try:
        if HUGGINGFACE_API_KEY:
            async with httpx.AsyncClient(timeout=60) as client:
                headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
                files = {"file": (audio.filename, audio_content)}
                response = await client.post(
                    "https://api-inference.huggingface.co/models/openai/whisper-large",
                    headers=headers,
                    files=files,
                )
                response.raise_for_status()
                output = response.json()
                text = output.get("text", "")
                return {"text": text}
    except Exception as e:
        logger.error(f"Hugging Face ASR error: {e}")

    if ollama:
        return {"text": "Ollama ASR not supported yet. Use Groq or Hugging Face."}

    return {"text": "All ASR providers failed. Check API keys."}

# ---------------------------
# Chat endpoint
# ---------------------------
@app.post("/api/chat")
async def chat_endpoint(data: ChatRequest):
    start = time.time()

    # Clean & trim history
    history = [{"role": m.get("role"), "content": m.get("content")} 
               for m in data.history if "role" in m and "content" in m]
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    messages = [{"role": "system", "content": "You are a helpful and empathetic coding assistant."}] + history + [{"role": "user", "content": data.message}]

    # ---------------------------
    # Try Groq
    # ---------------------------
    try:
        client = get_groq_client()
        if client:
            logger.info("Trying Groq API...")
            response = await run_groq_chat(client, messages)
            reply = response.choices[0].message.content
            logger.info(f"Groq success in {round(time.time()-start, 2)}s")
            return {"response": reply}
    except Exception as e:
        logger.error(f"Groq API Error: {e}")

    # ---------------------------
    # Try Hugging Face
    # ---------------------------
    try:
        if HUGGINGFACE_API_KEY:
            logger.info("Trying Hugging Face API...")
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
                payload = {
                    "inputs": data.message,
                    "parameters": {"max_new_tokens": 150, "temperature": 0.7},
                }
                response = await client.post(
                    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                output = response.json()
                text = output[0]["generated_text"] if isinstance(output, list) else str(output)
                logger.info(f"Hugging Face success in {round(time.time()-start, 2)}s")
                return {"response": text}
    except Exception as e:
        logger.error(f"Hugging Face API Error: {e}")

    # ---------------------------
    # Try Ollama
    # ---------------------------
    try:
        if ollama:
            logger.info("Trying Ollama API...")
            response = ollama.chat(
                model="llama3",
                messages=[
                    {"role": "system", "content": "You are a helpful coding assistant."},
                    {"role": "user", "content": data.message},
                ],
            )
            reply = response["message"]["content"]
            logger.info(f"Ollama success in {round(time.time()-start, 2)}s")
            return {"response": reply}
    except Exception as e:
        logger.error(f"Ollama API Error: {e}")

    logger.warning("All APIs failed after %s seconds", round(time.time()-start, 2))
    return {"response": "All API providers failed. Check API keys or internet connection."}
