import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import threading
import ollama

class ChatbotNode(Node):
    def __init__(self):
        super().__init__('chatbot_node')
        self.publisher = self.create_publisher(String, '/user_target', 10)
        
        # Run the input loop in a separate thread so it doesn't block ROS2 callbacks
        self.input_thread = threading.Thread(target=self.chat_loop)
        self.input_thread.daemon = True
        self.input_thread.start()

    def chat_loop(self):
        self.get_logger().info('LLM Chatbot ready! Type your command (e.g., "Find the red bottle"):')
        while rclpy.ok():
            try:
                user_input = input(">> ")
                if user_input.strip():
                    self.process_with_llm(user_input)
            except EOFError:
                break

    def process_with_llm(self, text):
        self.get_logger().info('Thinking...')
        try:
            # We use a strict system prompt to force the LLM to output a single word
            response = ollama.chat(model='llama3', messages=[
                {
                    'role': 'system',
                    'content': 'You are a strict robot parser. The user gives a command to find an object. Extract ONLY the singular core noun of the object. Do not include adjectives, articles, or punctuation. Example: "go look for the red bottle" -> "bottle".'
                },
                {
                    'role': 'user',
                    'content': text
                }
            ])
            
            # Clean up the output just in case
            target_object = response['message']['content'].strip().lower().strip('."\'')
            self.get_logger().info(f'LLM Extracted Target: "{target_object}"')

            msg = String()
            msg.data = target_object
            self.publisher.publish(msg)

        except Exception as e:
            self.get_logger().error(f'LLM Error (Is Ollama running?): {e}')

def main(args=None):
    rclpy.init(args=args)
    node = ChatbotNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()