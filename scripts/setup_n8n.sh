#!/bin/bash
# ---------------------------------------------------------------------------
# setup_n8n.sh — התקנה מחדש של n8n על ה-VM.
#
# הדיסק של המכונה אותחל ו-n8n נמחק ממנה. הסקריפט:
#   1. משדרג את Docker (הגרסה הישנה 20.10 לא יודעת לפרוס את שכבות
#      ה-image של n8n — "invalid tar header").
#   2. מרים את n8n עם volume קבוע ו-restart אוטומטי, כדי שהמערכת תשרוד
#      ריסטארט של המכונה.
# ---------------------------------------------------------------------------
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "== [1/4] removing legacy docker =="
sudo systemctl stop docker 2>/dev/null || true
sudo apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc >/dev/null 2>&1 || true

echo "== [2/4] adding docker official repo =="
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl gnupg >/dev/null
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

echo "== [3/4] installing docker-ce =="
sudo apt-get update -qq
sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
sudo systemctl enable --now docker
echo "docker server version: $(sudo docker version --format '{{.Server.Version}}')"

echo "== [4/4] starting n8n =="
sudo docker rm -f n8n 2>/dev/null || true
sudo docker volume create n8n_data >/dev/null
sudo docker pull -q docker.n8n.io/n8nio/n8n:latest

# סוד משותף לאימות חתימת ה-webhook של GitHub (נוד "Verify Request").
# נוצר פעם אחת ונשמר על המכונה; אינו נכתב ללוגים.
SECRET_FILE=/etc/n8n-webhook-secret
if [ ! -f "$SECRET_FILE" ]; then
  openssl rand -hex 32 | sudo tee "$SECRET_FILE" >/dev/null
  sudo chmod 600 "$SECRET_FILE"
fi
GH_SECRET=$(sudo cat "$SECRET_FILE")

sudo docker run -d \
  --name n8n \
  --restart unless-stopped \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST=35.193.190.149 \
  -e N8N_PORT=5678 \
  -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL=http://35.193.190.149:5678/ \
  -e GENERIC_TIMEZONE=Asia/Jerusalem \
  -e TZ=Asia/Jerusalem \
  -e N8N_RUNNERS_ENABLED=true \
  -e N8N_DIAGNOSTICS_ENABLED=false \
  -e GITHUB_WEBHOOK_SECRET="$GH_SECRET" \
  docker.n8n.io/n8nio/n8n:latest >/dev/null

echo "waiting for n8n to listen on 5678..."
for i in $(seq 1 60); do
  if curl -fsS -o /dev/null http://127.0.0.1:5678/healthz 2>/dev/null; then
    echo "n8n is UP after ${i}s"
    exit 0
  fi
  sleep 1
done

echo "n8n did NOT come up in 60s. last logs:"
sudo docker logs --tail 40 n8n
exit 1
