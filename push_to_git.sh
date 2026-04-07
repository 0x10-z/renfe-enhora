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
if ! git pull --rebase origin master 2>&1 | tee -a "$LOG_FILE"; then
    echo "[push] $(date '+%H:%M:%S') Conflictos detectados — resolviendo datos con --theirs..." | tee -a "$LOG_FILE"
    # Durante rebase: --theirs = commits locales (datos del VPS, más recientes)
    while git rebase --show-current-patch >/dev/null 2>&1; do
        git checkout --theirs public/data/ data/ 2>/dev/null || true
        git add public/data/ data/ 2>/dev/null || true
        if ! git rebase --continue 2>&1 | tee -a "$LOG_FILE"; then
            break
        fi
    done
    # Verificar que el rebase terminó bien
    if git rebase --show-current-patch >/dev/null 2>&1; then
        echo "[push] $(date '+%H:%M:%S') ERROR — rebase no resuelto, abortando" | tee -a "$LOG_FILE"
        git rebase --abort
        exit 1
    fi
    echo "[push] $(date '+%H:%M:%S') Rebase completado tras resolver conflictos" | tee -a "$LOG_FILE"
fi

# ── Instalar dependencias nuevas si requirements.txt cambió ──────────────────
if [ -f "$REPO_DIR/venv/bin/activate" ]; then
    source "$REPO_DIR/venv/bin/activate"
fi
echo "[push] $(date '+%H:%M:%S') pip install -r requirements.txt..." | tee -a "$LOG_FILE"
pip install -q -r "$REPO_DIR/requirements.txt" 2>&1 | tee -a "$LOG_FILE"

# ── Push ─────────────────────────────────────────────────────────────────────
echo "[push] $(date '+%H:%M:%S') Pushing a GitHub..." | tee -a "$LOG_FILE"
git push origin master 2>&1 | tee -a "$LOG_FILE"

echo "[push] $(date '+%H:%M:%S') OK — Vercel build disparado" | tee -a "$LOG_FILE"
