#!/bin/bash
# ---------------------------------------------------------------------------
# restart_n8n.sh — יוצר מחדש את קונטיינר ה-n8n עם קונפיגורציה מלאה.
#
# NODE_FUNCTION_ALLOW_BUILTIN=crypto הוא קריטי: ה-sandbox של צמתי Code חוסם
# כברירת מחדל את כל מודולי Node המובנים. בלעדיו נוד "Verify Request" נכשל
# עם "Module 'crypto' is disallowed" ואימות חתימת ה-HMAC לא יכול לרוץ.
# ---------------------------------------------------------------------------
set -euo pipefail

SECRET_FILE=/etc/n8n-webhook-secret
if [ ! -f "$SECRET_FILE" ]; then
  openssl rand -hex 32 | sudo tee "$SECRET_FILE" >/dev/null
  sudo chmod 600 "$SECRET_FILE"
fi
GH_SECRET=$(sudo cat "$SECRET_FILE")

PUBLIC_URL="http://35.193.190.149:5678"
if [ -f /etc/n8n-public-url ]; then
  PUBLIC_URL=$(sudo cat /etc/n8n-public-url)
fi

echo "== recreating n8n container =="
sudo docker rm -f n8n >/dev/null 2>&1 || true
sudo docker run -d \
  --name n8n \
  --restart unless-stopped \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=35.193.190.149 \
  -e N8N_PORT=5678 \
  -e N8N_PROTOCOL=http \
  -e N8N_WEBHOOK_URL="${PUBLIC_URL}/" \
  -e GENERIC_TIMEZONE=Asia/Jerusalem \
  -e TZ=Asia/Jerusalem \
  -e N8N_DIAGNOSTICS_ENABLED=false \
  -e NODE_FUNCTION_ALLOW_BUILTIN=crypto \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  -e GITHUB_WEBHOOK_SECRET="$GH_SECRET" \
  docker.n8n.io/n8nio/n8n:latest >/dev/null

echo "waiting for n8n..."
for i in $(seq 1 90); do
  if curl -fsS -o /dev/null http://127.0.0.1:5678/healthz 2>/dev/null; then
    echo "n8n healthy after ${i}s"
    break
  fi
  sleep 1
done

echo "waiting for workflow activation..."
for i in $(seq 1 60); do
  if sudo docker logs n8n 2>&1 | grep -q 'Activated workflow'; then
    echo "workflow activated after ${i}s"
    exit 0
  fi
  sleep 1
done

echo "WARNING: activation not seen in logs"
sudo docker logs --tail 20 n8n
