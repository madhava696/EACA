# backend/services/face_services.py
import logging
import cv2
import numpy as np
from typing import Any, List, Dict
from fer import FER
from collections import deque

logging.getLogger("moviepy").setLevel(logging.ERROR)

# Initialize FER with MTCNN for face detection
detector = FER(mtcnn=False)

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
    skip_frames: int = 2  # Note: skip_frames parameter isn't used in this version
) -> List[Dict[str, Any]]:
    """Detect emotions in a frame using FER with stable output."""
    if frame is None or frame.size == 0:
        return []

    # Resize for speed
    small_frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # Explicit type conversion before enhancement
    small_frame_uint8 = small_frame.astype(np.uint8)

    enhanced_frame = enhance_image(small_frame_uint8, gamma=gamma)

    # Explicit type conversion before detection
    enhanced_frame_uint8 = enhanced_frame.astype(np.uint8)

# ...existing code...
    try:
        # ✅ Convert BGR → RGB before passing to FER (fixes dtype error)
        rgb_frame = cv2.cvtColor(enhanced_frame_uint8, cv2.COLOR_BGR2RGB)

        # Ensure we actually have a proper ndarray with 3 channels
        if not isinstance(rgb_frame, np.ndarray):
            print(f"[FER Error] rgb_frame is not ndarray: {type(rgb_frame)}")
            return []
        if rgb_frame.ndim != 3 or rgb_frame.shape[2] != 3:
            print(f"[FER Error] Invalid frame shape {rgb_frame.shape}")
            return []

        # Convert to float32 and normalize if FER expects floats (safer for TF backends)
        rgb_frame = rgb_frame.astype(np.float32) / 255.0

        # Ensure contiguous memory layout
        rgb_frame = np.ascontiguousarray(rgb_frame.astype(np.uint8))

        # Debug info to help trace dtype/shape issues
        print(f"[FER debug] shape={rgb_frame.shape} dtype={rgb_frame.dtype} contiguous={rgb_frame.flags['C_CONTIGUOUS']}")

        detections = detector.detect_emotions(rgb_frame)
    except Exception as e:
        # Print error but return empty list to avoid crashing the stream
        print(f"[FER Error] Exception during detect_emotions: {e}")
        return []
# ...existing code...

    faces = []
    detected_emotions_this_frame = []  # Store emotions from this frame before smoothing

    for d in detections or []:
        x, y, w, h = d["box"]
        emotions = d.get("emotions", {})
        if not emotions:
            continue

        # Check for valid emotion scores (sometimes FER returns NaN or None)
        valid_emotions = {emo: score for emo, score in emotions.items() if score is not None and np.isfinite(score)}
        if not valid_emotions:
            continue  # Skip if no valid scores

        dominant_emotion = max(valid_emotions, key=valid_emotions.get)
        score = round(valid_emotions[dominant_emotion], 2)

        # Apply confidence threshold
        CONFIDENCE_THRESHOLD = 0.6  # Adjust as needed
        if score < CONFIDENCE_THRESHOLD:
            dominant_emotion = "neutral"
            score = 0.0

        # Scale coordinates back to full size
        x = int(x * frame.shape[1] / FRAME_WIDTH)
        y = int(y * frame.shape[0] / FRAME_HEIGHT)
        w = int(w * frame.shape[1] / FRAME_WIDTH)
        h = int(h * frame.shape[0] / FRAME_HEIGHT)

        detected_emotions_this_frame.append(dominant_emotion)

        faces.append({
            "box": (x, y, w, h),
            "dominant_emotion": dominant_emotion,
            "score": score
        })

    # Apply smoothing only if faces were detected in this frame
    if detected_emotions_this_frame:
        primary_emotion_this_frame = faces[0]["dominant_emotion"] if faces else "neutral"
        emotion_buffer.append(primary_emotion_this_frame)

        # Determine the smoothed emotion based on the buffer's history
        if len(emotion_buffer) >= 3:
            try:
                most_common = max(set(emotion_buffer), key=list(emotion_buffer).count)
                for face in faces:
                    face["dominant_emotion"] = most_common
            except ValueError:
                pass  # Buffer temporarily empty — ignore

    return faces


def detect_emotions_from_bytes(
    frame_bytes: bytes,
    gamma: float = 1.2,
    skip_frames: int = 2
) -> List[Dict[str, Any]]:
    """Detect emotions from raw image bytes."""
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return detect_emotions_from_array(frame, gamma=gamma, skip_frames=skip_frames)