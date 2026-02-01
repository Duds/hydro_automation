#!/usr/bin/env python3
"""
Safety monitoring script for Hydroponic Automation.
Scans logs for [SAFETY_OFF_FAILURE] tags and provides a summary of critical issues.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Standard safety tag used in the codebase
SAFETY_TAG = "[SAFETY_OFF_FAILURE]"

def scan_file(file_path: Path, verbose: bool = False):
    """Scan a single log file for safety failures."""
    if not file_path.exists():
        return 0, []

    failures = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if SAFETY_TAG in line:
                    failures.append({
                        'line': line.strip(),
                        'line_num': line_num,
                        'file': file_path.name
                    })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    if failures and verbose:
        print(f"\n>>> Found {len(failures)} failures in {file_path.name}:")
        for fail in failures:
            print(f"  Line {fail['line_num']}: {fail['line']}")
    
    return len(failures), failures

def main():
    parser = argparse.ArgumentParser(description="Monitor hydroponics logs for critical safety failures.")
    parser.add_argument("--log-dir", default="logs", help="Directory containing log files")
    parser.add_argument("--verbose", action="store_true", help="Print detailed failure information")
    parser.add_argument("--exit-code", action="store_true", help="Exit with code 1 if failures found")
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    if not log_dir.is_dir():
        print(f"Error: Log directory '{log_dir}' not found.")
        sys.exit(1)
        
    print(f"--- Safety Monitor scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    print(f"Scanning directory: {log_dir.absolute()}")
    
    total_failures = 0
    all_failures = []
    
    # Scan all .log files in the directory
    for log_file in log_dir.glob("*.log"):
        count, file_fails = scan_file(log_file, args.verbose)
        total_failures += count
        all_failures.extend(file_fails)
        
    print("-" * 50)
    if total_failures == 0:
        print("✅ NO SAFETY FAILURES DETECTED")
        print("System appears to be stopping the pump reliably.")
    else:
        print(f"❌ CRITICAL: {total_failures} SAFETY FAILURES DETECTED")
        if not args.verbose:
            print("Run with --verbose to see detailed failure lines.")
            # Show the last 3 failures anyway for context
            print("\nLast 3 critical events:")
            for fail in all_failures[-3:]:
                print(f"  [{fail['file']}:{fail['line_num']}] {fail['line']}")
                
    print("-" * 50)
    
    if args.exit_code and total_failures > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
