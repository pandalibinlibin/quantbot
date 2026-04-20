#!/usr/bin/env python3
"""
Detailed debug of dump_bin.py process
"""

import sys
import os

sys.path.append("/app")

from pathlib import Path
import pandas as pd
import subprocess


def debug_dump_bin_detailed():
    """Debug dump_bin.py in detail"""

    print("=== Detailed dump_bin.py Debug ===")

    # Check test directory results
    test_dir = Path("/app/qlib_data_test")
    print(f"\n=== Test Directory Results: {test_dir} ===")

    if test_dir.exists():
        print(f"✓ Test directory exists")

        # Check features structure
        features_dir = test_dir / "features"
        if features_dir.exists():
            print(f"✓ Features directory exists")

            # Check 1min directory
            min1_dir = features_dir / "1min"
            if min1_dir.exists():
                bin_files = list(min1_dir.glob("*.bin"))
                print(f"✓ 1min directory exists with {len(bin_files)} bin files")

                if bin_files:
                    print(f"Sample bin files: {[f.name for f in bin_files[:5]]}")
                else:
                    print("✗ No bin files found in 1min directory")

                    # Check if there are any files at all
                    all_files = list(min1_dir.iterdir())
                    print(f"All files in 1min directory: {[f.name for f in all_files]}")
            else:
                print("✗ 1min directory does not exist")

                # List all subdirectories in features
                subdirs = [d.name for d in features_dir.iterdir() if d.is_dir()]
                print(f"Available subdirectories in features: {subdirs}")
        else:
            print("✗ Features directory does not exist")

        # Check calendars
        calendars_dir = test_dir / "calendars"
        if calendars_dir.exists():
            calendar_files = list(calendars_dir.glob("*.txt"))
            print(f"✓ Calendars directory: {[f.name for f in calendar_files]}")
        else:
            print("✗ Calendars directory does not exist")

        # Check instruments
        instruments_dir = test_dir / "instruments"
        if instruments_dir.exists():
            instrument_files = list(instruments_dir.glob("*.txt"))
            print(f"✓ Instruments directory: {[f.name for f in instrument_files]}")
        else:
            print("✗ Instruments directory does not exist")
    else:
        print("✗ Test directory does not exist")

    # Test with a single CSV file
    print(f"\n=== Test Single CSV File Conversion ===")

    csv_dir = Path("/app/csv_data/cn_data")
    csv_files = list(csv_dir.glob("*.csv"))

    if csv_files:
        # Create a test directory with just one CSV file
        single_test_dir = Path("/app/single_csv_test")
        single_test_dir.mkdir(exist_ok=True)

        # Copy first CSV file
        test_csv = single_test_dir / csv_files[0].name
        import shutil

        shutil.copy2(csv_files[0], test_csv)

        print(f"Testing with single file: {test_csv.name}")

        # Test conversion
        cmd = [
            "python",
            "/app/scripts/dump_bin.py",
            "dump_all",
            "--data_path",
            str(single_test_dir),
            "--qlib_dir",
            "/app/single_qlib_test",
            "--freq",
            "1min",
            "--date_field_name",
            "date",
        ]

        print(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd="/app", timeout=30
            )
            print(f"Return code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")

            # Check single test results
            single_qlib_dir = Path("/app/single_qlib_test")
            if single_qlib_dir.exists():
                single_features = single_qlib_dir / "features" / "1min"
                if single_features.exists():
                    single_bin_files = list(single_features.glob("*.bin"))
                    print(f"✓ Single test created {len(single_bin_files)} bin files")
                    if single_bin_files:
                        print(f"Files: {[f.name for f in single_bin_files]}")
                else:
                    print("✗ Single test failed - no 1min features")
            else:
                print("✗ Single test directory not created")

        except Exception as e:
            print(f"✗ Single test failed: {e}")

    # Check CSV data format in detail
    print(f"\n=== CSV Data Format Analysis ===")

    if csv_files:
        sample_csv = csv_files[0]
        print(f"Analyzing: {sample_csv.name}")

        try:
            df = pd.read_csv(sample_csv)
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print(f"Data types:\n{df.dtypes}")
            print(f"Date column sample:\n{df['date'].head()}")
            print(f"Date column type: {type(df['date'].iloc[0])}")

            # Check for any issues with the data
            print(f"Null values:\n{df.isnull().sum()}")
            print(f"Duplicate dates: {df['date'].duplicated().sum()}")

        except Exception as e:
            print(f"Error analyzing CSV: {e}")


if __name__ == "__main__":
    debug_dump_bin_detailed()
