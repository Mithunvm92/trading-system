"""
LAYER 6: ANALYTICS & REPORTING
Runs: Weekly (Sunday)
Source of truth: trade_history.csv (CLOSED TRADES ONLY)
Enhanced with visual graphs and charts - OPTIMIZED VERSION
"""

import pandas as pd
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from textwrap import wrap
import matplotlib

matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import warnings

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OUTPUT_DIR = "output/"
REPORT_DIR = "output/reports/"
GRAPH_DIR = "output/reports/graphs/"
CRED_FILE = "config/credentials.json"
LOG_FILE = f"logs/reporting_{datetime.now().strftime('%Y%m%d')}.txt"

Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)
Path(GRAPH_DIR).mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# Set style for all graphs
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'DejaVu Sans'  # Better Unicode support


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ─────────────────────────────────────────────
# LOAD TRADE HISTORY
# ─────────────────────────────────────────────
def load_trade_history():
    try:
        df = pd.read_csv(f"{OUTPUT_DIR}trade_history.csv")

        if df.empty:
            raise ValueError("trade_history.csv is empty")

        required = ["Date", "Exit_Date", "PnL_Rs", "PnL_Pct"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing column: {col}")

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Exit_Date"] = pd.to_datetime(df["Exit_Date"], errors="coerce")
        df["PnL_Rs"] = pd.to_numeric(df["PnL_Rs"], errors="coerce")
        df["PnL_Pct"] = pd.to_numeric(df["PnL_Pct"], errors="coerce")
        df["RR"] = pd.to_numeric(df.get("RR", 2.0), errors="coerce").fillna(2.0)

        df = df.dropna(subset=["Exit_Date", "PnL_Rs"])

        log(f"Loaded {len(df)} closed trades")
        return df

    except Exception as e:
        log(f"No trade history available: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────
def weekly_metrics(df):
    week = df[df["Exit_Date"] >= datetime.now() - timedelta(days=7)]
    if week.empty:
        return None

    wins = week[week["PnL_Rs"] > 0]
    losses = week[week["PnL_Rs"] < 0]

    return {
        "Trades": int(len(week)),
        "Wins": int((week["PnL_Rs"] > 0).sum()),
        "Losses": int((week["PnL_Rs"] < 0).sum()),
        "WinRate_%": round((week["PnL_Rs"] > 0).mean() * 100, 2),
        "Total_PnL_Rs": round(float(week["PnL_Rs"].sum()), 2),
        "Avg_PnL_%": round(float(week["PnL_Pct"].mean()), 2),
        "Avg_Win_%": round(float(wins["PnL_Pct"].mean()), 2) if not wins.empty else 0,
        "Avg_Loss_%": round(float(losses["PnL_Pct"].mean()), 2) if not losses.empty else 0,
        "Best_Trade_%": round(float(week["PnL_Pct"].max()), 2) if not week.empty else 0,
        "Worst_Trade_%": round(float(week["PnL_Pct"].min()), 2) if not week.empty else 0,
    }


def monthly_metrics(df):
    month = df[df["Exit_Date"] >= datetime.now().replace(day=1)]
    if month.empty:
        return None

    cum = month.sort_values("Exit_Date")["PnL_Rs"].cumsum()
    dd = cum - cum.cummax()

    # Calculate consecutive losses
    month_sorted = month.sort_values("Exit_Date")
    month_sorted["Loss"] = month_sorted["PnL_Rs"] < 0
    max_consecutive = 0
    current_streak = 0

    for loss in month_sorted["Loss"]:
        if loss:
            current_streak += 1
            max_consecutive = max(max_consecutive, current_streak)
        else:
            current_streak = 0

    wins = month[month["PnL_Rs"] > 0]
    losses = month[month["PnL_Rs"] < 0]

    # Calculate expectancy
    win_rate = (month["PnL_Rs"] > 0).mean()
    avg_win = wins["PnL_Pct"].mean() if not wins.empty else 0
    avg_loss = losses["PnL_Pct"].mean() if not losses.empty else 0
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    return {
        "Trades": int(len(month)),
        "Wins": int((month["PnL_Rs"] > 0).sum()),
        "Losses": int((month["PnL_Rs"] < 0).sum()),
        "WinRate_%": round(win_rate * 100, 2),
        "Total_PnL_Rs": round(float(month["PnL_Rs"].sum()), 2),
        "Avg_Win_%": round(float(avg_win), 2),
        "Avg_Loss_%": round(float(avg_loss), 2),
        "Expectancy_%": round(float(expectancy), 2),
        "Max_Drawdown_Rs": round(float(dd.min()), 2),
        "Max_Consecutive_Losses": int(max_consecutive),
    }


# ─────────────────────────────────────────────
# PATTERN ANALYSIS (FIXED)
# ─────────────────────────────────────────────
def analyze_by_sector(df):
    """Analyze performance by sector - FIXED version"""
    sector_map = {
        'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'HCLTECH': 'IT', 'TECHM': 'IT',
        'RELIANCE': 'Energy', 'ONGC': 'Energy', 'BPCL': 'Energy', 'IOC': 'Energy',
        'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking',
        'KOTAKBANK': 'Banking', 'AXISBANK': 'Banking',
        'TATAMOTORS': 'Auto', 'M&M': 'Auto', 'MARUTI': 'Auto',
        'BAJAJ-AUTO': 'Auto', 'HEROMOTOCO': 'Auto',
        'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma',
        'DIVISLAB': 'Pharma', 'AUROPHARMA': 'Pharma',
        'TITAN': 'Consumer', 'ASIANPAINT': 'Consumer', 'HINDUNILVR': 'Consumer',
        'LT': 'Infra', 'ULTRACEMCO': 'Cement', 'ADANIPORTS': 'Infra'
    }

    if 'Stock' not in df.columns:
        return None

    df = df.copy()  # Avoid SettingWithCopyWarning
    df['Sector'] = df['Stock'].map(sector_map).fillna('Other')

    sector_stats = df.groupby('Sector').agg({
        'PnL_Rs': ['count', 'sum'],
        'PnL_Pct': 'mean'
    })

    sector_stats.columns = ['Trades', 'Total_PnL', 'Avg_PnL_%']

    # Win rate by sector - FIXED to suppress warning
    win_rates = df.groupby('Sector', group_keys=False).apply(
        lambda x: (x['PnL_Rs'] > 0).sum() / len(x) * 100,
        include_groups=False
    )
    sector_stats['WinRate_%'] = win_rates

    sector_stats = sector_stats.round(2)
    sector_stats = sector_stats.sort_values('Total_PnL', ascending=False)

    return sector_stats


def analyze_by_day(df):
    """Analyze by entry day of week - FIXED version"""
    if 'Date' not in df.columns:
        return None

    df = df.copy()  # Avoid SettingWithCopyWarning
    df['Entry_Day'] = df['Date'].dt.day_name()

    day_stats = df.groupby('Entry_Day').agg({
        'PnL_Rs': 'count',
        'PnL_Pct': 'mean'
    })

    day_stats.columns = ['Trades', 'Avg_PnL_%']

    # Win rate - FIXED to suppress warning
    win_rates = df.groupby('Entry_Day', group_keys=False).apply(
        lambda x: (x['PnL_Rs'] > 0).sum() / len(x) * 100,
        include_groups=False
    )
    day_stats['WinRate_%'] = win_rates

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    day_stats = day_stats.reindex(day_order).dropna()

    return day_stats.round(2)


# ─────────────────────────────────────────────
# GRAPH GENERATION (FIXED RUPEE SYMBOL)
# ─────────────────────────────────────────────

def generate_equity_curve(df):
    """Graph 1: Cumulative P&L over time (Equity Curve)"""
    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"{GRAPH_DIR}equity_curve_{ts}.png"

        df_sorted = df.sort_values('Exit_Date').copy()
        df_sorted['Cumulative_PnL'] = df_sorted['PnL_Rs'].cumsum()

        plt.figure(figsize=(12, 6))
        plt.plot(df_sorted['Exit_Date'], df_sorted['Cumulative_PnL'],
                 linewidth=2, color='#2E86AB', marker='o', markersize=4)

        plt.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1)

        plt.title('Equity Curve - Cumulative P&L Over Time', fontsize=14, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Cumulative P&L (Rs)', fontsize=12)  # Changed from ₹
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        max_val = df_sorted['Cumulative_PnL'].max()
        min_val = df_sorted['Cumulative_PnL'].min()
        last_val = df_sorted['Cumulative_PnL'].iloc[-1]

        plt.annotate(f'Peak: Rs {max_val:,.0f}',  # Changed from ₹
                     xy=(df_sorted[df_sorted['Cumulative_PnL'] == max_val]['Exit_Date'].iloc[0], max_val),
                     xytext=(10, 10), textcoords='offset points',
                     bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                     arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        log(f"Generated equity curve: {filepath}")
        return filepath
    except Exception as e:
        log(f"Error generating equity curve: {e}")
        return None


def generate_win_loss_distribution(df):
    """Graph 2: Distribution of Wins vs Losses"""
    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"{GRAPH_DIR}win_loss_dist_{ts}.png"

        wins = df[df['PnL_Pct'] > 0]['PnL_Pct']
        losses = df[df['PnL_Pct'] < 0]['PnL_Pct']

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Histogram
        if not wins.empty:
            ax1.hist(wins, bins=min(15, len(wins)), alpha=0.7, color='green',
                     label='Wins', edgecolor='black')
        if not losses.empty:
            ax1.hist(losses, bins=min(15, len(losses)), alpha=0.7, color='red',
                     label='Losses', edgecolor='black')

        ax1.set_xlabel('P&L %', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title('Win/Loss Distribution', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Pie chart
        win_count = len(wins)
        loss_count = len(losses)

        if win_count + loss_count > 0:
            colors_pie = ['#2ECC71', '#E74C3C']
            explode = (0.05, 0.05) if loss_count > 0 else (0.05,)
            sizes = [win_count, loss_count] if loss_count > 0 else [win_count]
            labels = ['Wins', 'Losses'] if loss_count > 0 else ['Wins']
            colors_to_use = colors_pie if loss_count > 0 else [colors_pie[0]]

            ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                    colors=colors_to_use, explode=explode, shadow=True)
            ax2.set_title('Win Rate Distribution', fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        log(f"Generated win/loss distribution: {filepath}")
        return filepath
    except Exception as e:
        log(f"Error generating distribution: {e}")
        return None


def generate_sector_performance(sector_stats):
    """Graph 3: Performance by Sector"""
    try:
        if sector_stats is None or sector_stats.empty:
            return None

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"{GRAPH_DIR}sector_performance_{ts}.png"

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        sectors = sector_stats.index
        total_pnl = sector_stats['Total_PnL']
        colors_bar = ['green' if x > 0 else 'red' for x in total_pnl]

        ax1.barh(sectors, total_pnl, color=colors_bar, edgecolor='black')
        ax1.set_xlabel('Total P&L (Rs)', fontsize=12)  # Changed from ₹
        ax1.set_title('Total P&L by Sector', fontsize=14, fontweight='bold')
        ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
        ax1.grid(True, alpha=0.3, axis='x')

        win_rates = sector_stats['WinRate_%']

        ax2.barh(sectors, win_rates, color='#3498DB', edgecolor='black')
        ax2.set_xlabel('Win Rate (%)', fontsize=12)
        ax2.set_title('Win Rate by Sector', fontsize=14, fontweight='bold')
        ax2.axvline(x=50, color='red', linestyle='--', linewidth=1, alpha=0.5,
                    label='50% threshold')
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.legend()

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        log(f"Generated sector performance: {filepath}")
        return filepath
    except Exception as e:
        log(f"Error generating sector chart: {e}")
        return None


def generate_day_of_week_analysis(day_stats):
    """Graph 4: Performance by Day of Week"""
    try:
        if day_stats is None or day_stats.empty:
            return None

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"{GRAPH_DIR}day_analysis_{ts}.png"

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        days = day_stats.index
        win_rates = day_stats['WinRate_%']
        colors_wr = ['green' if x >= 50 else 'orange' if x >= 40 else 'red' for x in win_rates]

        ax1.bar(days, win_rates, color=colors_wr, edgecolor='black', alpha=0.8)
        ax1.set_ylabel('Win Rate (%)', fontsize=12)
        ax1.set_title('Win Rate by Entry Day', fontsize=14, fontweight='bold')
        ax1.axhline(y=50, color='red', linestyle='--', linewidth=1, alpha=0.5,
                    label='50% threshold')
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.legend()
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        avg_pnl = day_stats['Avg_PnL_%']
        colors_pnl = ['green' if x > 0 else 'red' for x in avg_pnl]

        ax2.bar(days, avg_pnl, color=colors_pnl, edgecolor='black', alpha=0.8)
        ax2.set_ylabel('Average P&L (%)', fontsize=12)
        ax2.set_title('Average P&L by Entry Day', fontsize=14, fontweight='bold')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax2.grid(True, alpha=0.3, axis='y')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        log(f"Generated day analysis: {filepath}")
        return filepath
    except Exception as e:
        log(f"Error generating day chart: {e}")
        return None


def generate_monthly_performance(df):
    """Graph 5: Month-by-Month Performance - FIXED"""
    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"{GRAPH_DIR}monthly_performance_{ts}.png"

        df_copy = df.copy()
        df_copy['Month'] = df_copy['Exit_Date'].dt.to_period('M')

        monthly = df_copy.groupby('Month').agg({
            'PnL_Rs': ['sum', 'count'],
        })

        monthly.columns = ['Total_PnL', 'Trades']
        monthly.index = monthly.index.astype(str)

        # Win rate - FIXED
        win_rate = df_copy.groupby('Month', group_keys=False).apply(
            lambda x: (x['PnL_Rs'] > 0).sum() / len(x) * 100,
            include_groups=False
        )
        monthly['WinRate_%'] = win_rate

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        months = monthly.index
        pnl = monthly['Total_PnL']
        colors_pnl = ['green' if x > 0 else 'red' for x in pnl]

        ax1.bar(months, pnl, color=colors_pnl, edgecolor='black', alpha=0.8)
        ax1.set_ylabel('Total P&L (Rs)', fontsize=12)  # Changed from ₹
        ax1.set_title('Monthly P&L', fontsize=14, fontweight='bold')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax1.grid(True, alpha=0.3, axis='y')
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        for i, v in enumerate(pnl):
            ax1.text(i, v, f'Rs {v:,.0f}', ha='center',  # Changed from ₹
                     va='bottom' if v > 0 else 'top', fontsize=9)

        ax2.plot(months, monthly['WinRate_%'], marker='o', linewidth=2,
                 color='#2E86AB', markersize=8)
        ax2.set_ylabel('Win Rate (%)', fontsize=12)
        ax2.set_xlabel('Month', fontsize=12)
        ax2.set_title('Monthly Win Rate', fontsize=14, fontweight='bold')
        ax2.axhline(y=50, color='red', linestyle='--', linewidth=1, alpha=0.5,
                    label='50% target')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        log(f"Generated monthly performance: {filepath}")
        return filepath
    except Exception as e:
        log(f"Error generating monthly chart: {e}")
        return None


def generate_rr_analysis(df):
    """Graph 6: Risk-Reward Analysis - FIXED"""
    try:
        if 'RR' not in df.columns:
            return None

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"{GRAPH_DIR}rr_analysis_{ts}.png"

        df_copy = df.copy()
        bins = [0, 2.0, 2.5, 3.0, 10]
        labels = ['2.0-2.5', '2.5-3.0', '3.0-3.5', '3.5+']
        df_copy['RR_Range'] = pd.cut(df_copy['RR'], bins=bins, labels=labels)

        rr_stats = df_copy.groupby('RR_Range', observed=True).agg({
            'PnL_Rs': 'count',
            'PnL_Pct': 'mean'
        })

        rr_stats.columns = ['Trades', 'Avg_PnL_%']

        # Win rates - FIXED
        win_rates = df_copy.groupby('RR_Range', observed=True, group_keys=False).apply(
            lambda x: (x['PnL_Rs'] > 0).sum() / len(x) * 100,
            include_groups=False
        )
        rr_stats['WinRate_%'] = win_rates

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        rr_ranges = rr_stats.index.astype(str)

        ax1.bar(rr_ranges, rr_stats['WinRate_%'], color='#9B59B6',
                edgecolor='black', alpha=0.8)
        ax1.set_ylabel('Win Rate (%)', fontsize=12)
        ax1.set_xlabel('Risk-Reward Range', fontsize=12)
        ax1.set_title('Win Rate by R:R Setup', fontsize=14, fontweight='bold')
        ax1.axhline(y=50, color='red', linestyle='--', linewidth=1, alpha=0.5)
        ax1.grid(True, alpha=0.3, axis='y')

        colors_pnl = ['green' if x > 0 else 'red' for x in rr_stats['Avg_PnL_%']]

        ax2.bar(rr_ranges, rr_stats['Avg_PnL_%'], color=colors_pnl,
                edgecolor='black', alpha=0.8)
        ax2.set_ylabel('Average P&L (%)', fontsize=12)
        ax2.set_xlabel('Risk-Reward Range', fontsize=12)
        ax2.set_title('Average P&L by R:R Setup', fontsize=14, fontweight='bold')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        log(f"Generated RR analysis: {filepath}")
        return filepath
    except Exception as e:
        log(f"Error generating RR chart: {e}")
        return None


def generate_drawdown_chart(df):
    """Graph 7: Drawdown Chart"""
    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"{GRAPH_DIR}drawdown_{ts}.png"

        df_sorted = df.sort_values('Exit_Date').copy()
        df_sorted['Cumulative_PnL'] = df_sorted['PnL_Rs'].cumsum()
        df_sorted['Running_Max'] = df_sorted['Cumulative_PnL'].cummax()
        df_sorted['Drawdown'] = df_sorted['Cumulative_PnL'] - df_sorted['Running_Max']

        plt.figure(figsize=(12, 6))
        plt.fill_between(df_sorted['Exit_Date'], df_sorted['Drawdown'], 0,
                         color='red', alpha=0.3, label='Drawdown')
        plt.plot(df_sorted['Exit_Date'], df_sorted['Drawdown'],
                 color='darkred', linewidth=2)

        plt.title('Drawdown Analysis', fontsize=14, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Drawdown (Rs)', fontsize=12)  # Changed from ₹
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()

        max_dd = df_sorted['Drawdown'].min()
        if max_dd < 0:
            max_dd_date = df_sorted[df_sorted['Drawdown'] == max_dd]['Exit_Date'].iloc[0]
            plt.annotate(f'Max DD: Rs {max_dd:,.0f}',  # Changed from ₹
                         xy=(max_dd_date, max_dd),
                         xytext=(10, -20), textcoords='offset points',
                         bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                         arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        log(f"Generated drawdown chart: {filepath}")
        return filepath
    except Exception as e:
        log(f"Error generating drawdown chart: {e}")
        return None


# ─────────────────────────────────────────────
# BUILD TEXT REPORT
# ─────────────────────────────────────────────
def build_report(weekly, monthly, sector_stats, day_stats):
    lines = []
    lines.append("=" * 80)
    lines.append("WEEKLY TRADING PERFORMANCE REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)

    lines.append("\nWEEKLY SUMMARY")
    lines.append("-" * 80)
    if weekly:
        for k, v in weekly.items():
            lines.append(f"{k:<25}: {v}")
    else:
        lines.append("No trades closed this week")

    lines.append("\nMONTHLY SUMMARY")
    lines.append("-" * 80)
    if monthly:
        for k, v in monthly.items():
            lines.append(f"{k:<25}: {v}")
    else:
        lines.append("No trades closed this month")

    if sector_stats is not None and not sector_stats.empty:
        lines.append("\nSECTOR PERFORMANCE")
        lines.append("-" * 80)
        lines.append(f"{'Sector':<15} {'Trades':<8} {'WinRate%':<10} {'Total P&L':<15}")
        lines.append("-" * 80)
        for sector, row in sector_stats.iterrows():
            lines.append(
                f"{sector:<15} {int(row['Trades']):<8} {row['WinRate_%']:<10.1f} Rs {row['Total_PnL']:>12,.2f}")

    if day_stats is not None and not day_stats.empty:
        lines.append("\nDAY OF WEEK ANALYSIS")
        lines.append("-" * 80)
        lines.append(f"{'Day':<12} {'Trades':<8} {'WinRate%':<10} {'Avg P&L%':<10}")
        lines.append("-" * 80)
        for day, row in day_stats.iterrows():
            lines.append(f"{day:<12} {int(row['Trades']):<8} {row['WinRate_%']:<10.1f} {row['Avg_PnL_%']:<10.2f}")

    lines.append("\nVISUAL CHARTS GENERATED:")
    lines.append("-" * 80)
    lines.append("✓ Equity Curve")
    lines.append("✓ Win/Loss Distribution")
    lines.append("✓ Sector Performance")
    lines.append("✓ Day of Week Analysis")
    lines.append("✓ Monthly Performance")
    lines.append("✓ Risk-Reward Analysis")
    lines.append("✓ Drawdown Analysis")

    lines.append("\nData Source: trade_history.csv (closed trades only)")
    lines.append("=" * 80)
    return "\n".join(lines)


# ─────────────────────────────────────────────
# SAVE TXT + JSON
# ─────────────────────────────────────────────
def save_report(text_report, metrics):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    txt = f"{REPORT_DIR}weekly_report_{ts}.txt"
    jsn = f"{REPORT_DIR}metrics_{ts}.json"

    with open(txt, "w") as f:
        f.write(text_report)

    with open(jsn, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    with open(f"{REPORT_DIR}latest_report.txt", "w") as f:
        f.write(text_report)

    with open(f"{REPORT_DIR}latest_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    log(f"Saved report: {txt}")
    return txt


# ─────────────────────────────────────────────
# GENERATE ENHANCED PDF WITH GRAPHS
# ─────────────────────────────────────────────
def generate_pdf(text_report, graph_paths):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = f"{REPORT_DIR}weekly_report_{ts}.pdf"

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Page 1: Text Report
    x, y = 2 * cm, height - 2 * cm
    c.setFont("Courier-Bold", 12)
    c.drawString(x, y, "WEEKLY TRADING PERFORMANCE REPORT")
    y -= 0.8 * cm

    c.setFont("Courier", 9)
    for line in text_report.split("\n"):
        for w in wrap(line, 95):
            if y < 2 * cm:
                c.showPage()
                c.setFont("Courier", 9)
                y = height - 2 * cm
            c.drawString(x, y, w)
            y -= 12

    # Add graphs to PDF
    for graph_path in graph_paths:
        if graph_path and Path(graph_path).exists():
            c.showPage()

            img_width = width - 4 * cm
            img_height = (height - 4 * cm) * 0.8
            x_img = 2 * cm
            y_img = 2 * cm

            c.drawImage(graph_path, x_img, y_img,
                        width=img_width, height=img_height,
                        preserveAspectRatio=True)

    c.save()
    log(f"Enhanced PDF generated: {pdf_path}")
    return pdf_path


# ─────────────────────────────────────────────
# SEND PDF TO TELEGRAM
# ─────────────────────────────────────────────
def send_pdf_to_telegram(pdf_path):
    try:
        with open(CRED_FILE) as f:
            creds = json.load(f)

        token = creds.get("telegram_bot_token")
        chat_id = creds.get("telegram_chat_id")

        if not token or not chat_id:
            log("Telegram credentials not configured - skipping")
            return

        url = f"https://api.telegram.org/bot{token}/sendDocument"

        with open(pdf_path, "rb") as pdf:
            res = requests.post(
                url,
                data={"chat_id": chat_id, "caption": "📊 Weekly Trading Report with Charts"},
                files={"document": pdf},
                timeout=30
            )

        if res.status_code == 200:
            log("Telegram PDF sent successfully")
        else:
            log(f"Telegram error: {res.text}")
    except FileNotFoundError:
        log("Credentials file not found - skipping Telegram")
    except Exception as e:
        log(f"Error sending to Telegram: {e}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    log("=" * 80)
    log("STARTING WEEKLY REPORT WITH GRAPHS")
    log("=" * 80)

    df = load_trade_history()
    if df.empty:
        log("No closed trades → report skipped")
        return

    # Calculate metrics
    weekly = weekly_metrics(df)
    monthly = monthly_metrics(df)

    # Pattern analysis
    sector_stats = analyze_by_sector(df)
    day_stats = analyze_by_day(df)

    # Generate all graphs
    log("Generating visual charts...")
    graph_paths = []

    graph_paths.append(generate_equity_curve(df))
    graph_paths.append(generate_win_loss_distribution(df))
    graph_paths.append(generate_sector_performance(sector_stats))
    graph_paths.append(generate_day_of_week_analysis(day_stats))
    graph_paths.append(generate_monthly_performance(df))
    graph_paths.append(generate_rr_analysis(df))
    graph_paths.append(generate_drawdown_chart(df))

    # Remove None values
    graph_paths = [g for g in graph_paths if g is not None]

    log(f"Generated {len(graph_paths)} charts")

    # Build text report
    report = build_report(weekly, monthly, sector_stats, day_stats)

    # Save reports
    save_report(report, {
        "weekly": weekly,
        "monthly": monthly,
        "sector_stats": sector_stats.to_dict() if sector_stats is not None else {},
        "day_stats": day_stats.to_dict() if day_stats is not None else {}
    })

    # Generate PDF with graphs
    pdf = generate_pdf(report, graph_paths)

    # Send to Telegram
    send_pdf_to_telegram(pdf)

    print("\n" + report)
    log("=" * 80)
    log("WEEKLY REPORT COMPLETE")
    log(f"PDF saved: {pdf}")
    log(f"Graphs saved: {GRAPH_DIR}")
    log("=" * 80)


if __name__ == "__main__":
    main()