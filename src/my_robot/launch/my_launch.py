from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="my_robot",
                executable="talker",
                name="my_talker",
                output="screen",
            ),
            Node(
                package="my_robot",
                executable="listener",
                name="my_listener",
                output="screen",
            ),
            # Node(
            #     package="my_robot",
            #     executable="service_client",
            #     name="service_client",
            #     output="screen",
            #     arguments=["10", "10"],
            #     # parameters=["10", "10"],
            # ),
            # Node(
            #     package="my_robot",
            #     executable="service_server",
            #     name="service_server",
            #     output="screen",
            # ),
        ]
    )
