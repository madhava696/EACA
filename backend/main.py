# backend/main.py
# --- (Imports and other setup remain the same) ---
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from backend.routers import emotion_face, auth, profile
from backend.utils.database import Base, engine
from backend.deps import get_current_user

# --- (SSL workaround, Env Vars, Logging, Lazy Clients, Lifespan remain the same) ---
ssl._create_default_https_context = ssl._create_unverified_context
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 10))
TIMEOUT_GROQ = int(os.getenv("TIMEOUT_GROQ", 20))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")
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
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application Startup: Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Application Startup: Tables created successfully.")
    yield
    print("Application Shutdown: Goodbye!")
executor = ThreadPoolExecutor()


# ---------------------------
# FastAPI setup
# ---------------------------
app = FastAPI(
    title="Emotion-Aware Coding Assistant",
    lifespan=lifespan
)

# --- CORS Configuration with Explicit Methods ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    # ✅ Explicitly list common methods including OPTIONS
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# --- (Include Routers and Root Endpoint remain the same) ---
app.include_router(auth.router)
app.include_router(emotion_face.router)
app.include_router(profile.router)
@app.get("/")
def read_root():
    return {"message": "Emotion-Aware Coding Assistant Backend is running."}

# --- (Request Models, Emotion Prompts/Enhancement, Streaming Generators remain the same) ---
class ChatRequest(BaseModel):
    message: str
    emotion: str = "neutral"
    history: List[Any] = []
    stream: bool = False
def get_emotion_aware_system_prompt(emotion: str) -> str:
    # ... (Keep existing implementation) ...
    emotion = (emotion or "neutral").lower()

    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        return """You are an empathetic and patient coding assistant. The user appears stressed or anxious.
        - Use a calm, reassuring tone and short, clear sentences.
        - Break down the problem into the absolutely smallest, manageable steps.
        - Offer specific encouragement, focusing only on the current task."""

    elif "angry" in emotion or "disgusted" in emotion:
        return """You are a patient and professional coding assistant. The user appears highly frustrated.
        - Respond calmly and focus only on practical, technical solutions.
        - Acknowledge the frustration professionally ("I see this is frustrating") but do not dwell on it.
        - Provide concise, solution-focused steps to debug the current issue."""

    elif "sad" in emotion:
        return """You are a compassionate coding assistant. The user appears sad or discouraged.
        - Use a gentle, supportive tone and validate their feelings.
        - Offer encouraging reinforcement, reminding them of progress made.
        - Suggest a simple, quick win task before tackling anything large."""

    elif "happy" in emotion or "surprised" in emotion:
        return """You are an enthusiastic and engaging coding assistant. The user appears happy or excited.
        - Match their positive energy and use encouraging, upbeat language.
        - Celebrate their success and suggest ambitious next steps to build on their enthusiasm.
        - Be responsive to their excitement."""

    elif "confused" in emotion:
        return """You are a clear and patient coding assistant. The user appears confused.
        - Prioritize clear, simple explanations and define any technical jargon used.
        - Use analogies or step-by-step numbered lists for clarity.
        - Focus on verifying their foundational understanding before moving forward."""

    else:  # neutral or default
        return """You are a highly capable, focused, and helpful coding assistant.
        - Provide direct, accurate coding help and technical explanations.
        - Maintain a professional yet encouraging tone.
        - Ensure all answers are concise, clear, and relevant to the user's query."""
def enhance_response_with_emotion(response: str, emotion: str) -> str:
    # ... (Keep existing implementation) ...
    emotion = (emotion or "neutral").lower()

    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        response += "\n\n💡 **Tip**: Don't let anxiety take over. Debugging is a skill of patience. You got this!"

    elif "sad" in emotion:
        response += "\n\n💫 **Keep Going**: Small wins add up. Celebrate the next time a single line of code works!"

    elif "confused" in emotion:
        response += "\n\n🤔 **Need Clarity?**: Just ask me to re-explain the last concept using a different example."

    elif "happy" in emotion:
        response += " 🎉"

    return response
