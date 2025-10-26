# backend/routers/emotion_voice.py
from fastapi import APIRouter, Depends, UploadFile, File
from backend.deps import get_current_user
from backend.main import voice_endpoint # Import the ASR logic from main.py

router = APIRouter(tags=["emotion"], prefix="/api")

# The /api/voice endpoint is already defined in backend/main.py 
# to handle ASR using Groq/Hugging Face. 
# This file primarily serves to ensure the endpoint is registered 
# and accessible if the structure required it, but for simplicity, 
# we rely on the main.py definition.

# If you were to add voice *emotion* detection (not just ASR), 
# you would implement the logic here using libraries like speechbrain.
# For now, the endpoint in main.py handles ASR. 

# We will define a simple endpoint here that calls the main.py function 
# to keep the router file structure complete, although main.py directly 
# handles the route.

@router.post("/emotion/voice")
async def voice_emotion_endpoint(
    audio: UploadFile = File(...),
    current_user: Any = Depends(get_current_user)
):
    """
    Handles the voice message upload. Transcribes audio via main.py ASR endpoint.
    NOTE: The ASR logic is in main.py's @app.post("/api/voice") decorator.
    This router is a placeholder if you wish to separate logic later, 
    but the direct call to /api/voice in main.py is currently used by the frontend.
    
    Since the frontend is already calling /api/voice directly, 
    we must ensure the main FastAPI app includes the correct route.
    """
    # Rerouting or calling the underlying logic is complex due to FastAPI's design.
    # The current setup in main.py is the most efficient way to handle ASR.
    
    # Let's confirm the ASR endpoint is protected and functional.
    # Since the frontend calls /api/voice, we ensure that endpoint is protected
    # by adding authentication in main.py.
    
    # This router is not strictly needed since the route is defined in main.py.
    return {"message": "Voice endpoint is defined in backend/main.py for ASR. Use that endpoint."}
