#!/bin/bash

# Install the Physicar browser extension and open app
(code --install-extension /home/physicar/physicar_ws/.devcontainer/physicar-browser-ext.vsix > /dev/null 2>&1 && sleep 1 && code app.physicar) &