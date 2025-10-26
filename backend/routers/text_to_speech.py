# backend/routers/text_to_speech.py
from fastapi import APIRouter, HTTPException, Response, status, Depends
from pydantic import BaseModel
import asyncio
import logging
from io import BytesIO

# Import client getter from the NEW utility file
from backend.utils.clients import get_groq_client
# Import authentication dependency (we will comment it out temporarily)
# from backend.deps import get_current_user
from typing import Any

# Import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/api", tags=["tts"])
logger = logging.getLogger("backend.tts")
# Ensure an executor is available
executor = ThreadPoolExecutor()

class TTSRequest(BaseModel):
    text: str
    model: str = "tts-1" # Default model - adjust if Groq uses different names
    voice: str = "onyx"  # Example voice - adjust based on Groq's available voices

# --- Explicit OPTIONS handler for /tts ---
@router.options("/tts")
async def options_tts():
    """Handles CORS preflight requests for the TTS endpoint."""
    logger.info("OPTIONS /api/tts handled explicitly.") # Added /api prefix for clarity
    return Response(status_code=status.HTTP_200_OK)
# --------------------------------------------

# --- TEMPORARILY REMOVED AUTH DEPENDENCY FOR DEBUGGING ---
@router.post("/tts", response_class=Response)
# async def text_to_speech(payload: TTSRequest, current_user: Any = Depends(get_current_user)):
async def text_to_speech(payload: TTSRequest): # REMOVED current_user dependency
    """
    Generates speech audio from text using Groq TTS (if available).
    Returns audio/mpeg content.
    Requires authentication (TEMPORARILY DISABLED).
    """
    # Log entry into the POST endpoint
    logger.info("POST /api/tts endpoint called.")

    client = get_groq_client()
    if not client:
        logger.warning("Groq client not available for TTS.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS service requires a configured Groq client (check API key)."
        )

    # --- Actual Groq TTS Call (using executor for sync library) ---
    def sync_tts_call():
        try:
            logger.info(f"Calling Groq TTS: model={payload.model}, voice={payload.voice}")
            response = client.audio.speech.create(
                model=payload.model,
                voice=payload.voice,
                input=payload.text,
                response_format="mp3"
            )
            audio_stream = BytesIO()
            response.stream_to_file(audio_stream) # ASSUMPTION based on OpenAI
            audio_bytes = audio_stream.getvalue()
            if not audio_bytes:
                 raise ValueError("Groq TTS returned empty audio content.")
            return audio_bytes
        except AttributeError:
             logger.error("Groq client does not have 'audio.speech.create' or expected method. Check Groq SDK.")
             raise NotImplementedError("Groq TTS method not found or misconfigured.")
        except Exception as api_err:
             logger.error(f"Groq TTS API call failed: {api_err}")
             raise api_err


    try:
        # Added logging before the call
        # logger.info(f"Generating TTS for text: '{payload.text[:30]}...' by user {current_user.id}") # Cannot log user ID temporarily
        logger.info(f"Generating TTS for text: '{payload.text[:30]}...'")
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(executor, sync_tts_call)

        logger.info("TTS generation successful.")
        return Response(content=audio_bytes, media_type="audio/mpeg")

    except NotImplementedError as nie:
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(nie))
    except Exception as e:
        logger.error(f"Error during TTS generation task: {e}")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail_message = f"Failed to generate speech: {str(e)}"
        raise HTTPException(
            status_code=status_code,
            detail=detail_message
        )

