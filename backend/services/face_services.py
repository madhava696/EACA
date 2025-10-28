# backend/services/face_services.py
import logging
import cv2
import numpy as np
from typing import Any, List, Dict
from fer import FER
from collections import deque

logging.getLogger("moviepy").setLevel(logging.ERROR)

# Initialize FER with MTCNN for face detection
detector = FER(mtcnn=True)

FRAME_WIDTH = 320
FRAME_HEIGHT = 240

# Maintain short-term emotion smoothing
emotion_buffer = deque(maxlen=5)

def enhance_image(frame: np.ndarray[Any, Any], gamma: float = 1.2) -> np.ndarray[Any, Any]:
    """Enhance brightness and contrast for better emotion accuracy."""
    if frame is None or frame.size == 0:
        return frame

    if len(frame.shape) == 2 or frame.shape[2] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    # Convert to LAB color space and normalize brightness
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    lab = cv2.merge((l, a, b))
    frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Apply bilateral filter to reduce noise while preserving edges
    frame = cv2.bilateralFilter(frame, d=5, sigmaColor=75, sigmaSpace=75)

    # Apply gamma correction
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
                      for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(frame, table)


def detect_emotions_from_array(
    frame: np.ndarray[Any, Any],
    gamma: float = 1.2,
    skip_frames: int = 2
) -> List[Dict[str, Any]]:
    """Detect emotions in a frame using FER with stable output."""
    if frame is None or frame.size == 0:
        return []

    # Resize for speed
    small_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    enhanced_frame = enhance_image(small_frame, gamma=gamma)

    try:
        detections = detector.detect_emotions(enhanced_frame)
    except Exception as e:
        print(f"[FER Error] {e}")
        return []

    faces = []
    for d in detections or []:
        x, y, w, h = d["box"]
        emotions = d.get("emotions", {})
        if not emotions:
            continue

        dominant_emotion = max(emotions, key=emotions.get)
        score = round(emotions[dominant_emotion], 2)

        # Scale coordinates back to full size
        x = int(x * frame.shape[1] / FRAME_WIDTH)
        y = int(y * frame.shape[0] / FRAME_HEIGHT)
        w = int(w * frame.shape[1] / FRAME_WIDTH)
        h = int(h * frame.shape[0] / FRAME_HEIGHT)

        faces.append({
            "box": (x, y, w, h),
            "dominant_emotion": dominant_emotion,
            "score": score
        })

        # Smooth out flickering by using a moving average of recent emotions
        emotion_buffer.append(dominant_emotion)
        if len(emotion_buffer) > 3:
            most_common = max(set(emotion_buffer), key=emotion_buffer.count)
            faces[-1]["dominant_emotion"] = most_common

    return faces
