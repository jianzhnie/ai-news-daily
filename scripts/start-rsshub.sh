#!/bin/bash
# Start RSSHub in background for local AI feed aggregation.
# Run this before opening Folo to ensure RSSHub routes are reachable.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
RSSHUB_DIR="$REPO_DIR/RSSHub"
PID_FILE="$REPO_DIR/.rsshub.pid"
LOG_FILE="$REPO_DIR/.rsshub.log"
PORT="${RSSHUB_PORT:-1200}"

# Auto-clone RSSHub if not present
if [[ ! -d "$RSSHUB_DIR" ]]; then
    echo "RSSHub not found. Cloning..."
    git clone https://github.com/DIYgod/RSSHub.git --depth 1 "$RSSHUB_DIR"
    cd "$RSSHUB_DIR"
    pnpm i && pnpm build
    cd "$REPO_DIR"
fi

if [[ -f "$PID_FILE" ]]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "RSSHub is already running (PID: $old_pid)"
        echo "To restart: kill $old_pid && rm $PID_FILE && $0"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

echo "Starting RSSHub on port $PORT ..."
cd "$RSSHUB_DIR"

pnpm start \
    --port "$PORT" \
    >>"$LOG_FILE" 2>&1 &

pid=$!
echo "$pid" >"$PID_FILE"
echo "RSSHub started (PID: $pid)"
echo "Logs: $LOG_FILE"
echo "Test: curl -s http://localhost:$PORT/openai/news | head -5"

# Wait until RSSHub is ready
for _ in $(seq 1 30); do
    if curl -s --connect-timeout 1 "http://localhost:$PORT/openai/news" >/dev/null 2>&1; then
        echo "RSSHub is ready!"
        exit 0
    fi
    sleep 1
done

echo "WARNING: RSSHub did not become ready within 30s. Check $LOG_FILE"
exit 1
