forge_build=$1

if docker image inspect agent-service:latest > /dev/null 2>&1; then
    if [ "$forge_build" != "--forge_build" ]; then
        exit 0
    fi
fi

docker build -t agent-service -f docker/Dockerfile .
