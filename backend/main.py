
from fastapi import FastAPI
from backend.routers import emotion_face  # Absolute import works now

app = FastAPI(title="Emotion-Aware Coding Assistant")

# Include router
app.include_router(emotion_face.router)
