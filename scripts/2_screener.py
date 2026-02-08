"""
LAYER 2: SCREENING ENGINE
Runs: Daily 9:00 AM (after data collection)
Purpose: Apply 3-layer filters and identify candidates
"""

import pandas as pd
import json
from datetime import datetime
import argparse

# ═══════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════

DATA_DIR = "data/"
OUTPUT_DIR = "output/"
LOG_FILE = f"logs/screening_{datetime.now().strftime('%Y%m%d')}.txt"

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
# LOAD BASE FILTERS
# ═══════════════════════════════════════════════════════

with open("config/filters.json", "r") as f:
    BASE_FILTERS = json.load(f)

# ═══════════════════════════════════════════════════════
# FILTER MODES
# ═══════════════════════════════════════════════════════

def load_filters(mode):
    if mode == "testing":
        log("Running in TESTING mode (VERY RELAXED – DO NOT TRADE)")
        return {
            "mode": "testing",
            "layer1": {
                "min_volume": 100000,
                "min_price": 50,
                "max_price": 10000
            },
            "layer2": {
                "rsi_min": 40,
                "rsi_max": 80,
                "adx_min": 10,
                "volume_surge": 0.8
            },
            "layer3": {
                "max_extension": 25,
                "min_rr": 1.2
            }
        }

    elif mode == "relaxed":
        log("Running in RELAXED mode")
        return {
            "mode": "relaxed",
            "layer1": {
                "min_volume": 200000,
                "min_price": 100,
                "max_price": 5000
            },
            "layer2": {
                "rsi_min": 45,
                "rsi_max": 75,
                "adx_min": 15,
                "volume_surge": 1.1
            },
            "layer3": {
                "max_extension": 15,
                "min_rr": 1.8
            }
        }

    else:
        log("Running in STANDARD mode")
        BASE_FILTERS["mode"] = "standard"
        return BASE_FILTERS

# ═══════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════

def load_latest_data():
    today = datetime.now().strftime("%Y%m%d")
    file = f"{DATA_DIR}raw_data_{today}.csv"
    try:
        df = pd.read_csv(file)
        log(f"Loaded {len(df)} stocks from {file}")
        return df
    except Exception as e:
        log(f"ERROR loading data: {e}")
        return pd.DataFrame()

# ═══════════════════════════════════════════════════════
# LAYER 1 – LIQUIDITY FILTER
# ═══════════════════════════════════════════════════════

def layer1_filter(df, F):
    start = len(df)

    df = df[df["Vol_20D_Avg"] >= F["layer1"]["min_volume"]]
    log(f"  Volume filter: {len(df)} remain")

    df = df[
        (df["Close"] >= F["layer1"]["min_price"]) &
        (df["Close"] <= F["layer1"]["max_price"])
    ]
    log(f"  Price filter: {len(df)} remain")

    log(f"LAYER 1: Removed {start - len(df)}")
    return df

# ═══════════════════════════════════════════════════════
# LAYER 2 – MOMENTUM FILTER
# ═══════════════════════════════════════════════════════

def layer2_filter(df, F):
    start = len(df)
    mode = F.get("mode", "standard")

    if mode == "testing":
        df = df[df["Close"] > df["MA20"]]
        log(f"  TESTING MA filter: {len(df)} remain")

    elif mode == "relaxed":
        df = df[
            (df["Close"] > df["MA50"]) &
            (df["MA50"] > df["MA200"])
        ]
        log(f"  RELAXED MA filter: {len(df)} remain")

    else:
        df = df[
            (df["Close"] > df["MA50"]) &
            (df["Close"] > df["MA200"]) &
            (df["MA20"] > df["MA50"]) &
            (df["MA50"] > df["MA200"])
        ]
        log(f"  STANDARD MA filter: {len(df)} remain")

    df = df[
        (df["RSI"] >= F["layer2"]["rsi_min"]) &
        (df["RSI"] <= F["layer2"]["rsi_max"])
    ]
    log(f"  RSI filter: {len(df)} remain")

    df = df[df["ADX"] >= F["layer2"]["adx_min"]]
    log(f"  ADX filter: {len(df)} remain")

    df = df.copy()
    df["Vol_Ratio"] = df["Vol_5D_Avg"] / df["Vol_20D_Avg"]
    df = df[df["Vol_Ratio"] >= F["layer2"]["volume_surge"]]
    log(f"  Volume surge: {len(df)} remain")

    log(f"LAYER 2: Removed {start - len(df)}")
    return df

