import json
import os
import re
import time

import rclpy
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI
from rclpy.node import Node
from std_msgs.msg import String

from my_robot_msgs.srv import ParseIntent

from .utilities.yolo_objects import searchable_objects

load_dotenv()

_SEARCHABLE_SET = set(searchable_objects)

_SYSTEM_PROMPT = """You are an intent parser for a robot vision system.
The user will ask you to find or search for an object.
Extract the single physical object they want to find and return ONLY valid JSON in this exact format:
{{"objective": "<object name>"}}

Rules:
- Return ONLY the JSON object, no markdown, no explanation, no extra text.
- The value must be a single common noun (e.g. "apple", "banana", "car").
- If you cannot identify a clear search target, return {{"objective": null}}.
"""


class LLmOutputSender(Node):
    CLIENT = OpenAI(
        api_key="sta_21bfcd68f16a6fb61ccf6c3eb5e38f12ae870aa2a28055b4",
        base_url="https://api.freetheai.xyz/v1",
    )
    # CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def __init__(self):
        super().__init__("llm_command")
        self.publisher = self.create_publisher(String, "user_target", 10)
        self.srv = self.create_service(
            ParseIntent, "parse_intent", self.handle_parse_intent
        )

    def handle_parse_intent(
        self, request: ParseIntent.Request, response: ParseIntent.Response
    ):
        raw_text = request.command
        start_timer = time.time()
        self.get_logger().info(f"LLM request started for: '{raw_text}'")

        res = self.CLIENT.chat.completions.create(
            model="kai/openrouter/free",  # Change later
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
        )
        # res = self.CLIENT.models.generate_content(
        #     model="gemini-3.5-flash",
        #     config=types.GenerateContentConfig(system_instruction=_SYSTEM_PROMPT),
        #     contents=raw_text,
        # )
        finish_time = time.time()
        self.get_logger().info(f"LLM response in {finish_time - start_timer:.2f}s")

        content = str(res.choices[0].message.content).strip()

        try:
            data = json.loads(content)
            objective = data.get("objective")
        except (json.JSONDecodeError, AttributeError):
            match = re.search(r'"objective"\s*:\s*"([^"]+)"', content)
            objective = match.group(1) if match else None

        if not objective:
            self.get_logger().warn("No objective extracted from input")
            response.success = False
            response.message = "Could not understand what object to find."
            return response

        objective_lower = objective.lower().strip()

        if objective_lower not in _SEARCHABLE_SET:
            self.get_logger().warn(f"'{objective_lower}' not in searchable objects")
            response.success = False
            response.message = f"'{objective_lower}' is not a searchable object."
            return response

        pub_msg = String()
        pub_msg.data = objective_lower
        self.publisher.publish(pub_msg)
        self.get_logger().info(f"Published '{objective_lower}' to /user_target")

        response.success = True
        response.message = objective_lower
        return response


def term(args=None):
    rclpy.init(args=args)
    node = LLmOutputSender()

    while True:
        raw = input("What should I do?: ").strip()
        if not raw:
            break
        req = ParseIntent.Request()
        req.command = raw
        res = ParseIntent.Response()
        node.handle_parse_intent(req, res)
        print(f"Result: success={res.success}, message='{res.message}'")

    node.destroy_node()
    rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = LLmOutputSender()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    term()
