#!/bin/bash
# ---------------------------------------------------------------------------
# setup_caddy.sh — HTTPS קבוע ל-n8n באמצעות Caddy ו-Let's Encrypt.
#
# מחליף את Cloudflare Tunnel, שכתובתו אקראית ומשתנה בכל הפעלה מחדש — סיכון
# מיותר לקישור שאמור לעבוד ביום ההגשה.
#
# הדומיין: 35.193.190.149.sslip.io
# sslip.io הוא שירות DNS שמתרגם כתובת IP שמופיעה בשם המארח לאותו IP. כך יש
# שם מארח אמיתי שאפשר להנפיק עבורו תעודה, בלי לרכוש דומיין.
#
# דורש שפורטים 80 ו-443 יהיו פתוחים ב-firewall: 80 לאתגר ה-ACME, 443 לתעבורה.
# ---------------------------------------------------------------------------
set -euo pipefail

DOMAIN="35.193.190.149.sslip.io"

echo "== [1/5] writing Caddyfile =="
sudo mkdir -p /etc/caddy
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
${DOMAIN} {
    reverse_proxy localhost:5678
}
EOF

echo "== [2/5] starting caddy =="
sudo docker rm -f caddy >/dev/null 2>&1 || true
sudo docker pull -q caddy:latest >/dev/null
sudo docker run -d \
  --name caddy \
  --restart unless-stopped \
  --network host \
  -v /etc/caddy/Caddyfile:/etc/caddy/Caddyfile:ro \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy:latest >/dev/null

echo "== [3/5] waiting for the certificate =="
OK=0
for i in $(seq 1 90); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://${DOMAIN}/healthz" || echo 000)
  if [ "$CODE" = "200" ]; then
    echo "certificate issued and n8n reachable over HTTPS after ${i}s"
    OK=1
    break
  fi
  sleep 2
done

if [ "$OK" != "1" ]; then
  echo "FAILED: no valid HTTPS response (last code: $CODE). caddy logs:"
  sudo docker logs --tail 30 caddy
  exit 1
fi

# השלבים הבאים מפעילים מחדש את n8n ומכבים את הטאנל הזמני, ולכן הם מופרדים
# לסקריפט switch_to_caddy.sh — אין להריץ אותם בזמן שהערכה או הדגמה רצות.

echo
echo "PUBLIC_HTTPS_URL=https://${DOMAIN}"
curl -s --max-time 10 "https://${DOMAIN}/healthz"; echo
echo "Caddy is serving. Run switch_to_caddy.sh to complete the cutover."
