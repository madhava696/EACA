# backend/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/.env") # Load .env early
import os
import time
from io import BytesIO
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import ssl
import logging
import httpx
import json
from typing import Optional, List, Any


# --- Import Core Backend Components ---
# Import all necessary routers
from backend.routers import emotion_face, auth, profile, text_to_speech, emotion_text, chat
from backend.utils.database import Base, engine
from backend.deps import get_current_user
from backend.utils.clients import get_groq_client


# ---------------------------
# SSL workaround, Env Vars, Logging, Clients, Lifespan, Executor, FastAPI setup
# ---------------------------
ssl._create_default_https_context = ssl._create_unverified_context

# Initialize FastAPI app
app = FastAPI(title="Emotion-Aware Coding Assistant", lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY"); OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 10)); TIMEOUT_GROQ = int(os.getenv("TIMEOUT_GROQ", 20))
logging.basicConfig(level=logging.INFO); logger = logging.getLogger("backend")
try: import ollama
except Exception: ollama = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application Startup: Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Application Startup: Tables created successfully.")
    get_groq_client() # Initialize client on startup
    yield
    print("Application Shutdown: Goodbye!")
executor = ThreadPoolExecutor()
app = FastAPI(title="Emotion-Aware Coding Assistant", lifespan=lifespan)
origins = [ # Define allowed origins
    "http://localhost", "http://localhost:3000", "http://localhost:5173", "http://127.0.0.1",
    "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000",
    "https://*.lovable.app", "https://lovable.app", "http://localhost:8080",
        "http://127.0.0.1:8080", # Added lovable origins
]

# --- Custom Middleware to Handle OPTIONS (Keep this active) ---
@app.middleware("http")
async def intercept_options_requests(request: Request, call_next):
    if request.method == "OPTIONS":
        logger.info(f"Intercepted OPTIONS for {request.url.path}, returning 200 OK via middleware.")
        headers = {
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": request.headers.get("Access-Control-Request-Headers", "*"),
            "Access-Control-Allow-Credentials": "true", "Access-Control-Max-Age": "86400",
        }
        return PlainTextResponse("OK", status_code=status.HTTP_200_OK, headers=headers)
    response = await call_next(request); return response

# --- Standard CORS Middleware (Keep this active) ---
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"], # Allow all for simplicity after OPTIONS handled
)

# --- Include Routers ---
# Include routers WITHOUT adding an extra prefix here.
logger.info("Including routers...")
app.include_router(auth.router)           # Defines /auth/... internally
app.include_router(chat.router)           # Defines /api/chat... internally
app.include_router(emotion_face.router)   # Defines /api/... internally (e.g., /api/video_feed)
app.include_router(profile.router)        # Defines /api/... internally (e.g., /api/me)
app.include_router(emotion_text.router)   # Defines /api/... internally
app.include_router(text_to_speech.router) # Defines /api/... internally
logger.info("Routers included.")

@app.get("/")
def read_root(): return {"message": "EACA Backend Running."}

# --- Request Models ---
class ChatRequest(BaseModel):
    message: str
    emotion: Optional[str] = None
    history: List[Any] = []
    stream: bool | None = False

# --- Helper Functions ---
def get_emotion_aware_system_prompt(emotion: str) -> str:
    """ Returns different system prompts based on detected emotion """
    emotion = (emotion or "neutral").lower()
    # Add detailed prompt logic back here based on emotion...
    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion: return """You are an empathetic and patient coding assistant..."""
    elif "angry" in emotion or "disgusted" in emotion: return """You are a patient and professional coding assistant..."""
    elif "sad" in emotion: return """You are a compassionate coding assistant..."""
    elif "happy" in emotion or "surprised" in emotion: return """You are an enthusiastic and engaging coding assistant..."""
    elif "confused" in emotion: return """You are a clear and patient coding assistant..."""
    else: return """You are a highly capable, focused, and helpful coding assistant..."""

def enhance_response_with_emotion(response: str, emotion: str) -> str:
    """ Adds emotion-aware Markdown elements to the AI response """
    emotion = (emotion or "neutral").lower()
    # Add detailed enhancement logic back here based on emotion...
    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion: response += "\n\n💡 **Tip**: Don't let anxiety take over..."
    elif "sad" in emotion: response += "\n\n💫 **Keep Going**: Small wins add up..."
    elif "confused" in emotion: response += "\n\n🤔 **Need Clarity?**: Just ask me to re-explain..."
    elif "happy" in emotion: response += " 🎉"
    return response

