# ...existing code...
from fastapi import APIRouter, Query, Response, status, Depends, HTTPException
from fastapi.responses import StreamingResponse
import cv2
from backend.services.face_services import detect_emotions_from_array
from typing import Optional, List, Dict, Any
import logging
import time
import asyncio  # Import asyncio for background task management

# --- Import Authentication Dependency ---
from backend.deps import get_current_user

logger = logging.getLogger("backend.emotion_face")

# ✅ ADDED prefix="/api" here
router = APIRouter(prefix="/api", tags=["emotion_face"])

# --- In-memory cache for latest emotion data ---
# NOTE: Simple cache, consider Redis for production
latest_emotion_cache: Dict[str, Any] = {
    "dominant_emotion": "neutral",
    "score": 0.0,
    "timestamp": 0.0,
    "active": False  # Track if the stream is supposed to be active
}
CACHE_TIMEOUT = 10  # Seconds before cache is considered stale

# Initialize webcam as None. Will open only when requested.
cap: Optional[cv2.VideoCapture] = None
# --- Background Task Management ---
background_task = None
stop_event = asyncio.Event()


async def capture_and_detect_emotions(gamma: float = 1.2, skip_frames: int = 2):
    """Background task to capture frames and detect emotions."""
    global cap, latest_emotion_cache
    logger.info("Starting emotion detection background task...")

    if not cap or not cap.isOpened():
        try:
            cap = cv2.VideoCapture(0)  # Use default camera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Optional: Set resolution
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if not cap.isOpened():
                raise RuntimeError("Webcam not accessible")
            logger.info("Webcam opened successfully by background task.")
        except Exception as e:
            logger.error(f"⚠️ Failed to open webcam in background task: {e}")
            latest_emotion_cache["active"] = False
            return  # Stop task if camera fails

    frame_count = 0
    latest_emotion_cache["active"] = True
    latest_emotion_cache["timestamp"] = time.time()  # Update timestamp on start

    try:
        while not stop_event.is_set() and cap and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame from webcam in background task.")
                await asyncio.sleep(0.1)  # Avoid busy-looping
                continue

            # Run detection only every `skip_frames` frames
            if frame_count % skip_frames == 0:
                try:
                    # Run CPU-bound detection in executor to avoid blocking asyncio loop
                    loop = asyncio.get_event_loop()
                    # Convert frame to RGB before emotion detection
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    detected_faces = await loop.run_in_executor(
                        None,  # Use default executor
                        detect_emotions_from_array,  # The function to run
                        rgb_frame,  # Pass RGB frame instead of BGR
                        gamma
                    )

                    if detected_faces:
                        best_face = max(detected_faces, key=lambda f: f.get("score", 0))
                        current_time = time.time()
                        # Update cache only if detection is confident enough (already handled in service)
                        latest_emotion_cache.update({
                            "dominant_emotion": best_face.get("dominant_emotion", "neutral"),
                            "score": best_face.get("score", 0.0),
                            "timestamp": current_time
                        })
                        # logger.debug(f"Detected: {best_face['dominant_emotion']} ({best_face['score']:.2f})")
                    else:
                        # No face detected, update timestamp
                        latest_emotion_cache["timestamp"] = time.time()

                except Exception as detect_error:
                    logger.error(f"Error during emotion detection call: {detect_error}", exc_info=True)
                    latest_emotion_cache.update({
                        "dominant_emotion": "neutral",
                        "score": 0.0,
                        "timestamp": time.time()
                    })

            frame_count += 1
            # Adjust sleep: smaller value = higher CPU, potentially faster updates
            # Larger value = lower CPU, slower updates
            await asyncio.sleep(1 / 15)  # Aim for ~15 FPS processing cycle

    except Exception as e:
        logger.error(f"Exception in background task loop: {e}", exc_info=True)
    finally:
        logger.info("Emotion detection background task stopping...")
        if cap and cap.isOpened():
            cap.release()
            cap = None
            logger.info("Webcam released by background task.")
        latest_emotion_cache["active"] = False
        latest_emotion_cache["timestamp"] = time.time()
        stop_event.clear()


def stop_background_task():
    """Signals the background task to stop."""
    global background_task
    logger.info("Signaling background task to stop.")
    stop_event.set()
    # Wait briefly for task to potentially finish cleanup
    # asyncio.create_task(asyncio.sleep(0.5)) # Optional small delay
    # Check if task exists and cancel it if it hasn't stopped
    # if background_task and not background_task.done():
    #     background_task.cancel() # Force cancellation if needed
    background_task = None
    # Ensure cache reflects inactive state immediately
    latest_emotion_cache["active"] = False


# --- Endpoint to Start/Stop the Background Detection ---
@router.post("/emotion/control")
# async def control_emotion_detection(active: bool, gamma: float = 1.2, current_user: Any = Depends(get_current_user)): # Re-enable auth later
async def control_emotion_detection(active: bool, gamma: float = 1.2):  # Keep auth disabled for debug
    global background_task
    if active:
        if background_task and not background_task.done():
            logger.info("Emotion detection task already running.")
            return {"message": "Emotion detection already active."}
        else:
            stop_event.clear()
            # Create and run the task
            background_task = asyncio.create_task(capture_and_detect_emotions(gamma=gamma))
            logger.info("Emotion detection background task initiated.")
            return {"message": "Emotion detection starting."}
    else:
        if background_task and not background_task.done():
            stop_background_task()
            return {"message": "Emotion detection stopping."}
        else:
            # Ensure inactive state if task wasn't running or already stopped
            stop_background_task()  # Call to ensure cleanup/reset
            logger.info("Emotion detection task was not running or already stopped.")
            return {"message": "Emotion detection already inactive."}


