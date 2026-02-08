"""
CLEANUP UTILITY
Purpose: Clean up generated reports, logs, and temporary files
Preserves: Config files, requirements.txt, source code, and essential data
Usage: python cleanup.py [--all] [--reports] [--logs] [--data] [--graphs]
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent  # Trading_System root

# Directories to clean
CLEANUP_PATHS = {
    'reports': BASE_DIR / 'output' / 'reports',
    'graphs': BASE_DIR / 'output' / 'reports' / 'graphs',
    'logs': BASE_DIR / 'logs',
    'temp_data': BASE_DIR / 'data',
    'temp_output': BASE_DIR / 'output'
}

# Files to ALWAYS preserve
PRESERVE_FILES = {
    'config': [
        'settings.json',
        'credentials.json',
        'filters.json',
        'google_service_account.json'
    ],
    'data': [
        'master_watchlist.csv',
        'trade_history.csv',
        'trade_tracker.csv'
    ],
    'root': [
        'requirements.txt',
        'README.md',
        'run_daily.sh',
        'run_weekly.sh'
    ],
    'latest': [
        'latest_report.txt',
        'latest_metrics.json'
    ]
}


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def log(msg, color=''):
    """Print colored log messages"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'reset': '\033[0m'
    }

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color_code = colors.get(color, '')
    reset = colors['reset'] if color else ''
    print(f"{color_code}[{timestamp}] {msg}{reset}")


# ─────────────────────────────────────────────
# CLEANUP FUNCTIONS
# ─────────────────────────────────────────────

def get_file_age_days(filepath):
    """Get file age in days"""
    try:
        mtime = os.path.getmtime(filepath)
        age = (datetime.now() - datetime.fromtimestamp(mtime)).days
        return age
    except:
        return 0


def format_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def should_preserve(filepath, preserve_latest=True):
    """Check if file should be preserved"""
    filename = os.path.basename(filepath)

    # Always preserve config files
    if filename in PRESERVE_FILES['config']:
        return True

    # Always preserve essential data files
    if filename in PRESERVE_FILES['data']:
        return True

    # Always preserve root files
    if filename in PRESERVE_FILES['root']:
        return True

    # Optionally preserve latest reports
    if preserve_latest and filename in PRESERVE_FILES['latest']:
        return True

    return False


def clean_directory(directory, pattern='*', older_than_days=None,
                    preserve_latest=True, dry_run=False):
    """
    Clean files in a directory

    Args:
        directory: Path to directory
        pattern: File pattern to match (e.g., '*.pdf', '*.csv')
        older_than_days: Only delete files older than X days (None = all)
        preserve_latest: Keep latest_report.txt and latest_metrics.json
        dry_run: If True, only show what would be deleted

    Returns:
        tuple: (files_deleted, space_freed_bytes)
    """

    if not directory.exists():
        log(f"Directory does not exist: {directory}", 'yellow')
        return 0, 0

    files_deleted = 0
    space_freed = 0

    for filepath in directory.glob(pattern):
        if not filepath.is_file():
            continue

        # Check if should preserve
        if should_preserve(filepath, preserve_latest):
            log(f"  PRESERVE: {filepath.name}", 'green')
            continue

        # Check age if specified
        if older_than_days is not None:
            age = get_file_age_days(filepath)
            if age < older_than_days:
                continue

        # Get file size
        try:
            file_size = filepath.stat().st_size

            if dry_run:
                log(f"  WOULD DELETE: {filepath.name} ({format_size(file_size)})", 'yellow')
            else:
                filepath.unlink()
                log(f"  DELETED: {filepath.name} ({format_size(file_size)})", 'red')
                files_deleted += 1
                space_freed += file_size

        except Exception as e:
            log(f"  ERROR deleting {filepath.name}: {e}", 'red')

    return files_deleted, space_freed