async def generate_groq_stream(client, messages, emotion: str):
    """ Generate streaming response from Groq """
    def sync_groq_call(): # Inner function for executor
        return client.chat.completions.create(
            model="llama-3.1-8b-instant", messages=messages, temperature=0.7,
            stream=True, timeout=TIMEOUT_GROQ
        )
    try: # Full streaming logic with enhancement
        stream = await asyncio.get_event_loop().run_in_executor(executor, sync_groq_call)
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
        enhanced_response = enhance_response_with_emotion(full_response, emotion)
        final_chunk_content = enhanced_response[len(full_response):]
        if final_chunk_content: yield f"data: {json.dumps({'content': final_chunk_content, 'done': False})}\n\n"
        yield f"data: {json.dumps({'content': '', 'done': True, 'provider': 'groq', 'emotion_used': emotion})}\n\n"
    except Exception as e: # Error handling
        error_msg = f"Error in Groq stream: {str(e)}"; logger.error(error_msg)
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"

async def generate_fallback_stream(message: str, emotion: str):
    """ Generate streaming fallback response """
    emotion = (emotion or "neutral").lower()
    responses = []; provider = "fallback-neutral"
    # Add detailed fallback responses back here based on emotion...
    if "stressed" in emotion: responses = ["Take a deep breath..."]; provider="fallback-stressed"
    elif "happy" in emotion: responses = ["Great energy!"]; provider="fallback-happy"
    elif "confused" in emotion: responses = ["Let's break it down..."]; provider="fallback-confused"
    elif "sad" in emotion: responses = ["It's okay, keep going..."]; provider="fallback-sad"
    elif "angry" in emotion: responses = ["Frustrating! Let's solve it."]; provider="fallback-angry"
    else: responses = ["Thanks! How can I help?"]

    for part in responses: # Stream parts
        yield f"data: {json.dumps({'content': part, 'done': False})}\n\n"; await asyncio.sleep(0.05)
    yield f"data: {json.dumps({'content': '', 'done': True, 'provider': provider, 'emotion_used': emotion})}\n\n"

# --- Voice Endpoint (Corrected indentation in previous step, keep as is) ---
@app.options("/api/voice")
async def options_voice():
    # --- Corrected Function Body ---
    logger.info("OPTIONS /api/voice handled explicitly.")
    return Response(status_code=status.HTTP_200_OK)
    # --- End Correction ---

@app.post("/api/voice")
# async def voice_endpoint(audio: UploadFile = File(...), current_user: Any = Depends(get_current_user)): # Re-enable auth later
async def voice_endpoint(audio: UploadFile = File(...)): # Keep auth disabled for debug
    logger.info("POST /api/voice called (auth temporarily disabled).")
    audio_content = await audio.read()
    try: # Try Groq ASR
        client = get_groq_client()
        if client:
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(executor, lambda: client.audio.transcriptions.create(file=BytesIO(audio_content), model="whisper-large-v3"))
            return {"text": transcription.text, "provider": "groq"}
    except Exception as e:
        logger.error(f"Groq ASR error: {e}")
    try: # Try Hugging Face ASR
        if HUGGINGFACE_API_KEY:
            async with httpx.AsyncClient(timeout=60) as client:
                headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
                files = {"file": (audio.filename, audio_content)}
                response = await client.post("https://api-inference.huggingface.co/models/openai/whisper-large", headers=headers, files=files)
                response.raise_for_status()
                output = response.json()
                text = output.get("text", "")
                return {"text": text, "provider": "huggingface"}
    except Exception as e:
        logger.error(f"Hugging Face ASR error: {e}")
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="All ASR providers failed.")


# --- Chat Endpoints (Now handled by chat.router included above) ---
# Ensure these are commented out or removed if chat.router is included
# @app.options("/api/chat")
# async def options_chat(): ...
# @app.post("/api/chat")
# async def chat_endpoint(data: ChatRequest): ...

# @app.options("/api/chat/stream")
# async def options_chat_stream(): ...
# @app.post("/api/chat/stream")
# async def chat_stream_endpoint(data: ChatRequest): ...

