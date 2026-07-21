import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from anywhere

import time

import torch

import webui
from env import PhysicarEnv, drive, overlay
from model import CAMERA_H, CAMERA_W, PhysicarNet

TOTAL_STEPS = 30000      # total experience to train on
N_STEPS = 1500             # experience collected per policy update
BATCH_SIZE = 64
LEARNING_RATE = 0.0003
GAMMA = 0.99               # discount factor: weight of future rewards
RESUME = False             # True: pick up where model.zip left off


class Extractor:
    """Let PPO train our PhysicarNet directly, so what we deploy is exactly
    what was trained. Runs everything except the final action layer
    (mirrors the normalization inside PhysicarNet.forward)."""
    def __new__(cls, *a, **kw):
        from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

        class _E(BaseFeaturesExtractor):
            def __init__(self, observation_space):
                super().__init__(observation_space, features_dim=256)
                self.net = PhysicarNet()

            def forward(self, obs):
                x = obs / 255.0 * 2.0 - 1.0
                return torch.relu(self.net.head[0](self.net.cnn(x)))
        return _E(*a, **kw)


def main():
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.monitor import Monitor

    class Dashboard(BaseCallback):
        """Feed the MYAPP dashboard and the /sim overlay while training."""
        def _on_step(self):
            for info in self.locals["infos"]:
                if "episode" in info:   # Monitor adds this when one ends
                    webui.add_episode(info["episode"]["r"], info["episode"]["l"])
            webui.set_status(f"collecting experience... "
                             f"{self.num_timesteps:,}/{TOTAL_STEPS:,} steps")
            return True

        def _on_rollout_end(self):
            drive(0, 0)     # don't let the car run blind during the update
            text = (f"updating the policy... "
                    f"{self.num_timesteps:,}/{TOTAL_STEPS:,} steps done")
            webui.set_status(text)
            overlay(text, ttl=300)   # a policy update can take a few minutes

    # Monitor records every episode (reward, length) to logs/*.monitor.csv
    os.makedirs("logs", exist_ok=True)
    env = Monitor(PhysicarEnv(), time.strftime("logs/%Y%m%d-%H%M%S"))
    webui.serve_dashboard()

    if RESUME and os.path.exists("model.zip"):
        print("resuming from model.zip")
        model = PPO.load("model.zip", env=env)
    else:
        model = PPO("CnnPolicy", env,
                    n_steps=N_STEPS, batch_size=BATCH_SIZE,
                    learning_rate=LEARNING_RATE, gamma=GAMMA,
                    policy_kwargs={"features_extractor_class": Extractor,
                                   "normalize_images": False,
                                   "net_arch": []},
                    verbose=1)
    try:
        model.learn(total_timesteps=TOTAL_STEPS, progress_bar=True,
                    callback=Dashboard())
    except KeyboardInterrupt:
        pass                    # Ctrl+C: still export what was trained so far
    env.close()
    model.save("model.zip")     # full training state, for resuming later

    # Put the trained weights into a plain PhysicarNet and export it.
    net = PhysicarNet()
    trained = model.policy.features_extractor.net
    net.load_state_dict(trained.state_dict())
    with torch.no_grad():   # PPO's action layer becomes the final layer
        net.head[2].weight.copy_(model.policy.action_net.weight)
        net.head[2].bias.copy_(model.policy.action_net.bias)
    net.eval()
    torch.onnx.export(
        net, (torch.zeros(1, 3, CAMERA_H, CAMERA_W),),
        "model.onnx", input_names=["camera"], output_names=["actions"],
        opset_version=17, dynamo=False)
    print(f"\ntrained over {env.unwrapped.episode + 1} episodes"
          f" / saved -> model.zip, model.onnx")
    print("drive: python3 2_run.py")


if __name__ == "__main__":
    main()
