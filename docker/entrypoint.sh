#!/bin/sh
set -eu
umask 077
mkdir -p /app/config /app/data
if [ ! -f /app/config/default.json ]; then
    cp /app/default-config.json /app/config/default.json
fi
exec "$@"
