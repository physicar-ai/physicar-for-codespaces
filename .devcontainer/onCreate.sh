#!/bin/bash

# Install essential packages
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl gnupg2 lsb-release software-properties-common apt-transport-https ca-certificates locales \
    xvfb x11vnc novnc websockify xterm supervisor net-tools lxde-core lxterminal \
    jq python3-pip docker-compose tmux ffmpeg gh \
    nginx openbox tint2 xterm alsa-utils python3-dev

# noVNC symlink
sudo ln -sf vnc_lite.html /usr/share/novnc/index.html 2>/dev/null || true

# noVNC auto-reconnect patch - reload page 2s after disconnect
sudo sed -i 's|status("Something went wrong, connection is closed");|status("Reconnecting..."); setTimeout(function(){location.reload();},2000); return;|' /usr/share/novnc/vnc_lite.html 2>/dev/null || true
sudo sed -i 's|status("Disconnected");|status("Reconnecting..."); setTimeout(function(){location.reload();},2000); return;|' /usr/share/novnc/vnc_lite.html 2>/dev/null || true

# Openbox / tint2 config
sudo mkdir -p /etc/xdg/openbox
mkdir -p ~/.config/tint2
sudo ln -sf "$PWD/.devcontainer/rc.xml"    /etc/xdg/openbox/rc.xml
ln -sf "$PWD/.devcontainer/tint2rc" ~/.config/tint2/tint2rc
sudo ln -sf "$PWD/.devcontainer/xterm.desktop" /usr/share/applications/xterm.desktop

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

# SLAM/Nav2 packages for host-side navigation practice
sudo apt-get install -y --no-install-recommends \
  ros-jazzy-slam-toolbox \
  ros-jazzy-cartographer-ros \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-nav2-rviz-plugins \
  ros-jazzy-rviz2 \
  ros-jazzy-tf2-tools \
  ros-jazzy-rqt-tf-tree \
  ros-jazzy-rqt-graph \
  ros-jazzy-teleop-twist-keyboard

# Prevent automatic package upgrades (lock installed versions)
sudo apt-mark hold $(dpkg -l | grep -E '^ii  (ros-jazzy|gz-|libgz-)' | awk '{print $2}') 2>/dev/null || true
sudo sed -i 's|APT::Periodic::Unattended-Upgrade "1"|APT::Periodic::Unattended-Upgrade "0"|' /etc/apt/apt.conf.d/20auto-upgrades 2>/dev/null || true

# pip install
# Set pip to allow breaking system packages
pip3 config set global.break-system-packages true

# Pin numpy<2 globally (cv_bridge C++ ABI requires numpy 1.x)
sudo mkdir -p /etc/pip
echo 'numpy<2' | sudo tee /etc/pip/constraints.txt > /dev/null
echo 'PIP_CONSTRAINT=/etc/pip/constraints.txt' | sudo tee -a /etc/environment > /dev/null
export PIP_CONSTRAINT=/etc/pip/constraints.txt

# physicar-python & physicar-sim
pip3 install 'physicar~=1.0'
git submodule update --init .devcontainer/physicar-sim
git submodule update --init .devcontainer/physicar-ros
rm -rf .git .gitignore .gitmodules

pip3 install --no-cache-dir \
  flask flask-cors pyyaml requests \
  python-multipart \
  setuptools==70.0.0 2>/dev/null || true

# /opt/physicar directory
sudo mkdir -p /opt/physicar
echo -e "SIM=true" | sudo tee /opt/physicar/.env > /dev/null

# nginx config
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf "$PWD/.devcontainer/nginx.conf" /etc/nginx/sites-enabled/physicar

# supervisord log directory permissions
sudo mkdir -p /var/log/supervisor
sudo chown -R $(whoami) /var/log/supervisor

# Script execute permissions
chmod +x "$PWD/.devcontainer/"*.sh

# Allow nginx (www-data) to traverse /home/physicar
chmod o+x "$HOME"

# ~/.bashrc environment setup
cat >> ~/.bashrc << 'EOF'

# physicar
export DISPLAY=:1
export GZ_PARTITION=physicar
export GZ_CONFIG_PATH=/usr/share/gz
export FASTRTPS_DEFAULT_PROFILES_FILE=~/physicar_ws/.devcontainer/physicar-ros/fastdds-lo.xml
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
source /opt/ros/jazzy/setup.bash
source ~/physicar_ws/install/setup.bash 2>/dev/null || true
eval "$(register-python-argcomplete ros2)"
eval "$(register-python-argcomplete colcon)"
EOF

# physicar-myapp
sudo mkdir -p /opt/physicar/myapp
sudo chown -R physicar:physicar /opt/physicar/myapp

# Install flask & ultralytics for the host physicar user so the student app can use them immediately.
sudo -u physicar python3 -m pip install --break-system-packages --user 'flask~=3.1' 'flask-cors~=4.0' 'ultralytics~=8.4' 'numpy<2'

# Pull physicar sim v1 Docker image
docker pull physicar/sim:1

# Initial build - start container and wait for build to complete
echo "[onCreate] Starting initial build..."
bash "$PWD/.devcontainer/physicar.sh"
while ! docker logs physicar 2>&1 | grep -q "Build succeeded\|launch"; do sleep 5; done
echo "[onCreate] Initial build complete"

echo "[onCreate] Complete"
