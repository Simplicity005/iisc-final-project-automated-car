import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import socket

class UDPBridgeNode(Node):
    def __init__(self):
        super().__init__('udp_bridge_node')
        self.subscription = self.create_subscription(String, '/movement_commands', self.cmd_callback, 10)
        self.udp_ip = "192.168.1.100"
        self.udp_port = 4210
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def cmd_callback(self, msg):
        payload = msg.data.encode('utf-8')
        try:
            self.sock.sendto(payload, (self.udp_ip, self.udp_port))
        except Exception:
            pass
        self.get_logger().info(msg.data)

def main(args=None):
    rclpy.init(args=args)
    node = UDPBridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
