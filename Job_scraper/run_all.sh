#!/bin/bash
# run_all.sh — Full trial run: Portal Pipeline then Vendor Pipeline
# Used for scheduled trial runs and one-off full runs.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(which python3)"
LOG="$SCRIPT_DIR/logs/run_all_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$SCRIPT_DIR/logs"

echo "========================================" | tee -a "$LOG"
echo "Full Trial Run started: $(date)"         | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

echo "[1/2] Portal Pipeline..." | tee -a "$LOG"
"$PYTHON" "$SCRIPT_DIR/run_portals.py" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "[2/2] Vendor Pipeline..." | tee -a "$LOG"
"$PYTHON" "$SCRIPT_DIR/run_vendors.py" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "Full Trial Run complete: $(date)" | tee -a "$LOG"
