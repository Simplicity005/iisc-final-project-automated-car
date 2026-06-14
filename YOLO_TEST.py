"""
Bottle Detection & Autonomous Chaser
======================================
A modular, UI-rich bottle detection system using YOLOv8.
Features:
  - Real-time bottle detection and tracking
  - Thirds-based position analysis for autonomous navigation
  - Modular neural network abstraction (YOLOv8 or Roboflow ready)
  - Configurable motor speeds, deadzone, stop thresholds
  - Servo angle control
  - Object list display showing all detected classes
  - UDP command sending to ESP8266 robot

Dependencies:
  pip install ultralytics opencv-python pillow

Usage:
  python bottle-detection.py
"""

import os
import platform
import socket
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import scrolledtext, ttk
from typing import Any, Dict, List, Optional, Tuple


def _setup_wsl_display():
    """Auto-configure DISPLAY for WSL2 when no X server env is set."""
    if "microsoft" not in platform.release().lower():
        return
    if os.environ.get("DISPLAY"):
        return
    try:
        result = subprocess.run(
            ["grep", "nameserver", "/etc/resolv.conf"],
            capture_output=True,
            text=True,
            check=True,
        )
        host_ip = result.stdout.split()[1]
        os.environ["DISPLAY"] = f"{host_ip}:0.0"
        print(f"[WSL] Auto-set DISPLAY={os.environ['DISPLAY']}")
    except Exception as e:
        print(f"[WSL] Could not auto-set DISPLAY: {e}")
        print(
            "[WSL] Run: export DISPLAY=$(grep nameserver /etc/resolv.conf | awk '{print $2}'):0.0"
        )


def _get_ui_font(preferred: str, fallbacks: List[str]) -> str:
    """Return first available font from the preference list."""
    import tkinter.font as tkfont

    try:
        available = set(tkfont.families())
        for f in [preferred] + fallbacks:
            if f in available:
                return f
    except Exception:
        pass
    return preferred


import cv2
from PIL import Image, ImageTk

# ─────────────────────────────────────────────────────────────────────────────
#                            NEURAL NETWORK ABSTRACTOR
# ─────────────────────────────────────────────────────────────────────────────
# This abstraction allows easy switching between YOLOv8, Roboflow, or any model


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

    def __init__(
        self, model_path: str = "yolov8n.pt", classes: List[int] | None = None
    ):
        from ultralytics import YOLO

        print(f"[INFO] Loading YOLOv8 model: {model_path}")
        self.model = YOLO(model_path)
        self.classes = classes  # None = all classes, list = filter to these class IDs

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

    def __init__(
        self, model_path: str = "yolo26m.pt", classes: List[int] | None = None
    ):
        from ultralytics import YOLO

        print(f"[INFO] Loading YOLOv26 model: {model_path}")
        self.model = YOLO(model_path)
        self.classes = classes  # None = all classes, list = filter to these class IDs

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


class SingleClassDetector(DetectorBase):
    """For models that detect only one class (e.g., trained on bottles only)."""

    def __init__(self, detector: DetectorBase, confidence_threshold: float = 0.5):
        self.detector = detector
        self.confidence_threshold = confidence_threshold

    def detect(self, frame) -> List[DetectionResult]:
        all_detections = self.detector.detect(frame)
        return [d for d in all_detections if d.confidence >= self.confidence_threshold]


# ─────────────────────────────────────────────────────────────────────────────
#                              CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Config:
    """Centralized configuration for easy modification."""

    # UDP Settings
    udp_ip: str = "192.168.4.1"
    udp_port: int = 4210

    # Camera (Change to camera stream)
    camera_index: int | str = (
        # 0
        # "https://100.122.92.36:8080/video"
        # "http:///video"
        "http://192.168.1.13:8080/video"
        # "http://10.49.35.24:8000/video"
        # "rtsp://10.49.35.24:8000/h264_ulaw.sdp"
    )
    frame_width: int = 640
    frame_height: int = 480
    show_cam_on_frame: bool = True

    # Detection settings
    target_class_name: str = "bottle"
    confidence_threshold: float = 0.5

    # Position logic (thirds-based)
    left_boundary: float = 0.2  # Left third ends here
    right_boundary: float = 0.8  # Right third starts here
    deadzone_width: float = 0.15  # Center deadzone fraction

    # Distance/size logic
    stop_size_ratio: float = 0.25  # Bottle width / frame width to stop

    # Motor speeds
    speed_slow: int = 100
    speed_normal: int = 150
    speed_fast: int = 200

    # Debounce (prevents command spam)
    command_debounce: float = 0.2

    # Model path
    yolo_model_path: str = "yolov8n.pt"


