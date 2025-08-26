#!/bin/bash
export COMPOSE_PROJECT_NAME="agent-service"
export PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Xác định file compose
COMPOSE_FILE="$PROJECT_ROOT/deploy/compose/docker-compose.yml"
OVERRIDE_FILE="$PROJECT_ROOT/deploy/compose/docker-compose.override.yml"

# Xử lý tag dev khi chạy
TAG="$1"

if [ "$TAG" == "dev" ] && [ -f "$OVERRIDE_FILE" ]; then
    echo "Run server (dev)"
    docker compose -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" up -d
elif [ "$TAG" == "stop" ]; then
    echo "Stop server"
    docker compose -f "$COMPOSE_FILE" down
else
    echo "Run server"
    docker compose -f "$COMPOSE_FILE" up -d
fi