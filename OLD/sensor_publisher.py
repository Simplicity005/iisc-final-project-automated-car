import rclpy
from rclpy.node import Node

from my_robot_msgs.msg import SensorReading


class SensorPublisher(Node):
    def __init__(self):
        super().__init__("sensor_publisher")
        self.publisher = self.create_publisher(SensorReading, "sensor_data", 10)
        self.timer = self.create_timer(1.0, self.publish_reading)
        self.count = 0

    def publish_reading(self):
        msg = SensorReading()
        msg.temperature = 25.0 + self.count * 0.1
        msg.humidity = 60.0 + self.count * 0.5
        self.publisher.publish(msg)
        self.get_logger().info(
            f"Published: temp={msg.temperature:.1f} humidity={msg.humidity:.1f}"
        )
        self.count += 1


def main(args=None):
    rclpy.init(args=args)
    node = SensorPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
