#!/bin/bash
# ============================================================================
# Auto AI Daily Digest — designed for crontab / scheduled execution
#
# Usage:
#   bash scripts/auto-digest.sh                # smart days based on weekday
#   bash scripts/auto-digest.sh --days 3       # override days
#   bash scripts/auto-digest.sh --dry-run      # preview without API call
#   bash scripts/auto-digest.sh --provider openai
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$REPO_DIR/logs"
LOG_FILE="$LOG_DIR/digest-$(date +%Y%m%d-%H%M%S).log"
RSSHUB_PORT="${RSSHUB_PORT:-1200}"
RETENTION_DAYS="${DIGEST_LOG_RETENTION:-30}"

mkdir -p "$LOG_DIR"

# ── Logging ──────────────────────────────────────────────────────────────
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== AI Digest started at $(date) ==="

# ── Parse arguments early (need to know if dry-run) ───────────────────────
DAYS=""
PROVIDER=""
DRY_RUN=false
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --days)       DAYS="$2"; shift 2 ;;
        --provider)   PROVIDER="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=true; shift ;;
        *)            EXTRA_ARGS+=("$1"); shift ;;
    esac
done

# ── API Key (skip for dry-run) ───────────────────────────────────────────
if ! $DRY_RUN; then
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
    if [ -z "$ANTHROPIC_API_KEY" ] && [ -f "$HOME/.anthropic/api_key" ]; then
        export ANTHROPIC_API_KEY="$(cat "$HOME/.anthropic/api_key")"
    fi
    if [ -z "$ANTHROPIC_API_KEY" ] && [ -f "$REPO_DIR/.env" ]; then
        source "$REPO_DIR/.env" 2>/dev/null || true
    fi
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo "ERROR: ANTHROPIC_API_KEY not set."
        echo "Put your key in one of:"
        echo "  ~/.anthropic/api_key"
        echo "  $REPO_DIR/.env (ANTHROPIC_API_KEY=sk-ant-...)"
        echo "Or run with --dry-run to skip the API call."
        exit 1
    fi
    echo "API key: ${ANTHROPIC_API_KEY:0:12}..."
fi

# ── RSSHub ───────────────────────────────────────────────────────────────
check_rsshub() {
    curl -s --connect-timeout 2 "http://localhost:$RSSHUB_PORT/openai/news" >/dev/null 2>&1
}

if ! check_rsshub; then
    echo "RSSHub not running. Starting..."
    bash "$SCRIPT_DIR/start-rsshub.sh"
    for i in $(seq 1 60); do
        if check_rsshub; then
            echo "RSSHub ready after ${i}s"
            break
        fi
        sleep 1
    done
    if ! check_rsshub; then
        echo "ERROR: RSSHub failed to start within 60s"
        exit 1
    fi
else
    echo "RSSHub is running on port $RSSHUB_PORT"
fi

# ── Smart day selection ───────────────────────────────────────────────────
if [ -z "$DAYS" ]; then
    DOW=$(date +%u)  # 1=Mon, 7=Sun
    if [ "$DOW" -eq 1 ]; then
        DAYS=3  # Monday: cover weekend
    elif [ "$DOW" -eq 6 ] || [ "$DOW" -eq 7 ]; then
        DAYS=2  # Weekend: wider window
    else
        DAYS=1  # Weekday
    fi
fi

CMD=(python3 "$REPO_DIR/scripts/daily_digest.py" --days "$DAYS")
[ -n "$PROVIDER" ] && CMD+=(--provider "$PROVIDER")
$DRY_RUN && CMD+=(--dry-run)
[ ${#EXTRA_ARGS[@]} -gt 0 ] && CMD+=("${EXTRA_ARGS[@]}")

echo "Running: ${CMD[*]}"
"${CMD[@]}"
rc=$?

# ── Cleanup old logs ─────────────────────────────────────────────────────
find "$LOG_DIR" -name "digest-*.log" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

echo "=== Digest finished at $(date), exit=$rc ==="
exit $rc
