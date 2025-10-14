# backend/services/face_services.py
import logging
import cv2
import numpy as np
from typing import Any, List, Dict
from fer import FER

# Suppress MoviePy verbose logs
logging.getLogger("moviepy").setLevel(logging.ERROR)

# Initialize FER detector with MTCNN only once
detector = FER(mtcnn=True)

# Resize frames to speed up detection
FRAME_WIDTH = 320  # reduced from full webcam size
FRAME_HEIGHT = 240

def enhance_image(frame: np.ndarray[Any, Any], gamma: float = 1.2) -> np.ndarray[Any, Any]:
    """Enhance brightness/contrast for low-light frames."""
    # Convert grayscale frames to BGR if needed
    if len(frame.shape) == 2 or frame.shape[2] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    # Histogram equalization in YCrCb
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y_eq = cv2.equalizeHist(y)
    ycrcb_eq = cv2.merge([y_eq, cr, cb])
    frame_eq = cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)

    # Gamma correction
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
                      for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(frame_eq, table)

def detect_emotions_from_array(frame: np.ndarray[Any, Any], gamma: float = 1.2, skip_frames: int = 2) -> List[Dict[str, Any]]:
    """
    Detect emotions in a frame using FER + MTCNN.
    skip_frames: Skip detection for every N frames to save CPU.
    """
    # Resize frame for faster processing
    small_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    enhanced_frame = enhance_image(small_frame, gamma=gamma)
    try:
        results = detector.detect_emotions(enhanced_frame)
    except Exception as e:
        print(f"[FER Error] {e}")
        return []

    faces = []
    for face in results or []:
        x, y, w, h = face["box"]
        # Scale coordinates back to original frame size
        x = int(x * frame.shape[1] / FRAME_WIDTH)
        w = int(w * frame.shape[1] / FRAME_WIDTH)
        y = int(y * frame.shape[0] / FRAME_HEIGHT)
        h = int(h * frame.shape[0] / FRAME_HEIGHT)

        emotions = face["emotions"]
        if not emotions:
            continue
        dominant_emotion = max(emotions, key=emotions.get)
        score = emotions[dominant_emotion]
        faces.append({
            "box": (x, y, w, h),
            "dominant_emotion": dominant_emotion,
            "score": round(score, 2)
        })

    return faces