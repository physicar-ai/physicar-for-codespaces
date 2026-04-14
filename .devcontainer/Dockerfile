FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-24.04

# Create physicar user with sudo privileges
RUN useradd -m -s /bin/bash physicar && \
    echo "physicar ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    usermod -aG sudo physicar

USER physicar
WORKDIR /home/physicar