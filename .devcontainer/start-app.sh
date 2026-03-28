#!/bin/bash

WORKSPACE="$HOME/physicar_ws"
PHYSICAR_PYTHON_DEV="$WORKSPACE/.devcontainer/physicar-python/src"
PHYSICAR_PYTHON_PKG="$(python3 -c 'import physicar, os; print(os.path.dirname(os.path.dirname(physicar.__file__)))' 2>/dev/null)"

RELOAD_DIR="${PHYSICAR_PYTHON_DEV}"
if [ ! -d "$RELOAD_DIR" ]; then
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
