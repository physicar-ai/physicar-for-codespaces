#!/bin/bash

# Install essential packages
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl gnupg2 lsb-release software-properties-common apt-transport-https ca-certificates locales \
    xvfb x11vnc novnc websockify fluxbox xterm supervisor net-tools lxde-core lxterminal \
    jq python3-pip python3-boto3 docker-compose tmux ffmpeg gh # s3fs 

# pip install
# Set pip to allow breaking system packages
pip3 config set global.break-system-packages true

# Install AWS CLI
pip3 install awscli

# Install cloudflared (for the token-gated Cloudflare Quick Tunnel; app-browser.sh)
CF_ARCH="$(dpkg --print-architecture)"
sudo curl -fsSL -o /usr/local/bin/cloudflared \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
sudo chmod +x /usr/local/bin/cloudflared

# physicar-python & deepracer-simapp-mount
pip3 install physicar[codespaces-deepracer]
git clone https://github.com/physicar-ai/deepracer-simapp-mount.git .devcontainer/deepracer-simapp-mount

# Clean up root git files (not needed for end users)
rm -rf .git .gitignore

# Pull deepracer-simapp Docker image
docker pull physicar/deepracer-simapp

# deepracer-for-cloud setup
$PWD/.devcontainer/deepracer-for-cloud/bin/init.sh -c local -a cpu -s compose

#### sub workers cp
for i in $(seq 2 7); do
    cp -f "$PWD/.devcontainer/deepracer-for-cloud/defaults/template-worker.env" "$PWD/.devcontainer/deepracer-for-cloud/worker-$i.env"
done

# MinIO
cat <<'EOF' > ~/.aws/credentials
[minio]
aws_access_key_id = physicar
aws_secret_access_key = physicar
EOF

source $PWD/.devcontainer/deepracer-for-cloud/bin/activate.sh --minio 2>/dev/null
sleep 5

# warmup training
bash "$PWD/.devcontainer/warmup-training.sh"

echo "[onCreate] Complete"


