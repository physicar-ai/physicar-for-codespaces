#!/bin/bash

# Install the Physicar browser extension and open app
(code --install-extension /home/physicar/physicar_ws/.devcontainer/physicar-browser-ext.vsix > /dev/null 2>&1 && sleep 1 && code app.physicar) &

# Keep Alive (only while a training/evaluation job is running)
# Codespaces idles after 30min of no terminal activity. Print a heartbeat
# every 4min, but only when DeepRacer training/eval containers are up.
(
while true; do
    sleep 240
    names=$(docker ps --format '{{.Names}}' 2>/dev/null)
    train_ids=$(echo "$names" | sed -nE 's/^deepracer-([0-9]+)-robomaker-[0-9]+$/\1/p' | sort -un)
    eval_ids=$(echo "$names" | sed -nE 's/^deepracer-eval-([0-9]+)-robomaker-[0-9]+$/\1/p' | sort -un)
    lines=()
    for id in $train_ids; do
        [ -n "$id" ] && lines+=("training run_id=$id")
    done
    for id in $eval_ids; do
        [ -n "$id" ] && lines+=("evaluation run_id=$id")
    done
    if [ ${#lines[@]} -gt 0 ]; then
        echo "[Codespace keep-alive] $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
        for l in "${lines[@]}"; do
            echo "  - $l"
        done
    fi
done
)&
