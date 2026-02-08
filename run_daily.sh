#!/bin/bash

PROJECT_ROOT="/Users/admin/Downloads/Pycharm/Trading_System"
SCRIPT_DIR="$PROJECT_ROOT/scripts"
LOG_DIR="$PROJECT_ROOT/logs"
PYTHON="$SCRIPT_DIR/.venv310/bin/python"

mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/cron.log"

echo "=================================================" | tee -a "$LOG_FILE"
echo "🚀 Trading System Run Started: $(date)" | tee -a "$LOG_FILE"
echo "Python: $PYTHON" | tee -a "$LOG_FILE"
echo "=================================================" | tee -a "$LOG_FILE"

# Safety check
if [ ! -x "$PYTHON" ]; then
  echo "❌ Python venv not found: $PYTHON" | tee -a "$LOG_FILE"
  exit 1
fi

# ─────────────────────────────────────────────
# LAYER 1 – DATA COLLECTION
# ─────────────────────────────────────────────
echo "▶️ Running Data Collector" | tee -a "$LOG_FILE"
$PYTHON "$SCRIPT_DIR/1_data_collector.py" >> "$LOG_FILE" 2>&1

# ─────────────────────────────────────────────
# LAYER 2 – SCREENER (TESTING MODE)
# ─────────────────────────────────────────────
echo "▶️ Running Screener (TESTING MODE)" | tee -a "$LOG_FILE"
$PYTHON "$SCRIPT_DIR/2_screener.py" --mode testing >> "$LOG_FILE" 2>&1

# ─────────────────────────────────────────────
# LAYER 3 – ANALYZER
# ─────────────────────────────────────────────
echo "▶️ Running Analyzer" | tee -a "$LOG_FILE"
$PYTHON "$SCRIPT_DIR/3_analyzer.py" >> "$LOG_FILE" 2>&1

# ─────────────────────────────────────────────
# LAYER 4 – NOTIFIER
# ─────────────────────────────────────────────
echo "▶️ Running Notifier" | tee -a "$LOG_FILE"
$PYTHON "$SCRIPT_DIR/4_notifier.py" >> "$LOG_FILE" 2>&1 || \
echo "⚠️ Notifier skipped (credentials missing)" | tee -a "$LOG_FILE"

# ─────────────────────────────────────────────
# LAYER 5 – TRACKER
# ─────────────────────────────────────────────
echo "▶️ Running EOD Tracker" | tee -a "$LOG_FILE"
$PYTHON "$SCRIPT_DIR/5_tracker.py" >> "$LOG_FILE" 2>&1

# ─────────────────────────────────────────────
# LAYER 6 – REPORTER (SUNDAY ONLY)
# ─────────────────────────────────────────────
DAY=$(date +%u)
if [ "$DAY" -eq 7 ]; then
  echo "📊 Sunday detected — Running Weekly Reporter" | tee -a "$LOG_FILE"
  $PYTHON "$SCRIPT_DIR/6_reporter.py" >> "$LOG_FILE" 2>&1
else
  echo "⏭️ Not Sunday — Skipping Reporter" | tee -a "$LOG_FILE"
fi

echo "✅ Trading System Run Complete: $(date)" | tee -a "$LOG_FILE"
echo "=================================================" | tee -a "$LOG_FILE"
