#!/bin/bash

# Kill any stale process holding port 8000
lsof -t -i :8000 | xargs -r kill -9 2>/dev/null
sleep 0.5

WORKSPACE="$HOME/physicar_ws"
PHYSICAR_PYTHON_DEV="$WORKSPACE/.devcontainer/physicar-python/src"
PHYSICAR_PYTHON_PKG="$(python3 -c 'import physicar, os; print(os.path.dirname(os.path.dirname(physicar.__file__)))' 2>/dev/null)"

RELOAD_DIR="${PHYSICAR_PYTHON_DEV}"
if [ ! -d "$RELOAD_DIR" ]; then
    pip3 install --upgrade 'physicar[codespaces-deepracer]' 2>/dev/null
    # deepracer-simapp-mount follows the latest v1.* TAG (not main HEAD), so
    # commits ship to students only when a release tag is pushed — same policy
    # as the device updater.
    SIMAPP_DIR="$WORKSPACE/.devcontainer/deepracer-simapp-mount"
    git -C "$SIMAPP_DIR" fetch --tags 2>/dev/null
    SIMAPP_TAG=$(git -C "$SIMAPP_DIR" tag -l 'v1.*' --sort=-v:refname | head -1)
    [ -n "$SIMAPP_TAG" ] && git -C "$SIMAPP_DIR" -c advice.detachedHead=false checkout -f "$SIMAPP_TAG" 2>/dev/null
    RELOAD_DIR="$PHYSICAR_PYTHON_PKG"
fi

exec /usr/bin/python3 -m uvicorn physicar.codespaces.deepracer.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir "$RELOAD_DIR" \
    --reload-include '*.yaml' \
    --reload-include '*.html' \
    --reload-include '*.js' \
    --reload-include '*.css' \
    --timeout-keep-alive 0 \
    --timeout-graceful-shutdown 0
