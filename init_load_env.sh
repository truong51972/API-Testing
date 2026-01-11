if [ -f "load_env.sh" ]; then
    rm load_env.sh
fi

touch load_env.sh
sudo chmod +x load_env.sh
nano load_env.sh

./load_env.sh