#!/bin/bash
# ---------------------------------------------------------------------------
# switch_to_caddy.sh — מעביר את n8n לכתובת הקבועה ומכבה את הטאנל הזמני.
#
# מפעיל מחדש את n8n, ולכן אין להריץ אותו בזמן שהערכה או הדגמה רצות.
# ---------------------------------------------------------------------------
set -euo pipefail

DOMAIN="35.193.190.149.sslip.io"

echo "== pointing n8n at the permanent URL =="
echo "https://${DOMAIN}" | sudo tee /etc/n8n-public-url >/dev/null
bash /tmp/restart_n8n.sh 2>&1 | tail -2

echo "== retiring the temporary cloudflare tunnel =="
sudo docker rm -f cloudflared >/dev/null 2>&1 || true

echo "== verifying =="
for i in $(seq 1 60); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://${DOMAIN}/healthz" || echo 000)
  if [ "$CODE" = "200" ]; then
    echo "HTTPS OK after ${i} checks"
    break
  fi
  sleep 2
done

echo
echo "running containers:"
sudo docker ps --format '  {{.Names}}\t{{.Status}}'
echo
echo "PUBLIC_HTTPS_URL=https://${DOMAIN}"
curl -s --max-time 10 "https://${DOMAIN}/healthz"; echo