# ═══════════════════════════════════════════════════════
# LAYER 3 – RISK & STRUCTURE
# ═══════════════════════════════════════════════════════

def layer3_filter(df, F):
    df = df.copy()
    start = len(df)

    df = df[df["Close"] > df["High_20D"]]
    log(f"  Breakout filter: {len(df)} remain")

    df["Pct_Above_MA20"] = ((df["Close"] - df["MA20"]) / df["MA20"]) * 100
    df = df[df["Pct_Above_MA20"] <= F["layer3"]["max_extension"]]
    log(f"  Extension filter: {len(df)} remain")

    df["Entry"] = df["Close"]
    df["SL"] = df["Support"] * 0.995
    df["Risk_Per_Share"] = df["Entry"] - df["SL"]
    df["Target"] = df["Entry"] + (2 * df["Risk_Per_Share"])
    df["RR"] = (df["Target"] - df["Entry"]) / df["Risk_Per_Share"]

    df = df[df["RR"] >= F["layer3"]["min_rr"]]
    log(f"  RR filter: {len(df)} remain")

    df["Risk_Pct"] = (df["Risk_Per_Share"] / df["Entry"]) * 100

    if F.get("mode") == "testing":
        df = df[df["Risk_Pct"] <= 12]
        log(f"  TESTING Risk % filter: {len(df)} remain")
    else:
        df = df[df["Risk_Pct"] <= 5]
        log(f"  Risk % filter: {len(df)} remain")

    log(f"LAYER 3: Removed {start - len(df)}")
    return df

# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["standard", "relaxed", "testing"],
        default="standard",
        help="Screening mode"
    )
    args = parser.parse_args()

    FILTERS = load_filters(args.mode)

    log("=" * 70)
    log("STARTING SCREENING")

    if args.mode == "testing":
        log("⚠️ TESTING MODE – OUTPUT IS NOT FOR TRADING")

    df = load_latest_data()
    if df.empty:
        log("No data available")
        return

    log(f"Starting universe: {len(df)} stocks")

    df = layer1_filter(df, FILTERS)
    if df.empty:
        log("No stocks after Layer 1")
        return

    df = layer2_filter(df, FILTERS)
    if df.empty:
        log("No stocks after Layer 2")
        return

    df = layer3_filter(df, FILTERS)
    if df.empty:
        log("No stocks after Layer 3")
        return

    output_cols = [
        "Symbol", "Entry", "SL", "Target", "RR",
        "Risk_Pct", "MA20", "MA50", "MA200",
        "RSI", "ADX", "ATR"
    ]

    shortlist = df[output_cols].round(2)
    shortlist["Mode"] = args.mode

    today = datetime.now().strftime("%Y%m%d")
    file = f"{OUTPUT_DIR}shortlist_{today}.csv"
    shortlist.to_csv(file, index=False)

    log("=" * 70)
    log(f"SCREENING COMPLETE: {len(shortlist)} stocks")
    log(f"Saved to: {file}")
    log("=" * 70)

    print("\n" + "=" * 90)
    print("SHORTLIST")
    print("=" * 90)
    print(shortlist[["Symbol", "Entry", "SL", "Target", "RR", "Mode"]].to_string(index=False))
    print("=" * 90)

if __name__ == "__main__":
    main()
