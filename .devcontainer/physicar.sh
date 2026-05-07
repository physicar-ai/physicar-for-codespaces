#!/usr/bin/env bash

PHYSICAR_DIR="/opt/physicar"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PHYSICAR_DIR/.env" 2>/dev/null || true
IS_DEV=false
[[ "$DEV" == "true" || "$DEV" == "1" ]] && IS_DEV=true

IMAGE_NAME="physicar/sim:1"

if ! $IS_DEV; then
    pip3 install --upgrade 'physicar~='"$(python3 -c "import physicar; print(physicar.__version__)")" 2>/dev/null
    
    # Update physicar-sim to latest tag (v1.*)
    # (physicar-ros is updated inside the Docker container via updater.sh)
    for repo in physicar-sim; do
        dir="$SCRIPT_DIR/$repo"
        [[ -d "$dir/.git" ]] || continue

        # Clean stale git locks (recovery from power loss / kill -9)
        for lock in "$dir/.git/index.lock" "$dir/.git/HEAD.lock"; do
            if [[ -f "$lock" ]]; then
                local_age=$(( $(date +%s) - $(stat -c %Y "$lock" 2>/dev/null || echo 0) ))
                (( local_age > 300 )) && rm -f "$lock"
            fi
        done

        # Fetch with timeout — skip on network failure
        timeout 30 git -c gc.auto=0 -C "$dir" fetch --tags 2>/dev/null || continue

        latest=$(git -C "$dir" tag -l 'v1.*' --sort=-v:refname | head -1)
        [[ -z "$latest" ]] && continue

        # Skip if already at this exact commit
        current=$(git -C "$dir" rev-parse HEAD 2>/dev/null)
        target=$(git -C "$dir" rev-parse "$latest^{}" 2>/dev/null)
        [[ "$current" == "$target" ]] && continue

        # Force checkout: overwrite tracked files, keep untracked/.gitignore'd
        echo "[physicar] Updating $repo → $latest"
        git -c gc.auto=0 -c advice.detachedHead=false -C "$dir" checkout -f "$latest" 2>/dev/null
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

# Start container if not running (handles Exited state after Codespaces suspend/resume)
if ! docker ps --filter name=physicar --filter status=running -q | grep -q .; then
  if docker inspect physicar &>/dev/null; then
    # Container exists but stopped — just restart (preserves built workspace)
    docker start physicar &>/dev/null
  else
    docker run -d \
      --name physicar \
      --restart unless-stopped \
      --network host \
      --ipc host \
      -v "$PHYSICAR_DIR:$PHYSICAR_DIR" \
      -v "$SCRIPT_DIR/physicar-ros:/root/ros2_ws/src/physicar-ros" \
      -v /tmp/.X11-unix:/tmp/.X11-unix \
      -e TZ="$(cat /etc/timezone 2>/dev/null || echo UTC)" \
      -e DISPLAY=":1" \
      -e CODESPACE_NAME \
      "$IMAGE_NAME" \
      bash -c 'bash /root/ros2_ws/src/physicar-ros/entrypoint.sh || sleep infinity'
  fi
fi