async def generate_groq_stream(client, messages, emotion: str):
    # ... (Keep existing implementation) ...
    def sync_groq_call():
        return client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            stream=True,
            timeout=TIMEOUT_GROQ
        )

    try:
        stream = await asyncio.get_event_loop().run_in_executor(
            executor,
            sync_groq_call
        )

        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content

                yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"

        enhanced_response = enhance_response_with_emotion(full_response, emotion)
        final_chunk_content = enhanced_response[len(full_response):]

        if final_chunk_content:
             yield f"data: {json.dumps({'content': final_chunk_content, 'done': False})}\n\n"

        yield f"data: {json.dumps({'content': '', 'done': True, 'provider': 'groq', 'emotion_used': emotion})}\n\n"

    except Exception as e:
        error_msg = f"Error in Groq stream: {str(e)}"
        logger.error(error_msg)
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
async def generate_fallback_stream(message: str, emotion: str):
    # ... (Keep existing implementation) ...
    emotion = (emotion or "neutral").lower()

    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        responses = [
            "I sense some stress in your tone... ",
            "Let's take this step-by-step and simplify the problem. ",
            "What specific part are you working on right now?",
            "\n\n💡 Remember: Even experienced developers encounter challenges."
        ]
        provider = "fallback-stressed"
    elif "happy" in emotion or "surprised" in emotion:
        responses = [
            "Great! I love that positive energy! ",
            "Tell me what you want to build next — ",
            "let's channel that excitement into something amazing! 🎉"
        ]
        provider = "fallback-happy"
    elif "confused" in emotion:
        responses = [
            "No worries — confusion is just the first step toward understanding. ",
            "Let's break it down together. ",
            "Where did you get stuck? 🤔"
        ]
        provider = "fallback-confused"
    elif "sad" in emotion:
        responses = [
            "I notice you might be feeling down. ",
            "Remember that every developer faces challenges. ",
            "Let's work through this together — ",
            "what's troubling you? 💫"
        ]
        provider = "fallback-sad"
    elif "angry" in emotion or "disgusted" in emotion:
        responses = [
            "I understand this might be frustrating. ",
            "Let's approach this calmly and systematically. ",
            "What specific issue is causing the most trouble?"
        ]
        provider = "fallback-angry"
    else:
        responses = [
            "Thanks for reaching out! ",
            "I'm here to help with your coding questions. ",
            "What would you like to work on today? 😊"
        ]
        provider = "fallback-neutral"

    for part in responses:
        yield f"data: {json.dumps({'content': part, 'done': False})}\n\n"
        await asyncio.sleep(0.05)

    yield f"data: {json.dumps({'content': '', 'done': True, 'provider': provider, 'emotion_used': emotion})}\n\n"

# ---------------------------
# ASR / Voice endpoint
# ---------------------------
@app.post("/api/voice")
async def voice_endpoint(audio: UploadFile = File(...), current_user: Any = Depends(get_current_user)):
    # ... (Keep existing ASR logic implementation) ...
    audio_content = await audio.read()

    # Try Groq ASR
    try:
        client = get_groq_client()
        if client:
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(
                executor,
                lambda: client.audio.transcriptions.create(
                    file=BytesIO(audio_content),
                    model="whisper-large-v3",
                )
            )
            return {"text": transcription.text, "provider": "groq"}
    except Exception as e:
        logger.error(f"Groq ASR error: {e}")

    # Try Hugging Face ASR
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
                return {"text": text, "provider": "huggingface"}
    except Exception as e:
        logger.error(f"Hugging Face ASR error: {e}")

    # Final Fallback
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="All ASR providers failed. Check API keys and ensure Groq and Hugging Face clients are initialized."
    )

