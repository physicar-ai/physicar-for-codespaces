#!/bin/bash

# The tunnel gate token (/tmp/pc-token) and the app.physicar bookmark are owned
# entirely by app-browser.sh: it seeds both empty on start, then rewrites them
# with the per-session token and token-gated tunnel URL.

# Start supervisord
if command -v supervisord &> /dev/null; then
    # Clean up existing processes
    pkill -f "supervisord.*supervisord.conf" 2>/dev/null || true
    sleep 1
    
    # Start supervisord with the specified configuration
    supervisord -c ~/physicar_ws/.devcontainer/supervisord.conf
fi

