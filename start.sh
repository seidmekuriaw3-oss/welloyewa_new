#!/usr/bin/env bash
set -e

# Start Redis in the background (data persisted to /tmp/redis-data)
mkdir -p /tmp/redis-data
redis-server \
  --daemonize yes \
  --port 6379 \
  --bind 127.0.0.1 \
  --dir /tmp/redis-data \
  --save 900 1 \
  --save 300 10 \
  --save 60 10000 \
  --logfile /tmp/redis.log \
  --maxmemory 64mb \
  --maxmemory-policy allkeys-lru

echo "Redis started on 127.0.0.1:6379"

# Start the FastAPI app
exec uvicorn main:app --host 0.0.0.0 --port 5000 --proxy-headers --forwarded-allow-ips='*'
