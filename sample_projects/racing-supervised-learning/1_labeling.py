import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from anywhere

import math
import select
import sys
import termios
import time
import tty
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import requests

import webui
from model import ACTIONS, CAMERA_PAN, CAMERA_TILT

BASE_URL = "http://localhost"

ACTION_TIMEOUT = 0.5    # seconds a key press keeps the robot moving


def camera():
    """Latest camera frame as a BGR image (ndarray)."""
    jpg = requests.get(f"{BASE_URL}/camera", timeout=2).content
    return cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)


def drive(speed, steering):
    """speed in m/s, steering in degrees (+ = left). The API wants radians."""
    requests.post(f"{BASE_URL}/speed", json={"value": float(speed)}, timeout=2)
    requests.post(f"{BASE_URL}/steering",
                  json={"value": math.radians(steering)}, timeout=2)


def look(pan, tilt):
    """Point the camera (degrees)."""
    requests.post(f"{BASE_URL}/camera/pan",
                  json={"value": math.radians(pan)}, timeout=2)
    requests.post(f"{BASE_URL}/camera/tilt",
                  json={"value": math.radians(tilt)}, timeout=2)


def read_key(timeout=0.0):
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    return sys.stdin.read(1) if r else None


def main():
    for key in ACTIONS:
        Path("data", key).mkdir(parents=True, exist_ok=True)
    session = datetime.now().strftime("%Y%m%d_%H%M%S")  # unique filenames
    look(CAMERA_PAN, CAMERA_TILT)   # the model's fixed viewpoint
    webui.set_counts({k: len(list(Path("data", k).glob("*.jpg")))
                      for k in ACTIONS})
    webui.serve_labeling()          # MYAPP tab: photo counts + last shot

    print("The key you press is the answer (y); the photo at that moment is the question (x).")
    for key, action in ACTIONS.items():
        print(f"  [{key}] {action}  ->  data/{key}/")
    print("  [space] stop now   [q] quit\n")

    old = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    moving_until, n = 0.0, 0
    try:
        while True:
            key = read_key(0.05)
            if key == "q":
                break
            if key == " ":
                drive(0, 0)
                moving_until = 0.0
            elif key in ACTIONS:
                img = camera()
                cv2.imwrite(f"data/{key}/{session}_{n:06d}.jpg", img)
                n += 1
                webui.shot(key, img)
                drive(ACTIONS[key]["speed"], ACTIONS[key]["steering"])
                moving_until = time.time() + ACTION_TIMEOUT

            if moving_until and time.time() >= moving_until:
                drive(0, 0)
                moving_until = 0.0

            state = "moving " if moving_until else "stopped"
            print(f"\r  {state}  photos {n:,}   ", end="")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        drive(0, 0)
        print(f"\nsaved: data/  ({n:,} photos)")


if __name__ == "__main__":
    main()
