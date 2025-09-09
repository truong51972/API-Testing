#!/bin/bash

CURRENT_PATH=$(pwd)

# Get the model name from the first argument
MODEL_NAME="$1"
# Remove './models/' prefix if present
MODEL_NAME="${MODEL_NAME#./models/}"
MODEL_NAME="${MODEL_NAME#/models/}"

shift

VOLUME_MOUNT="$CURRENT_PATH/models/"
OUT_TYPE="f16"

while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
        --volume-mount)
            VOLUME_MOUNT="$2"
            shift # skip next value since it's been used
            ;;
        --out-type)
            OUT_TYPE="$2"
            shift
            ;;
        *)
            echo "Unknown option: $key"
            exit 1
            ;;
    esac
    shift # skip current tag
done

if [ -d "$VOLUME_MOUNT" ]; then
    echo "'$VOLUME_MOUNT' exists!"
else
    echo "'$VOLUME_MOUNT' does not exist!"
    echo "Checking parent directory..."
    PARENT_PATH=$(dirname "$CURRENT_PATH")
    VOLUME_MOUNT="$PARENT_PATH/models/"

    if [ -d "$VOLUME_MOUNT" ]; then
        echo "'$VOLUME_MOUNT' exists!"
    else
        echo "'$VOLUME_MOUNT' does not exist!"
        exit 1
    fi
fi

echo
echo "---------------------------------------------------------------------"
echo

docker run --rm -v $VOLUME_MOUNT:/models \
    ghcr.io/ggml-org/llama.cpp:full \
    --convert /models/$MODEL_NAME \
    --outfile /models/$MODEL_NAME/model.gguf \
    --outtype $OUT_TYPE