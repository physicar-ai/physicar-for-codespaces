#!/usr/bin/env bash

source /opt/physicar/.env 2>/dev/null || true
IS_DEV=false
[[ "$DEV" == "true" || "$DEV" == "1" ]] && IS_DEV=true

if $IS_DEV; then
    IMAGE_NAME="physicar/device-dev:1"
else
    pip3 install --upgrade 'physicar~='"$(python3 -c "import physicar; print(physicar.__version__)")" 2>/dev/null
    git -C "$WORKSPACE/.devcontainer/physicar-sim" pull 2>/dev/null
    git -C "$WORKSPACE/.devcontainer/physicar-ros" pull 2>/dev/null
    IMAGE_NAME="physicar/device:1"

# ────────────────── Docker Container ──────────────────

if ! $IS_DEV; then
  docker pull "$IMAGE_NAME" &>/dev/null
    if docker inspect physicar &>/dev/null; then
      LATEST_ID=$(docker inspect --format='{{.Id}}' "$IMAGE_NAME" 2>/dev/null || true)
      CURRENT_ID=$(docker inspect --format='{{.Image}}' physicar 2>/dev/null || true)
      if [[ -n "$LATEST_ID" && "$LATEST_ID" != "$CURRENT_ID" ]]; then
        docker rm -f physicar &>/dev/null
      fi
    fi
fi

# Run container
if ! docker inspect physicar &>/dev/null; then
  docker run -d \
    --name physicar \
    --restart unless-stopped \
    --privileged \
    --network host \
    --pid host \
    --ipc host \
    --cgroupns host \
    --userns host \
    -v "$PHYSICAR_DIR:$PHYSICAR_DIR" \
    -v /home/physicar/physicar_ws/.devcontainer/physicar-ros:/root/ros2_ws/src/physicar-ros \
    -v /var/run:/var/run \
    -v /dev:/dev \
    -v /sys:/sys \
    -v /media:/media:rslave \
    -v /mnt:/mnt:rslave \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e TZ="$(cat /etc/timezone 2>/dev/null || echo UTC)" \
    -e DISPLAY=":1" \
    -e ROS_LOCALHOST_ONLY=1 \
    "$IMAGE_NAME" \
    bash -c 'bash /root/ros2_ws/src/physicar-ros/entrypoint.sh || sleep infinity'
fi