#!/usr/bin/env bash
# push_to_git.sh — hace push de los commits locales acumulados por run_pipeline.sh.
# NO ejecuta el pipeline ni hace commits.
#
# Cron: 0 * * * * /home/0x10/renfe-enhora/push_to_git.sh >> /home/0x10/renfe-enhora/logs/push.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$REPO_DIR/logs/push.log"

cd "$REPO_DIR"
mkdir -p logs

# ── Comprobar si hay commits locales por publicar ─────────────────────────────
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master 2>/dev/null || echo "")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[push] $(date '+%H:%M:%S') Sin commits nuevos — omitiendo push" | tee -a "$LOG_FILE"
    exit 0
fi

# ── Sincronizar con remoto (rebase sobre commits de código) ──────────────────
echo "[push] $(date '+%H:%M:%S') git pull --rebase..." | tee -a "$LOG_FILE"
git pull --rebase origin master 2>&1 | tee -a "$LOG_FILE"

# ── Push ─────────────────────────────────────────────────────────────────────
echo "[push] $(date '+%H:%M:%S') Pushing a GitHub..." | tee -a "$LOG_FILE"
git push origin master 2>&1 | tee -a "$LOG_FILE"

echo "[push] $(date '+%H:%M:%S') OK — Vercel build disparado" | tee -a "$LOG_FILE"
