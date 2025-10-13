# backend/routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.deps import get_current_user
from typing import Optional

router = APIRouter(prefix="/api", tags=["chat"])

class ChatIn(BaseModel):
    message: str
    emotion: Optional[str] = "neutral"

@router.post("/chat")
async def chat(payload: ChatIn, user = Depends(get_current_user)):
    # Example emotion-aware reply logic (mock)
    emotion = (payload.emotion or "neutral").lower()
    msg = payload.message
    if "stressed" in emotion or "anxious" in emotion:
        reply = "I sense some stress — let's take this step-by-step and simplify the problem."
    elif "happy" in emotion:
        reply = "Great! I love that energy. Tell me what you want to build next."
    elif "confused" in emotion:
        reply = "No worries — let's break it down. Where did you get stuck?"
    else:
        reply = "Thanks — here's a helpful reply based on your message."
    return {"reply": reply, "emotion_used": emotion}
