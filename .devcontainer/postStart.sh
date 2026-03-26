#!/bin/bash

# Create app.physicar file with the Codespace URL for app access
(
sudo chattr -i app.physicar
echo "https://${CODESPACE_NAME}-8000.app.github.dev" > app.physicar
chmod 444 app.physicar
sudo chattr +i app.physicar
) 2>/dev/null &

# Start supervisord
if command -v supervisord &> /dev/null; then
    # Clean up existing processes
    pkill -f "supervisord.*supervisord.conf" 2>/dev/null || true
    sleep 1
    
    # Start supervisord with the specified configuration
    supervisord -c ~/physicar_ws/.devcontainer/supervisord.conf
    sleep 2
fi

