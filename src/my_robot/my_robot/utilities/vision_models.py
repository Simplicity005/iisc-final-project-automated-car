from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class DetectorBase:
    """Abstract base class for any object detection model."""

    def detect(self, frame) -> List["DetectionResult"]:
        """Return list of detection results."""
        raise NotImplementedError


@dataclass
class DetectionResult:
    """Represents a single detection."""

    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center: Tuple[int, int]  # cx, cy


class YOLOv8Detector(DetectorBase):
    """YOLOv8 detector wrapper."""

    def __init__(self, model_path: str = "yolov8n.pt", classes: List[int] = None):
        from ultralytics import YOLO

        print(f"[INFO] Loading YOLOv8 model: {model_path}")
        self.model = YOLO(model_path)
        self.classes = classes  # None = all classes, list = filter to these class IDs
        print(f"[SUCCESS] Loaded YOLOv8 model: {model_path}")

    def detect(self, frame) -> List[DetectionResult]:
        results = self.model(frame, classes=self.classes, conf=0.5, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                class_name = r.names[class_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                detections.append(
                    DetectionResult(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=(cx, cy),
                    )
                )
        return detections


class YOLOv26Detector(DetectorBase):
    """YOLOv26 detector wrapper."""

    def __init__(self, model_path: str = "yolo26m.pt", classes: List[int] = None):
        from ultralytics import YOLO

        print(f"[INFO] Loading YOLOv26 model: {model_path}")
        self.model = YOLO(model_path)
        self.classes = classes  # None = all classes, list = filter to these class IDs
        print(f"[SUCCESS] Loaded YOLOv26 model: {model_path}")

    def detect(self, frame) -> List[DetectionResult]:
        results = self.model(frame, classes=self.classes, conf=0.5, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                class_name = r.names[class_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                detections.append(
                    DetectionResult(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=(cx, cy),
                    )
                )
        return detections


class RoboflowDetector(DetectorBase):
    """Placeholder for Roboflow integration."""

    def __init__(self, api_key: str, model_url: str, class_names: List[str]):
        self.api_key = api_key
        self.model_url = model_url
        self.class_names = class_names
        print(f"[INFO] Roboflow detector configured (placeholder)")
        # Integration would use roboflow SDK or inference API here

    def detect(self, frame) -> List[DetectionResult]:
        # Placeholder implementation
        return []
