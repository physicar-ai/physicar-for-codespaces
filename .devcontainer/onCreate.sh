#!/usr/bin/env bash
set -euo pipefail

# Runs once at workspace creation (and during Codespaces prebuild).
# cwd is the workspace folder (/home/physicar/physicar_ws).
#
# Strip git/GitHub metadata so the student workspace stays clean.
rm -rf .git .github .gitignore .gitattributes
