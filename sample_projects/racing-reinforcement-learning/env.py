import math
import time

import cv2
import gymnasium as gym
import numpy as np
import requests
from gymnasium import spaces
from shapely.geometry import Point, Polygon
from shapely.geometry.polygon import LinearRing

from model import ACTIONS, CAMERA_H, CAMERA_PAN, CAMERA_TILT, CAMERA_W

BASE_URL = "http://localhost"    # robot web API; simulator endpoints live under /sim/api

STEP_DT = 1 / 15        # one action per camera frame
MAX_STEPS = 150         # episode length limit (10 s at 15 Hz)
WORLDS = ["physicar_base"]   # tracks to train on
WHEELBASE = 0.18        # robot dimensions (from its URDF), for wheel positions
TRACK_OF_CAR = 0.16


class PhysicarEnv(gym.Env):

    def reward(self):
        """Score for the step: 1.0 on the center line, 0.0 at the track
        border, scaled by the track width at the nearest waypoint."""
        x, y = self.state["x"], self.state["y"]
        center = self.state["waypoints_center"]
        d = Point(x, y).distance(LinearRing(center))
        i = int(np.argmin(np.hypot(center[:, 0] - x, center[:, 1] - y)))
        half_width = np.hypot(*(self.state["waypoints_outer"][i]
                                - self.state["waypoints_inner"][i])) / 2
        reward = 1.0 - d / half_width
        return float(reward)

    def on_reset(self):
        """Start the next episode on the center line, moving the start
        point 10% along the track each episode so training covers the
        whole lap. The WORLDS tracks take turns every 10 episodes."""
        respawn(world=WORLDS[(self.episode // 10) % len(WORLDS)],
                start=(self.episode * 0.10) % 1.0)

    # ══════════════════ machinery below ══════════════════

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(
            0, 255, (3, CAMERA_H, CAMERA_W), np.float32)
        self.action_space = spaces.Discrete(len(ACTIONS))
        self.episode = -1               # becomes 0 on the first reset()
        self._track_world = None

    # ── track geometry ────────────────────────────────────────────────────

    def _load_track(self):
        current = sim_status().get("current")
        if current == self._track_world:
            return
        r = requests.get(f"{BASE_URL}/sim/api/route", timeout=5).json()
        center = np.asarray(r["waypoints"], float)
        inner = np.asarray(r["inner"], float)
        outer = np.asarray(r["outer"], float)
        if np.allclose(center[0], center[-1]):    # closed loop: drop dup row
            center, inner, outer = center[:-1], inner[:-1], outer[:-1]
        self._waypoints = center
        self._inner_pts = inner
        self._outer_pts = outer
        self._road = Polygon(r["outer"], [r["inner"]])
        self._bounds = requests.get(f"{BASE_URL}/sim/api/bounds", timeout=5).json()
        self._track_world = current

    def _wheel_points(self, x, y, yaw_rad):
        c, s = math.cos(yaw_rad), math.sin(yaw_rad)
        return [Point(x + dx * c - dy * s, y + dx * s + dy * c)
                for dx, dy in ((WHEELBASE / 2, TRACK_OF_CAR / 2),
                               (WHEELBASE / 2, -TRACK_OF_CAR / 2),
                               (-WHEELBASE / 2, TRACK_OF_CAR / 2),
                               (-WHEELBASE / 2, -TRACK_OF_CAR / 2))]

    def _refresh(self):
        self.obs = camera(CAMERA_W, CAMERA_H).transpose(2, 0, 1).astype(np.float32)

        pose = sim_pose()
        odom = requests.get(f"{BASE_URL}/odom", timeout=2).json()
        objects = requests.get(f"{BASE_URL}/sim/api/objects", timeout=2).json().get("objects", [])
        lights = requests.get(f"{BASE_URL}/sim/api/traffic_lights", timeout=2).json().get("lights", [])

        wheels = self._wheel_points(pose["x"], pose["y"], pose["yaw"])
        on_track = [self._road.contains(w) for w in wheels]

        # crashed = a movable object moved since the episode started — only
        # the car can push one (reference poses are snapshotted in reset())
        self._is_crashed = any(
            o["movable"] and math.hypot(
                o["current"]["x"] - self._obj_ref.get(o["name"], o["current"])["x"],
                o["current"]["y"] - self._obj_ref.get(o["name"], o["current"])["y"]) > 0.03
            for o in objects)
        self._is_offtrack = not any(on_track)

        self.state = {
            "x": pose["x"], "y": pose["y"],
            "heading": math.degrees(pose["yaw"]),
            "linear_velocity": odom["velocity"]["linear"],
            "angular_velocity": odom["velocity"]["angular"],
            "waypoints_center": self._waypoints,
            "waypoints_inner": self._inner_pts,
            "waypoints_outer": self._outer_pts,
            "objects": objects,
            "traffic_lights": lights,
            "bounds": self._bounds,
            "steps": self._steps,
            "episode": self.episode,
        }

    def is_terminated(self):
        """The episode dies here: offtrack (all four wheels out) or crashed."""
        return self._is_offtrack or self._is_crashed

    def is_truncated(self):
        """The episode is cut here: the step limit is reached."""
        return self._steps >= MAX_STEPS

    # ── gymnasium interface ───────────────────────────────────────────────

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        drive(0, 0)
        self.episode += 1
        self._steps = 0
        self.on_reset()
        # A world respawn resets the gimbal — restore the model's viewpoint
        look(CAMERA_PAN, CAMERA_TILT)
        time.sleep(0.3)                 # let physics settle
        self._load_track()
        # crash detection baseline: where the objects are right now
        objects = requests.get(f"{BASE_URL}/sim/api/objects", timeout=5).json().get("objects", [])
        self._obj_ref = {o["name"]: o["current"] for o in objects}
        self._refresh()
        self._t_step = time.time()
        return self.obs, {}

    def step(self, action):
        action = int(action)
        drive(ACTIONS[action]["speed"], ACTIONS[action]["steering"])
        # steady step period: sleep whatever remains of STEP_DT after the
        # time already spent since the last step (refresh, reward, inference)
        time.sleep(max(0.0, STEP_DT - (time.time() - self._t_step)))
        self._t_step = time.time()
        self._steps += 1
        self._refresh()

        reward = float(self.reward())
        terminated = self.is_terminated()
        truncated = self.is_truncated()
        overlay(f"episode {self.episode} · step {self._steps}/{MAX_STEPS}"
                f" · reward {reward:+.2f}")
        return self.obs, reward, terminated, truncated, {"action": action}

    def close(self):
        drive(0, 0)
        overlay("")


# ── web API helpers ───────────────────────────────────────────────────────

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


def sim_status():
    """Simulator status: current world, running/switching flags."""
    return requests.get(f"{BASE_URL}/sim/api/status", timeout=5).json()


def sim_pose(retries=20):
    """Exact vehicle pose {x, y, yaw(rad)} — retries the brief windows where
    the simulator has no pose yet (right after a teleport or world switch)."""
    for _ in range(retries):
        d = requests.get(f"{BASE_URL}/sim/api/pose", timeout=5).json()
        if "x" in d:
            return d
        time.sleep(0.15)
    raise RuntimeError("simulator pose unavailable")


def teleport(x, y, yaw):
    """Place the vehicle at an exact pose (yaw in radians)."""
    requests.post(f"{BASE_URL}/sim/api/pose",
                  json={"x": float(x), "y": float(y), "yaw": float(yaw)},
                  timeout=5)


def overlay(text, ttl=10):
    """Show a status line on the /sim screen (empty text clears it).
    The text disappears by itself after ttl seconds unless refreshed."""
    requests.post(f"{BASE_URL}/sim/api/overlay",
                  json={"text": str(text), "ttl": ttl}, timeout=2)


def respawn(world=None, start=0.0):
    """Reset the car onto the center line for a fresh run.

    world: switch to this track first (only when different — a switch
           takes seconds, so rotate worlds every N episodes, not every one)
    start: where to start on the track, as a lap fraction (0.0 = start line)
    """
    if world is not None:
        while True:
            s = sim_status()
            if (s.get("running") and s.get("current") == world
                    and not s.get("switching")):
                break
            if not s.get("switching"):    # ask (again) — another script may
                requests.post(f"{BASE_URL}/sim/api/switch",   # have flipped it
                              json={"world": f"{world}.world"}, timeout=5)
            time.sleep(2)

    wp = requests.get(f"{BASE_URL}/sim/api/route", timeout=5).json()["waypoints"]
    i = int(start % 1.0 * (len(wp) - 1))
    yaw = math.atan2(wp[i + 1][1] - wp[i][1], wp[i + 1][0] - wp[i][0])
    teleport(wp[i][0], wp[i][1], yaw)
