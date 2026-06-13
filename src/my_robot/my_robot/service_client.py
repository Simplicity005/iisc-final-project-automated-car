import sys

import rclpy
from example_interfaces.srv import AddTwoInts
from rclpy.node import Node


class AddTwoIntsClient(Node):
    def __init__(self, a, b):
        super().__init__("add_two_ints_client")
        self.client = self.create_client(AddTwoInts, "add_two_ints")

        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for server...")

        self.send_request(a, b)

    def send_request(self, a, b):
        request = AddTwoInts.Request()
        request.a = a
        request.b = b
        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        result = future.result()
        self.get_logger().info(f"Result: {a} + {b} = {result.sum}")


def main(args=None):
    if len(sys.argv) != 3:
        print("Usage: ros2 run my_robot service_client <num1> <num2>")
        return
    a = int(sys.argv[1])
    b = int(sys.argv[2])
    rclpy.init(args=args)
    node = AddTwoIntsClient(a, b)
    node.destroy_node()
    rclpy.shutdown()
