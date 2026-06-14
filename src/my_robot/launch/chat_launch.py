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
                executable="discord_bot",
                name="discord_bot",
                output="screen",
            ),
        ]
    )
