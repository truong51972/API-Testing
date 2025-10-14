#!/bin/bash

CURRENT_PATH=$(pwd)

# Get the model name from the first argument
MODEL_NAME="$1"
# Remove './models/' prefix if present
MODEL_NAME="${MODEL_NAME#./models/}"
MODEL_NAME="${MODEL_NAME#/models/}"
MODEL_NAME="${MODEL_NAME#models/}"

shift

VOLUME_MOUNT="$CURRENT_PATH/models/"
OUT_TYPE="f16"
QUANTIZATION_METHOD="q4_k_m"
DO_QUANTIZATION=false

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
        --quantize)
            DO_QUANTIZATION=true
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

echo "Converting model '$MODEL_NAME' to gguf format..."
docker run -u $(id -u):$(id -g) --rm -v $VOLUME_MOUNT:/models \
    ghcr.io/ggml-org/llama.cpp:full \
    --convert /models/$MODEL_NAME \
    --outfile /models/$MODEL_NAME/model.gguf \
    --outtype $OUT_TYPE \
    > /dev/null 2>&1 # Suppress output
    
echo "Done!"
echo

if [ "$DO_QUANTIZATION" = true ]; then
    echo "Quantizing model '$MODEL_NAME' with method '$QUANTIZATION_METHOD'..."
    docker run -u $(id -u):$(id -g) --rm -v $VOLUME_MOUNT:/models \
        ghcr.io/ggml-org/llama.cpp:full \
        --quantize /models/$MODEL_NAME/model.gguf \
        /models/$MODEL_NAME/model-$QUANTIZATION_METHOD.bin \
        $QUANTIZATION_METHOD \
        10 \
        > /dev/null 2>&1 # Suppress output

    if [ $? -ne 0 ]; then
        echo "Quantization failed!"
        exit 1
    fi
    echo "Done!"
    echo


    echo "Replacing original model with quantized model..."
    rm $VOLUME_MOUNT$MODEL_NAME/model.gguf
    mv $VOLUME_MOUNT$MODEL_NAME/model-$QUANTIZATION_METHOD.bin $VOLUME_MOUNT$MODEL_NAME/model.gguf
    echo "Done!"
    echo

    MODEL_NAME="$MODEL_NAME/model-$QUANTIZATION_METHOD.bin"
else
    echo "Converting model '$MODEL_NAME' to gguf format..."
fi

