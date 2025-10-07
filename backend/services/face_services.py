import logging
import cv2
from typing import Any, List, Dict
import numpy as np
from fer import FER

# Suppress MoviePy verbose logs
logging.getLogger("moviepy").setLevel(logging.ERROR)

# Initialize FER detector with MTCNN
detector = FER(mtcnn=True)

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
                      for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(frame_eq, table)

def detect_emotions_from_array(frame: np.ndarray[Any, Any], gamma: float = 1.2) -> List[Dict[str, Any]]:
    """Detect emotions in a frame using FER + MTCNN."""
    
    enhanced_frame = enhance_image(frame, gamma=gamma)
    try:
        results = detector.detect_emotions(enhanced_frame)
    except Exception as e:
        print(f"[FER Error] {e}")
        return []

    faces = []
    for face in results or []:
        x, y, w, h = face["box"]
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
