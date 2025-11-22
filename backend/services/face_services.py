# backend/services/face_services.py
import logging
import cv2
import numpy as np
from typing import Any, List, Dict
from collections import deque
import os

logging.getLogger("moviepy").setLevel(logging.ERROR)

# Paths to cascades (assumes OpenCV/ folder at repo root)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FACE_CASCADE_PATH = os.path.join(BASE_DIR, 'OpenCV', 'haarcascade_frontalface_default.xml')
EYE_CASCADE_PATH = os.path.join(BASE_DIR, 'OpenCV', 'haarcascade_eye.xml')

if not os.path.exists(FACE_CASCADE_PATH) or not os.path.exists(EYE_CASCADE_PATH):
    raise FileNotFoundError(f"Missing Haar cascades. Expected at:\n{FACE_CASCADE_PATH}\n{EYE_CASCADE_PATH}")

face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)

FRAME_WIDTH = 320
FRAME_HEIGHT = 240

# Maintain short-term emotion smoothing
emotion_buffer = deque(maxlen=5)

def enhance_image(frame: np.ndarray[Any, Any], gamma: float = 1.2) -> np.ndarray[Any, Any]:
    """Enhance brightness and contrast for better detection."""
    if frame is None or frame.size == 0:
        return frame

    if len(frame.shape) == 2 or frame.shape[2] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    lab = cv2.merge((l, a, b))
    frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    frame = cv2.bilateralFilter(frame, d=5, sigmaColor=75, sigmaSpace=75)

    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
                      for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(frame, table)


def detect_emotions_from_array(
    frame: np.ndarray[Any, Any],
    gamma: float = 1.2,
    skip_frames: int = 2
) -> List[Dict[str, Any]]:
    """
    Lightweight heuristic emotion detection using Haar cascades:
    - detects faces and eyes
    - heuristics: eyes present -> neutral/alert; no eyes/closed -> tired; large mouth opening could map to surprised (optional)
    """
    if frame is None or frame.size == 0:
        return []

    # Resize and convert
    small = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    if small.dtype != np.uint8:
        small = (small * 255).astype(np.uint8) if small.max() <= 1.0 else small.astype(np.uint8)

    enhanced = enhance_image(small, gamma=gamma)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)

    faces_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5, minSize=(40, 40))

    faces = []
    detected_emotions_this_frame = []

    for (x, y, w, h) in faces_rects:
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = enhanced[y:y+h, x:x+w]

        # detect eyes inside face roi
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(8,8))
        eyes_count = len(eyes)

        # Basic mouth openness heuristic (optional): use simple contour area on lower half
        mouth_score = 0.0
        try:
            lower_half = roi_gray[int(h*0.5):h, :]
            _, thresh = cv2.threshold(lower_half, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                max_area = max((cv2.contourArea(c) for c in contours), default=0)
                mouth_score = float(max_area) / (w * h + 1e-6)
        except Exception:
            mouth_score = 0.0

        # Heuristic to map to emotion
        if eyes_count == 0:
            dominant = "tired_or_eyes_closed"
            score = 0.6
        else:
            # if mouth large -> surprised
            if mouth_score > 0.03:
                dominant = "surprised"
                score = min(0.9, 0.5 + mouth_score)
            else:
                dominant = "neutral"
                score = 0.7 if eyes_count >= 2 else 0.6

        # scale bbox back to original frame size
        orig_w = frame.shape[1]
        orig_h = frame.shape[0]
        sx = int(x * orig_w / FRAME_WIDTH)
        sy = int(y * orig_h / FRAME_HEIGHT)
        sw = int(w * orig_w / FRAME_WIDTH)
        sh = int(h * orig_h / FRAME_HEIGHT)

        detected_emotions_this_frame.append(dominant)
        faces.append({
            "box": (sx, sy, sw, sh),
            "dominant_emotion": dominant,
            "score": round(float(score), 2),
            "eyes_detected": int(eyes_count),
            "mouth_score": round(float(mouth_score), 4)
        })

    # smoothing
    if detected_emotions_this_frame:
        primary = faces[0]["dominant_emotion"] if faces else "neutral"
        emotion_buffer.append(primary)
        if len(emotion_buffer) >= 3:
            try:
                most_common = max(set(emotion_buffer), key=list(emotion_buffer).count)
                for face in faces:
                    face["dominant_emotion"] = most_common
            except Exception:
                pass

    return faces


def detect_emotions_from_bytes(frame_bytes: bytes, gamma: float = 1.2, skip_frames: int = 2) -> List[Dict[str, Any]]:
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return detect_emotions_from_array(frame, gamma=gamma, skip_frames=skip_frames)
