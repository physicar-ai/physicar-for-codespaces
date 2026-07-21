import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from anywhere

import argparse
import math
import time

import cv2
import numpy as np
import requests
from ultralytics import YOLO

import webui

BASE_URL = "http://localhost"

SPEED = 0.8            # m/s while chasing
STEER_GAIN = 30.0
NEAR_HEIGHT = 0.45     # stop when the target fills this fraction of the frame
IMG_SIZE = 320         # inference resolution — a ball doesn't need 640,
                       # and it's ~4x less compute on the robot's CPU
CONF = 0.15            # accept weak detections of the target class — up close
                       # the classifier wavers between lookalike classes
LOST_TIMEOUT = 1.0     # keep the last sighting this long before searching


def camera():
    """Latest camera frame as a BGR image (ndarray)."""
    jpg = requests.get(f"{BASE_URL}/camera", timeout=2).content
    return cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)


def drive(speed, steering):
    """speed in m/s, steering in degrees (+ = left). The API wants radians."""
    requests.post(f"{BASE_URL}/speed", json={"value": float(speed)}, timeout=2)
    requests.post(f"{BASE_URL}/steering",
                  json={"value": math.radians(steering)}, timeout=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="sports ball",
                    help="any COCO class: 'sports ball', 'person', 'dog' ...")
    args = ap.parse_args()

    # NCNN — the fastest backend on the robot's CPU (RPi5).
    # The exported model ships with this project.
    yolo = YOLO("yolov8n_ncnn_model", task="detect")
    ids = {name: i for i, name in yolo.names.items()}
    if args.target not in ids:
        raise SystemExit(f"unknown class '{args.target}' — use a COCO class name")
    webui.serve()   # MYAPP tab: camera + detections, live
    print(f"chasing '{args.target}' — Ctrl+C to stop")

    last_best, last_seen = None, 0.0
    try:
        while True:
            t0 = time.time()
            img = camera()
            h, w = img.shape[:2]

            # look for the target class only: picking each box's top class
            # instead would lose the target up close, where a lookalike
            # class starts to outscore it
            best, dets = None, []
            for box in yolo(img, imgsz=IMG_SIZE, conf=CONF,
                            classes=[ids[args.target]], verbose=False)[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                dets.append((args.target, float(box.conf[0]), (x1, y1, x2, y2)))
                if best is None or (x2 - x1) * (y2 - y1) > best[0]:
                    best = ((x2 - x1) * (y2 - y1), (x1 + x2) / 2, y2 - y1)

            if best is not None:
                last_best, last_seen = best, time.time()
            elif time.time() - last_seen < LOST_TIMEOUT:
                best = last_best              # one flickered frame != lost

            if best is None:
                drive(0.0, 15)                              # look around
                status = "searching..."
            else:
                _, cx, box_h = best
                offset = (cx - w / 2) / (w / 2)             # -1 .. 1
                steering = max(-20, min(20, -offset * STEER_GAIN))
                speed = 0.0 if box_h / h > NEAR_HEIGHT else SPEED
                drive(speed, steering)
                status = (f"tracking  offset {offset:+.2f}  "
                          + ("arrived" if speed == 0 else f"speed {speed}"))
            webui.update(img, dets, args.target, status)
            print(f"\r{status}                   ", end="")

            time.sleep(max(0.0, 1 / 10 - (time.time() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        drive(0, 0)
        print("\nstopped")


if __name__ == "__main__":
    main()
