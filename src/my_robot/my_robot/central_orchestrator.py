import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from example_interfaces.srv import SetBool

class CentralOrchestrator(Node):
    def __init__(self):
        super().__init__('central_orchestrator')
        self.target_sub = self.create_subscription(String, '/user_target', self.target_callback, 10)
        self.vision_sub = self.create_subscription(Bool, '/detection_status', self.vision_callback, 10)
        self.cmd_pub = self.create_publisher(String, '/movement_commands', 10)
        self.yolo_client = self.create_client(SetBool, '/set_yolo_target')
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.state = 'IDLE'
        self.current_target = ''

    def target_callback(self, msg):
        if self.current_target != msg.data:
            self.current_target = msg.data
            self.state = 'SEARCHING'
            self.send_yolo_update()

    def send_yolo_update(self):
        if self.yolo_client.wait_for_service(timeout_sec=1.0):
            req = SetBool.Request()
            req.data = True
            self.yolo_client.call_async(req)

    def vision_callback(self, msg):
        if msg.data and self.state == 'SEARCHING':
            self.state = 'FOUND'
            stop_msg = String()
            stop_msg.data = 'STOP'
            self.cmd_pub.publish(stop_msg)

    def timer_callback(self):
        if self.state == 'SEARCHING':
            turn_msg = String()
            turn_msg.data = 'TURN'
            self.cmd_pub.publish(turn_msg)

def main(args=None):
    rclpy.init(args=args)
    node = CentralOrchestrator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()