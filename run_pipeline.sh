#!/usr/bin/env bash
# run_pipeline.sh — ejecuta el pipeline Python y escribe JSON en disco
# NO hace operaciones git. El commit y push lo gestiona push_to_git.sh.
#
# Cron: */5 * * * * /home/0x10/renfe-enhora/run_pipeline.sh >> /home/0x10/renfe-enhora/logs/pipeline.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCKFILE="/tmp/renfe-pipeline.lock"
LOG_FILE="$REPO_DIR/logs/pipeline.log"

# ── Prevent concurrent runs ───────────────────────────────────────────────────
if [ -f "$LOCKFILE" ]; then
    echo "[pipeline] $(date '+%H:%M:%S') Otra instancia en curso — omitiendo" >&2
    exit 0
fi
touch "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# ── Setup ─────────────────────────────────────────────────────────────────────
cd "$REPO_DIR"
mkdir -p logs

# Activate virtualenv if present
if [ -f "$REPO_DIR/venv/bin/activate" ]; then
    source "$REPO_DIR/venv/bin/activate"
fi

# ── Run pipeline ──────────────────────────────────────────────────────────────
echo "[pipeline] $(date '+%H:%M:%S') Iniciando pipeline..." | tee -a "$LOG_FILE"

if ! python3 -m scripts.main 2>&1 | tee -a "$LOG_FILE"; then
    echo "[pipeline] $(date '+%H:%M:%S') FALLO — datos no actualizados" | tee -a "$LOG_FILE"
    exit 1
fi

echo "[pipeline] $(date '+%H:%M:%S') OK — JSON actualizado en public/data/" | tee -a "$LOG_FILE"