# --- Explicit OPTIONS handler for control endpoint ---
@router.options("/emotion/control")
async def options_emotion_control():
    logger.info("OPTIONS /api/emotion/control handled explicitly.")
    return Response(status_code=status.HTTP_200_OK)


# --- Endpoint to Get Latest Emotion Data ---
@router.get("/emotion/latest")
# async def get_latest_emotion_data(current_user: Any = Depends(get_current_user)): # Re-enable auth later
async def get_latest_emotion_data():  # Keep auth disabled for debug
    """Returns the latest detected emotion from the cache."""
    is_active = latest_emotion_cache.get("active", False)
    timestamp = latest_emotion_cache.get("timestamp", 0.0)
    is_stale = (time.time() - timestamp) > CACHE_TIMEOUT

    # Log cache state for debugging
    # logger.debug(f"Latest emotion cache state: Active={is_active}, Stale={is_stale}, Emotion={latest_emotion_cache.get('dominant_emotion')}")

    # Return neutral if inactive or stale
    if not is_active or is_stale:
        return {"dominant_emotion": "neutral", "score": 0.0, "active": is_active, "stale": is_stale}

    # Return cached data if active and not stale
    return {
        "dominant_emotion": latest_emotion_cache.get("dominant_emotion", "neutral"),
        "score": latest_emotion_cache.get("score", 0.0),
        "active": is_active,
        "stale": is_stale
    }


# --- Explicit OPTIONS handler for latest emotion ---
@router.options("/emotion/latest")
async def options_emotion_latest():
    logger.info("OPTIONS /api/emotion/latest handled explicitly.")
    return Response(status_code=status.HTTP_200_OK)


# --- Video Feed (Optional - for visual confirmation) ---
async def generate_feed_frames(gamma: float = 1.2):  # Made async
    """Yields frames from webcam with overlay based on cache."""
    global cap, latest_emotion_cache

    # Ensure camera is open for the feed if needed
    local_cap = cap  # Use global cap if available
    opened_locally = False
    if not local_cap or not local_cap.isOpened():
        logger.info("Feed opening webcam as background task hasn't.")
        try:
            local_cap = cv2.VideoCapture(0)
            local_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            local_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if not local_cap.isOpened():
                raise RuntimeError("Webcam not accessible for video feed")
            opened_locally = True
        except Exception as e:
            logger.error(f"⚠️ Failed to open webcam for video feed: {e}")
            # Yield a single error frame? For now, just stop.
            return

    try:
        while local_cap and local_cap.isOpened():
            ret, frame = local_cap.read()
            if not ret:
                logger.warning("Failed to read frame for video feed.")
                break

            # --- Read from Cache for Overlay ---
            cache_copy = latest_emotion_cache.copy()  # Read cache atomically
            current_emotion = cache_copy.get("dominant_emotion", "neutral")
            current_score = cache_copy.get("score", 0.0)
            is_active = cache_copy.get("active", False)
            timestamp = cache_copy.get("timestamp", 0.0)
            is_stale = (time.time() - timestamp) > CACHE_TIMEOUT

            # Draw status indicator
            status_text = "ACTIVE" if is_active and not is_stale else ("INACTIVE" if not is_active else "STALE")
            status_color = (0, 255, 0) if is_active and not is_stale else ((0, 0, 255) if not is_active else (0, 165, 255))  # Orange for stale
            cv2.putText(frame, f"Status: {status_text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

            # Draw emotion label if active and not stale and score > 0
            if is_active and not is_stale and current_score > 0:
                label_text = f"{current_emotion.upper()} ({current_score:.2f})"
                (text_width, text_height), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                rect_x = 10
                rect_y = frame.shape[0] - 40
                cv2.rectangle(frame, (rect_x, rect_y), (rect_x + text_width + 10, rect_y + text_height + 10), status_color, -1)
                cv2.putText(frame, label_text, (rect_x + 5, rect_y + text_height + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Allow other tasks to run
            await asyncio.sleep(1 / 30)  # Aim for ~30 FPS feed rate

            # Check if global stop event was set (e.g., by control endpoint)
            if stop_event.is_set():
                logger.info("Stop event detected in video feed generator.")
                break

    except Exception as e:
        logger.error(f"Error in video feed generation: {e}", exc_info=True)
    finally:
        logger.info("Video feed generator stopping.")
        if opened_locally and local_cap and local_cap.isOpened():
            local_cap.release()
            logger.info("Webcam opened by feed generator released.")
        # Do not release global cap here


@router.options("/video_feed")
async def options_video_feed():
    logger.info("OPTIONS /api/video_feed handled explicitly.")
    return Response(status_code=status.HTTP_200_OK)


@router.get("/video_feed")
# async def video_feed_endpoint(gamma: float = Query(1.2), current_user: Any = Depends(get_current_user)): # Re-enable auth later
async def video_feed_endpoint(gamma: float = Query(1.2)):  # Keep auth disabled for debug
    """Streams webcam feed with emotion overlay read from cache."""
    logger.info("GET /api/video_feed requested.")
    # This just starts the *display* stream, not the background detection task.
    return StreamingResponse(generate_feed_frames(gamma=gamma),
                             media_type="multipart/x-mixed-replace; boundary=frame")
# ...existing code...