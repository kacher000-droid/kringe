#!/usr/bin/env bash
cd "$(dirname "$0")"
termux-wake-lock 2>/dev/null || true

PORT=$(grep -E '^PORT=' .env | cut -d= -f2)
PORT=${PORT:-8000}

pkill -f "cloudflared tunnel" 2>/dev/null || true
pkill -f "nokey@localhost.run" 2>/dev/null || true

URL=""
TUN_PID=""
trap '[ -n "$TUN_PID" ] && kill $TUN_PID 2>/dev/null' EXIT

echo "Пробую туннель localhost.run..."
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes \
    -R "80:localhost:$PORT" nokey@localhost.run > tunnel.log 2>&1 &
TUN_PID=$!

for i in $(seq 1 25); do
  URL=$(grep -o 'https://[a-zA-Z0-9-]*\.lhr\.life' tunnel.log | head -n1)
  [ -n "$URL" ] && break
  sleep 1
done

if [ -z "$URL" ]; then
  kill $TUN_PID 2>/dev/null
  echo "localhost.run не ответил, пробую Cloudflare..."
  cloudflared tunnel --protocol http2 --url "http://localhost:$PORT" --no-autoupdate > tunnel.log 2>&1 &
  TUN_PID=$!
  for i in $(seq 1 40); do
    URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -n1)
    [ -n "$URL" ] && break
    sleep 1
  done
fi

if [ -z "$URL" ]; then
  echo "Не удалось получить адрес туннеля, смотри tunnel.log"
  exit 1
fi

echo "Mini App: $URL"
export WEBAPP_URL="$URL"
python main.py
