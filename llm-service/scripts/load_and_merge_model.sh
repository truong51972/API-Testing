#!/bin/bash

CURRENT_PATH=$(pwd)

# Get the model name from the first argument
MODEL_NAME="$1"
# Remove './models/' prefix if present
MODEL_NAME="${MODEL_NAME#./models/}"
MODEL_NAME="${MODEL_NAME#/models/}"
MODEL_NAME="${MODEL_NAME#models/}"

shift

VOLUME_MOUNT_MODELS="$CURRENT_PATH/models/"
VOLUME_MOUNT_MODELFILES="$CURRENT_PATH/modelfiles/"

if [ -d "$VOLUME_MOUNT_MODELS$MODEL_NAME" ]; then
    echo "'$VOLUME_MOUNT_MODELS$MODEL_NAME' exists!"
else
    echo "'$VOLUME_MOUNT_MODELS$MODEL_NAME' does not exist!"
    exit 1
fi

MODEL_PATH="models/$MODEL_NAME"

docker run --rm --gpus all \
    -v $VOLUME_MOUNT_MODELS:/app/models \
    -v $VOLUME_MOUNT_MODELFILES:/app/modelfiles \
    llm-service \
    python load_and_merge_model.py "$MODEL_PATH"