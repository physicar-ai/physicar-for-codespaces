# PhysiCar Workspace

This workspace (`/home/physicar/physicar_ws`) runs the **PhysiCar** robot in a simulation environment, so you can develop and test autonomous driving without real hardware. The simulation exposes the **same ROS 2 topics and Web API** as the real robot, so code written here runs unchanged on an actual PhysiCar. 

## PhysiCar Sim

The Gazebo Harmonic based simulation environment for **PhysiCar AI**

The source is installed at `/opt/physicar/src/physicar-sim`


### Simulation API

An HTTP API for track management and vehicle state queries is served under the `/sim/api/` path.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sim/api/status` | Simulator runtime status |
| `GET` | `/sim/api/pose` | Vehicle pose (world absolute coordinates) |
| `GET` | `/sim/api/route` | Track waypoints (route) |
| `GET` | `/sim/api/track_bounds` | Track bounds (bounding box) |
| `GET` | `/sim/api/obstacles` | World obstacles (boxes) query |
| `GET` | `/sim/api/worlds` | World list (includes the current world) |
| `POST` | `/sim/api/respawn` | Reload the world to reset all objects to their start state |
| `POST` | `/sim/api/switch` | Switch world (`{"world": "<name>.world"}`) |


## PhysiCar ROS

The ROS 2 Jazzy stack for **PhysiCar AI**

The source is installed at `/opt/physicar/src/physicar-ros`

### Vehicle Specs

| Item | Spec |
|------|------|
| Computer | Raspberry Pi 5 (8 GB) |
| LiDAR | 360°, 0.10–16 m, 10 Hz |
| IMU | 6-axis (accelerometer + gyroscope), 50 Hz |
| Camera | 480×360, 15 fps, MF, FOV 100°, Night Vision |
| Camera Pan | ±30° |
| Camera Tilt | ±30° |
| Battery | 2S Lithium 7.4 V |
| Steering | Ackermann |
| Max Speed | 3.0 m/s |
| Max Wheel Steering Angle | ±20° |

### Apps

#### Agent

- LLM-based Tool Call app.
- User-defined tool path: `/opt/physicar/userdata/agent/tools.py`
  > If there are no user-defined tools or loading fails, the package's built-in tools are loaded.

#### DeepRacer
- Reinforcement-learning-based autonomous driving app.
- Model storage location: `/opt/physicar/userdata/deepracer/models/<model_name>/`

#### MyApp

- Your own robot web app.
- Launch an app on port **5000** and it becomes accessible at `/myapp/`.
- Path rules
    - nginx strips `/myapp` from `/myapp/` requests and forwards them to the app (5000). So the app only needs to be written relative to its own root (`/`).
    - Write HTML links, static resources, redirects, and `fetch` as **relative paths**. Absolute paths (`/...`) point outside `/myapp/` and will break.

- Auto-start script
    - `/home/physicar/physicar_ws/myapp.sh`: runs automatically at boot. The command that launches the app on port 5000.
        ```
        python3 /home/physicar/physicar_ws/app.py
        ```
    - `/home/physicar/physicar_ws/myapp.log`: execution log of the auto-start script.



### ROS 2 Interfaces

#### Sensors

| Name | Kind | Type | Description |
|------|------|------|-------------|
| `/camera/image_raw/compressed` | topic | [`CompressedImage`](https://docs.ros2.org/latest/api/sensor_msgs/msg/CompressedImage.html) | Camera image (JPEG) |
| `/battery_state` | topic | [`BatteryState`](https://docs.ros2.org/latest/api/sensor_msgs/msg/BatteryState.html) | Battery state (1 Hz) |
| `/imu` | topic | [`Imu`](https://docs.ros2.org/latest/api/sensor_msgs/msg/Imu.html) | IMU (50 Hz) |
| `/odom` | topic | [`Odometry`](https://docs.ros2.org/latest/api/nav_msgs/msg/Odometry.html) | Odometry |
| `/scan` | topic | [`LaserScan`](https://docs.ros2.org/latest/api/sensor_msgs/msg/LaserScan.html) | LiDAR scan (raw) |
| `/scan_filtered` | topic | [`LaserScan`](https://docs.ros2.org/latest/api/sensor_msgs/msg/LaserScan.html) | LiDAR scan (filtered) |

#### Control

| Name | Kind | Type | Description |
|------|------|------|-------------|
| `/cmd_vel` | topic | [`Twist`](https://docs.ros2.org/latest/api/geometry_msgs/msg/Twist.html) | Velocity + steering (Ackermann conversion) |
| `/speed` | topic | [`Float64`](https://docs.ros2.org/latest/api/std_msgs/msg/Float64.html) | Speed (m/s) |
| `/steering` | topic | [`Float64`](https://docs.ros2.org/latest/api/std_msgs/msg/Float64.html) | Steering angle (rad) |
| `/camera/pan` | topic | [`Float64`](https://docs.ros2.org/latest/api/std_msgs/msg/Float64.html) | Camera pan (rad) |
| `/camera/tilt` | topic | [`Float64`](https://docs.ros2.org/latest/api/std_msgs/msg/Float64.html) | Camera tilt (rad) |
| `/audio` | topic | [`Audio`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/msg/Audio.msg) | Audio playback |

#### Agent Tools

| Name | Kind | Type | Description |
|------|------|------|-------------|
| `/agent/tool/call` | service | [`ToolCall`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/ToolCall.srv) | Run a tool |
| `/agent/tool/get` | service | [`ToolGet`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/ToolGet.srv) | Get a tool |
| `/agent/tool/init` | service | [`ToolInit`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/ToolInit.srv) | Initialize tools |
| `/agent/tool/list` | service | [`ToolList`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/ToolList.srv) | List tools |
| `/agent/tool/load` | service | [`ToolLoad`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/ToolLoad.srv) | Reload tools |
| `/agent/tool/set` | service | [`ToolSet`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/ToolSet.srv) | Register/update tools |

#### DeepRacer

| Name | Kind | Type | Description |
|------|------|------|-------------|
| `/deepracer/control` | service | [`DeepracerControl`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/DeepracerControl.srv) | Start/stop inference |
| `/deepracer/inference` | topic | [`DeepracerInference`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/msg/DeepracerInference.msg) | Inference result |
| `/deepracer/load_model` | service | [`DeepracerLoadModel`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/DeepracerLoadModel.srv) | Load a model |
| `/deepracer/unload_model` | service | [`DeepracerUnloadModel`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/DeepracerUnloadModel.srv) | Unload a model |
| `/deepracer/set_config` | service | [`DeepracerSetConfig`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/DeepracerSetConfig.srv) | Speed scale, action selection |
| `/deepracer/status` | service | [`DeepracerStatus`](https://github.com/physicar-ai/physicar-ros/blob/main/physicar_interfaces/srv/DeepracerStatus.srv) | Get status |

### Web API

Interactive docs at `/docs` (OpenAPI).

#### Sensor Queries

Query endpoints support real-time streaming via `?stream=true` (camera uses MJPEG, others use SSE).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/states` | Full state snapshot (select with `?include=odom,battery,imu`) |
| `GET` | `/speed` | Speed (m/s) |
| `GET` | `/steering` | Steering angle (rad) |
| `GET` | `/odom` | Odometry |
| `GET` | `/battery` | Battery state |
| `GET` | `/imu` | IMU |
| `GET` | `/lidar` | LiDAR scan |
| `GET` | `/camera` | Camera image (JPEG, resize with `?width`/`?height`) |
| `GET` | `/camera/pan` | Camera pan angle |
| `GET` | `/camera/tilt` | Camera tilt angle |
| `GET` | `/audio` | Audio state |

