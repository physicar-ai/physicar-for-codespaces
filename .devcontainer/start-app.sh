#!/bin/bash

WORKSPACE="$HOME/physicar_ws"
PHYSICAR_PYTHON="$WORKSPACE/.devcontainer/physicar-python"

if [ ! -d "$PHYSICAR_PYTHON/src" ]; then
    pip3 install --upgrade physicar[codespaces-deepracer]
fi

exec /usr/bin/python3 -m uvicorn physicar.codespaces.deepracer.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir "$PHYSICAR_PYTHON/src" \
    --reload-include '*.yaml' \
    --reload-include '*.html' \
    --reload-include '*.js' \
    --reload-include '*.css' \
    --timeout-keep-alive 0 \
    --timeout-graceful-shutdown 0