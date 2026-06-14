import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from my_robot_msgs.srv import DetectObject


class CentralOrchestrator(Node):
    def __init__(self):
        super().__init__("central_orchestrator")

        # /user_target is published by llm_output_node when a valid object is parsed
        self.target_sub = self.create_subscription(
            String,
            "user_target",
            self.target_callback,
            10,
        )

        self.cmd_pub = self.create_publisher(String, "movement_commands", 10)

        # vision_node exposes a DetectObject service instead of a topic
        self.detect_client = self.create_client(DetectObject, "detect_object")

        self.state = "IDLE"
        self.current_target = ""
        self._detection_pending = False
        self._pending_target = ""
        self._last_turn_time = 0.0

        # Timer drives the search loop
        self.timer = self.create_timer(0.5, self.timer_callback)

    # ------------------------------------------------------------------
    # Subscription callbacks
    # ------------------------------------------------------------------

    def target_callback(self, msg: String):
        """Triggered when llm_output_node publishes a valid, searchable object."""
        if msg.data == self.current_target and self.state == "SEARCHING":
            return
        if self.state == "SEARCHING":
            self.get_logger().info(
                f"Switching target: '{self.current_target}' → '{msg.data}'"
            )
        self.current_target = msg.data
        self.state = "SEARCHING"
        self._detection_pending = False
        self.get_logger().info(
            f"New target: '{self.current_target}' — entering SEARCHING"
        )
        self._on_new_target()

    # ------------------------------------------------------------------
    # Timer callback
    # ------------------------------------------------------------------

    def timer_callback(self):
        if self.state == "SEARCHING" and not self._detection_pending:
            self._request_detection()
        elif self.state == "SEARCHING":
            self._on_searching()

    # ------------------------------------------------------------------
    # DetectObject service helpers
    # ------------------------------------------------------------------

    def _request_detection(self):
        if not self.detect_client.service_is_ready():
            self.get_logger().warn("detect_object service not ready yet")
            return

        req = DetectObject.Request()
        req.object_to_detect = self.current_target
        self._detection_pending = True
        self._pending_target = self.current_target
        future = self.detect_client.call_async(req)
        future.add_done_callback(self._on_detect_response)

    def _on_detect_response(self, future):
        self._detection_pending = False
        try:
            result: DetectObject.Response = future.result()
        except Exception as e:
            self.get_logger().error(f"DetectObject service call failed: {e}")
            return

        # Target changed while this request was in flight — discard the result
        if self._pending_target != self.current_target:
            self.get_logger().info(
                f"Discarding stale result for '{self._pending_target}' "
                f"(now searching for '{self.current_target}')"
            )
            return

        if result.success:
            self.get_logger().info(f"Object found: {result.message}")
            self._on_found()
        else:
            self.get_logger().info(f"Not found yet: {result.message}")
            self._on_not_found()

    # ------------------------------------------------------------------
    # Dummy state handlers — fill these in later
    # ------------------------------------------------------------------

    def _on_new_target(self):
        """Called when a new target arrives and the state switches to SEARCHING."""
        pass

    def _on_searching(self):
        """Called each timer tick while a detection request is already in flight."""
        pass

    def _on_found(self):
        """Called when DetectObject returns success=True."""
        stop_msg = String()
        stop_msg.data = "STOP"
        self.cmd_pub.publish(stop_msg)
        self.get_logger().info(
            f"'{self.current_target}' found — stopping and returning to IDLE"
        )
        self._on_idle()

    def _on_not_found(self):
        """Called when DetectObject returns success=False — rotate to keep searching."""
        now = time.monotonic()
        if now - self._last_turn_time < 1.0:
            return
        self._last_turn_time = now
        left_msg = String()
        left_msg.data = "LEFT"
        self.cmd_pub.publish(left_msg)

    def _on_idle(self):
        """Called to transition back to IDLE (e.g. after task complete or timeout)."""
        self.state = "IDLE"
        self.current_target = ""
        self._detection_pending = False


def main(args=None):
    rclpy.init(args=args)
    node = CentralOrchestrator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
