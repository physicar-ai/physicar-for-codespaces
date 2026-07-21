import math
import time

import cv2
import numpy as np
import requests

import webui

BASE_URL = "http://localhost"

SPEED = 0.5            # m/s while the line is visible
STEER_GAIN = 20.0      # how hard to steer per unit of line offset
YELLOW_LO = (20, 80, 80)     # HSV range of the yellow line
YELLOW_HI = (35, 255, 255)


def camera():
    """Latest camera frame as a BGR image (ndarray)."""
    jpg = requests.get(f"{BASE_URL}/camera", timeout=2).content
    return cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)


def drive(speed, steering):
    """speed in m/s, steering in degrees (+ = left). The API wants radians."""
    requests.post(f"{BASE_URL}/speed", json={"value": float(speed)}, timeout=2)
    requests.post(f"{BASE_URL}/steering",
                  json={"value": math.radians(steering)}, timeout=2)


def find_line_offset(img):
    """Return the yellow line's horizontal offset from image center,
    normalized to [-1, 1] (None if no line is visible), plus the mask."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, YELLOW_LO, YELLOW_HI)
    mask[:img.shape[0] // 2] = 0             # look at the lower half (near road)
    m = cv2.moments(mask)
    if m["m00"] < 1000:                       # too few yellow pixels
        return None, mask
    cx = m["m10"] / m["m00"]
    return (cx - img.shape[1] / 2) / (img.shape[1] / 2), mask


def main():
    webui.serve()   # MYAPP tab: camera + mask + line offset, live
    print("following the yellow line — Ctrl+C to stop")
    try:
        while True:
            t0 = time.time()
            img = camera()
            offset, mask = find_line_offset(img)

            if offset is None:
                steering = 15
                drive(0.3, steering)          # search: creep and turn
                status = "line lost — searching"
            else:
                steering = max(-20, min(20, -offset * STEER_GAIN))
                drive(SPEED, steering)
                status = f"offset {offset:+.2f}  steering {steering:+.1f}"
            print(f"\r{status}          ", end="")
            webui.update(img, mask, offset, steering, status)
            time.sleep(max(0.0, 1 / 15 - (time.time() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        drive(0, 0)
        print("\nstopped")


if __name__ == "__main__":
    main()
