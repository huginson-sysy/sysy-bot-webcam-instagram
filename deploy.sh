#!/usr/bin/env bash
# Deploy auf VPS — schließt config/.env aus (VPS-Token bleibt erhalten).
set -e
cd "$(dirname "$0")"

VPS="${DEPLOY_HOST:-root@dein-server}"   # Zielhost per Umgebungsvariable: DEPLOY_HOST=root@1.2.3.4 ./deploy.sh
REMOTE=/opt/insta-schwaltenweiher

echo "→ Sync Code (ohne .env, ohne logs)"
rsync -av --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude 'logs/' \
  --exclude 'config/.env' \
  ./ "$VPS:$REMOTE/"

echo "→ Pip Update"
ssh "$VPS" "cd $REMOTE && .venv/bin/pip install -q -r requirements.txt"

echo "→ Status"
ssh "$VPS" "grep DRY_RUN $REMOTE/config/.env; crontab -l | grep insta"

echo "✓ Deploy fertig."
