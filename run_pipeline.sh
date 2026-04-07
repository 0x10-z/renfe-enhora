#!/usr/bin/env bash
# run_pipeline.sh — ejecuta el pipeline Python, escribe JSON+Parquet en disco y hace commit local.
# NO hace push. El push lo gestiona push_to_git.sh (cron horario).
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

echo "[pipeline] $(date '+%H:%M:%S') OK — datos actualizados en public/data/ y data/" | tee -a "$LOG_FILE"

# ── Commit local (sin push) ───────────────────────────────────────────────────
if git diff --quiet -- public/data/ data/; then
    echo "[pipeline] $(date '+%H:%M:%S') Sin cambios en datos — omitiendo commit" | tee -a "$LOG_FILE"
    exit 0
fi

TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
git add public/data/ data/
git commit -m "data: actualizar tablero ${TIMESTAMP}"
echo "[pipeline] $(date '+%H:%M:%S') Commit local creado — push pendiente para push_to_git.sh" | tee -a "$LOG_FILE"
