"""
LAYER 5: POSITION TRACKING
Runs: Daily 3:30 PM
Purpose: Update positions, calculate P&L, check triggers
"""

import pandas as pd
import yfinance as yf
from datetime import datetime

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

OUTPUT_DIR = 'output/'
LOG_FILE = f'logs/tracking_{datetime.now().strftime("%Y%m%d")}.txt'


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')


# ═══════════════════════════════════════════════════════
# LOAD TRACKER (TYPE SAFE)
# ═══════════════════════════════════════════════════════

def load_tracker():
    try:
        df = pd.read_csv(f"{OUTPUT_DIR}trade_tracker.csv")
        log(f"Loaded {len(df)} positions from tracker")
        return df
    except:
        log("No tracker file - creating new")

        return pd.DataFrame({
            'Date': pd.Series(dtype='str'),
            'Stock': pd.Series(dtype='str'),
            'Entry': pd.Series(dtype='float'),
            'SL': pd.Series(dtype='float'),
            'T1': pd.Series(dtype='float'),
            'T2': pd.Series(dtype='float'),
            'Quantity': pd.Series(dtype='int'),
            'Position': pd.Series(dtype='float'),
            'Current': pd.Series(dtype='float'),
            'PnL_Rs': pd.Series(dtype='float'),
            'PnL_Pct': pd.Series(dtype='float'),
            'Days_Held': pd.Series(dtype='int'),
            'Status': pd.Series(dtype='str'),
            'Notes': pd.Series(dtype='str'),
            'ATR': pd.Series(dtype='float'),
            'T1_Hit': pd.Series(dtype='bool')
        })


# ═══════════════════════════════════════════════════════
# UPDATE CURRENT PRICES
# ═══════════════════════════════════════════════════════

def update_current_prices(df):
    active_idx = df[df['Status'] == 'ACTIVE'].index

    for idx in active_idx:
        symbol = df.at[idx, 'Stock'] + '.NS'
        try:
            hist = yf.Ticker(symbol).history(period='1d')
            if not hist.empty:
                df.at[idx, 'Current'] = round(hist['Close'].iloc[-1], 2)
        except Exception as e:
            log(f"Price fetch error {symbol}: {e}")

    return df


# ═══════════════════════════════════════════════════════
# CALCULATE P&L (SAFE)
# ═══════════════════════════════════════════════════════

def calculate_pnl(df):
    numeric_cols = ['Entry', 'Current', 'Quantity', 'PnL_Rs', 'PnL_Pct']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['PnL_Rs'] = (df['Current'] - df['Entry']) * df['Quantity']
    df['PnL_Pct'] = ((df['Current'] - df['Entry']) / df['Entry']) * 100

    df['PnL_Rs'] = df['PnL_Rs'].round(2)
    df['PnL_Pct'] = df['PnL_Pct'].round(2)

    return df


# ═══════════════════════════════════════════════════════
# CHECK TRIGGERS
# ═══════════════════════════════════════════════════════

def check_triggers(df):
    actions = []

    for idx in df[df['Status'] == 'ACTIVE'].index:
        row = df.loc[idx]

        # SL HIT
        if row['Current'] <= row['SL']:
            actions.append({
                'Stock': row['Stock'],
                'Rule': 'SL_HIT',
                'Message': f"SL hit @ ₹{row['Current']}. EXIT."
            })
            df.at[idx, 'Status'] = 'CLOSED'
            continue

        # BREAKEVEN LOCK
        if row['PnL_Pct'] >= 3 and row['SL'] < row['Entry']:
            new_sl = row['Entry']
            df.at[idx, 'SL'] = new_sl
            actions.append({
                'Stock': row['Stock'],
                'Rule': 'BREAKEVEN',
                'Message': f"Move SL to Entry ₹{new_sl}"
            })

        # T1 HIT (ONLY ONCE)
        if row['Current'] >= row['T1'] and not row.get('T1_Hit', False):
            df.at[idx, 'T1_Hit'] = True
            trail_sl = round(row['Current'] - (1.5 * row.get('ATR', 20)), 2)
            df.at[idx, 'SL'] = max(df.at[idx, 'SL'], trail_sl)

            actions.append({
                'Stock': row['Stock'],
                'Rule': 'T1_HIT',
                'Message': f"T1 hit. Book 50%. Trail SL to ₹{trail_sl}"
            })

        # MONTH END
        if row['Days_Held'] >= 25:
            actions.append({
                'Stock': row['Stock'],
                'Rule': 'MONTH_END',
                'Message': f"Day {row['Days_Held']}: Prepare exit"
            })

    return actions, df


# ═══════════════════════════════════════════════════════
# ADD NEW TRADES
# ═══════════════════════════════════════════════════════

def add_new_trades(tracker):
    today = datetime.now().strftime('%Y%m%d')
    file = f"{OUTPUT_DIR}daily_signals_{today}.csv"

    try:
        signals = pd.read_csv(file)

        for _, row in signals.iterrows():
            tracker = pd.concat([tracker, pd.DataFrame([{
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Stock': row['Stock'],
                'Entry': row['Entry'],
                'SL': row['SL'],
                'T1': row['T1'],
                'T2': row.get('T2', 0),
                'Quantity': row['Quantity'],
                'Position': row['Position'],
                'Current': row['Entry'],
                'PnL_Rs': 0,
                'PnL_Pct': 0,
                'Days_Held': 0,
                'Status': 'ACTIVE',
                'Notes': '',
                'ATR': row.get('ATR', 20),
                'T1_Hit': False
            }])], ignore_index=True)

        log(f"Added {len(signals)} new trades")

    except:
        log("No new signals today")

    return tracker


# ═══════════════════════════════════════════════════════
# UPDATE DAYS HELD
# ═══════════════════════════════════════════════════════

def update_days_held(df):
    for idx in df[df['Status'] == 'ACTIVE'].index:
        entry_date = pd.to_datetime(df.at[idx, 'Date'])
        df.at[idx, 'Days_Held'] = (datetime.now() - entry_date).days
    return df


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    log("=" * 50)
    log("STARTING EOD TRACKING")
    log("=" * 50)

    tracker = load_tracker()
    tracker = add_new_trades(tracker)
    tracker = update_current_prices(tracker)
    tracker = calculate_pnl(tracker)
    tracker = update_days_held(tracker)

    actions, tracker = check_triggers(tracker)

    tracker.to_csv(f"{OUTPUT_DIR}trade_tracker.csv", index=False)
    log("Tracker updated and saved")

    print("\nACTIVE POSITIONS:")
    active = tracker[tracker['Status'] == 'ACTIVE']
    if not active.empty:
        print(active[['Stock', 'Entry', 'Current', 'PnL_Rs', 'PnL_Pct', 'Days_Held']])
        print(f"\nTotal P&L: ₹{active['PnL_Rs'].sum():,.2f}")
    else:
        print("No active positions")

    if actions:
        print("\n⚠️ ACTION ITEMS:")
        for a in actions:
            print(f"{a['Stock']} → {a['Rule']}: {a['Message']}")

    log("=" * 50)
    log("EOD TRACKING COMPLETE")
    log("=" * 50)


if __name__ == "__main__":
    main()
