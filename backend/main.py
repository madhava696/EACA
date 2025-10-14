from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.routers import emotion_face, auth, profile
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
import json

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
    allow_origins=["http://localhost:8080", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (EXCLUDE chat.router since we have enhanced version in main.py)
app.include_router(auth.router)
app.include_router(emotion_face.router)
app.include_router(profile.router)

@app.get("/")
def read_root():
    return {"message": "Emotion-Aware Coding Assistant Backend"}

# ---------------------------
# Request models
# ---------------------------
class ChatRequest(BaseModel):
    message: str
    emotion: str = "neutral"
    history: list = []
    stream: bool = False  # ✅ ADDED streaming option

# ---------------------------
# Emotion-aware system prompts
# ---------------------------
def get_emotion_aware_system_prompt(emotion: str) -> str:
    """
    Returns different system prompts based on detected emotion
    """
    emotion = (emotion or "neutral").lower()
    
    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        return """You are an empathetic coding assistant. The user appears stressed or anxious. 
        - Use a calm, reassuring tone
        - Break down complex problems into simple steps
        - Offer encouragement and remind them it's okay to take breaks
        - Focus on one thing at a time
        - Provide clear, step-by-step guidance"""
    
    elif "angry" in emotion or "disgusted" in emotion:
        return """You are a patient coding assistant. The user appears frustrated.
        - Stay calm and professional
        - Acknowledge their frustration without mirroring it
        - Offer practical solutions
        - Keep responses concise and solution-focused
        - Avoid technical jargon"""
    
    elif "sad" in emotion:
        return """You are a compassionate coding assistant. The user appears sad.
        - Use a gentle, supportive tone
        - Offer encouragement and positive reinforcement
        - Celebrate small wins and progress
        - Be patient and understanding
        - Remind them that learning takes time"""
    
    elif "happy" in emotion or "surprised" in emotion:
        return """You are an enthusiastic coding assistant. The user appears happy or excited.
        - Match their positive energy
        - Use encouraging and upbeat language
        - Celebrate their progress and curiosity
        - Build on their excitement with engaging content
        - Suggest fun or creative coding projects"""
    
    elif "confused" in emotion:
        return """You are a clear and patient coding assistant. The user appears confused.
        - Explain concepts in simple terms
        - Use analogies and examples
        - Break down complex topics step by step
        - Ask clarifying questions if needed
        - Provide multiple explanations if something isn't clear"""
    
    else:  # neutral or default
        return """You are a helpful and empathetic coding assistant.
        - Provide clear, accurate coding help
        - Explain concepts thoroughly
        - Offer practical examples
        - Be supportive and encouraging
        - Adapt to the user's needs"""

# ---------------------------
# Emotion-aware response enhancement
# ---------------------------
def enhance_response_with_emotion(response: str, emotion: str) -> str:
    """
    Adds emotion-aware elements to the AI response
    """
    emotion = (emotion or "neutral").lower()
    
    if "stressed" in emotion or "anxious" in emotion:
        if "error" in response.lower() or "bug" in response.lower():
            response += "\n\n💡 **Remember**: Even experienced developers encounter errors. Take a deep breath and tackle this one step at a time."
        else:
            response += "\n\n🌟 You're doing great! Let me know if you need me to break any of this down further."
    
    elif "sad" in emotion:
        response += "\n\n💫 I know coding can be challenging sometimes, but you're making progress! Every developer goes through this."
    
    elif "confused" in emotion:
        response += "\n\n🤔 If any part of this doesn't make sense, just ask me to explain it differently!"
    
    elif "happy" in emotion:
        if "!" in response or "great" in response.lower():
            response += " 🎉"
        else:
            response += " 😊"
    
    return response

# ---------------------------
# Thread executor for Groq (sync API)
# ---------------------------
executor = ThreadPoolExecutor()

# ---------------------------
# Streaming generators
# ---------------------------
async def generate_groq_stream(client, messages, emotion: str):
    """Generate streaming response from Groq"""
    try:
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            stream=True,
            timeout=TIMEOUT_GROQ
        )
        
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                
                # Send each chunk as SSE
                yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
        
        # Enhance the final response with emotion
        enhanced_response = enhance_response_with_emotion(full_response, emotion)
        
        # Send final enhanced response
        yield f"data: {json.dumps({'content': enhanced_response, 'done': True, 'provider': 'groq', 'emotion_used': emotion})}\n\n"
        
    except Exception as e:
        error_msg = f"Error in Groq stream: {str(e)}"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"