# ─────────────────────────────────────────────────────────────────────────────
#                              UDP COMMUNICATION
# ─────────────────────────────────────────────────────────────────────────────


class UDPClient:
    """Handles UDP communication with ESP8266 robot."""

    def __init__(self, config: Config):
        self.config = config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.last_command = None
        self.last_send_time = 0.0

    def send(self, command: str) -> bool:
        """Send command with debounce. Returns True if actually sent."""
        now = time.time()
        if (
            command == self.last_command
            and (now - self.last_send_time) < self.config.command_debounce
        ):
            return False

        try:
            self.sock.sendto(
                command.encode(), (self.config.udp_ip, self.config.udp_port)
            )
            self.last_command = command
            self.last_send_time = now
            print(f"UDP → {command}")
            return True
        except Exception as e:
            print(f"[UDP ERROR] {e}")
            return False

    def send_speed(self, speed: int):
        """Send motor speed command."""
        self.send(f"SPEED:{speed}")

    def send_turn(self, direction: str):
        """Send turn command."""
        self.send(direction.upper())

    def send_servo(self, angle: int):
        """Send servo angle command."""
        self.send(f"SERVO:{angle}")

    def send_stop(self):
        """Send stop command."""
        self.send("STOP")

    def close(self):
        """Clean up socket."""
        self.send_stop()
        self.sock.close()


# ─────────────────────────────────────────────────────────────────────────────
#                              BRAIN / DECISION MAKER
# ─────────────────────────────────────────────────────────────────────────────


class BottleBrain:
    """
    Processes detections and decides robot actions.
    Takes detection data and returns appropriate commands.
    """

    def __init__(self, config: Config):
        self.config = config
        self.detector: Optional[DetectorBase] = None

    def initialize_detector(self):
        """Initialize the detector (YOLOv8 by default)."""
        # This makes it easy to swap detectors - just change this method
        # self.detector = YOLOv8Detector(model_path=self.config.yolo_model_path)
        self.detector = YOLOv26Detector()  # model_path=self.config.yolo_model_path)
        print(f"[INFO] Detector initialized for class: {self.config.target_class_name}")

    def analyze_frame(self, frame) -> Dict[str, Any]:
        """
        Main brain function - processes frame and returns action decision.

        Returns dict with:
            - 'action': 'LEFT', 'RIGHT', 'FORWARD', 'STOP'
            - 'speed': speed value (0-255)
            - 'bottle_found': bool
            - 'bottle_bbox': (x1, y1, x2, y2) or None
            - 'bottle_center': (cx, cy) or None
            - 'bottle_size': size ratio (0-1)
            - 'all_detections': list of all detected objects
        """
        if self.detector is None:
            return self._default_response()

        detections = self.detector.detect(frame)

        # Separate bottle from other objects
        bottle_detections = [
            d
            for d in detections
            if d.class_name.lower() == self.config.target_class_name.lower()
        ]

        if not bottle_detections:
            return self._default_response(all_objects=detections)

        # Get best bottle detection (highest confidence)
        best_bottle = max(bottle_detections, key=lambda d: d.confidence)

        x1, y1, x2, y2 = best_bottle.bbox
        cx, cy = best_bottle.center
        bottle_w = x2 - x1
        bottle_size = bottle_w / self.config.frame_width

        # Determine action based on position
        frame_w = self.config.frame_width
        frame_cx = frame_w / 2
        deadzone = frame_w * self.config.deadzone_width

        # Left of deadzone
        if cx < frame_cx - deadzone:
            action = "LEFT"
        # Right of deadzone
        elif cx > frame_cx + deadzone:
            action = "RIGHT"
        # Centered
        else:
            # Check size to determine if close enough
            if bottle_size >= self.config.stop_size_ratio:
                action = "STOP"
            else:
                action = "FORWARD"

        return {
            "action": action,
            "speed": self._get_speed_for_size(bottle_size),
            "bottle_found": False,
            "bottle_bbox": (x1, y1, x2, y2),
            "bottle_center": (cx, cy),
            "bottle_size": bottle_size,
            "all_detections": detections,
            "confidence": best_bottle.confidence,
        }

    def _get_speed_for_size(self, size_ratio: float) -> int:
        """Determine motor speed based on bottle size (distance proxy)."""
        if size_ratio > 0.2:
            return self.config.speed_slow
        elif size_ratio > 0.1:
            return self.config.speed_normal
        else:
            return self.config.speed_fast

    def _default_response(self, all_objects: List | None = None) -> Dict[str, Any]:
        """Return default response when no bottle found."""
        return {
            "action": "STOP",
            "speed": 0,
            "bottle_found": False,
            "bottle_bbox": None,
            "bottle_center": None,
            "bottle_size": 0,
            "all_detections": all_objects or [],
            "confidence": 0,
        }


