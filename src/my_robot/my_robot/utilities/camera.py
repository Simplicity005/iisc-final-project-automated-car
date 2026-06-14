import cv2
import numpy as np

# IP camera MJPEG stream URL — update host/port to match your camera's config
CAMERA_URL = "http://192.168.1.13:8080/video"

_capture: cv2.VideoCapture | None = None


def _get_capture() -> cv2.VideoCapture:
    global _capture
    if _capture is None or not _capture.isOpened():
        _capture = cv2.VideoCapture(CAMERA_URL)
        # Limit buffer to 1 frame so reads always return the latest image
        _capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not _capture.isOpened():
            raise RuntimeError(f"Cannot open camera stream at {CAMERA_URL}")
    return _capture


def snapshot() -> np.ndarray:
    """Return the most recent BGR frame from the IP camera."""
    cap = _get_capture()
    # Drain any buffered frames so we get the live image, not a stale one
    for _ in range(5):
        cap.grab()
    ok, frame = cap.read()
    if not ok:
        global _capture
        _capture.release()
        _capture = None
        cap = _get_capture()
        for _ in range(5):
            cap.grab()
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Failed to read frame from camera stream")
    return frame


def show_snapshot():
    """Open an OpenCV window showing a single frame. Press any key to close."""
    frame = snapshot()
    cv2.imshow("Camera Snapshot", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def release():
    """Release the camera capture. Call on node shutdown."""
    global _capture
    if _capture is not None:
        _capture.release()
        _capture = None


if __name__ == "__main__":
    print(f"Connecting to {CAMERA_URL} — press q to quit ...")
    while True:
        frame = snapshot()
        cv2.imshow("Camera Preview", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    release()
    cv2.destroyAllWindows()
