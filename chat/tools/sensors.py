import base64
import json
import math

from typing import Annotated

import requests
from pydantic import Field

from physicar.chat.types import TextContent, ImageContent


def camera():
    """Capture an image from the front camera."""
    r = requests.get("http://localhost/camera", timeout=5)
    r.raise_for_status()
    tool_call_output_contents = [
        ImageContent(
            mime="image/jpeg",
            base64=base64.b64encode(r.content).decode(),
        ),
    ]
    return tool_call_output_contents


def lidar(
    step: Annotated[float, Field(description="angular step in degrees (0.5~30)", ge=0.5, le=30)] = 5.0,
):
    """Read 360° LiDAR distance scan.

    Returns angle→distance(m) map. 0°=front, +90°=left, -90°=right, 180°=rear.
    Smaller step = more points (e.g. step=5 → 72 points, step=30 → 12 points).
    Range: 0.15m ~ 16m.
    """
    r = requests.get("http://localhost/lidar", params={"step": step}, timeout=5)
    r.raise_for_status()
    tool_call_output_contents = [
        TextContent(text=json.dumps(r.json(), ensure_ascii=False)),
    ]
    return tool_call_output_contents


def states():
    """Read robot states: speed, steering, camera pan/tilt, and battery."""
    def get(path):
        r = requests.get("http://localhost" + path, timeout=5)
        r.raise_for_status()
        return r.json()

    tool_call_output_contents = [
        TextContent(text=json.dumps({"speed": get('/speed')})),
        TextContent(text=json.dumps({"steering_deg": round(math.degrees(get('/steering')), 1)})),
        TextContent(text=json.dumps({"pan_deg": round(math.degrees(get('/camera/pan')), 1)})),
        TextContent(text=json.dumps({"tilt_deg": round(math.degrees(get('/camera/tilt')), 1)})),
        TextContent(text=json.dumps(get('/battery'), ensure_ascii=False)),
    ]
    return tool_call_output_contents