# ---------------------------
# Enhanced Emotion-Aware Chat endpoint (Non-streaming)
# ---------------------------
@app.post("/api/chat")
async def chat_endpoint(data: ChatRequest, current_user: Any = Depends(get_current_user)):
    # ... (Keep existing Non-streaming logic implementation) ...
    if data.stream:
        return await chat_stream_endpoint(data, current_user)

    start = time.time()

    history = [{"role": m.get("role"), "content": m.get("content")}
               for m in data.history if "role" in m and "content" in m]
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    system_prompt = get_emotion_aware_system_prompt(data.emotion)

    messages = [
        {"role": "system", "content": system_prompt}
    ] + history + [
        {"role": "user", "content": data.message}
    ]

    # Try Groq
    try:
        client = get_groq_client()
        if client:
            logger.info("Trying Groq API with emotion: %s", data.emotion)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                executor,
                lambda: client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=0.7,
                    timeout=TIMEOUT_GROQ
                )
            )

            reply = response.choices[0].message.content
            enhanced_reply = enhance_response_with_emotion(reply, data.emotion)

            logger.info(f"Groq success in {round(time.time()-start, 2)}s")
            return {
                "reply": enhanced_reply,
                "emotion_used": data.emotion,
                "provider": "groq",
                "user_id": current_user.id # Add user ID for debug/context
            }
    except Exception as e:
        logger.error(f"Groq API Error: {e}")

    # Fallback
    logger.info("Using fallback emotion-aware responses")
    emotion = (data.emotion or "neutral").lower()

    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        reply = "I sense some stress in your tone — let's take this step-by-step and simplify the problem. What specific part are you working on right now?"
    elif "happy" in emotion or "surprised" in emotion:
        reply = "Great! I love that positive energy. Tell me what you want to build next — let's channel that excitement into something amazing!"
    elif "confused" in emotion:
        reply = "No worries — confusion is just the first step toward understanding. Let's break it down together. Where did you get stuck?"
    elif "sad" in emotion:
        reply = "I notice you might be feeling down. Remember that every developer faces challenges. Let's work through this together — what's troubling you?"
    elif "angry" in emotion or "disgusted" in emotion:
        reply = "I understand this might be frustrating. Let's approach this calmly. What specific issue is causing the most trouble?"
    else:
        reply = "Thanks for reaching out! I'm here to help with your coding questions. What would you like to work on today?"

    logger.info(f"Fallback success in {round(time.time()-start, 2)}s")
    return {
        "reply": reply,
        "emotion_used": data.emotion,
        "provider": "fallback",
        "user_id": current_user.id
    }


# ---------------------------
# Streaming Chat Endpoint (SSE)
# ---------------------------
@app.post("/api/chat/stream")
async def chat_stream_endpoint(data: ChatRequest, current_user: Any = Depends(get_current_user)):
    """Streaming endpoint for real-time chat responses"""
    # ... (Keep existing Streaming logic implementation) ...
    history = [{"role": m.get("role"), "content": m.get("content")}
               for m in data.history if "role" in m and "content" in m]
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    system_prompt = get_emotion_aware_system_prompt(data.emotion)

    messages = [
        {"role": "system", "content": system_prompt}
    ] + history + [
        {"role": "user", "content": data.message}
    ]

    async def generate():
        # Try Groq streaming first
        try:
            client = get_groq_client()
            if client:
                logger.info("Using Groq streaming with emotion: %s", data.emotion)
                async for chunk in generate_groq_stream(client, messages, data.emotion):
                    yield chunk
                return
        except Exception as e:
            logger.error(f"Groq streaming error in main generation: {e}")

        # Fallback to simulated streaming
        logger.info("Using fallback streaming with emotion: %s", data.emotion)
        async for chunk in generate_fallback_stream(data.message, data.emotion):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-User-ID": str(current_user.id) if current_user and hasattr(current_user, 'id') else 'guest'
        }
    )

