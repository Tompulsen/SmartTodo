#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
test -f .env || { echo "Missing deployment .env"; exit 1; }
mode="${1:-image}"
previous="$(docker inspect --format '{{.Image}}' smarttodo 2>/dev/null || true)"
case "$mode" in
    image)
        docker compose pull smarttodo
        ;;
    source)
        test -d repository/.git || { echo "Missing source checkout: repository"; exit 1; }
        test -z "$(git -C repository status --porcelain)" || {
            echo "Source checkout has local changes; update stopped."; exit 1;
        }
        git -C repository pull --ff-only origin main
        revision="$(git -C repository rev-parse HEAD)"
        docker build --pull -f repository/docker/Dockerfile \
            --build-arg "VCS_REF=$revision" -t "smarttodo:$revision" repository
        export SMARTTODO_IMAGE="smarttodo:$revision"
        ;;
    *)
        echo "Usage: sh update.sh [image|source]"
        exit 1
        ;;
esac
if docker compose up -d --wait --wait-timeout 120 smarttodo; then
    echo "SmartTodo is healthy."
else
    echo "Update failed; restoring the previous image."
    if [ -n "$previous" ]; then
        SMARTTODO_IMAGE="$previous" docker compose up -d --wait --wait-timeout 120 smarttodo
    fi
    exit 1
fi
