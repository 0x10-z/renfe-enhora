#!/usr/bin/env bash
# deploy.sh — run pipeline and push updated JSON to GitHub
# Triggered by cron on the VPS every 5 minutes.
#
# Prerequisites:
#   - python3 virtualenv at ./venv  (or system python3 with deps installed)
#   - Git remote "origin" configured with push access (SSH key recommended)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCKFILE="/tmp/renfe-pipeline.lock"
LOG_FILE="$REPO_DIR/logs/pipeline.log"

# ── Prevent concurrent runs ───────────────────────────────────────────────────
if [ -f "$LOCKFILE" ]; then
    echo "[deploy] Another instance is running — skipping" >&2
    exit 0
fi
touch "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# ── Setup ─────────────────────────────────────────────────────────────────────
cd "$REPO_DIR"
mkdir -p logs

# Borrar caché GTFS para forzar recarga
rm -rf .cache/gtfs

# Activate virtualenv if present
if [ -f "$REPO_DIR/venv/bin/activate" ]; then
    source "$REPO_DIR/venv/bin/activate"
fi

# ── Pull latest changes ────────────────────────────────────────────────────────
# ── Pull latest changes (shallow safe) ─────────────────────────────────────────
echo "[deploy] $(date '+%H:%M:%S') Fetching (shallow)..." | tee -a "$LOG_FILE"

git fetch --depth=1 origin master

echo "[deploy] Resetting to origin/master..." | tee -a "$LOG_FILE"
git reset --hard origin/master

# Limpieza agresiva para evitar crecimiento del repo
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# ── Run pipeline ──────────────────────────────────────────────────────────────
echo "[deploy] $(date '+%H:%M:%S') Running pipeline…" | tee -a "$LOG_FILE"

if ! python3 -m scripts.main 2>&1 | tee -a "$LOG_FILE"; then
    echo "[deploy] Pipeline FAILED — aborting push" | tee -a "$LOG_FILE"
    exit 1
fi

# ── Commit and push if data changed ───────────────────────────────────────────
if git diff --quiet -- public/data/; then
    echo "[deploy] No data changes — skipping commit" | tee -a "$LOG_FILE"
    exit 0
fi

TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
git add public/data/
git commit -m "data: actualizar tablero ${TIMESTAMP}"

echo "[deploy] Pushing to GitHub…" | tee -a "$LOG_FILE"
git push origin master

echo "[deploy] Done — data publicada en $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"

# Borrar caché GTFS tras finalizar el pipeline
rm -rf .cache/gtfs
