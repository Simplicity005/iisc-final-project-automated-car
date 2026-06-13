import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    def __init__(self):
        super().__init__("my_talker")
        self.publisher = self.create_publisher(String, "my_chatter", 10)
        self.timer = self.create_timer(1.0, self.publish_message)
        self.count = 0

    def publish_message(self):
        msg = String()
        msg.data = f"Hello from my node: {self.count}"
        self.publisher.publish(msg)
        self.get_logger().info(f"Publishing: {msg.data}")
        self.count += 1


def main(args=None):
    rclpy.init(args=args)
    node = Talker()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
