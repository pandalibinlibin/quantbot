#!/usr/bin/env python3
"""
Debug data conversion process
"""

import sys
import os

sys.path.append("/app")

from pathlib import Path
import pandas as pd
import subprocess


def debug_data_conversion():
    """Debug the data conversion process"""

    print("=== Data Conversion Debug ===")

    # Check CSV data directory
    csv_dir = Path("/app/csv_data/cn_data")
    print(f"\n=== CSV Data Directory: {csv_dir} ===")

    if csv_dir.exists():
        csv_files = list(csv_dir.glob("*.csv"))
        print(f"✓ CSV directory exists with {len(csv_files)} files")

        if csv_files:
            # Check first few CSV files
            for i, csv_file in enumerate(csv_files[:3]):
                print(f"\n--- CSV File {i+1}: {csv_file.name} ---")
                try:
                    df = pd.read_csv(csv_file)
                    print(f"Shape: {df.shape}")
                    print(f"Columns: {list(df.columns)}")
                    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
                    print(f"Sample data:\n{df.head(2)}")
                except Exception as e:
                    print(f"Error reading CSV: {e}")
        else:
            print("✗ No CSV files found")
    else:
        print(f"✗ CSV directory does not exist: {csv_dir}")
        return

    # Check Qlib data directory
    qlib_dir = Path("/app/qlib_data")
    print(f"\n=== Qlib Data Directory: {qlib_dir} ===")

    if qlib_dir.exists():
        print(f"✓ Qlib directory exists")

        # Check features directory
        features_dir = qlib_dir / "features"
        if features_dir.exists():
            print(f"✓ Features directory exists")

            # Check for different frequency directories
            for freq in ["day", "1min"]:
                freq_dir = features_dir / freq
                if freq_dir.exists():
                    bin_files = list(freq_dir.glob("*.bin"))
                    print(f"✓ {freq} directory: {len(bin_files)} bin files")
                    if bin_files:
                        print(f"  Sample files: {[f.name for f in bin_files[:3]]}")
                else:
                    print(f"✗ {freq} directory does not exist")
        else:
            print("✗ Features directory does not exist")

        # Check calendars directory
        calendars_dir = qlib_dir / "calendars"
        if calendars_dir.exists():
            print(f"✓ Calendars directory exists")
            calendar_files = list(calendars_dir.glob("*.txt"))
            print(f"  Calendar files: {[f.name for f in calendar_files]}")
        else:
            print("✗ Calendars directory does not exist")

        # Check instruments directory
        instruments_dir = qlib_dir / "instruments"
        if instruments_dir.exists():
            print(f"✓ Instruments directory exists")
            instrument_files = list(instruments_dir.glob("*.txt"))
            print(f"  Instrument files: {[f.name for f in instrument_files]}")
        else:
            print("✗ Instruments directory does not exist")
    else:
        print(f"✗ Qlib directory does not exist: {qlib_dir}")

    # Test dump_bin.py command manually
    print(f"\n=== Test dump_bin.py Command ===")

    if csv_files:
        cmd = [
            "python",
            "/app/scripts/dump_bin.py",
            "dump_all",
            "--data_path",
            str(csv_dir),
            "--qlib_dir",
            "/app/qlib_data_test",  # Use test directory
            "--freq",
            "1min",
            "--date_field_name",
            "date",
        ]

        print(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd="/app", timeout=60
            )
            print(f"Return code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")

            # Check test directory results
            test_dir = Path("/app/qlib_data_test")
            if test_dir.exists():
                features_test = test_dir / "features" / "1min"
                if features_test.exists():
                    test_files = list(features_test.glob("*.bin"))
                    print(f"✓ Test conversion created {len(test_files)} bin files")
                else:
                    print("✗ Test conversion failed - no 1min features created")
            else:
                print("✗ Test directory not created")

        except subprocess.TimeoutExpired:
            print("✗ Command timed out")
        except Exception as e:
            print(f"✗ Command failed: {e}")


if __name__ == "__main__":
    debug_data_conversion()
