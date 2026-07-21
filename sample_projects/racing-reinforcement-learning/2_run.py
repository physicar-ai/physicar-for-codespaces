import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from anywhere

import math
import time

import cv2
import numpy as np
import onnxruntime as ort
import requests

import webui
from model import ACTIONS, CAMERA_H, CAMERA_PAN, CAMERA_TILT, CAMERA_W

BASE_URL = "http://localhost"


def camera(width, height):
    """Latest camera frame as a BGR image, resized by the server."""
    jpg = requests.get(f"{BASE_URL}/camera",
                       params={"width": width, "height": height},
                       timeout=2).content
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


sess = ort.InferenceSession("model.onnx", providers=["CPUExecutionProvider"])
look(CAMERA_PAN, CAMERA_TILT)   # the model's fixed viewpoint
webui.serve_monitor()           # MYAPP tab: model view + action probabilities

print("driving — Ctrl+C to stop")
try:
    while True:
        t0 = time.time()
        img = camera(CAMERA_W, CAMERA_H)
        x = img.transpose(2, 0, 1)[None].astype(np.float32)

        probs = sess.run(None, {"camera": x})[0][0]
        action = int(probs.argmax())
        drive(ACTIONS[action]["speed"], ACTIONS[action]["steering"])
        webui.update(probs, action)

        print(f"\raction {action} {ACTIONS[action]}  conf {probs.max():.2f}   ", end="")
        time.sleep(max(0.0, 1 / 15 - (time.time() - t0)))
except KeyboardInterrupt:
    pass
finally:
    drive(0, 0)
    print("\nstopped")
