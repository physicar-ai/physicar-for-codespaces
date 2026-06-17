FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN useradd -m -s /bin/bash physicar && \
    echo "physicar ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    usermod -aG sudo physicar

ENV PHYSICAR_WS=/opt/physicar

RUN mkdir -p "$PHYSICAR_WS/src" && chown -R physicar:physicar "$PHYSICAR_WS"

RUN git clone https://github.com/physicar-ai/physicar-ros.git "$PHYSICAR_WS/src/physicar-ros" && \
    git clone https://github.com/physicar-ai/physicar-sim.git "$PHYSICAR_WS/src/physicar-sim"

RUN bash "$PHYSICAR_WS/src/physicar-ros/deploy/install-sim.sh"

USER physicar
WORKDIR /home/physicar/physicar_ws