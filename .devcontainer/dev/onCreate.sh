#!/bin/bash

# Install essential packages
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl gnupg2 lsb-release software-properties-common apt-transport-https ca-certificates locales \
    xvfb x11vnc novnc websockify fluxbox xterm supervisor net-tools lxde-core lxterminal \
    jq python3-pip python3-boto3 docker-compose tmux ffmpeg gh \
    nginx openbox alsa-utils python3-dev # s3fs

# noVNC 심링크
sudo ln -sf vnc_lite.html /usr/share/novnc/index.html 2>/dev/null || true

# ROS 2 Jazzy
if [ ! -f /opt/ros/jazzy/setup.bash ]; then
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
  sudo apt-get update -y
  sudo apt-get install -y --no-install-recommends \
    ros-jazzy-ros-base \
    ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-cv-bridge \
    ros-jazzy-xacro \
    python3-rosdep \
    python3-colcon-common-extensions

  source /opt/ros/jazzy/setup.bash
  sudo rosdep init 2>/dev/null || true
  rosdep update --rosdistro jazzy 2>/dev/null || true
fi

# Gazebo Harmonic
if ! command -v gz &>/dev/null; then
  sudo curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
    -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
  sudo apt-get update -y
  sudo apt-get install -y gz-harmonic ros-jazzy-ros-gz
fi

# pip install
# Set pip to allow breaking system packages
pip3 config set global.break-system-packages true

# physicar-python & physicar-sim
git submodule update --init
pip3 install -e "$PWD/.devcontainer/physicar-python"

pip3 install --no-cache-dir \
  opencv-python-headless \
  flask flask-cors websockets pyyaml requests \
  python-multipart watchdog \
  setuptools==70.0.0 2>/dev/null || true

# numpy 시스템 버전 유지
pip3 install --break-system-packages --force-reinstall numpy==1.26.4 2>/dev/null || true

# /opt/physicar 디렉토리
sudo mkdir -p /opt/physicar
echo -e "DEV=true\nSIM=true" | sudo tee /opt/physicar/.env > /dev/null

# nginx 설정
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf "$PWD/.devcontainer/nginx.conf" /etc/nginx/sites-enabled/physicar

# ~/.bashrc 환경 설정
cat >> ~/.bashrc << 'EOF'
export DISPLAY=:1
source /opt/ros/jazzy/setup.bash
source ~/physicar_ws/install/setup.bash 2>/dev/null || true
export ROS_LOCALHOST_ONLY=1
eval "$(register-python-argcomplete ros2)"
eval "$(register-python-argcomplete colcon)"
EOF

# Pull deepracer-simapp Docker image
echo "$DOCKER_PASSWORD" | docker login -u physicar --password-stdin
docker pull physicar/device-dev:1

echo "[onCreate] Complete"