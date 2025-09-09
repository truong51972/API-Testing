#!/bin/bash
# Get the model name from the first argument
MODEL_NAME="$1"
# Remove './models/' prefix if present
MODEL_NAME="${MODEL_NAME#./models/}"
MODEL_NAME="${MODEL_NAME#/models/}"

shift

hf download "$MODEL_NAME" --local-dir "./models/$MODEL_NAME"