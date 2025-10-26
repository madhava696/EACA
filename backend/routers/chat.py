# backend/routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.deps import get_current_user
from typing import Optional, List, Any
from fastapi.responses import StreamingResponse
import asyncio

# --- Pydantic Schemas ---

class ChatIn(BaseModel):
    message: str
    emotion: Optional[str] = "neutral"
    history: Optional[List[Any]] = []
    stream: Optional[bool] = False

# Note: Using dict for non-streaming response body to allow dynamic content
# which is common in FastAPI responses, rather than a strict BaseModel.

# --- Core Logic / Mock LLM Generation ---

def _get_emotion_aware_reply(emotion: str, msg: str, history: List[Any]) -> str:
    """
    Generates a mock emotion-aware reply based on the detected emotion.
    In a real application, this logic would route to a powerful LLM.
    """
    emotion = emotion.lower()
    
    # 1. Handle Core Emotions and States
    if "stressed" in emotion or "anxious" in emotion:
        reply = "I sense some stress — let's take this step-by-step and simplify the problem. Remember to breathe, and tell me what the biggest roadblock is."
    elif "happy" in emotion or "joy" in emotion:
        reply = "That's fantastic energy! Let's leverage this momentum. What's the next big feature you're tackling?"
    elif "confused" in emotion:
        reply = "No worries, confusion happens! Let's zero in on the exact line or concept that's holding you up. Where did you get stuck?"
    elif "sad" in emotion:
        reply = "It sounds like you're feeling down. Take a quick break or try working on something simple to build confidence."
    elif "angry" in emotion:
        reply = "Frustration is normal when debugging! Before you break something, let's isolate the root cause. Which file are you looking at right now?"
    elif "fearful" in emotion:
        reply = "Don't be afraid to make a mistake! The best coders experiment constantly. What is the smallest, safest step we can take to test your theory?"
    elif "surprised" in emotion:
        reply = "That was unexpected! Was that a good surprise (Aha!) or a bad surprise (Uh Oh!)? Tell me what happened so we can document it."
    elif "disgusted" in emotion or "contempt" in emotion:
        reply = "Ugh, bad code smells happen. Let's clean this up together. Which block of code needs refactoring the most right now?"
    else: # Catches 'neutral' and any unhandled variants
        reply = "Thanks for the input. I'm focused and ready to assist with your query."

    # 2. Add Contextual Hint (Optional Mock LLM Feature)
    # This block keeps your original secondary logic, slightly cleaned up.
    last_bot = next((h for h in reversed(history) if h.get("role") == "bot"), None)
    if last_bot and "error" in last_bot.get("content", "").lower() and "error" not in msg.lower():
        reply += " Also, remember to check your full error logs and the exact stack trace—that usually saves time."

    # --- TODO: Integrate Real LLM Here ---
    # When nlp_services.py is ready, integrate it here to generate a meaningful reply based on msg
    # e.g.:
    # llm_reply = await call_llm(msg, emotion, history)
    # reply = reply + "\n\n" + llm_reply
    # ------------------------------------

    return reply


async def _stream_reply_generator(reply: str, delay: float = 0.05):
    """
    Generates a stream chunk-by-chunk for the frontend.
    """
    
    # Simple word-based streaming mock
    for token in reply.split():
        # In a real LLM, this would be an API stream chunk.
        # For simplicity and debugging, we just yield the text.
        yield token + " "
        await asyncio.sleep(delay)
    
    # Ensure a clean end-of-stream signal if needed by the frontend parser
    # For text/plain, just an empty yield is often enough, but a final newline is safe.
    yield "\n"


router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat")
async def chat(payload: ChatIn, user = Depends(get_current_user)):
    """
    Handles chat requests, providing an emotion-aware reply.
    """
    
    emotion = (payload.emotion or "neutral").lower()
    msg = payload.message or ""

    # Prepare user message and history for processing
    history = list(payload.history or [])
    history.append({"role": "user", "content": msg})

    # Get the mock reply
    reply = _get_emotion_aware_reply(emotion, msg, history)
    
    # Add the bot's reply to the history copy
    history.append({"role": "bot", "content": reply})

    if payload.stream:
        # For streaming, we return the text stream
        return StreamingResponse(
            _stream_reply_generator(reply), 
            media_type="text/plain"
        )

    # For non-streaming (API consumers), return JSON
    return {
        "reply": reply,
        "emotion_used": emotion,
        "history": history
    }