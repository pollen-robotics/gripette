# gripette

Gripper version of the [Grabette](https://github.com/SteveNguyen/grabette) data collection system.
gRPC motor+camera service for the gripper, running on a Raspberry Pi Zero 2W.

Streams camera frames (JPEG) at ~10Hz synchronized with motor positions, and accepts motor commands for two Feetech STS3215 servos over the network.

## Hardware

- Raspberry Pi Zero 2W
- RPi camera module (1296x972, fisheye lens)
- Two Feetech STS3215 servos on `/dev/ttyS0` (baudrate 1000000, IDs 1 and 2)

## Installation

### Development machine (mock mode, no hardware needed)

```bash
uv sync --extra dev
uv run python generate_proto.py   # only needed if you modify gripper.proto
uv run python main.py
```

### Raspberry Pi Zero 2W

Requires system Python 3.11 with `libcamera` and `numpy` installed at the system level.

```bash
sudo apt install libcap-dev

uv venv --python /usr/bin/python3 --system-site-packages
uv sync --extra rpi --no-install-package numpy
uv run python main.py
```

## Configuration

All settings via environment variables with `GRIPPER_` prefix:

| Variable | Default | Description |
|---|---|---|
| `GRIPPER_HOST` | `0.0.0.0` | Server bind address |
| `GRIPPER_PORT` | `50051` | gRPC port |
| `GRIPPER_MOTOR_PORT` | `/dev/ttyS0` | Serial port for servos |
| `GRIPPER_MOTOR_BAUDRATE` | `1000000` | Serial baudrate |
| `GRIPPER_MOTOR_ID_1` | `1` | First servo ID |
| `GRIPPER_MOTOR_ID_2` | `2` | Second servo ID |
| `GRIPPER_JPEG_QUALITY` | `70` | JPEG compression quality |
| `GRIPPER_LOG_LEVEL` | `INFO` | Logging level |

## Usage

### Python client

```python
from gripette.client import GripperClient

with GripperClient("192.168.1.36:50051") as g:
    print(g.ping())

    g.torque_on()
    g.move(-0.5, -1.0)          # goal positions in radians

    for frame in g.stream():    # 10Hz camera + motor state
        print(f"Frame {frame.sequence}: {len(frame.jpeg_data)}B, "
              f"motors=({frame.motor1:.2f}, {frame.motor2:.2f})")
        break

    m1, m2 = g.read_motors()    # lightweight, no camera
    g.torque_off()
```

### Teleoperation bridge

Reads angle sensors from the grabette glove (Pi 4) and forwards them as motor commands to the gripper:

```bash
uv run python scripts/teleop_bridge.py --dry-run   # preview without moving motors
uv run python scripts/teleop_bridge.py              # live control
```

Requires the grabette service running on `192.168.1.35:8000`.

### Motor test

Sends a 1Hz sinusoidal command and records feedback positions for delay analysis:

```bash
uv run python scripts/sinus_test.py
# Outputs sinus_test.csv and sinus_test.png
```

### Camera test

Measures stream framerate and saves a sample frame:

```bash
uv run python scripts/camera_test.py
# Outputs camera_test.jpg
```

## systemd service

```bash
sudo cp systemd/gripette.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gripette
sudo systemctl start gripette
```

## Proto definition

The gRPC service contract is defined in `proto/gripper.proto`. To regenerate the Python files after modifying it:

```bash
uv sync --extra dev
uv run python generate_proto.py
```

Generated files in `gripette/proto/` are committed to the repository.
