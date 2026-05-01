#!/usr/bin/env bash

PHYSICAR_DIR="/opt/physicar"
source "$PHYSICAR_DIR/.env" 2>/dev/null || true
IS_DEV=false
[[ "$DEV" == "true" || "$DEV" == "1" ]] && IS_DEV=true

IMAGE_NAME="physicar/sim:1"

if ! $IS_DEV; then
    pip3 install --upgrade 'physicar~='"$(python3 -c "import physicar; print(physicar.__version__)")" 2>/dev/null
    
    # Update submodules to latest tag within same major version (v1.*)
    for repo in physicar-sim physicar-ros; do
        dir="$WORKSPACE/.devcontainer/$repo"
        git -C "$dir" fetch --tags 2>/dev/null
        latest=$(git -C "$dir" tag -l 'v1.*' --sort=-v:refname | head -1)
        [[ -n "$latest" ]] && git -C "$dir" checkout "$latest" 2>/dev/null
    done
fi

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
    --network host \
    --ipc host \
    -v "$PHYSICAR_DIR:$PHYSICAR_DIR" \
    -v /home/physicar/physicar_ws/.devcontainer/physicar-ros:/root/ros2_ws/src/physicar-ros \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e TZ="$(cat /etc/timezone 2>/dev/null || echo UTC)" \
    -e DISPLAY=":1" \
    -e CODESPACE_NAME \
    "$IMAGE_NAME" \
    bash -c 'bash /root/ros2_ws/src/physicar-ros/entrypoint.sh || sleep infinity'
fi