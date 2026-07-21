import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from anywhere

from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, Subset

import webui
from model import ACTIONS, CAMERA_H, CAMERA_W, PhysicarNet

EPOCHS = 20
BATCH_SIZE = 64
LEARNING_RATE = 0.001
VAL_SPLIT = 0.2
RESUME = False      # True: keep training the weights saved in model.pt


class DrivingData(Dataset):
    def __init__(self, augment=False):
        self.augment = augment
        self.samples = []                       # (photo path, class index)
        for i, key in enumerate(ACTIONS):
            for f in sorted(Path("data", key).glob("*.jpg")):
                self.samples.append((f, i))
        if not self.samples:
            raise SystemExit("data/ is empty — collect photos with 1_labeling.py first")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        img = cv2.imread(str(path))
        img = cv2.resize(img, (CAMERA_W, CAMERA_H), interpolation=cv2.INTER_AREA)
        if self.augment:    # random brightness/contrast, label stays the same
            img = cv2.convertScaleAbs(img, alpha=np.random.uniform(0.8, 1.2),
                                      beta=np.random.uniform(-30, 30))
        camera = torch.from_numpy(img.transpose(2, 0, 1).astype(np.float32))
        return camera, label


def main():
    data = DrivingData(augment=True)      # training: random lighting
    plain = DrivingData()                 # validation: photos as-is
    n_val = max(1, int(len(data) * VAL_SPLIT))
    idx = torch.randperm(len(data)).tolist()
    train_set = Subset(data, idx[n_val:])
    val_set = Subset(plain, idx[:n_val])
    train_dl = DataLoader(train_set, BATCH_SIZE, shuffle=True)
    val_dl = DataLoader(val_set, BATCH_SIZE)
    print(f"training on {len(train_set)} photos, validating on {len(val_set)}"
          f" / {len(ACTIONS)} actions")
    webui.serve_dashboard()     # MYAPP tab: accuracy curve per epoch
    webui.set_status(f"training on {len(train_set)} photos...")

    net = PhysicarNet()
    if RESUME and os.path.exists("model.pt"):
        print("resuming from model.pt")
        net.load_state_dict(torch.load("model.pt"))
    opt = torch.optim.Adam(net.parameters(), lr=LEARNING_RATE)

    for epoch in range(EPOCHS):
        net.train()
        for camera, y in train_dl:
            loss = F.nll_loss(net(camera).clamp_min(1e-8).log(), y)
            opt.zero_grad(); loss.backward(); opt.step()

        net.eval()
        correct = total = 0
        with torch.no_grad():
            for camera, y in val_dl:
                correct += (net(camera).argmax(1) == y).sum().item()
                total += len(y)
        print(f"epoch {epoch + 1:2d}/{EPOCHS}  accuracy {correct / total:.3f}")
        webui.add_epoch(correct / total)
        webui.set_status(f"epoch {epoch + 1}/{EPOCHS}"
                         f" · accuracy {correct / total:.3f}")

    net.eval()
    torch.save(net.state_dict(), "model.pt")    # weights, for resuming later
    torch.onnx.export(
        net, (torch.zeros(1, 3, CAMERA_H, CAMERA_W),),
        "model.onnx", input_names=["camera"], output_names=["actions"],
        opset_version=17, dynamo=False)
    webui.set_status("done — saved model.onnx")
    print("\nsaved -> model.pt, model.onnx")
    print("drive: python3 3_run.py")


if __name__ == "__main__":
    main()
