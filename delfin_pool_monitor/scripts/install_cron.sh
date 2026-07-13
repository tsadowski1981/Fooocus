#!/usr/bin/env bash
# Dodaje wpis crontab uruchamiajacy codzienny raport Delfin o 18:00.
# Uzycie: bash scripts/install_cron.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$(command -v python3)"
LOG_FILE="$PROJECT_DIR/data/cron.log"
CRON_LINE="0 18 * * * cd $PROJECT_DIR && $PYTHON_BIN -m delfin_monitor report >> $LOG_FILE 2>&1"

mkdir -p "$PROJECT_DIR/data"

if crontab -l 2>/dev/null | grep -Fq "delfin_monitor report"; then
    echo "Wpis crontab dla delfin_monitor juz istnieje, nic nie zmieniam:"
    crontab -l | grep -F "delfin_monitor report"
    exit 0
fi

(crontab -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -
echo "Dodano wpis crontab:"
echo "  $CRON_LINE"
echo "Logi codziennego raportu beda zapisywane w: $LOG_FILE"
