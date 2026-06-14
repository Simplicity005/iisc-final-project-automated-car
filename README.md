
<div align="center">

# 🤖 ROS2 Core Orchestrator
**LLM-Vision Directed Robotics Interface**

[![ROS2](https://img.shields.io/badge/ROS2-Jazzy-22314E?style=for-the-badge&logo=ros)](https://docs.ros.org/en/jazzy/index.html)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/Hardware-ESP8266-000000?style=for-the-badge&logo=espressif)](https://www.espressif.com/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?style=for-the-badge&logo=ubuntu)](https://ubuntu.com/)

A highly modular, distributed ROS2 architecture bridging high-level artificial intelligence (LLMs & YOLO) with resource-constrained hardware via a localized state-machine.

[Architecture](#architecture) • [Network Graph](#network-graph) • [Team Domains](#team-domains) • [Quick Start](#quick-start)

</div>

---

## ✦ Architecture

Due to the computational limits of the ESP8266 chassis, the entire ROS2 network operates on a host PC. The system is designed around a central state-machine orchestrator, ensuring rapid state updates and the ability to instantly override hardware commands using strictly defined **Topics** and **Services**.

```mermaid
graph TD
    %% Styling
    classDef central fill:#22314E,stroke:#fff,stroke-width:2px,color:#fff;
    classDef nodes fill:#f4f4f4,stroke:#333,stroke-width:1px,color:#333;
    classDef hardware fill:#E95420,stroke:#fff,stroke-width:2px,color:#fff;

    %% Nodes
    D[💬 Chatbot Node]:::nodes
    A{🧠 Central Orchestrator}:::central
    B[👁️ Vision Node]:::nodes
    C[🎥 Camera Stream]:::nodes
    E[🛜 UDP Bridge]:::nodes
    HW((ESP8266 Chassis)):::hardware

    %% Connections
    D -- "/user_target (Topic)" --> A
    A -- "/set_yolo_target (Service)" --> B
    C -- "/video_frames (Topic)" --> B
    B -- "/detection_status (Topic)" --> A
    A -- "/movement_commands (Topic)" --> E
    E -. "UDP Payloads (Wi-Fi)" .-> HW

```

---

## ✦ Network Graph

To maintain system integrity across different development teams, all inter-node communication must strictly adhere to the following payload definitions.

### Asynchronous Data Streams (Topics)

| Publisher | Subscriber | Topic Name | Message Type | Purpose |
| --- | --- | --- | --- | --- |
| **Chatbot** | **Central** | `/user_target` | `std_msgs/msg/String` | Streams the extracted object target. |
| **Vision** | **Central** | `/detection_status` | `std_msgs/msg/Bool` | Broadcasts `True` upon target acquisition. |
| **Central** | **UDP Bridge** | `/movement_commands` | `std_msgs/msg/String` | Emits hardware state (`TURN` / `STOP`). |
| **Camera** | **Vision** | `/video_frames` | `sensor_msgs/msg/Image` | Hoses raw hardware camera feed. |

### Synchronous Configuration (Services)

| Client | Server | Service Name | Request Type | Purpose |
| --- | --- | --- | --- | --- |
| **Central** | **Vision** | `/set_yolo_target` | `example_interfaces/srv/SetBool` | Dynamically overrides YOLO's search filter. |

---

## ✦ Central Orchestrator Flow

The central orchestrator is the state-machine core of the system. It listens for user intent, configures the vision node, and publishes movement commands based on detection status.

1. **Receive target input**
   - Subscribes to `/user_target` (`std_msgs/msg/String`).
   - When a new target string arrives, the orchestrator updates `current_target` and enters the `SEARCHING` state.

2. **Trigger vision configuration**
   - Calls the `/set_yolo_target` service (`example_interfaces/srv/SetBool`) on the vision node.
   - In the current implementation, it sends `req.data = True` to enable or refresh YOLO target filtering.
   - This is a synchronous request/response mechanism that ensures the vision node is explicitly told when a new target search begins.

3. **Watch detection status**
   - Subscribes to `/detection_status` (`std_msgs/msg/Bool`).
   - When the vision node publishes `True`, the orchestrator transitions from `SEARCHING` to `FOUND`.
   - Once the target is found, the orchestrator sends a `STOP` command to the motor control chain.

4. **Publish movement commands**
   - Publishes to `/movement_commands` (`std_msgs/msg/String`).
   - While in the `SEARCHING` state, it repeatedly sends `TURN` at the timer interval (0.1s).
   - When the target is found, it publishes `STOP`.

### Subscribed and published channels used by the orchestrator

- `/user_target` (subscriber): receives the desired object target from the chatbot/NLP node.
- `/detection_status` (subscriber): receives boolean confirmation from the vision node.
- `/movement_commands` (publisher): sends robot action states to the UDP bridge.
- `/set_yolo_target` (service client): requests vision node target updates and search mode activation.

### How the entire system works together

- The **camera stream** node publishes raw frames on `/video_frames`.
- The **vision node** consumes `/video_frames` and detects whether the current object of interest is visible.
- The **central orchestrator** controls the state transitions: it decides when vision should search, when to keep turning, and when to stop.
- The **UDP bridge** receives `/movement_commands` and sends low-latency Wi-Fi payloads to the ESP8266 chassis.

Together, this design separates high-level intent, visual perception, and low-level actuation into clearly defined ROS2 channels, allowing each module to evolve independently while preserving a single orchestration path.

---

## ✦ Team Domains

> **Maintainers:** Update your respective blocks with specific dependencies and run commands as your modules reach completion.

* **Status:** 🟡 In Development
* **Role:** The core state machine. Listens to inputs, overrides previous states, configures vision, and publishes hardware commands.

* **Status:** 🔴 Pending
* **Role:** YOLO inference node. Scans the `/video_frames` feed exclusively for the class specified by the Orchestrator.

* **Status:** 🔴 Pending
* **Role:** Interfaces directly with camera hardware, broadcasting image data to the ROS2 network.

* **Status:** 🔴 Pending
* **Role:** Parses user natural language to extract isolated target items, publishing them to the Orchestrator.

* **Status:** 🔴 Pending
* **Role:** Subscribes to ROS2 string states and translates them into 100ms UDP payloads directed at the ESP8266 static IP.

---

## ✦ Quick Start

> **⚠️ Required Internal Setup:** > All developers must configure their local machines using the official [Innovate Invent Club Jazzy Setup Guide](https://github.com/https-www-innovateinvent-club/ros_2_projects/blob/main/setup/jazzy-setup-demos.md) before proceeding.

### 1. Prerequisites

* **OS:** Ubuntu 24.04 (Noble) / WSL2
* **Framework:** ROS2 Jazzy Jalisco
* **Network:** ESP8266 and Host PC on the same localized Wi-Fi.

If using WSL2, ensure your display is exported to view camera streams:

```bash
echo "export DISPLAY=:0" >> ~/.bashrc
source ~/.bashrc

```

### 2. Workspace Build

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone [YOUR_REPOSITORY_URL] llm_vision_bot
cd ~/ros2_ws
colcon build
source install/setup.bash

```

### 3. Developer Execution

When modifying your specific python node, use the standard build/run cycle:

```bash
cd ~/ros2_ws
colcon build --packages-select [YOUR_PACKAGE_NAME]
source install/setup.bash
ros2 run [YOUR_PACKAGE_NAME] [YOUR_NODE_EXECUTABLE]

```
