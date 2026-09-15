#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/workspaces/repopilot"
cd "$ROOT"

echo
echo "=========================================="
echo " Stopping RepoPilot LOCAL Interview Mode"
echo "=========================================="
echo

# Disable write / execution mode for the next inactive state.
if [[ -f backend/.env ]]; then
    sed -i \
        's/^LIVE_EXECUTION_ENABLED=.*/LIVE_EXECUTION_ENABLED=false/' \
        backend/.env

    sed -i \
        's/^PUBLISH_ENABLED=.*/PUBLISH_ENABLED=false/' \
        backend/.env
fi

# Stop local static frontend.
if [[ -f /tmp/repopilot-frontend.pid ]]; then
    kill "$(cat /tmp/repopilot-frontend.pid)" \
        >/dev/null 2>&1 || true

    rm -f /tmp/repopilot-frontend.pid
fi

fuser -k 3000/tcp >/dev/null 2>&1 || true

# Stop containers but KEEP all named volumes/data.
docker compose stop \
    api worker redis database || true

# Never leave Codespaces ports public.
if [[ -n "${CODESPACE_NAME:-}" ]]; then
    gh codespace ports visibility \
        3000:private \
        8000:private \
        -c "$CODESPACE_NAME" \
        >/dev/null 2>&1 || true
fi

echo
echo "RepoPilot stopped."
echo
echo "IMPORTANT:"
echo "On Windows, press Ctrl+C in the GitHub CLI tunnel window."
echo
echo "Then you may stop the Codespace from GitHub."
echo
