"""
LAYER 1: DATA COLLECTION
Runs: Daily 8:00 AM
Purpose: Fetch all required data from free sources
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import json
import time

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════

with open('config/settings.json', 'r') as f:
    CONFIG = json.load(f)

WATCHLIST_FILE = 'data/master_watchlist.csv'
OUTPUT_DIR = 'data/'
LOG_FILE = f'logs/data_collection_{datetime.now().strftime("%Y%m%d")}.txt'


# ═══════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')


# ═══════════════════════════════════════════════════════
# FUNCTION 1: Load Watchlist
# ═══════════════════════════════════════════════════════

def load_watchlist():
    try:
        df = pd.read_csv(WATCHLIST_FILE)

        if df.empty or 'Symbol' not in df.columns:
            raise ValueError("Watchlist file empty or missing 'Symbol' column")

        symbols = df['Symbol'].dropna().tolist()
        symbols_yf = [s + '.NS' for s in symbols]

        log(f"Loaded {len(symbols)} stocks from watchlist")
        return symbols_yf

    except Exception as e:
        log(f"ERROR loading watchlist: {e}")
        return []


# ═══════════════════════════════════════════════════════
# FUNCTION 2: Fetch Price Data from Yahoo Finance
# ═══════════════════════════════════════════════════════

def fetch_price_data(symbols):
    """Fetch OHLCV data for all stocks"""

    all_data = []

    for symbol in symbols:
        try:
            log(f"Fetching data for {symbol}...")

            # Get 6 months data for MA calculations
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='6mo')

            if hist.empty:
                log(f"  WARNING: No data for {symbol}")
                continue

            # Get latest data
            latest = hist.iloc[-1]

            # Calculate moving averages
            hist['MA20'] = hist['Close'].rolling(20).mean()
            hist['MA50'] = hist['Close'].rolling(50).mean()
            hist['MA200'] = hist['Close'].rolling(200).mean()

            # Calculate RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            hist['RSI'] = 100 - (100 / (1 + rs))

            # Calculate ADX (simplified)
            # For production, use ta-lib: from ta.trend import ADXIndicator
            hist['ADX'] = 30  # Placeholder - replace with actual calculation

            # Calculate ATR
            high_low = hist['High'] - hist['Low']
            high_close = abs(hist['High'] - hist['Close'].shift())
            low_close = abs(hist['Low'] - hist['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            hist['ATR'] = true_range.rolling(14).mean()

            # Get volume metrics
            vol_20d = hist['Volume'].rolling(20).mean().iloc[-1]
            vol_5d = hist['Volume'].rolling(5).mean().iloc[-1]

            # Check 20-day high for breakout
            high_20d = hist['High'].rolling(20).max().iloc[-21]  # 20 days ago

            # Compile data
            stock_data = {
                'Symbol': symbol.replace('.NS', ''),
                'Date': hist.index[-1].strftime('%Y-%m-%d'),
                'Close': round(latest['Close'], 2),
                'Open': round(latest['Open'], 2),
                'High': round(latest['High'], 2),
                'Low': round(latest['Low'], 2),
                'Volume': int(latest['Volume']),
                'MA20': round(hist['MA20'].iloc[-1], 2),
                'MA50': round(hist['MA50'].iloc[-1], 2),
                'MA200': round(hist['MA200'].iloc[-1], 2),
                'RSI': round(hist['RSI'].iloc[-1], 2),
                'ADX': round(hist['ADX'].iloc[-1], 2),
                'ATR': round(hist['ATR'].iloc[-1], 2),
                'Vol_20D_Avg': int(vol_20d),
                'Vol_5D_Avg': int(vol_5d),
                'High_20D': round(high_20d, 2),
                'Support': round(hist['Low'].rolling(10).min().iloc[-1], 2),
                'Resistance': round(hist['High'].max(), 2)
            }

            all_data.append(stock_data)

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            log(f"  ERROR fetching {symbol}: {e}")
            continue

    df = pd.DataFrame(all_data)

    # Save to CSV
    today = datetime.now().strftime('%Y%m%d')
    output_file = f"{OUTPUT_DIR}raw_data_{today}.csv"
    df.to_csv(output_file, index=False)

    log(f"Saved data for {len(df)} stocks to {output_file}")

    return df


# ═══════════════════════════════════════════════════════
# FUNCTION 3: Fetch NSE Bhav Copy (Delivery %)
# ═══════════════════════════════════════════════════════

def fetch_delivery_data():
    """
    Fetch delivery percentage from NSE
    Note: NSE API requires proper headers and cookies
    For production, implement proper NSE scraping
    """

    # Placeholder - implement NSE scraping
    # For now, assume 50% delivery for all stocks

    log("NOTE: Using placeholder delivery data (50%)")
    log("TODO: Implement NSE Bhav Copy scraping")

    return None


# ═══════════════════════════════════════════════════════
# FUNCTION 4: Check Market Regime
# ═══════════════════════════════════════════════════════

def check_market_regime():
    """Check if Nifty is above key MAs"""

    try:
        nifty = yf.Ticker('^NSEI')
        hist = nifty.history(period='1y')

        hist['MA50'] = hist['Close'].rolling(50).mean()
        hist['MA200'] = hist['Close'].rolling(200).mean()

        latest = hist.iloc[-1]

        regime = {
            'Date': hist.index[-1].strftime('%Y-%m-%d'),
            'Nifty_Close': float(round(latest['Close'], 2)),
            'MA50': float(round(latest['MA50'], 2)),
            'MA200': float(round(latest['MA200'], 2)),
            'Above_MA50': bool(latest['Close'] > latest['MA50']),
            'Above_MA200': bool(latest['Close'] > latest['MA200'])
        }

        # Fetch VIX
        vix = yf.Ticker('^INDIAVIX')
        vix_hist = vix.history(period='5d')
        regime['VIX'] = float(round(vix_hist['Close'].iloc[-1], 2))

        # Decision
        if regime['Above_MA50'] and regime['Above_MA200'] and regime['VIX'] < 20:
            regime['Status'] = 'GREEN'
            regime['Trade'] = True
        else:
            regime['Status'] = 'YELLOW'
            regime['Trade'] = False

        log(f"Market Regime: {regime['Status']} (Nifty: {regime['Nifty_Close']}, VIX: {regime['VIX']})")

        # Save
        with open(f"{OUTPUT_DIR}market_regime.json", 'w') as f:
            json.dump(regime, f, indent=2)

        return regime

    except Exception as e:
        log(f"ERROR checking market regime: {e}")
        return {'Trade': False}


# ═══════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════

def main():
    log("=" * 50)
    log("STARTING DATA COLLECTION")
    log("=" * 50)

    # Step 1: Check market regime
    regime = check_market_regime()

    if regime['Status'] == 'RED':
        log("RED market regime - Skipping data collection")
        return

    log(f"{regime['Status']} regime - Proceeding with data collection")

    # Step 2: Load watchlist
    watchlist = load_watchlist()

    if not watchlist:
        log("ERROR: Empty watchlist - Aborting")
        return

    # Step 3: Fetch price data
    data = fetch_price_data(watchlist)

    log("=" * 50)
    log("DATA COLLECTION COMPLETE")
    log("=" * 50)


if __name__ == "__main__":
    main()
