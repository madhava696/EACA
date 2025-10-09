from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import cv2
from backend.services.face_services import detect_emotions_from_array

router = APIRouter()

# Initialize webcam
cap = cv2.VideoCapture(0)

def generate_frames(gamma: float = 1.2):
    """Generate frames from webcam with detected emotions."""
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        faces = detect_emotions_from_array(frame, gamma=gamma)

        for face in faces:
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

@router.get("/video_feed")
def video_feed(gamma: float = 1.2):
    """Stream webcam feed."""
    return StreamingResponse(generate_frames(gamma=gamma),
                             media_type="multipart/x-mixed-replace; boundary=frame")
