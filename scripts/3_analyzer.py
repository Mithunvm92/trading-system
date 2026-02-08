"""
LAYER 3: ANALYSIS & TRADE SETUP
Runs: Daily 9:15 AM
Purpose: Calculate position sizes and generate final signals
"""

import pandas as pd
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

with open("config/settings.json", "r") as f:
    CONFIG = json.load(f)

CAPITAL = CONFIG["capital"]
RISK_PER_TRADE = CONFIG["risk_per_trade_pct"] / 100
MAX_POSITION_PCT = CONFIG["max_position_pct"] / 100
MAX_TRADES = CONFIG["max_concurrent_trades"]

OUTPUT_DIR = "output/"
LOG_FILE = f"logs/analysis_{datetime.now().strftime('%Y%m%d')}.txt"

# ═══════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════

def log(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {message}"
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

# ═══════════════════════════════════════════════════════
# LOAD SHORTLIST
# ═══════════════════════════════════════════════════════

def load_shortlist():
    today = datetime.now().strftime("%Y%m%d")
    file = f"{OUTPUT_DIR}shortlist_{today}.csv"
    try:
        df = pd.read_csv(file)
        log(f"Loaded {len(df)} stocks from shortlist")
        return df
    except Exception as e:
        log(f"ERROR loading shortlist: {e}")
        return pd.DataFrame()

# ═══════════════════════════════════════════════════════
# CHECK EXISTING POSITIONS
# ═══════════════════════════════════════════════════════

def check_existing_positions():
    try:
        tracker = pd.read_csv(f"{OUTPUT_DIR}trade_tracker.csv")
        return len(tracker[tracker["Status"] == "ACTIVE"])
    except:
        return 0

# ═══════════════════════════════════════════════════════
# POSITION SIZING
# ═══════════════════════════════════════════════════════

def calculate_position_size(entry, sl, capital):
    max_risk_amount = capital * RISK_PER_TRADE
    risk_per_share = entry - sl

    if risk_per_share <= 0:
        return 0, 0

    qty = int(max_risk_amount / risk_per_share)
    position_value = qty * entry

    max_position = capital * MAX_POSITION_PCT
    if position_value > max_position:
        qty = int(max_position / entry)
        position_value = qty * entry

    return qty, position_value

# ═══════════════════════════════════════════════════════
# BROKER CHARGES
# ═══════════════════════════════════════════════════════

def calculate_charges(position_value):
    brokerage_buy = min(position_value * 0.0005, 20)
    exchange_txn = position_value * 0.0000297
    gst = (brokerage_buy + exchange_txn) * 0.18
    stamp = position_value * 0.00015
    sebi = position_value * 0.000001
    buy = brokerage_buy + exchange_txn + gst + stamp + sebi

    brokerage_sell = min(position_value * 0.0005, 20)
    stt = position_value * 0.001
    exchange_txn_sell = position_value * 0.0000297
    gst_sell = (brokerage_sell + exchange_txn_sell) * 0.18
    dp = 18.5 * 1.18
    sell = brokerage_sell + stt + exchange_txn_sell + gst_sell + dp

    return round(buy + sell, 2)

# ═══════════════════════════════════════════════════════
# GENERATE SIGNALS
# ═══════════════════════════════════════════════════════

def generate_signals(df):
    signals = []

    for _, row in df.iterrows():
        qty, position = calculate_position_size(row["Entry"], row["SL"], CAPITAL)
        if qty == 0:
            continue

        charges = calculate_charges(position)
        breakeven_pct = (charges / position) * 100
        min_target = row["Entry"] * (1 + breakeven_pct / 100 + 0.02)

        if row["Target"] < min_target:
            log(f"SKIP {row['Symbol']}: Target too low after charges")
            continue

        expected_profit = (row["Target"] - row["Entry"]) * qty
        net_profit = expected_profit - charges
        net_expectancy_pct = (net_profit / position) * 100

        # 🔐 SAFE T2 LOGIC (NO Resistance dependency)
        atr = row.get("ATR", 20)
        t2 = round(row["Target"] + (1.5 * atr), 2)

        signal = {
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Stock": row["Symbol"],
            "Entry": row["Entry"],
            "SL": row["SL"],
            "T1": row["Target"],
            "T2": t2,
            "RR": row["RR"],
            "Quantity": qty,
            "Position": position,
            "Risk_Rs": round((row["Entry"] - row["SL"]) * qty, 2),
            "Risk_Pct": row["Risk_Pct"],
            "Charges": charges,
            "Breakeven": round(min_target, 2),
            "Net_Expectancy_Pct": round(net_expectancy_pct, 2),
            "ATR": atr,
            "Mode": row.get("Mode", "unknown")
        }

        signals.append(signal)

    return pd.DataFrame(signals)

# ═══════════════════════════════════════════════════════
# SELECT TOP TRADES
# ═══════════════════════════════════════════════════════

def select_top_trades(signals, max_trades):
    if len(signals) <= max_trades:
        return signals

    return signals.sort_values(
        by=["RR", "Net_Expectancy_Pct"],
        ascending=[False, False]
    ).head(max_trades)

# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    log("=" * 60)
    log("STARTING TRADE ANALYSIS")
    log("=" * 60)

    df = load_shortlist()
    if df.empty:
        log("No shortlist available")
        return

    active = check_existing_positions()
    available = MAX_TRADES - active

    log(f"Active positions: {active}/{MAX_TRADES}")
    log(f"Available slots: {available}")

    if available <= 0:
        log("Portfolio full")
        return

    signals = generate_signals(df)
    if signals.empty:
        log("No valid signals after analysis")
        return

    final_signals = select_top_trades(signals, available)

    today = datetime.now().strftime("%Y%m%d")
    outfile = f"{OUTPUT_DIR}daily_signals_{today}.csv"
    final_signals.to_csv(outfile, index=False)

    log("=" * 60)
    log(f"ANALYSIS COMPLETE: {len(final_signals)} signals")
    log(f"Saved to: {outfile}")
    log("=" * 60)

    print("\n" + "=" * 90)
    print("FINAL TRADE SIGNALS")
    print("=" * 90)
    print(
        final_signals[
            ["Stock", "Entry", "SL", "T1", "T2", "RR", "Quantity", "Position", "Net_Expectancy_Pct"]
        ].to_string(index=False)
    )
    print("=" * 90)

if __name__ == "__main__":
    main()
