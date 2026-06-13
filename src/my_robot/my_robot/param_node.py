import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ParamNode(Node):
    def __init__(self):
        super().__init__("param_node")

        self.declare_parameter("publish_rate", 1.0)
        self.declare_parameter("message", "Hello from param node")

        rate: float = self.get_parameter("publish_rate").value  # type: ignore
        self.msg_text = self.get_parameter("message").value

        self.publisher = self.create_publisher(String, "my_chatter", 10)
        self.timer = self.create_timer(rate, self.publish_message)
        self.get_logger().info(f'Publishing every {rate}s: "{self.msg_text}"')

    def publish_message(self):
        msg = String()
        msg.data = self.msg_text
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ParamNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
