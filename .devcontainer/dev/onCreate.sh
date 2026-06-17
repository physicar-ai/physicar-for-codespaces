#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
#  Codespaces onCreate (DEV) — dev extras on top of prebuilt image
# ═══════════════════════════════════════════════════════════════════════════════

PHYSICAR_WS=/opt/physicar

# DEV flag in .env
echo "DEV=true" >> "$PHYSICAR_WS/userdata/.env"

# physicar-python editable install (for development, overrides PyPI version)
git clone https://github.com/physicar-ai/physicar-python.git "$PHYSICAR_WS/src/physicar-python"
pip3 install --break-system-packages -e "$PHYSICAR_WS/src/physicar-python"

echo "[onCreate DEV] Complete"
