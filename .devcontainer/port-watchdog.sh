#!/bin/bash
# Port forwarding watchdog
# Periodically checks if Codespace port 80 forwarding is working.
# If the public URL returns HTTP/2 404, toggles visibility to recover.

CHECK_INTERVAL=10
PUBLIC_URL="https://${CODESPACE_NAME}-80.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/"

# Wait for the app to be ready on localhost:80
echo "[port-watchdog] Waiting for app on localhost:80..."
until curl -sf -o /dev/null http://localhost:80/; do
    sleep 3
done
echo "[port-watchdog] App is up. Starting port forwarding watchdog."

while true; do
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$PUBLIC_URL" 2>/dev/null)

    if [ "$HTTP_STATUS" = "404" ]; then
        echo "[port-watchdog] $(date '+%Y-%m-%d %H:%M:%S') HTTP 404 detected. Toggling port visibility to recover..."
        gh codespace ports visibility 80:public -c "$CODESPACE_NAME" 2>&1
        sleep 3
        gh codespace ports visibility 80:private -c "$CODESPACE_NAME" 2>&1
        echo "[port-watchdog] $(date '+%Y-%m-%d %H:%M:%S') Port visibility toggled."
    fi

    sleep "$CHECK_INTERVAL"
done