import json
import os
import re
import time

import rclpy
from dotenv import load_dotenv
from google import genai
from google.genai import types
from rclpy.node import Node
from std_msgs.msg import String

from my_robot_msgs.srv import DetectObject

from .utilities.camera import snapshot
from .utilities.vision_models import YOLOv8Detector, YOLOv26Detector


class VisionManager(Node):
    def __init__(self):
        super().__init__("vision_manager")
        # self.publisher = self.create_publisher(String, "user_target", 10)
        # self.subscriber = self.create_subscription(
        #     String, "bot_input", self.parse_intent, 10
        # )
        self.detect_srv = self.create_service(
            DetectObject, "detect_object", self.detect_callback
        )
        self.detector = YOLOv26Detector()

    def detect_callback(
        self, request: DetectObject.Request, response: DetectObject.Response
    ):
        # Edit this to implement your detection logic
        object_name = request.object_to_detect
        self.get_logger().info(f"Detect service called for: {object_name}")

        if self.detector is None:
            self.get_logger().error("Detector not Setup")
            response.success = False
            response.message = "YOLO object detection model not setup"
            return response

        current_snapshot = snapshot()
        detections = self.detector.detect(current_snapshot)

        object_detections = [
            d for d in detections if d.class_name.lower() == object_name.lower()
        ]

        self.get_logger().info(
            f"objects found {', '.join([d.class_name for d in detections])}"
        )

        if not object_detections:
            self.get_logger().info(f"{object_name} not found yet")
            response.success = False
            response.message = "Object not found yet!"
            return response

        # # Get best bottle detection (highest confidence)
        # best_bottle = max(bottle_detections, key=lambda d: d.confidence)

        # x1, y1, x2, y2 = best_bottle.bbox
        # cx, cy = best_bottle.center
        # bottle_w = x2 - x1
        # bottle_size = bottle_w / self.config.frame_width

        # # Determine action based on position
        # frame_w = self.config.frame_width
        # frame_cx = frame_w / 2
        # deadzone = frame_w * self.config.deadzone_width

        response.success = True
        response.message = f"Object {object_name} found!"
        return response


def main(args=None):
    rclpy.init(args=args)
    node = VisionManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
