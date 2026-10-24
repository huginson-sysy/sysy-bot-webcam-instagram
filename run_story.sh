#!/usr/bin/env bash
# VPS Cron-Wrapper für Story-Bot. Eigene Logs, eigene Rotation.
set -e
export TZ=Europe/Berlin
cd "$(dirname "$0")"
mkdir -p logs

LOG=logs/story_cron.log
[ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || stat -f%z "$LOG")" -gt 5242880 ] && \
  mv "$LOG" "$LOG.1" && : > "$LOG"

BOT_LOG=logs/story.log
[ -f "$BOT_LOG" ] && [ "$(stat -c%s "$BOT_LOG" 2>/dev/null || stat -f%z "$BOT_LOG")" -gt 5242880 ] && \
  tail -n 2000 "$BOT_LOG" > "$BOT_LOG.tmp" && mv "$BOT_LOG.tmp" "$BOT_LOG"

echo "[$(date -Iseconds)] tick" >> "$LOG"
.venv/bin/python story_bot.py >> "$LOG" 2>&1
