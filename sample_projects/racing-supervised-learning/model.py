import torch
import torch.nn as nn

# The action table. Keys are the keyboard keys used in 1_labeling.py and the
# class labels the model learns. Edit freely — add actions, change values.
# (hardware limits: |steering| <= 20 deg, speed <= 3.0 m/s)
ACTIONS = {
    "1": {"speed": 0.5, "steering": 20.0},    # left
    "2": {"speed": 0.5, "steering": 0.0},     # straight
    "3": {"speed": 0.5, "steering": -20.0},   # right
}

CAMERA_W, CAMERA_H = 160, 120   # model input resolution (camera is 480x360)
CAMERA_PAN, CAMERA_TILT = 0.0, -15.0   # camera angle (deg) — data collection
                                       # and inference must use the same view


class PhysicarNet(nn.Module):
    """Small CNN: camera image in -> action scores out.
    Normalization lives inside the network, so a raw image goes in."""

    def __init__(self):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(3, 32, 8, 4), nn.ReLU(),
            nn.Conv2d(32, 64, 4, 2), nn.ReLU(),
            nn.Conv2d(64, 64, 3, 1), nn.ReLU(), nn.Flatten())
        with torch.no_grad():
            n = self.cnn(torch.zeros(1, 3, CAMERA_H, CAMERA_W)).shape[1]
        self.head = nn.Sequential(
            nn.Linear(n, 256), nn.ReLU(),
            nn.Linear(256, len(ACTIONS)))

    def forward(self, camera):
        x = camera / 255.0 * 2.0 - 1.0                    # 0-255 -> -1..1
        return torch.softmax(self.head(self.cnn(x)), dim=1)