def clean_empty_directories(base_path, dry_run=False):
    """Remove empty directories"""
    removed = 0

    for dirpath, dirnames, filenames in os.walk(base_path, topdown=False):
        for dirname in dirnames:
            full_path = Path(dirpath) / dirname

            try:
                # Check if directory is empty
                if not any(full_path.iterdir()):
                    if dry_run:
                        log(f"  WOULD REMOVE EMPTY DIR: {full_path}", 'yellow')
                    else:
                        full_path.rmdir()
                        log(f"  REMOVED EMPTY DIR: {full_path}", 'red')
                        removed += 1
            except:
                pass

    return removed


# ─────────────────────────────────────────────
# CLEANUP MODES
# ─────────────────────────────────────────────

def cleanup_reports(older_than_days=None, keep_latest=True, dry_run=False):
    """Clean up report files"""
    log("\n" + "=" * 80, 'blue')
    log("CLEANING REPORTS", 'blue')
    log("=" * 80, 'blue')

    reports_dir = CLEANUP_PATHS['reports']
    total_deleted = 0
    total_space = 0

    # Clean PDFs
    log("\nCleaning PDF reports...", 'blue')
    deleted, space = clean_directory(
        reports_dir,
        '*.pdf',
        older_than_days=older_than_days,
        preserve_latest=keep_latest,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    # Clean TXT reports
    log("\nCleaning TXT reports...", 'blue')
    deleted, space = clean_directory(
        reports_dir,
        '*.txt',
        older_than_days=older_than_days,
        preserve_latest=keep_latest,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    # Clean JSON metrics
    log("\nCleaning JSON metrics...", 'blue')
    deleted, space = clean_directory(
        reports_dir,
        '*.json',
        older_than_days=older_than_days,
        preserve_latest=keep_latest,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    log(f"\nReports cleanup: {total_deleted} files, {format_size(total_space)} freed", 'green')
    return total_deleted, total_space


def cleanup_graphs(older_than_days=None, dry_run=False):
    """Clean up graph images"""
    log("\n" + "=" * 80, 'blue')
    log("CLEANING GRAPHS", 'blue')
    log("=" * 80, 'blue')

    graphs_dir = CLEANUP_PATHS['graphs']
    total_deleted = 0
    total_space = 0

    # Clean PNG graphs
    log("\nCleaning graph images...", 'blue')
    deleted, space = clean_directory(
        graphs_dir,
        '*.png',
        older_than_days=older_than_days,
        preserve_latest=False,  # No latest concept for graphs
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    log(f"\nGraphs cleanup: {total_deleted} files, {format_size(total_space)} freed", 'green')
    return total_deleted, total_space


def cleanup_logs(older_than_days=7, dry_run=False):
    """Clean up log files older than X days"""
    log("\n" + "=" * 80, 'blue')
    log("CLEANING LOGS", 'blue')
    log("=" * 80, 'blue')

    logs_dir = CLEANUP_PATHS['logs']
    total_deleted = 0
    total_space = 0

    # Clean TXT logs
    log(f"\nCleaning log files older than {older_than_days} days...", 'blue')
    deleted, space = clean_directory(
        logs_dir,
        '*.txt',
        older_than_days=older_than_days,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    # Clean LOG files
    deleted, space = clean_directory(
        logs_dir,
        '*.log',
        older_than_days=older_than_days,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    log(f"\nLogs cleanup: {total_deleted} files, {format_size(total_space)} freed", 'green')
    return total_deleted, total_space


def cleanup_temp_data(older_than_days=30, dry_run=False):
    """Clean up temporary data files"""
    log("\n" + "=" * 80, 'blue')
    log("CLEANING TEMPORARY DATA", 'blue')
    log("=" * 80, 'blue')

    data_dir = CLEANUP_PATHS['temp_data']
    total_deleted = 0
    total_space = 0

    # Clean raw data CSVs (preserve master_watchlist.csv)
    log(f"\nCleaning temporary data files older than {older_than_days} days...", 'blue')
    deleted, space = clean_directory(
        data_dir,
        'raw_data_*.csv',
        older_than_days=older_than_days,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    # Clean NSE bhav copies
    deleted, space = clean_directory(
        data_dir,
        'nse_bhav_copy_*.csv',
        older_than_days=older_than_days,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    # Clean screener outputs (except fundamentals)
    deleted, space = clean_directory(
        data_dir,
        'screener_*.csv',
        older_than_days=older_than_days,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    log(f"\nData cleanup: {total_deleted} files, {format_size(total_space)} freed", 'green')
    return total_deleted, total_space


def cleanup_temp_output(older_than_days=7, dry_run=False):
    """Clean up temporary output files"""
    log("\n" + "=" * 80, 'blue')
    log("CLEANING TEMPORARY OUTPUTS", 'blue')
    log("=" * 80, 'blue')

    output_dir = CLEANUP_PATHS['temp_output']
    total_deleted = 0
    total_space = 0

    # Clean daily signals (preserve recent ones)
    log(f"\nCleaning old signal files (>{older_than_days} days)...", 'blue')
    deleted, space = clean_directory(
        output_dir,
        'daily_signals_*.csv',
        older_than_days=older_than_days,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    # Clean shortlists
    deleted, space = clean_directory(
        output_dir,
        'shortlist_*.csv',
        older_than_days=older_than_days,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    # Clean template files
    deleted, space = clean_directory(
        output_dir,
        'daily_signals_YYYYMMDD.csv',
        older_than_days=None,
        preserve_latest=False,
        dry_run=dry_run
    )
    total_deleted += deleted
    total_space += space

    log(f"\nOutput cleanup: {total_deleted} files, {format_size(total_space)} freed", 'green')
    return total_deleted, total_space


# ─────────────────────────────────────────────
# SUMMARY REPORT
# ─────────────────────────────────────────────

def print_summary(stats):
    """Print cleanup summary"""
    log("\n" + "=" * 80, 'green')
    log("CLEANUP SUMMARY", 'green')
    log("=" * 80, 'green')

    total_files = sum(s[0] for s in stats.values())
    total_space = sum(s[1] for s in stats.values())

    for category, (files, space) in stats.items():
        log(f"{category:20}: {files:4} files, {format_size(space):>10}", 'blue')

    log("-" * 80)
    log(f"{'TOTAL':20}: {total_files:4} files, {format_size(total_space):>10}", 'green')
    log("=" * 80, 'green')


def get_current_disk_usage():
    """Get current disk usage of the project"""
    log("\n" + "=" * 80, 'blue')
    log("CURRENT DISK USAGE", 'blue')
    log("=" * 80, 'blue')

    usage = {}

    for name, path in CLEANUP_PATHS.items():
        if path.exists():
            total_size = sum(
                f.stat().st_size
                for f in path.rglob('*')
                if f.is_file()
            )
            file_count = sum(1 for f in path.rglob('*') if f.is_file())
            usage[name] = (file_count, total_size)
            log(f"{name:20}: {file_count:4} files, {format_size(total_size):>10}")

    total_files = sum(u[0] for u in usage.values())
    total_size = sum(u[1] for u in usage.values())

    log("-" * 80)
    log(f"{'TOTAL':20}: {total_files:4} files, {format_size(total_size):>10}", 'green')
    log("=" * 80, 'blue')

    return usage


# ─────────────────────────────────────────────
# MAIN CLEANUP ORCHESTRATOR
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Cleanup utility for Trading System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup.py --all              # Clean everything (keep latest reports)
  python cleanup.py --reports          # Clean only reports
  python cleanup.py --reports --older-than 7   # Clean reports older than 7 days
  python cleanup.py --logs --older-than 30     # Clean logs older than 30 days
  python cleanup.py --dry-run --all    # Preview what would be deleted
  python cleanup.py --nuclear          # Delete EVERYTHING (including latest)
        """
    )

    # Cleanup targets
    parser.add_argument('--all', action='store_true',
                        help='Clean all categories (reports, graphs, logs, temp data)')
    parser.add_argument('--reports', action='store_true',
                        help='Clean report files (PDF, TXT, JSON)')
    parser.add_argument('--graphs', action='store_true',
                        help='Clean graph images')
    parser.add_argument('--logs', action='store_true',
                        help='Clean log files')
    parser.add_argument('--data', action='store_true',
                        help='Clean temporary data files')
    parser.add_argument('--output', action='store_true',
                        help='Clean temporary output files')

    # Options
    parser.add_argument('--older-than', type=int, metavar='DAYS',
                        help='Only delete files older than X days')
    parser.add_argument('--no-keep-latest', action='store_true',
                        help='Do not preserve latest_report.txt and latest_metrics.json')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without actually deleting')
    parser.add_argument('--nuclear', action='store_true',
                        help='Delete EVERYTHING including latest reports (use with caution!)')
    parser.add_argument('--usage', action='store_true',
                        help='Show current disk usage and exit')

    args = parser.parse_args()

    # Show usage and exit if requested
    if args.usage:
        get_current_disk_usage()
        return

    # If no specific target, default to showing help
    if not any([args.all, args.reports, args.graphs, args.logs,
                args.data, args.output, args.nuclear]):
        parser.print_help()
        print("\nℹ️  Use --usage to see current disk usage")
        print("ℹ️  Use --dry-run with any cleanup to preview changes")
        return

    # Warning for nuclear option
    if args.nuclear:
        log("\n" + "!" * 80, 'red')
        log("WARNING: NUCLEAR CLEANUP MODE", 'red')
        log("This will delete ALL generated files including latest reports!", 'red')
        log("!" * 80, 'red')

        response = input("\nAre you ABSOLUTELY sure? Type 'DELETE EVERYTHING' to confirm: ")
        if response != 'DELETE EVERYTHING':
            log("Cleanup cancelled.", 'yellow')
            return

        args.all = True
        args.no_keep_latest = True
        log("\nProceeding with nuclear cleanup...\n", 'red')

    # Dry run warning
    if args.dry_run:
        log("\n" + "=" * 80, 'yellow')
        log("DRY RUN MODE - No files will be deleted", 'yellow')
        log("=" * 80, 'yellow')

    # Show current usage
    log("\nBEFORE CLEANUP:", 'blue')
    before_usage = get_current_disk_usage()

    # Execute cleanup
    stats = {}
    keep_latest = not args.no_keep_latest
    older_than = args.older_than

    if args.all or args.reports:
        stats['Reports'] = cleanup_reports(older_than, keep_latest, args.dry_run)

    if args.all or args.graphs:
        stats['Graphs'] = cleanup_graphs(older_than, args.dry_run)

    if args.all or args.logs:
        # Default to 7 days for logs if not specified
        log_days = older_than if older_than else 7
        stats['Logs'] = cleanup_logs(log_days, args.dry_run)

    if args.all or args.data:
        # Default to 30 days for temp data if not specified
        data_days = older_than if older_than else 30
        stats['Temp Data'] = cleanup_temp_data(data_days, args.dry_run)

    if args.all or args.output:
        # Default to 7 days for temp output if not specified
        output_days = older_than if older_than else 7
        stats['Temp Output'] = cleanup_temp_output(output_days, args.dry_run)

    # Clean empty directories
    if not args.dry_run:
        log("\n" + "=" * 80, 'blue')
        log("CLEANING EMPTY DIRECTORIES", 'blue')
        log("=" * 80, 'blue')
        removed = clean_empty_directories(BASE_DIR / 'output', args.dry_run)
        log(f"Removed {removed} empty directories", 'green')

    # Print summary
    print_summary(stats)

    # Show after usage if not dry run
    if not args.dry_run:
        log("\nAFTER CLEANUP:", 'blue')
        after_usage = get_current_disk_usage()

    if args.dry_run:
        log("\n" + "=" * 80, 'yellow')
        log("DRY RUN COMPLETE - No files were deleted", 'yellow')
        log("Run without --dry-run to actually delete files", 'yellow')
        log("=" * 80, 'yellow')


if __name__ == "__main__":
    main()