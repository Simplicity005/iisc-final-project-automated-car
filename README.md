
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
flowchart TD
    classDef central fill:#22314E,stroke:#fff,stroke-width:2px,color:#fff
    classDef nodes fill:#f4f4f4,stroke:#333,stroke-width:1px,color:#333
    classDef hardware fill:#E95420,stroke:#fff,stroke-width:2px,color:#fff
    classDef ui fill:#6C3483,stroke:#fff,stroke-width:2px,color:#fff
    classDef camera fill:#1a6b3c,stroke:#fff,stroke-width:2px,color:#fff

    UI[🖥️ UI Layer<br/>Terminal / Discord Bot]:::ui
    D[💬 LLM Intent Node]:::nodes
    A{🧠 Central Orchestrator}:::central
    E[🛜 UDP Bridge]:::nodes
    HW((ESP8266 Chassis)):::hardware

    subgraph VS [" "]
        direction TB
        CAM[📷 IP Camera]:::camera
        B[👁️ Vision Node]:::nodes
        CAM -. MJPEG .-> B
    end

    UI -->|/bot_input| D
    D -->|/user_target| A
    A <-->|/detect_object| B
    A -->|/movement_commands| E
    E -. UDP .-> HW
```

---

## ✦ Network Graph

To maintain system integrity across different development teams, all inter-node communication must strictly adhere to the following payload definitions.

### Asynchronous Data Streams (Topics)

| Publisher | Subscriber | Topic Name | Message Type | Purpose |
| --- | --- | --- | --- | --- |
| **UI Layer** | **LLM Intent** | `/bot_input` | `std_msgs/msg/String` | Raw natural language from the user. |
| **LLM Intent** | **Central** | `/user_target` | `std_msgs/msg/String` | Validated, lowercase object target (e.g. `"apple"`). |
| **Central** | **UDP Bridge** | `/movement_commands` | `std_msgs/msg/String` | Emits hardware state (`TURN` / `STOP`). |

### Synchronous Configuration (Services)

| Client | Server | Service Name | Service Type | Purpose |
| --- | --- | --- | --- | --- |
| **Central** | **Vision** | `/detect_object` | `my_robot_msgs/srv/DetectObject` | Trigger detection for a named object; returns `success` + `message`. |

### Custom Service Definitions (`my_robot_msgs`)

#### `DetectObject.srv`
```
string object_to_detect
---
bool success
string message
```

Call example:
```bash
ros2 service call /detect_object my_robot_msgs/srv/DetectObject "{object_to_detect: 'bottle'}"
```

---

## ✦ Team Domains

> **Maintainers:** Update your respective blocks with specific dependencies and run commands as your modules reach completion.

### 🧠 Central Orchestrator
* **Status:** 🟢 Functional
* **Role:** The core state machine. Listens to inputs, overrides previous states, triggers vision detection, and publishes hardware commands.
* **Dependencies:** `rclpy`, `std_msgs`, `example_interfaces`
* **Run Command:**
```bash
ros2 run my_robot central_orchestrator
```

### 💬 LLM Intent Node
* **Status:** 🟢 Functional
* **Role:** Subscribes to `/bot_input`, sends the raw message to Google Gemini to extract the search target, validates it against the YOLO-80 class list, and publishes the lowercase result to `/user_target`. Prints `True` on success, `False` if the object is not in the searchable set.
* **Dependencies:** `rclpy`, `std_msgs`, `google-genai`, `python-dotenv`
* **Environment:** Requires `GEMINI_API_KEY` set in a `.env` file at the workspace root.
* **Input format:** Any natural language — `"Find me an apple"`, `"Search for banana"`, etc.
* **Run Command:**
```bash
ros2 run my_robot terminal_ui
```

### 👁️ Vision Node
* **Status:** 🟢 Functional
* **Role:** Exposes the `/detect_object` service. The Central Orchestrator calls this service with an object name; the Vision Node grabs a live camera frame, runs YOLOv26 inference, and replies directly with `success: bool` and a `message`. No topic feedback — the Orchestrator drives the loop by calling the service repeatedly and acts on the response.
* **Dependencies:** `rclpy`, `my_robot_msgs`, `ultralytics`, `opencv-python`, `python-dotenv`
* **Model:** `yolo26m.pt` (place in `~/ros2_ws/` before running)
* **Run Command:**
```bash
ros2 run my_robot vision_node
```

### 📷 Camera Utility (`utilities/camera.py`)
* **Status:** 🟢 Functional
* **Role:** Thin wrapper around an IP camera MJPEG stream. Consumed internally by the Vision Node — not a standalone ROS node.
* **Camera URL:** `http://192.168.1.13:8080/video` (update `CAMERA_URL` in `camera.py` to match your device)
* **Key fixes:**
  * `CAP_PROP_BUFFERSIZE = 1` — prevents OpenCV from caching stale frames
  * 5-frame `grab()` drain before each `read()` — ensures the returned image is live
