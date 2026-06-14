import threading
import time

import cv2
import numpy as np

# IP camera MJPEG stream URL — update host/port to match your camera's config
CAMERA_URL = "http://10.49.35.24:8000/video"  # "http://192.168.1.13:8080/video"

_FRAME_TIMEOUT = 5.0  # seconds to wait for the first frame before raising


class _LiveCapture:
    """
    Background thread that reads from the MJPEG stream as fast as the camera
    produces frames, keeping only the latest. This guarantees snapshot() always
    returns the frame that was live at the moment of the call, not a buffered one.
    """

    def __init__(self, url: str):
        self._url = url
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        cap = self._connect()
        while not self._stop.is_set():
            ok, frame = cap.read()
            if ok:
                with self._lock:
                    self._frame = frame
            else:
                cap.release()
                time.sleep(0.5)
                cap = self._connect()
        cap.release()

    def _connect(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self._url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def get_frame(self) -> np.ndarray:
        deadline = time.monotonic() + _FRAME_TIMEOUT
        while time.monotonic() < deadline:
            with self._lock:
                if self._frame is not None:
                    return self._frame.copy()
            time.sleep(0.02)
        raise RuntimeError(f"Timed out waiting for a frame from {self._url}")

    def release(self):
        self._stop.set()
        self._thread.join(timeout=2.0)


_live: _LiveCapture | None = None


def _get_live() -> _LiveCapture:
    global _live
    if _live is None:
        _live = _LiveCapture(CAMERA_URL)
    return _live


def snapshot() -> np.ndarray:
    """Return the live BGR frame from the IP camera at the moment of the call."""
    return _get_live().get_frame()


def show_snapshot():
    """Open an OpenCV window showing a single live frame. Press any key to close."""
    frame = snapshot()
    cv2.imshow("Camera Snapshot", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def release():
    """Stop the background reader and release the camera. Call on node shutdown."""
    global _live
    if _live is not None:
        _live.release()
        _live = None


if __name__ == "__main__":
    print(f"Connecting to {CAMERA_URL} — press q to quit ...")
    while True:
        frame = snapshot()
        cv2.imshow("Camera Preview", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    release()
    cv2.destroyAllWindows()
