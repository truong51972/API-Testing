#!/bin/bash
# Get the model name from the first argument

IMAGE_NAME="llm-service"

./scripts/build_image.sh

MODEL_NAME="$1"
# Remove './models/' prefix if present
MODEL_NAME="${MODEL_NAME#./models/}"
MODEL_NAME="${MODEL_NAME#/models/}"
MODEL_NAME="${MODEL_NAME#models/}"

CURRENT_PATH=$(pwd)
VOLUME_MOUNT="$CURRENT_PATH/models/"

shift

docker run -u $(id -u):$(id -g) --rm -v $VOLUME_MOUNT:/app/models \
    $IMAGE_NAME \
    hf download "$MODEL_NAME" --local-dir "models/$MODEL_NAME"