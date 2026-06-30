#!/usr/bin/env bash
# Runs a cloudflared "quick tunnel" to the local gateway and captures the
# assigned public URL into voice_gateway/.tunnel_url so place_call.py can read it.
#
# Quick tunnels are ephemeral (random *.trycloudflare.com host, new on each start) —
# fine for the POC. For a stable hostname later, use a NAMED tunnel + DNS record.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL_FILE="$HERE/.tunnel_url"
PORT="${GATEWAY_PORT:-8090}"

: > "$URL_FILE"

# --no-autoupdate keeps the binary stable; logs go to stdout (captured by systemd journal).
exec cloudflared tunnel --no-autoupdate --url "http://localhost:${PORT}" 2>&1 \
  | while IFS= read -r line; do
      echo "$line"
      if [[ "$line" =~ (https://[a-zA-Z0-9.-]+\.trycloudflare\.com) ]]; then
        echo "${BASH_REMATCH[1]}" > "$URL_FILE"
        echo ">>> tunnel URL captured: ${BASH_REMATCH[1]} -> $URL_FILE"
      fi
    done
