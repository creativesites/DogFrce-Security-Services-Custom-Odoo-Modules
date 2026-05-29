#!/bin/sh

if command -v docker >/dev/null 2>&1; then
  DOCKER_BIN=$(command -v docker)
elif [ -x /Applications/Docker.app/Contents/Resources/bin/docker ]; then
  DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker
else
  echo "docker is not installed or not on PATH"
  echo "Install or start Docker Desktop: https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if [ -x /Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose ]; then
  COMPOSE_BIN=/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose
  export DOCKER_CONFIG=${DOCKER_CONFIG:-"$HOME/.docker"}
  export PATH="/Applications/Docker.app/Contents/Resources/bin:/Applications/Docker.app/Contents/Resources/cli-plugins:$PATH"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BIN=$(command -v docker-compose)
fi
