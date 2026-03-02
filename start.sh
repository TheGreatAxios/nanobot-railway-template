#!/bin/bash
set -e

mkdir -p /data/.nanobot/workspace
mkdir -p /data/.nanobot/sessions
mkdir -p /data/.nanobot/cron

# Initialize nanobot config if it doesn't exist
if [ ! -f /data/.nanobot/config.json ]; then
  echo '{}' > /data/.nanobot/config.json
  echo "Created initial config.json"
fi

exec python /app/server.py
