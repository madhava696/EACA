from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import cv2
from backend.services.face_services import detect_emotions_from_array
from typing import Optional

router = APIRouter()

# Initialize webcam as None. Will open only when requested.
cap: Optional[cv2.VideoCapture] = None

def generate_frames(gamma: float = 1.2, skip_frames: int = 2):
    """Yield frames from webcam with emotion detection every few frames."""
    global cap
    if not cap or not cap.isOpened():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("⚠️ Webcam not accessible")
            return

    frame_count = 0
    current_faces = []

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Run detection only every `skip_frames` frames
            if frame_count % skip_frames == 0:
                current_faces = detect_emotions_from_array(frame, gamma=gamma)
            frame_count += 1

            for face in current_faces:
                x, y, w, h = face["box"]
                emotion = face["dominant_emotion"]
                score = face["score"]

                # Draw rectangle & label
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                text = f"{emotion.upper()} ({score:.2f})"
                text_x = x + w - 10 - (len(text) * 10)
                text_y = max(y - 10, 20)
                cv2.rectangle(frame, (text_x - 5, text_y - 25),
                              (text_x + len(text) * 10, text_y + 5), (0, 255, 0), -1)
                cv2.putText(frame, text, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        stop_webcam()

def stop_webcam():
    """Stop and release the webcam."""
    global cap
    if cap and cap.isOpened():
        cap.release()
        cap = None
        print("ℹ️ Webcam stopped.")

@router.get("/video_feed")
def video_feed(gamma: float = Query(1.2), active: bool = Query(True)):
    """
    Stream webcam feed with emotion detection.
    - active=True: starts streaming
    - active=False: stops webcam
    """
    if not active:
        stop_webcam()
        return {"message": "Webcam disabled."}

    return StreamingResponse(generate_frames(gamma=gamma),
                             media_type="multipart/x-mixed-replace; boundary=frame")
