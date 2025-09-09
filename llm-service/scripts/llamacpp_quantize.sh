#!/bin/bash

CURRENT_PATH=$(pwd)

# Get the model name from the first argument
MODEL_NAME="$1"
# Remove './models/' prefix if present
MODEL_NAME="${MODEL_NAME#./models/}"
MODEL_NAME="${MODEL_NAME#/models/}"

shift

VOLUME_MOUNT="$CURRENT_PATH/models/"
IS_VOLUME_MOUNT_SET=false

GGUF_MODEL_NAME="model"
IS_GGUF_MODEL_NAME_SET=false

QUANTIZATION_METHOD="q4_k_m"

while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
        --volume-mount)
            VOLUME_MOUNT="$2"
            IS_VOLUME_MOUNT_SET=true
            shift # skip next value since it's been used
            ;;
        --model-gguf-name)
            GGUF_MODEL_NAME="$2"
            shift
            ;;
        --quantization-method)
            QUANTIZATION_METHOD="$2"
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
    if [ "$IS_VOLUME_MOUNT_SET" = true ]; then
        exit 1
    fi
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

GGUF_MODEL_PATH="$MODEL_NAME/$GGUF_MODEL_NAME.gguf"

if [ -f "$VOLUME_MOUNT$GGUF_MODEL_PATH" ]; then
    echo "'$VOLUME_MOUNT$GGUF_MODEL_PATH' exists!"
else
    echo "'$VOLUME_MOUNT$GGUF_MODEL_PATH' does not exist!"
    exit 1
fi

QUANTIZED_GGUF_MODEL_PATH="$MODEL_NAME/$GGUF_MODEL_NAME.$QUANTIZATION_METHOD.gguf"

echo
echo "---------------------------------------------------------------------"
echo

docker run --rm -v $VOLUME_MOUNT:/models \
    ghcr.io/ggml-org/llama.cpp:full \
    --quantize /models/$GGUF_MODEL_PATH /models/$QUANTIZED_GGUF_MODEL_PATH \
    $QUANTIZATION_METHOD \
    10 \