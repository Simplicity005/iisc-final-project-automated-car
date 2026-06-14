import cv2
import numpy as np

# IP camera MJPEG stream URL — update host/port to match your camera's config
CAMERA_URL = "http://192.168.1.100:8080/video"

_capture: cv2.VideoCapture | None = None


def _get_capture() -> cv2.VideoCapture:
    global _capture
    if _capture is None or not _capture.isOpened():
        _capture = cv2.VideoCapture(CAMERA_URL)
        if not _capture.isOpened():
            raise RuntimeError(f"Cannot open camera stream at {CAMERA_URL}")
    return _capture


def snapshot() -> np.ndarray:
    """Return a single BGR frame from the IP camera, ready for OpenCV or YOLO."""
    cap = _get_capture()
    ok, frame = cap.read()
    if not ok:
        # Stream may have dropped — reset and retry once
        _capture.release()
        cap = _get_capture()
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Failed to read frame from camera stream")
    return frame


def release():
    """Release the camera capture. Call on node shutdown."""
    global _capture
    if _capture is not None:
        _capture.release()
        _capture = None
