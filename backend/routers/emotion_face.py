from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import cv2
from backend.services.face_services import detect_emotions_from_array

router = APIRouter()

cap = cv2.VideoCapture(0)  # Webcam capture

def generate_frames(gamma: float = 1.2):
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        faces = detect_emotions_from_array(frame, gamma=gamma)

        for face in faces:
            x, y, w, h = face["box"]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{face['dominant_emotion']} ({face['score']})",
                        (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@router.get("/video_feed")
def video_feed(gamma: float = 1.2):
    return StreamingResponse(generate_frames(gamma=gamma),
                             media_type="multipart/x-mixed-replace; boundary=frame")
