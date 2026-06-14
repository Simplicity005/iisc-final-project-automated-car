import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from example_interfaces.srv import SetString
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge
from ultralytics import YOLO

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        self.status_pub = self.create_publisher(Bool, '/detection_status', 10)
        self.annotated_pub = self.create_publisher(Image, '/annotated_frames', 10)
        self.image_sub = self.create_subscription(Image, '/video_frames', self.image_callback, 10)
        self.is_searching = False
        self.bridge = CvBridge()
        self.model = YOLO('yolov8n.pt')
        self.current_target_class = None
        self.set_target_srv = self.create_service(
            SetString, '/set_yolo_target', self.set_target_callback
        )

    def set_target_callback(self, request, response):
        self.current_target_class = request.data
        self.is_searching = True
        response.success = True
        response.message = f"Now searching for: {self.current_target_class}"
        return response

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            return

        if not self.is_searching:
            annotated_msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            self.annotated_pub.publish(annotated_msg)
            return

        results = self.model(frame, verbose=False)
        annotated_frame = results[0].plot()
        
        annotated_msg = self.bridge.cv2_to_imgmsg(annotated_frame, encoding="bgr8")
        self.annotated_pub.publish(annotated_msg)

        found = False
        for r in results:
            for c in r.boxes.cls:
                class_name = self.model.names[int(c)]
                if class_name == self.current_target_class:
                    found = True
                    break
            if found:
                break

        if found:
            status_msg = Bool()
            status_msg.data = True
            self.status_pub.publish(status_msg)

def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
