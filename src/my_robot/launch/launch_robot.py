from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="my_robot",
                executable="llm_parser",
                name="llm_command",
                output="screen",
            ),
            Node(
                package="my_robot",
                executable="vision_node",
                name="vision_manager",
                output="screen",
            ),
            Node(
                package="my_robot",
                executable="central_orchestrator",
                name="central_orchestrator",
                output="screen",
            ),
            Node(
                package="my_robot",
                executable="udp_bridge_node",
                name="udp_bridge_node",
                output="screen",
            ),
        ]
    )