#### Control (Publish)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/speed` | Speed command |
| `POST` | `/steering` | Steering command |
| `POST` | `/camera/pan` | Camera pan |
| `POST` | `/camera/tilt` | Camera tilt |
| `POST` | `/audio` | Audio playback |

#### Agent Tools

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/agent/tool/list` | List tools |
| `GET` | `/agent/tool/get/{name}` | Get a tool |
| `POST` | `/agent/tool/call/{name}` | Run a tool |
| `POST` | `/agent/tool/set` | Register/update tools |
| `GET` | `/agent/tool/file` | Get tool source file |
| `POST` | `/agent/tool/load` | Reload tools |
| `POST` | `/agent/tool/init` | Initialize tools |

#### DeepRacer

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/deepracer/load_model` | Load a model |
| `POST` | `/deepracer/unload_model` | Unload a model |
| `POST` | `/deepracer/control` | Start/stop inference |
| `POST` | `/deepracer/set_config` | Speed scale / action settings |
| `GET` | `/deepracer/status` | Get status |
| `GET` | `/deepracer/inference` | Inference result (`?stream=true`) |
| `GET` | `/deepracer/models` | List models |
| `GET` | `/deepracer/models/{name}` | Model details |
| `DELETE` | `/deepracer/models/{name}` | Delete a model |
| `POST` | `/deepracer/models/import/{init,chunk,complete,cancel}` | Chunked model upload |

