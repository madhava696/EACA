# backend/routers/text_to_speech.py
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.services.text_to_speech_services import generate_tts_audio
from backend.deps import get_current_user
from backend.main import get_groq_client # Import the client getter

router = APIRouter(tags=["tts"], prefix="/api")
logger = logging.getLogger("tts_router")

class TTSServiceRequest(BaseModel):
    text: str
    
@router.post("/tts")
async def text_to_speech_endpoint(
    payload: TTSServiceRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Generates speech audio (MP3 stream) from text input.
    """
    if not payload.text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text input is required.")

    groq_client = get_groq_client()
    
    audio_stream = await generate_tts_audio(payload.text, groq_client)
    
    # Return the audio stream as an MP3 file
    return StreamingResponse(audio_stream, media_type="audio/mp3")
