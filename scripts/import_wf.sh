#!/bin/bash
# ---------------------------------------------------------------------------
# import_wf.sh — ייבוא ה-workflow לתוך מופע ה-n8n שהותקן מחדש.
# ---------------------------------------------------------------------------
set -euo pipefail

WF=/tmp/dual_code_auditor_wf_updated.json
test -f "$WF" || { echo "missing $WF"; exit 1; }

echo "== copying workflow into container =="
sudo docker cp "$WF" n8n:/tmp/wf.json

echo "== importing =="
sudo docker exec -u node n8n n8n import:workflow --input=/tmp/wf.json

echo "== workflows now present =="
sudo docker exec -u node n8n n8n list:workflow
