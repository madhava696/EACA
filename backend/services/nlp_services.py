# backend/services/nlp_services.py
import logging
from typing import Dict
import os
from dotenv import load_dotenv

# Note: Since the backend main.py runs sync Groq and async Hugging Face (via httpx),
# we will use the async httpx client directly in the router for simplicity, 
# and keep this service file for local/direct model loading if needed in the future.
# However, to meet your goal of using HF API, the core logic will be implemented 
# in the router, which is better practice for managing async API calls.

logger = logging.getLogger("nlp_services")

# Mapping model output to simplified core emotion categories
EMOTION_MAPPING = {
    "joy": "happy",
    "love": "happy",
    "excitement": "happy",
    "optimism": "happy",
    "sadness": "sad",
    "grief": "sad",
    "anger": "angry",
    "frustration": "angry",
    "fear": "fearful",
    "anxiety": "fearful",
    "surprise": "surprised",
    "disgust": "disgusted",
    "shame": "sad",
    "neutral": "neutral"
}

def map_emotion(raw_emotion: str) -> str:
    """Maps detailed model emotions to a simplified set of core emotions."""
    return EMOTION_MAPPING.get(raw_emotion.lower(), "neutral")

# The heavy lifting (API calling) is placed in the router (emotion_text.py)
# to handle the asynchronous nature of external API calls within FastAPI.
