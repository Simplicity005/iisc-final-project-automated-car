
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

    UI <-->|parse_intent srv| D
    D -->|/user_target| A
    A <-->|detect_object srv| B
    A -->|/movement_commands<br/>LEFT · STOP| E
    E -. UDP .-> HW
```

---

## ✦ App Flow

End-to-end lifecycle of a single user command — from Discord message to hardware motion.

```mermaid
flowchart TD
    classDef svc fill:#1a3a5c,stroke:#7ab,stroke-width:1.5px,color:#fff
    classDef topic fill:#2d4a1e,stroke:#8bc,stroke-width:1.5px,color:#fff
    classDef hw fill:#E95420,stroke:#fff,stroke-width:2px,color:#fff
    classDef decision fill:#4a3060,stroke:#b9a,stroke-width:1.5px,color:#fff
    classDef err fill:#6b1a1a,stroke:#f88,stroke-width:1.5px,color:#fff

    U([👤 User]) -->|mention / slash cmd| BOT[Discord Bot]
    BOT -->|parse_intent Request| LLM[LLM Intent Node]
    LLM -->|Gemini API call| GEM((Google Gemini))
    GEM -->|JSON objective| LLM

    LLM --> CHK{Valid YOLO\nobject?}
    CHK -->|No| FAIL[success=False\nmessage=reason]:::err
    FAIL --> BOT
    BOT -->|❌ Error reply| U

    CHK -->|Yes| OK[success=True\npublish /user_target]
    OK --> BOT
    BOT -->|✅ Searching reply| U
    OK -->|/user_target topic| ORC{Central\nOrchestrator}:::decision

    ORC -->|state = SEARCHING| TIMER[⏱ Timer 0.5 s]
    TIMER -->|detect_object Request| VIS[Vision Node]
    VIS -->|snapshot + YOLO| CAM[📷 IP Camera]
    CAM --> VIS

    VIS --> DET{Object\ndetected?}
    DET -->|No → success=False| ORC
    ORC -->|LEFT cmd| UDP[🛜 UDP Bridge]
    UDP -. UDP packet .-> ESP((ESP8266)):::hw
    ESP -. rotate left .-> ESP
    UDP --> TIMER

    DET -->|Yes → success=True| ORC
    ORC -->|state = FOUND\nSTOP cmd| UDP2[🛜 UDP Bridge]
    UDP2 -. UDP packet .-> ESP2((ESP8266)):::hw
    ESP2 -. motors stop .-> ESP2
```

---

## ✦ Network Graph

To maintain system integrity across different development teams, all inter-node communication must strictly adhere to the following payload definitions.

### Asynchronous Data Streams (Topics)

| Publisher | Subscriber | Topic Name | Message Type | Purpose |
| --- | --- | --- | --- | --- |
| **LLM Intent** | **Central** | `/user_target` | `std_msgs/msg/String` | Validated, lowercase object target (e.g. `"apple"`). |
| **Central** | **UDP Bridge** | `/movement_commands` | `std_msgs/msg/String` | Emits hardware state (`LEFT` / `STOP`). |

### Synchronous Request-Response (Services)

| Client | Server | Service Name | Service Type | Purpose |
| --- | --- | --- | --- | --- |
| **Discord Bot** | **LLM Intent** | `parse_intent` | `my_robot_msgs/srv/ParseIntent` | Send raw text; returns `success` + parsed object name or error reason. |
| **Central** | **Vision** | `detect_object` | `my_robot_msgs/srv/DetectObject` | Trigger detection for a named object; returns `success` + `message`. |

### Custom Service Definitions (`my_robot_msgs`)

#### `ParseIntent.srv`
```
string command
---
bool success
string message
```

Call example:
```bash
ros2 service call /parse_intent my_robot_msgs/srv/ParseIntent "{command: 'find me an apple'}"
```

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
* **Dependencies:** `rclpy`, `std_msgs`, `my_robot_msgs`
* **Run Command:**
```bash
ros2 run my_robot central_orchestrator
```

### 💬 LLM Intent Node
* **Status:** 🟢 Functional
* **Role:** Exposes the `parse_intent` service. When called, sends the raw text to Google Gemini, extracts the search target, and validates it against the YOLO-80 class list. Returns `success=True` + the object name if valid (and publishes it to `/user_target`), or `success=False` + an error reason if not.
* **Dependencies:** `rclpy`, `std_msgs`, `my_robot_msgs`, `google-genai`, `python-dotenv`
* **Environment:** Requires `GEMINI_API_KEY` in `.env`
* **Input format:** Any natural language — `"Find me an apple"`, `"Search for banana"`, etc.
* **Run Commands:**
```bash
ros2 run my_robot llm_parser    # headless service server
ros2 run my_robot terminal_ui   # interactive terminal input loop (dev/debug)
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

### 🤖 Discord Bot (`discord_bot.py`)
* **Status:** 🟢 Functional
* **Role:** The live UI layer. Calls the `parse_intent` service on the LLM Intent Node and replies directly to Discord with the result — either confirming the search target or reporting an error if the object isn't recognizable.
* **Dependencies:** `rclpy`, `my_robot_msgs`, `py-cord`, `python-dotenv`
* **Environment:** Requires `TOKEN` (Discord bot token) in `.env`
* **Architecture:**
  * `DiscordBotNode(Node)` — ROS2 node, owns the service client and instantiates the bot with `self`
  * `DiscordBot(discord.Bot)` — Pycord bot, holds `self.node` reference to call `node.call_parse_intent()`
  * `BotCommands(discord.Cog)` — groups slash commands; `/run` and `/hello`
  * ROS2 spins in a daemon thread; Pycord's asyncio event loop runs in the main thread; `run_in_executor` bridges the two
* **Triggers:**
  * `/run <command>` slash command
  * Mentioning the bot in any message: `@Robot find me a bottle`
* **Responses:**
  * ✅ `Searching for: bottle` — object valid, orchestrator is now searching
  * ❌ `Error: 'foo' is not a searchable object.` — LLM couldn't match it to YOLO class list
* **Run Command:**
```bash
ros2 run my_robot discord_bot
```

### 🛜 UDP Bridge
* **Status:** 🔴 Pending
* **Role:** Subscribes to ROS2 string states and translates them into 100ms UDP payloads directed at the ESP8266 static IP.

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
GEMINI_API_KEY=your_gemini_key_here
TOKEN=your_discord_bot_token_here
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