# ─────────────────────────────────────────────────────────────────────────────
#                              GUI APPLICATION
# ─────────────────────────────────────────────────────────────────────────────


class BottleDetectionApp:
    """Main GUI application for bottle detection and robot control."""

    def __init__(self, root):
        self.root = root
        self.root.title("🤖 BOTTLE DETECTION & CHASER")
        self.root.configure(bg="#0d1117")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)

        # State
        self.config = Config()
        self.running = True
        self.brain = BottleBrain(self.config)
        self.udp = UDPClient(self.config)
        self.last_action = None

        # Camera
        self.cap = cv2.VideoCapture(self.config.camera_index)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)

        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self._cap_thread = None
        self._canvas_w = 0
        self._canvas_h = 0

        # UI
        self._build_ui()
        self._initialize_detector()

        # Start frame loop
        self._cap_thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="rtsp-capture"
        )
        self._cap_thread.start()
        self._update_frame()

    def _initialize_detector(self):
        """Initialize detector in background to avoid UI freeze."""
        self.status_label.config(text="Initializing detector...", fg="#f79327")
        threading.Thread(target=self._init_detector_bg, daemon=True).start()

    def _init_detector_bg(self):
        """Background detector initialization."""
        self.brain.initialize_detector()
        self.root.after(
            0, lambda: self.status_label.config(text="✅ Detector ready", fg="#3fb950")
        )

    # ─────────────────────────────────────────────────────────────────────
    #                           UI BUILDING
    # ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        """Build the complete UI layout."""
        # Title bar
        title_bar = tk.Frame(self.root, bg="#0d1117")
        title_bar.pack(fill="x", padx=16, pady=(14, 8))

        tk.Label(
            title_bar,
            text=" Bottle Detection",
            font=("Segoe UI", 14, "bold"),
            fg="#58a6ff",
            bg="#0d1117",
        ).pack(side="left")

        self.status_label = tk.Label(
            title_bar,
            text="Initializing...",
            font=("Segoe UI", 9),
            fg="#8b949e",
            bg="#0d1117",
        )
        self.status_label.pack(side="left", padx=(16, 0))

        tk.Label(
            title_bar,
            text=f"UDP {self.config.udp_ip}:{self.config.udp_port}",
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#0d1117",
        ).pack(side="right")

        # Main content area
        content = tk.Frame(self.root, bg="#0d1117")
        content.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Left: Camera feed
        cam_panel = tk.Frame(content, bg="#161b22", bd=0)
        cam_panel.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(
            cam_panel,
            bg="#0d1117",
            bd=0,
            highlightthickness=0,
            width=self.config.frame_width,
            height=self.config.frame_height,
        )
        self.canvas.pack(padx=8, pady=8, fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Right: Controls and info
        side_panel = tk.Frame(content, bg="#0d1117", width=320)
        side_panel.pack(side="right", fill="y", padx=(16, 0))
        side_panel.pack_propagate(False)

        # Scrollable container for side panel
        scrollable = tk.Frame(side_panel, bg="#0d1117")
        scrollable.pack(fill="both", expand=True)

        self._build_detection_status(scrollable)
        self._build_action_display(scrollable)
        self._build_all_objects(scrollable)
        self._build_speed_controls(scrollable)
        self._build_servo_control(scrollable)
        self._build_config_section(scrollable)
        self._build_emergency_stop(scrollable)
        self._build_quit_button(scrollable)

    def _section_label(self, parent, text):
        """Create a section header label."""
        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 9, "bold"),
            fg="#8b949e",
            bg="#0d1117",
            anchor="w",
            pady=6,
        ).pack(fill="x")

    def _build_detection_status(self, parent):
        """Build detection status card."""
        self._section_label(parent, "DETECTION STATUS")

        status_card = tk.Frame(parent, bg="#161b22", bd=0)
        status_card.pack(fill="x", pady=(0, 12))

        self.status_found = tk.Label(
            status_card,
            text="Scanning...",
            font=("Segoe UI", 11, "bold"),
            fg="#f0f6fc",
            bg="#161b22",
            pady=8,
        )
        self.status_found.pack()

        self.status_confidence = tk.Label(
            status_card,
            text="—",
            font=("Segoe UI", 9),
            fg="#8b949e",
            bg="#161b22",
            pady=2,
        )
        self.status_confidence.pack()

        self.status_size = tk.Label(
            status_card,
            text="—",
            font=("Segoe UI", 9),
            fg="#8b949e",
            bg="#161b22",
            pady=2,
        )
        self.status_size.pack()

    def _build_action_display(self, parent):
        """Build action display card."""
        self._section_label(parent, "CURRENT ACTION")

        action_card = tk.Frame(parent, bg="#161b22", bd=0)
        action_card.pack(fill="x", pady=(0, 12))

        self.action_label = tk.Label(
            action_card,
            text="WAITING",
            font=("Segoe UI", 16, "bold"),
            fg="#f0f6fc",
            bg="#161b22",
            pady=12,
        )
        self.action_label.pack()

        # Speed indicator
        self.speed_label = tk.Label(
            action_card,
            text="Speed: —",
            font=("Segoe UI", 10),
            fg="#8b949e",
            bg="#161b22",
            pady=4,
        )
        self.speed_label.pack()

    def _build_all_objects(self, parent):
        """Build detected objects list."""
        self._section_label(parent, "ALL DETECTED OBJECTS")

        objects_card = tk.Frame(parent, bg="#161b22", bd=0)
        objects_card.pack(fill="x", pady=(0, 12))

        self.objects_text = scrolledtext.ScrolledText(
            objects_card,
            height=6,
            font=("Consolas", 9),
            fg="#c9d1d9",
            bg="#0d1117",
            bd=0,
            padx=8,
            pady=8,
            wrap="word",
            state="disabled",
        )
        self.objects_text.pack(fill="both", expand=True)

    def _build_speed_controls(self, parent):
        """Build speed preset controls."""
        self._section_label(parent, "MOTOR SPEED PRESETS")

        speed_card = tk.Frame(parent, bg="#161b22", bd=0)
        speed_card.pack(fill="x", pady=(0, 12))

        # Preset buttons
        btn_frame = tk.Frame(speed_card, bg="#161b22")
        btn_frame.pack(fill="x", padx=8, pady=8)

        self.speed_vars = {
            "slow": tk.IntVar(value=self.config.speed_slow),
            "normal": tk.IntVar(value=self.config.speed_normal),
            "fast": tk.IntVar(value=self.config.speed_fast),
        }

        self.speed_buttons = {}
        for mode, color in [
            ("SLOW", "#da3633"),  # Red
            ("NORMAL", "#f79327"),  # Orange
            ("FAST", "#3fb950"),  # Green
        ]:
            frame = tk.Frame(btn_frame, bg="#161b22")
            frame.pack(side="left", expand=True, fill="x")

            btn = tk.Button(
                frame,
                text=mode,
                font=("Segoe UI", 9, "bold"),
                fg="#f0f6fc",
                bg=color,
                activebackground=self._brighten(color, 20),
                relief="flat",
                bd=0,
                pady=8,
                cursor="hand2",
                command=lambda m=mode, v=self.speed_vars[mode.lower()]: (
                    self._on_speed_change(m, v)
                ),
            )
            btn.pack(fill="x")
            self.speed_buttons[mode] = btn

        # Speed adjustment slider
        speed_adj_frame = tk.Frame(speed_card, bg="#161b22")
        speed_adj_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.speed_adjust_var = tk.IntVar(value=self.config.speed_normal)

        tk.Label(
            speed_adj_frame,
            text="Adjust:",
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#161b22",
            anchor="w",
        ).pack(anchor="w")

        slider = tk.Scale(
            speed_adj_frame,
            from_=0,
            to=255,
            orient="horizontal",
            variable=self.speed_adjust_var,
            bg="#161b22",
            fg="#8b949e",
            troughcolor="#21262d",
            activebackground="#58a6ff",
            highlightthickness=0,
            bd=0,
            sliderrelief="flat",
            sliderlength=20,
            command=self._on_speed_adjust,
        )
        slider.pack(fill="x")

    def _build_servo_control(self, parent):
        """Build servo angle control."""
        self._section_label(parent, "SERVO ANGLE")

        servo_card = tk.Frame(parent, bg="#161b22", bd=0)
        servo_card.pack(fill="x", pady=(0, 12))

        self.servo_var = tk.IntVar(value=90)
        servo_slider = tk.Scale(
            servo_card,
            from_=0,
            to=180,
            orient="horizontal",
            variable=self.servo_var,
            bg="#161b22",
            fg="#8b949e",
            troughcolor="#21262d",
            activebackground="#58a6ff",
            highlightthickness=0,
            bd=0,
            sliderrelief="flat",
            sliderlength=18,
            command=self._on_servo_change,
        )
        servo_slider.pack(fill="x", padx=8, pady=(0, 8))

    def _build_config_section(self, parent):
        """Build configuration panel."""
        self._section_label(parent, "CONFIGURATION")

        config_card = tk.Frame(parent, bg="#161b22", bd=0)
        config_card.pack(fill="x", pady=(0, 12))

        # Deadzone
        dz_frame = tk.Frame(config_card, bg="#161b22")
        dz_frame.pack(fill="x", padx=10, pady=4)

        tk.Label(
            dz_frame,
            text="Deadzone (center):",
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#161b22",
            anchor="w",
        ).pack(side="left", expand=True)

        self.deadzone_var = tk.DoubleVar(value=self.config.deadzone_width)
        tk.Entry(
            dz_frame,
            textvariable=self.deadzone_var,
            font=("Consolas", 9),
            width=5,
            bg="#0d1117",
            fg="#c9d1d9",
            bd=1,
            relief="flat",
            insertbackground="#58a6ff",
        ).pack(side="right")

        # Stop threshold
        stop_frame = tk.Frame(config_card, bg="#161b22")
        stop_frame.pack(fill="x", padx=10, pady=4)

        tk.Label(
            stop_frame,
            text="Stop size (bottle%):",
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#161b22",
            anchor="w",
        ).pack(side="left", expand=True)

        self.stop_size_var = tk.DoubleVar(value=self.config.stop_size_ratio)
        tk.Entry(
            stop_frame,
            textvariable=self.stop_size_var,
            font=("Consolas", 9),
            width=5,
            bg="#0d1117",
            fg="#c9d1d9",
            bd=1,
            relief="flat",
            insertbackground="#58a6ff",
        ).pack(side="right")

    def _build_emergency_stop(self, parent):
        """Build emergency stop button."""
        tk.Button(
            parent,
            text="🛑 EMERGENCY STOP",
            font=("Segoe UI", 10, "bold"),
            fg="#f0f6fc",
            bg="#da3633",
            activebackground="#ff7b72",
            relief="flat",
            bd=0,
            pady=12,
            cursor="hand2",
            command=self._on_emergency_stop,
        ).pack(fill="x")

    def _build_quit_button(self, parent):
        """Build quit button."""
        tk.Button(
            parent,
            text="QUIT",
            font=("Segoe UI", 8),
            fg="#8b949e",
            bg="#0d1117",
            activebackground="#161b22",
            relief="flat",
            bd=0,
            pady=6,
            cursor="hand2",
            command=self._quit,
        ).pack(fill="x")

    # ─────────────────────────────────────────────────────────────────────
    #                           UI HELPERS
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _brighten(hex_color, amount):
        """Lighten a hex color by amount."""
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        r = min(255, r + amount)
        g = min(255, g + amount)
        b = min(255, b + amount)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ─────────────────────────────────────────────────────────────────────
    #                           EVENT HANDLERS
    # ─────────────────────────────────────────────────────────────────────

    def _on_speed_change(self, mode, var):
        """Handle speed preset button clicks."""
        speed = var.get()
        self.speed_adjust_var.set(speed)
        self.udp.send_speed(speed)

        # Update button colors
        for m, btn in self.speed_buttons.items():
            color = {"SLOW": "#da3633", "NORMAL": "#f79327", "FAST": "#3fb950"}.get(m)
            if m == mode:
                btn.config(bg=self._brighten(color, 40))  # Highlighted
            else:
                btn.config(bg=color)

    def _on_speed_adjust(self, val):
        """Handle manual speed slider."""
        speed = int(val)
        self.udp.send_speed(speed)

    def _on_servo_change(self, val):
        """Handle servo angle slider."""
        angle = int(val)
        self.udp.send_servo(angle)

    def _on_emergency_stop(self):
        """Handle emergency stop button."""
        self.udp.send_stop()
        self.status_found.config(text="🛑 EMERGENCY STOP", fg="#da3633")
        self.action_label.config(text="STOP", fg="#da3633")
        self.speed_label.config(text="Speed: 0")

    # ─────────────────────────────────────────────────────────────────────
    #                           MAIN LOOP
    # ─────────────────────────────────────────────────────────────────────

    def _on_canvas_resize(self, event):
        self._canvas_w = event.width
        self._canvas_h = event.height

    def _capture_loop(self):
        """Background thread: continuously reads the latest frame from the stream.
        Only the most recent frame is kept — stale frames are discarded.
        """
        while self.running:
            if not self.cap.isOpened():
                import time

                time.sleep(0.05)
                continue
            ret, frame = self.cap.read()
            if ret:
                with self._frame_lock:
                    self._latest_frame = frame

    def _update_frame(self):
        """UI thread: grab latest decoded frame and render it. Non-blocking."""
        if not self.running:
            return

        with self._frame_lock:
            frame = self._latest_frame

        if frame is not None:
            frame = cv2.flip(frame, 1)

            if not self.config.show_cam_on_frame:
                frame[:] = 0

            result = self.brain.analyze_frame(frame)
            self._process_result(result, frame)
            self._draw_overlays(frame, result)

            cw, ch = self._canvas_w, self._canvas_h
            if cw > 1 and ch > 1:
                frame = cv2.resize(frame, (cw, ch), interpolation=cv2.INTER_LINEAR)

            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.canvas.imgtk = imgtk
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=imgtk)

        self.root.after(30, self._update_frame)

    def _process_result(self, result: Dict, frame):
        """Process brain result and update UI/commands."""
        # Update status
        if result["bottle_found"]:
            self.status_found.config(text="✅ Bottle detected", fg="#3fb950")
            self.status_confidence.config(
                text=f"Confidence: {result['confidence']:.0%}"
            )
            self.status_size.config(
                text=f"Bottle size: {result['bottle_size'] * 100:.1f}% of frame"
            )
        else:
            self.status_found.config(text="❌ No bottle found", fg="#8b949e")
            self.status_confidence.config(text="—")
            self.status_size.config(text="—")

        # Update action
        action = result["action"]
        if action != self.last_action:
            if action == "STOP":
                self.action_label.config(text="STOP", fg="#da3633")
                self.udp.send_stop()
            else:
                self.action_label.config(text=action, fg="#3fb950")
                self.udp.send_turn(action)

            self.last_action = action

        # Update speed display
        speed = result["speed"]
        self.speed_label.config(text=f"Speed: {speed}")

        # If we're moving, send speed
        # if action != "STOP":
        #     self.udp.send_speed(speed)

        # Update objects list
        self._update_objects_list(result["all_detections"])

    def _update_objects_list(self, detections: List):
        """Update the detected objects list display."""
        self.objects_text.config(state="normal")
        self.objects_text.delete(1.0, "end")

        if detections:
            # Group by class
            class_counts = {}
            for d in detections:
                name = d.class_name
                if name in class_counts:
                    class_counts[name] += 1
                else:
                    class_counts[name] = 1

            for name, count in sorted(class_counts.items()):
                self.objects_text.insert("end", f"• {name}: {count}\n")
        else:
            self.objects_text.insert("end", "No objects detected")

        self.objects_text.config(state="disabled")

    def _draw_overlays(self, frame, result: Dict):
        """Draw visualization overlays on frame."""
        h, w = frame.shape[:2]

        # Draw thirds lines
        line_color = (33, 38, 45)
        cv2.line(frame, (w // 3, 0), (w // 3, h), line_color, 2)
        cv2.line(frame, (2 * w // 3, 0), (2 * w // 3, h), line_color, 2)
        cv2.line(frame, (0, h // 3), (w, h // 3), line_color, 2)
        cv2.line(frame, (0, 2 * h // 3), (w, 2 * h // 3), line_color, 2)

        # Draw deadzone center
        cx = w // 2
        deadzone_w = w * self.config.deadzone_width
        cv2.rectangle(
            frame, (int(cx - deadzone_w), 0), (int(cx + deadzone_w), h), (40, 40, 40), 1
        )

        # Draw bottle bounding box and info
        if result["bottle_found"]:
            x1, y1, x2, y2 = result["bottle_bbox"]
            cx, cy = result["bottle_center"]
            color = (63, 185, 80)  # Green

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Center point
            cv2.circle(frame, (cx, cy), 6, color, -1)

            # Confidence label
            label = f"{result['confidence']:.0%}"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, y1 - lh - 8), (x1 + lw + 6, y1), color, -1)
            cv2.putText(
                frame,
                label,
                (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2,
            )

            # Center crosshair to bottle
            cv2.line(frame, (cx, cy), (w // 2, h // 2), color, 1)

        # All object boxes (darker)
        for d in result["all_detections"]:
            if (
                not result["bottle_found"]
                or d.class_name != self.config.target_class_name
            ):
                x1, y1, x2, y2 = d.bbox
                color = (63, 149, 185)  # Blue
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                cv2.putText(
                    frame,
                    d.class_name,
                    (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
                    1,
                )

    def _quit(self):
        """Cleanup and exit."""
        self.running = False
        if self._cap_thread is not None:
            self._cap_thread.join(timeout=1.0)
        self._on_emergency_stop()
        self.cap.release()
        self.udp.close()
        self.root.destroy()


def main():
    """Application entry point."""
    _setup_wsl_display()
    root = tk.Tk()
    app = BottleDetectionApp(root)

    # Handle window close
    def on_closing():
        app._quit()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # root.state("zoomed") is Windows-only; use attributes on Linux/WSL
    try:
        root.state("zoomed")
    except tk.TclError:
        root.attributes("-zoomed", True)

    # Start
    root.mainloop()


if __name__ == "__main__":
    main()
