from fastapi import FastAPI
from backend.routers import emotion_face

app = FastAPI(title="Emotion-Aware Coding Assistant")

# Include the emotion_face router
app.include_router(emotion_face.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Emotion-Aware Coding Assistant"}
