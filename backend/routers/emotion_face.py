from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import cv2
import numpy as np
import base64
import logging
from backend.services.face_services import detect_emotions_from_array

router = APIRouter(prefix="/emotion_face", tags=["emotion_face"])
logger = logging.getLogger("backend.emotion_face")

# Global webcam variable
camera = None
latest_emotion = {"emotion": "neutral", "confidence": 0.0}


# ------------------ MODELS ------------------
class FrameData(BaseModel):
    image: str  # Base64 encoded frame


# ------------------ START DETECTION ------------------
@router.get("/start")
async def start_emotion_detection():
    """Start webcam capture."""
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            raise HTTPException(status_code=500, detail="Failed to access webcam.")
    return {"status": "started"}


# ------------------ STREAM VIDEO ------------------
def generate_stream():
    """Stream MJPEG frames with emotion overlay."""
    global camera, latest_emotion
    while True:
        if camera is None:
            break
        success, frame = camera.read()
        if not success:
            break

        # Detect emotions
        faces = detect_emotions_from_array(frame)
        if faces:
            top_face = max(faces, key=lambda f: f["score"])
            latest_emotion = {
                "emotion": top_face["dominant_emotion"],
                "confidence": top_face["score"],
            }

            # Draw bounding box and emotion text
            x, y, w, h = top_face["box"]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{latest_emotion['emotion']} ({latest_emotion['confidence']})",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

        _, jpeg = cv2.imencode(".jpg", frame)
        frame_bytes = jpeg.tobytes()

        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


@router.get("/stream")
async def stream_video():
    """Return live MJPEG stream."""
    global camera
    if camera is None:
        raise HTTPException(status_code=400, detail="Camera not started.")
    return StreamingResponse(generate_stream(), media_type="multipart/x-mixed-replace; boundary=frame")


# ------------------ FRAME EMOTION (Frontend polling) ------------------
@router.get("/frame/latest")
async def get_latest_emotion():
    """Return latest detected emotion."""
    return JSONResponse(latest_emotion)


# ------------------ STOP DETECTION ------------------
@router.get("/stop")
async def stop_emotion_detection():
    """Stop webcam and release resources."""
    global camera
    if camera and camera.isOpened():
        camera.release()
    camera = None
    return {"status": "stopped"}


# ------------------ FRAME ANALYSIS (Optional: for API POST image input) ------------------
@router.post("/frame")
async def analyze_frame(data: FrameData):
    """Analyze a single frame from frontend (base64)."""
    try:
        image_data = base64.b64decode(data.image.split(",")[-1])
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        faces = detect_emotions_from_array(frame)
        if not faces:
            return {"emotion": "neutral", "confidence": 0.0}

        top_face = max(faces, key=lambda f: f["score"])
        return {
            "emotion": top_face["dominant_emotion"],
            "confidence": top_face["score"]
        }

    except Exception as e:
        logger.error(f"Error analyzing frame: {e}")
        raise HTTPException(status_code=500, detail=f"Emotion detection failed: {e}")
