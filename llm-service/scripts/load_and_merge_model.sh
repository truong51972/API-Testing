#!/bin/bash

CURRENT_PATH=$(pwd)

# Get the model name from the first argument
MODEL_NAME="$1"
shift

VOLUME_MOUNT="$CURRENT_PATH/models/"

if [ -d "$VOLUME_MOUNT$MODEL_NAME" ]; then
    echo "'$VOLUME_MOUNT$MODEL_NAME' exists!"
else
    echo "'$VOLUME_MOUNT$MODEL_NAME' does not exist!"
    exit 1
fi

MODEL_PATH="models/$MODEL_NAME"

docker run --rm --gpus all -v $VOLUME_MOUNT:/app/models \
    load_and_merge_model \
    "$MODEL_PATH"