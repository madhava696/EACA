# backend/routers/emotion_text.py
import os
import json
import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.services.nlp_services import map_emotion
from backend.deps import get_current_user

router = APIRouter(tags=["emotion"], prefix="/api")
logger = logging.getLogger("emotion_text_router")

# --- Environment Variables ---
# Assumes HUGGINGFACE_API_KEY is loaded in main.py's environment
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Hugging Face Model for Emotion Classification
# We use a multi-label model for better results.
HF_MODEL_URL = "https://api-inference.huggingface.co/models/dima806/sentiment_emotion_model"

class TextEmotionRequest(BaseModel):
    text: str

@router.post("/emotion/text")
async def detect_text_emotion(
    payload: TextEmotionRequest, 
    current_user: str = Depends(get_current_user)
):
    """
    Detects emotion from text using the Hugging Face Inference API.
    Requires HUGGINGFACE_API_KEY environment variable.
    """
    if not HUGGINGFACE_API_KEY:
        logger.warning("HUGGINGFACE_API_KEY is not set. Using mock emotion.")
        # Mock logic fallback (e.g., keyword match)
        text = payload.text.lower()
        if "error" in text or "bug" in text:
            return {"emotion": "angry", "raw_score": 0.8}
        if "thanks" in text or "great" in text:
            return {"emotion": "happy", "raw_score": 0.9}
        return {"emotion": "neutral", "raw_score": 0.5}

    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    
    # Payload for the Hugging Face model
    hf_payload = json.dumps({"inputs": payload.text})
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(HF_MODEL_URL, headers=headers, content=hf_payload)
            response.raise_for_status()
            
            # Expected response format: [[{'label': 'joy', 'score': 0.99}, ...]]
            results = response.json()
            
            if not results or not results[0]:
                raise ValueError("HF model returned no results.")
            
            # Find the highest scoring emotion
            top_result = max(results[0], key=lambda x: x['score'])
            
            detected_emotion = map_emotion(top_result['label'])
            
            return {
                "emotion": detected_emotion,
                "raw_emotion": top_result['label'],
                "raw_score": top_result['score'],
                "provider": "huggingface"
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HF API Error ({e.response.status_code}): {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Hugging Face API Error: {e.response.text}")
    except Exception as e:
        logger.error(f"Text Emotion Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal emotion detection error.")