async def generate_fallback_stream(message: str, emotion: str):
    """Generate streaming fallback response"""
    emotion = (emotion or "neutral").lower()
    
    if "stressed" in emotion or "anxious" in emotion:
        responses = [
            "I sense some stress in your tone... ",
            "Let's take this step-by-step and simplify the problem. ",
            "What specific part are you working on right now?",
            "\n\n💡 Remember: Even experienced developers encounter challenges."
        ]
    elif "happy" in emotion:
        responses = [
            "Great! I love that positive energy! ",
            "Tell me what you want to build next — ",
            "let's channel that excitement into something amazing! 🎉"
        ]
    elif "confused" in emotion:
        responses = [
            "No worries — confusion is just the first step toward understanding. ",
            "Let's break it down together. ",
            "Where did you get stuck? 🤔"
        ]
    elif "sad" in emotion:
        responses = [
            "I notice you might be feeling down. ",
            "Remember that every developer faces challenges. ",
            "Let's work through this together — ",
            "what's troubling you? 💫"
        ]
    elif "angry" in emotion:
        responses = [
            "I understand this might be frustrating. ",
            "Let's approach this calmly. ",
            "What specific issue is causing the most trouble?"
        ]
    else:
        responses = [
            "Thanks for reaching out! ",
            "I'm here to help with your coding questions. ",
            "What would you like to work on today? 😊"
        ]
    
    # Stream each part with delays to simulate typing
    full_response = ""
    for part in responses:
        full_response += part
        yield f"data: {json.dumps({'content': part, 'done': False})}\n\n"
        await asyncio.sleep(0.1)  # Small delay for natural typing effect
    
    yield f"data: {json.dumps({'content': '', 'done': True, 'provider': 'fallback', 'emotion_used': emotion})}\n\n"

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
# Enhanced Emotion-Aware Chat endpoint (Non-streaming)
# ---------------------------
@app.post("/api/chat")
async def chat_endpoint(data: ChatRequest):
    # If streaming is requested, use the streaming endpoint
    if data.stream:
        return await chat_stream_endpoint(data)
    
    start = time.time()

    # Clean & trim history
    history = [{"role": m.get("role"), "content": m.get("content")} 
               for m in data.history if "role" in m and "content" in m]
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    
    # ✅ Get emotion-aware system prompt
    system_prompt = get_emotion_aware_system_prompt(data.emotion)
    
    messages = [
        {"role": "system", "content": system_prompt}
    ] + history + [
        {"role": "user", "content": data.message}
    ]

    # ---------------------------
    # Try Groq (with emotion context)
    # ---------------------------
    try:
        client = get_groq_client()
        if client:
            logger.info("Trying Groq API with emotion: %s", data.emotion)
            
            # Use thread pool for sync Groq API
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
            
            # ✅ Enhance response based on emotion
            enhanced_reply = enhance_response_with_emotion(reply, data.emotion)
            
            logger.info(f"Groq success in {round(time.time()-start, 2)}s")
            return {
                "reply": enhanced_reply, 
                "emotion_used": data.emotion,
                "provider": "groq"
            }
    except Exception as e:
        logger.error(f"Groq API Error: {e}")

    # ---------------------------
    # Fallback: Simple emotion-aware responses
    # ---------------------------
    logger.info("Using fallback emotion-aware responses")
    emotion = (data.emotion or "neutral").lower()
    msg = data.message
    
    if "stressed" in emotion or "anxious" in emotion:
        reply = "I sense some stress in your tone — let's take this step-by-step and simplify the problem. What specific part are you working on right now?"
    elif "happy" in emotion:
        reply = "Great! I love that positive energy. Tell me what you want to build next — let's channel that excitement into something amazing!"
    elif "confused" in emotion:
        reply = "No worries — confusion is just the first step toward understanding. Let's break it down together. Where did you get stuck?"
    elif "sad" in emotion:
        reply = "I notice you might be feeling down. Remember that every developer faces challenges. Let's work through this together — what's troubling you?"
    elif "angry" in emotion:
        reply = "I understand this might be frustrating. Let's approach this calmly. What specific issue is causing the most trouble?"
    else:
        reply = "Thanks for reaching out! I'm here to help with your coding questions. What would you like to work on today?"

    logger.info(f"Fallback success in {round(time.time()-start, 2)}s")
    return {
        "reply": reply,
        "emotion_used": data.emotion,
        "provider": "fallback"
    }

# ---------------------------
# NEW: Streaming Chat Endpoint
# ---------------------------
@app.post("/api/chat/stream")
async def chat_stream_endpoint(data: ChatRequest):
    """Streaming endpoint for real-time chat responses"""
    
    # Clean & trim history
    history = [{"role": m.get("role"), "content": m.get("content")} 
               for m in data.history if "role" in m and "content" in m]
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    
    # Get emotion-aware system prompt
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
            logger.error(f"Groq streaming error: {e}")
        
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
        }
    )