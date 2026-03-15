#!/bin/bash
set -euo pipefail

# Announce server restart countdown via RCON + Discord
# Sends center-screen messages at: 30, 20, 10, 5, 4, 3, 2, 1 minutes
#
# Usage: ./scripts/announce-restart.sh
#
# Requires: mcrcon, ValheimRcon mod on server
# Environment:
#   RCON_PORT (default: 25575)
#   RCON_PASSWORD (required)
#   DISCORD_WEBHOOK (optional — skips Discord if not set)

RCON_HOST="${RCON_HOST:-127.0.0.1}"
RCON_PORT="${RCON_PORT:-25575}"
RCON_PASSWORD="${RCON_PASSWORD:?RCON_PASSWORD is required}"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

send_discord() {
  local msg="$1"
  if [ -n "$DISCORD_WEBHOOK" ]; then
    curl -s -X POST "$DISCORD_WEBHOOK" \
      -H "Content-Type: application/json" \
      -d "{\"content\": \"$msg\"}" > /dev/null || echo "WARNING: Failed to send Discord message"
  fi
}

send_rcon() {
  local msg="$1"
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASSWORD" "showMessage $msg" || echo "WARNING: Failed to send RCON message"
}

send_message() {
  local msg="$1"
  echo "$(date '+%H:%M:%S') Announcing: $msg"
  send_rcon "$msg"
  send_discord "⚠️ **$msg**"
}

wait_minutes() {
  local mins="$1"
  echo "Waiting ${mins} minutes..."
  sleep $((mins * 60))
}

echo "Starting restart countdown (30 minutes)"
send_discord "🔄 **Server update deployed to Thunderstore — restart countdown starting (30 minutes)**"

send_message "Server restarting in 30 minutes"
wait_minutes 10

send_message "Server restarting in 20 minutes"
wait_minutes 10

send_message "Server restarting in 10 minutes"
wait_minutes 5

send_message "Server restarting in 5 minutes"
wait_minutes 1

send_message "Server restarting in 4 minutes"
wait_minutes 1

send_message "Server restarting in 3 minutes"
wait_minutes 1

send_message "Server restarting in 2 minutes"
wait_minutes 1

send_message "Server restarting in 1 minute"
wait_minutes 1

send_message "Server restarting NOW"
send_discord "🔧 **Server is restarting — back online shortly**"

echo "Countdown complete"
