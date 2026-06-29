#!/bin/bash
# Ensure the Docker daemon is up. Run by supervisord ([program:docker]) before the
# services that depend on Docker (minio, app, eval).
#
# On a Codespace stop->start the docker-in-docker daemon (containerd) sometimes
# fails to come back cleanly ("timeout waiting for containerd to start"), which
# breaks minio/app/eval. This heals it. No-op when Docker is already running.
set -u

if docker info > /dev/null 2>&1; then
    echo "[docker-ensure] Docker already running."
    exit 0
fi

echo "[docker-ensure] Docker daemon not running -- (re)starting via dind init..."
# dind feature init: removes stale PID files and (re)starts dockerd.
if [ -x /usr/local/share/docker-init.sh ]; then
    /usr/local/share/docker-init.sh true > /tmp/docker-init.log 2>&1 || true
fi

# Wait up to ~60s for the daemon to accept connections.
for _ in $(seq 1 30); do
    if docker info > /dev/null 2>&1; then
        echo "[docker-ensure] Docker is up."
        exit 0
    fi
    sleep 2
done

echo "[docker-ensure] WARNING: Docker did not become ready in time." >&2
exit 1
