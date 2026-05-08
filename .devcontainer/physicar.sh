#!/usr/bin/env bash

PHYSICAR_DIR="/opt/physicar"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PHYSICAR_DIR/.env" 2>/dev/null || true
IS_DEV=false
[[ "$DEV" == "true" || "$DEV" == "1" ]] && IS_DEV=true

COMPOSE_FILE="$SCRIPT_DIR/physicar-ros/docker-compose.yml"

if ! $IS_DEV; then
    pip3 install --upgrade physicar 2>/dev/null
    
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

export TZ="$(cat /etc/timezone 2>/dev/null || echo UTC)"

docker compose -f "$COMPOSE_FILE" --profile sim up -d 2>/dev/null

# Auto-update image (every 3 minutes, applied on next physicar.sh run)
(
  while true; do
    sleep 180
    docker compose -f "$COMPOSE_FILE" --profile sim pull 2>/dev/null || true
  done
) &