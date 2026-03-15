#!/bin/bash
set -euo pipefail

# Announce server restart countdown via RCON
# Sends center-screen messages at: 30, 20, 10, 5, 4, 3, 2, 1 minutes
#
# Usage: ./scripts/announce-restart.sh
#
# Requires: mcrcon, ValheimRcon mod on server
# Environment: RCON_PORT (default: 2458), RCON_PASSWORD (required)

RCON_HOST="${RCON_HOST:-127.0.0.1}"
RCON_PORT="${RCON_PORT:-25575}"
RCON_PASSWORD="${RCON_PASSWORD:?RCON_PASSWORD is required}"

send_message() {
  local msg="$1"
  echo "$(date '+%H:%M:%S') Announcing: $msg"
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASSWORD" "showMessage $msg" || echo "WARNING: Failed to send RCON message"
}

wait_minutes() {
  local mins="$1"
  echo "Waiting ${mins} minutes..."
  sleep $((mins * 60))
}

echo "Starting restart countdown (30 minutes)"

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

echo "Countdown complete"