* **Debug / Preview:** Run directly to open a live OpenCV window:
```bash
python3 src/my_robot/my_robot/utilities/camera.py
# Press q to quit
```
Or call `show_snapshot()` from Python to preview a single frame:
```python
from my_robot.utilities.camera import show_snapshot
show_snapshot()
```

### 🛜 UDP Bridge
* **Status:** 🔴 Pending
* **Role:** Subscribes to ROS2 string states and translates them into 100ms UDP payloads directed at the ESP8266 static IP.

---

## ✦ Adding a Discord UI

The UI layer is intentionally decoupled — it only needs to publish a `std_msgs/msg/String` to `/bot_input`. Swapping the terminal for a Discord bot requires no changes to any other node.

```python
# discord_ui_node.py (skeleton)
import discord
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class DiscordUINode(Node):
    def __init__(self):
        super().__init__("discord_ui")
        self.publisher = self.create_publisher(String, "bot_input", 10)

    def forward(self, text: str):
        msg = String()
        msg.data = text
        self.publisher.publish(msg)

# In your Discord on_message handler, call node.forward(message.content)
```

Any message sent in the Discord channel gets forwarded into the ROS2 network unchanged. The LLM Intent Node handles all parsing — the Discord bot stays dumb.

---

## ✦ Quick Start

> **⚠️ Required Internal Setup:** All developers must configure their local machines using the official [Innovate Invent Club Jazzy Setup Guide](https://github.com/https-www-innovateinvent-club/ros_2_projects/blob/main/setup/jazzy-setup-demos.md) before proceeding.

### 1. Prerequisites

* **OS:** Linux Ubuntu 24.04 (Noble) or WSL2 equivalent
* **Framework:** ROS2 Jazzy Jalisco
* **Network:** ESP8266 and Host PC on the same localized Wi-Fi.
* **Python:** `empy==3.3.4` required — ROS2 Jazzy is incompatible with empy 4.x:
```bash
pip install "empy==3.3.4"
```

If using WSL2, ensure your display is exported to view camera streams:

```bash
echo "export DISPLAY=:0" >> ~/.bashrc
source ~/.bashrc
```

### 2. Environment Variables

Create a `.env` file at the workspace root (never commit this):

```bash
# ~/ros2_ws/.env
GEMINI_API_KEY=your_key_here
```

### 3. Workspace Build

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone [YOUR_REPOSITORY_URL] .
cd ~/ros2_ws
colcon build
source install/setup.bash
```

### 4. Developer Build Script

The `build_robot.sh` script automatically detects your shell (bash/zsh) and sources the correct setup file. It now accepts an optional package argument:

```bash
# Build everything
./build_robot.sh
./build_robot.sh all

# Build a specific package only
./build_robot.sh my_robot
./build_robot.sh my_robot_msgs
```

When adding new custom messages or services, always build `my_robot_msgs` first:
```bash
./build_robot.sh my_robot_msgs && ./build_robot.sh my_robot
```

### 5. Manual Developer Execution

If you prefer the manual cycle:

```bash
cd ~/ros2_ws
colcon build --packages-select [YOUR_PACKAGE_NAME]
source install/setup.bash
ros2 run [YOUR_PACKAGE_NAME] [YOUR_NODE_EXECUTABLE]
```
