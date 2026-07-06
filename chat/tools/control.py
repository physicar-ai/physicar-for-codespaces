import math
import time

from typing import Annotated

import requests
from pydantic import Field

from physicar.chat.types import TextContent


def drive(
    speed: Annotated[float, Field(description="m/s (-3..3, +=forward)")] = 0.0,
    steering: Annotated[float, Field(description="degrees (-20..20, +=left)")] = 0.0,
):
    """Set speed and steering.

    e.g. turn right: drive(speed=1, steering=-10)
    e.g. steer left only: drive(steering=10)
    e.g. stop: drive(speed=0)
    """
    requests.post("http://localhost/speed", json={"value": float(speed)}, timeout=5).raise_for_status()
    requests.post("http://localhost/steering", json={"value": math.radians(float(steering))}, timeout=5).raise_for_status()
    tool_call_output_contents = [
        TextContent(text="done"),
    ]
    return tool_call_output_contents


def look(
    pan: Annotated[float, Field(description="camera pan degrees (-30..30, +=left)")] = 0.0,
    tilt: Annotated[float, Field(description="camera tilt degrees (-30..30, +=up)")] = 0.0,
):
    """Rotate the camera. pan=left/right, tilt=up/down."""
    requests.post("http://localhost/camera/pan", json={"value": math.radians(float(pan))}, timeout=5).raise_for_status()
    requests.post("http://localhost/camera/tilt", json={"value": math.radians(float(tilt))}, timeout=5).raise_for_status()
    tool_call_output_contents = [
        TextContent(text="done"),
    ]
    return tool_call_output_contents


def sleep(
    seconds: Annotated[float, Field(description="seconds to wait (0.1~60)")] = 1.0,
):
    """Wait for a given duration. Use between tool calls to create timed sequences.

    e.g. drive forward 2s then stop: drive(speed=1) → sleep(2) → drive(speed=0)
    """
    time.sleep(max(0.1, min(60.0, seconds)))
    tool_call_output_contents = [
        TextContent(text="done"),
    ]
    return tool_call_output_contents
