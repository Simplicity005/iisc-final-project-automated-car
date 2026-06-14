import socket

import rclpy
from rclpy.node import Node
from rich.console import Console
from std_msgs.msg import String

# THE UDP COMMANDS
# FORWARD
# FORWARD FAST
# BACKWARD
# BACKWARD FAST
# RIGHT
# RIGHT FAST
# LEFT
# LEFT FAST
# STOP

_CMD_STYLES = {
    "STOP": "bold red",
    "FORWARD": "bold green",
    "FORWARD FAST": "bold bright_green",
    "BACKWARD": "bold cyan",
    "BACKWARD FAST": "bold bright_cyan",
    "LEFT": "bold yellow",
    "LEFT FAST": "bold bright_yellow",
    "RIGHT": "bold magenta",
    "RIGHT FAST": "bold bright_magenta",
}

_console = Console()


class UDPBridgeNode(Node):
    def __init__(self):
        super().__init__("udp_bridge_node")
        self.subscription = self.create_subscription(
            String, "/movement_commands", self.cmd_callback, 10
        )
        self.udp_ip = "10.49.35.50"
        self.udp_port = 4210
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def cmd_callback(self, msg):
        payload = msg.data.encode("utf-8")
        try:
            self.sock.sendto(payload, (self.udp_ip, self.udp_port))
        except Exception:
            pass

        style = _CMD_STYLES.get(msg.data.upper(), "bold white")
        _console.print(f"[{style}]UDP ▶ {msg.data}[/{style}]")


def main(args=None):
    rclpy.init(args=args)
    node = UDPBridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
