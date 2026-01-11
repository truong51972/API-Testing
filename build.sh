cd agent-service
./scripts/build_image.sh --forge_build
cd ..

cd frontend
./deploy/scripts/run.sh build
cd ..
