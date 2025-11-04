# backend/routers/chat.py
import asyncio
import json
import logging
import time
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Any

# --- Imports ---
from backend.deps import get_current_user  # re-enable later if needed
from backend.utils.clients import get_groq_client
from backend.utils.chat_helpers import (
    get_emotion_aware_system_prompt,
    enhance_response_with_emotion,
    generate_groq_stream,
    generate_fallback_stream,
    MAX_HISTORY,
    TIMEOUT_GROQ,
    executor,
)

logger = logging.getLogger("backend.chat")

# --- Request Model ---
class ChatRequest(BaseModel):
    message: str
    emotion: str = "neutral"
    history: List[Any] = []
    stream: bool = False


# --- Router Definition ---
router = APIRouter(prefix="/api", tags=["chat"])


# --- OPTIONS handler ---
@router.options("/chat")
async def options_chat():
    logger.info("OPTIONS /api/chat handled by chat router.")
    return Response(status_code=status.HTTP_200_OK)


# --- Unified Chat Endpoint (Handles both streaming & non-streaming) ---
@router.post("/chat")
# async def chat_endpoint(data: ChatRequest, current_user: Any = Depends(get_current_user)):
async def chat_endpoint(data: ChatRequest):
    """
    Unified chat endpoint.
    - If stream=True → returns SSE stream
    - Else → returns full JSON reply
    """
    logger.info(f"POST /api/chat | Emotion: {data.emotion} | Stream: {data.stream}")

    # Prepare conversation context
    history = [
    {
        "role": "assistant" if m.get("role") == "bot" else m.get("role"),
        "content": m.get("content")
    }
    for m in data.history
    if m.get("role") and m.get("content")
][-MAX_HISTORY:]
    system_prompt = get_emotion_aware_system_prompt(data.emotion)
    messages = [{"role": "system", "content": system_prompt}] + history + [
        {"role": "user", "content": data.message}
    ]

    # ------------------------------------------------------------
    # STREAMING MODE
    # ------------------------------------------------------------
    if data.stream:
        logger.info("Streaming mode enabled for /api/chat.")
        client = get_groq_client()

        # --- Groq Streaming ---
        if client:
            try:
                async def groq_event_stream():
                    async for chunk in generate_groq_stream(client, messages, data.emotion):
                        yield chunk
                return StreamingResponse(groq_event_stream(), media_type="text/event-stream")
            except Exception as e:
                logger.error(f"Groq stream error: {e}", exc_info=True)

        # --- Fallback Streaming ---
        async def fallback_stream():
            async for chunk in generate_fallback_stream(data.message, data.emotion):
                yield chunk

        logger.info("Using fallback streaming (Groq unavailable or failed).")
        return StreamingResponse(fallback_stream(), media_type="text/event-stream")

    # ------------------------------------------------------------
    # NON-STREAMING MODE
    # ------------------------------------------------------------
    start = time.time()
    try:
        client = get_groq_client()
        if client:
            logger.info("Attempting Groq non-stream call...")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                executor,
                lambda: client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    temperature=0.7,
                    timeout=TIMEOUT_GROQ,
                ),
            )
            reply = response.choices[0].message.content
            enhanced_reply = enhance_response_with_emotion(reply, data.emotion)
            logger.info(f"Groq non-stream success in {round(time.time()-start, 2)}s")

            return {
                "reply": enhanced_reply,
                "emotion_used": data.emotion,
                "provider": "groq",
                "user_id": "temp_debug_user",
            }
        else:
            raise Exception("Groq client unavailable")

    except Exception as e:
        logger.error(f"Groq non-stream API Error: {e}", exc_info=True)

    # ------------------------------------------------------------
    # FALLBACK NON-STREAMING
    # ------------------------------------------------------------
    logger.info("Using fallback non-stream response.")
    emotion = (data.emotion or "neutral").lower()

    if "stressed" in emotion or "anxious" in emotion or "fearful" in emotion:
        reply = "I sense some stress... Let's take this step-by-step. What specific part are you working on right now? Remember to breathe!"
        provider = "fallback-stressed"
    elif "happy" in emotion or "surprised" in emotion:
        reply = "Great! I love that positive energy. Tell me what you want to build next — let's channel that excitement! 🎉"
        provider = "fallback-happy"
    elif "confused" in emotion:
        reply = "No worries... Let's break it down together. Where did you get stuck? 🤔"
        provider = "fallback-confused"
    elif "sad" in emotion:
        reply = "Feeling down? Remember every developer faces challenges. Let's work through this together. What's troubling you? 💫"
        provider = "fallback-sad"
    elif "angry" in emotion or "disgusted" in emotion:
        reply = "Frustrating! Let's approach this calmly. What specific issue is causing the most trouble?"
        provider = "fallback-angry"
    else:
        reply = "Thanks for reaching out! I'm here to help with your coding questions. What would you like to work on today? 😊"
        provider = "fallback-neutral"

    logger.info(f"Fallback non-stream success in {round(time.time()-start, 2)}s")

    return {
        "reply": reply,
        "emotion_used": data.emotion,
        "provider": provider,
        "user_id": "temp_debug_user",
    }
