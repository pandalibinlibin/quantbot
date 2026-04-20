#!/usr/bin/env python3
"""
Debug stock code format mismatch between D.instruments() and features directory
"""

import sys
import os

sys.path.append("/app")

import qlib
from qlib.data import D
from pathlib import Path


def debug_stock_code_format():
    """Debug stock code format mismatch"""

    print("=== Debug Stock Code Format ===")

    # Initialize Qlib
    try:
        qlib.init(provider_uri="/app/qlib_data_test", region="cn")
        print("✓ Qlib initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Qlib: {e}")
        return

    # Check what D.instruments() returns
    print("\n--- D.instruments() Output ---")
    try:
        instruments = D.instruments(market="all")
        print(f"Total instruments: {len(instruments)}")
        print("First 10 instruments from D.instruments():")
        instruments_list = list(instruments)
        for i, inst in enumerate(instruments_list[:10]):
            print(f"  {i+1}. '{inst}' (type: {type(inst)})")
    except Exception as e:
        print(f"✗ Failed to get instruments: {e}")
        return

    # Check actual features directory structure
    print("\n--- Features Directory Structure ---")
    features_dir = Path("/app/qlib_data_test/features")
    if features_dir.exists():
        feature_dirs = [d.name for d in features_dir.iterdir() if d.is_dir()]
        print(f"Total feature directories: {len(feature_dirs)}")
        print("First 10 feature directories:")
        for i, dir_name in enumerate(sorted(feature_dirs)[:10]):
            print(f"  {i+1}. '{dir_name}'")
    else:
        print("✗ Features directory does not exist")
        return

    # Check for format mismatch
    print("\n--- Format Mismatch Analysis ---")
    instruments_set = set(instruments_list)
    feature_dirs_set = set(feature_dirs)

    # Check if any instruments match feature directories exactly
    exact_matches = instruments_set & feature_dirs_set
    print(f"Exact matches: {len(exact_matches)}")
    if exact_matches:
        print("Sample exact matches:")
        for match in list(exact_matches)[:5]:
            print(f"  '{match}'")

    # Check case-insensitive matches
    instruments_lower = {inst.lower() for inst in instruments_list}
    feature_dirs_lower = {d.lower() for d in feature_dirs}
    case_insensitive_matches = instruments_lower & feature_dirs_lower
    print(f"Case-insensitive matches: {len(case_insensitive_matches)}")

    # Show format differences
    print("\n--- Format Analysis ---")
    sample_instrument = instruments_list[0] if instruments_list else None
    sample_feature_dir = feature_dirs[0] if feature_dirs else None

    if sample_instrument and sample_feature_dir:
        print(f"Sample instrument from D.instruments(): '{sample_instrument}'")
        print(f"Sample feature directory: '{sample_feature_dir}'")
        print(f"Are they equal? {sample_instrument == sample_feature_dir}")
        print(
            f"Case-insensitive equal? {sample_instrument.lower() == sample_feature_dir.lower()}"
        )

    # Test data loading with different formats
    print("\n--- Data Loading Test ---")
    if sample_instrument:
        test_cases = [
            sample_instrument,  # Original format
            sample_instrument.lower(),  # Lowercase
            sample_instrument.upper(),  # Uppercase
        ]

        for test_code in test_cases:
            try:
                data = D.features(
                    instruments=[test_code],
                    fields=["$close"],
                    start_time="2026-02-11",
                    end_time="2026-02-11",
                    freq="1min",
                )
                print(f"✓ Successfully loaded data for '{test_code}': {len(data)} rows")
            except Exception as e:
                print(f"✗ Failed to load data for '{test_code}': {e}")


if __name__ == "__main__":
    debug_stock_code_format()
