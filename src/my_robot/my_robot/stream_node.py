import threading
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge

class StreamNode(Node):
    def __init__(self):
        super().__init__('stream_node')
        self.publisher = self.create_publisher(Image, '/video_frames', 10)
        self.timer = self.create_timer(0.05, self.timer_callback)
        self.cap = cv2.VideoCapture("http://10.49.35.24:8000/video")
        self.bridge = CvBridge()

        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self._running = True
        self._cap_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name='video_capture_thread'
        )
        self._cap_thread.start()

    def _capture_loop(self):
        while self._running:
            if not self.cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if ret:
                with self._frame_lock:
                    self._latest_frame = frame
            else:
                time.sleep(0.01)

    def timer_callback(self):
        with self._frame_lock:
            frame = None if self._latest_frame is None else self._latest_frame.copy()

        if frame is None:
            return

        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        self.publisher.publish(msg)

    def destroy_node(self):
        self._running = False
        if self._cap_thread.is_alive():
            self._cap_thread.join(timeout=1.0)
        self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = StreamNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
