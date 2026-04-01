#!/usr/bin/env bash
# push_to_git.sh — hace commit de public/data/ y push a GitHub → dispara Vercel
# NO ejecuta el pipeline. Solo publica los datos ya generados por run_pipeline.sh.
#
# Cron: 0 * * * * /home/0x10/renfe-enhora/push_to_git.sh >> /home/0x10/renfe-enhora/logs/push.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$REPO_DIR/logs/push.log"

cd "$REPO_DIR"
mkdir -p logs

# ── Comprobar si hay cambios en los datos ─────────────────────────────────────
if git diff --quiet -- public/data/; then
    echo "[push] $(date '+%H:%M:%S') Sin cambios en public/data/ — omitiendo commit" | tee -a "$LOG_FILE"
    exit 0
fi

# ── Commit y push ─────────────────────────────────────────────────────────────
TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
git add public/data/
git commit -m "data: actualizar tablero ${TIMESTAMP}"

echo "[push] $(date '+%H:%M:%S') Pushing a GitHub..." | tee -a "$LOG_FILE"
git push origin master

echo "[push] $(date '+%H:%M:%S') OK — Vercel build disparado" | tee -a "$LOG_FILE"
