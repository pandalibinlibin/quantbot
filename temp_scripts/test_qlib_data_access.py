#!/usr/bin/env python3
"""
Test Qlib data access directly
"""

import sys
import os

sys.path.append("/app")

import qlib
from qlib.data import D
from pathlib import Path


def test_qlib_data_access():
    """Test if Qlib can access the data correctly"""

    print("=== Test Qlib Data Access ===")

    # Initialize Qlib with the correct path
    try:
        qlib.init(provider_uri="/app/qlib_data", region="cn")
        print("✓ Qlib initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Qlib: {e}")
        return

    # Test 1: Check instruments
    print("\n--- Test 1: Check Instruments ---")
    try:
        instruments = D.instruments(market="all")
        instruments_list = list(instruments)
        print(f"Total instruments found: {len(instruments_list)}")
        if instruments_list:
            print("First 5 instruments:")
            for i, inst in enumerate(instruments_list[:5]):
                print(f"  {i+1}. {inst}")
        else:
            print("✗ No instruments found!")
            return
    except Exception as e:
        print(f"✗ Failed to get instruments: {e}")
        return

    # Test 2: Check calendar
    print("\n--- Test 2: Check Calendar ---")
    try:
        calendar = D.calendar(
            start_time="2026-02-11", end_time="2026-02-11", freq="1min"
        )
        calendar_list = list(calendar)
        print(f"Calendar entries for 2026-02-11: {len(calendar_list)}")
        if calendar_list:
            print("First 3 calendar entries:")
            for i, cal in enumerate(calendar_list[:3]):
                print(f"  {i+1}. {cal}")
    except Exception as e:
        print(f"✗ Failed to get calendar: {e}")

    # Test 3: Try to load basic data
    print("\n--- Test 3: Load Basic Data ---")
    if instruments_list:
        test_instrument = instruments_list[0]
        print(f"Testing with instrument: {test_instrument}")

        try:
            # Test basic field loading
            data = D.features(
                instruments=[test_instrument],
                fields=["$close"],
                start_time="2026-02-11",
                end_time="2026-02-11",
                freq="1min",
            )
            print(f"✓ Successfully loaded data: {len(data)} rows")
            if not data.empty:
                print("Sample data:")
                print(data.head(3))
            else:
                print("✗ Data is empty!")
        except Exception as e:
            print(f"✗ Failed to load data: {e}")

    # Test 4: Check file structure
    print("\n--- Test 4: Check File Structure ---")
    qlib_data_path = Path("/app/qlib_data")

    # Check main directories
    for subdir in ["features", "instruments", "calendars"]:
        subdir_path = qlib_data_path / subdir
        if subdir_path.exists():
            print(f"✓ {subdir}/ exists")
            if subdir == "features":
                # Check a few feature directories
                feature_dirs = list(subdir_path.iterdir())[:3]
                for fdir in feature_dirs:
                    if fdir.is_dir():
                        bin_files = list(fdir.glob("*.bin"))
                        print(f"  {fdir.name}/: {len(bin_files)} bin files")
        else:
            print(f"✗ {subdir}/ missing")

    # Test 5: Check specific stock data
    print("\n--- Test 5: Check Specific Stock Data ---")
    features_path = qlib_data_path / "features"
    if features_path.exists():
        # Look for a specific stock directory
        stock_dirs = [d for d in features_path.iterdir() if d.is_dir()]
        if stock_dirs:
            test_stock_dir = stock_dirs[0]
            print(f"Testing stock directory: {test_stock_dir.name}")

            bin_files = list(test_stock_dir.glob("*.1min.bin"))
            print(f"1min bin files: {len(bin_files)}")
            for bin_file in bin_files[:3]:
                size_kb = bin_file.stat().st_size / 1024
                print(f"  {bin_file.name}: {size_kb:.1f} KB")


if __name__ == "__main__":
    test_qlib_data_access()
