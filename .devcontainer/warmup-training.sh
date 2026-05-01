#!/bin/bash

DRFC_DIR="$HOME/physicar_ws/.devcontainer/deepracer-for-cloud"
sed -i "s|^DR_LOCAL_S3_MODEL_PREFIX=.*|DR_LOCAL_S3_MODEL_PREFIX=models/_warmup_model|" "$DRFC_DIR/run.env"
sed -i "s|^DR_LOCAL_S3_PRETRAINED=.*|DR_LOCAL_S3_PRETRAINED=False|" "$DRFC_DIR/run.env"
source "$DRFC_DIR/bin/activate.sh" 2>/dev/null
dr-upload-custom-files
dr-start-training -q -w
sleep 60
dr-stop-training 2>/dev/null || true
sleep 10
aws $DR_LOCAL_PROFILE_ENDPOINT_URL s3 rm --recursive "s3://$DR_LOCAL_S3_BUCKET/models/_warmup_model" 2>/dev/null || true