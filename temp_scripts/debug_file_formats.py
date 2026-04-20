#!/usr/bin/env python3
"""
Debug file formats to find the mismatch
"""

import os
from pathlib import Path


def debug_file_formats():
    """Debug CSV files, instruments file, and features directories"""

    print("=== Debug File Formats ===")

    # Check CSV files
    print("\n--- CSV Files ---")
    csv_dir = Path("/app/csv_data")
    if csv_dir.exists():
        csv_files = list(csv_dir.glob("*.csv"))[:5]
        for csv_file in csv_files:
            print(f"CSV: {csv_file.name}")
    else:
        print("CSV directory not found")

    # Check instruments file
    print("\n--- Instruments File ---")
    instruments_file = Path("/app/qlib_data/instruments/all.txt")
    if instruments_file.exists():
        with open(instruments_file, "r") as f:
            lines = f.readlines()[:5]
            for i, line in enumerate(lines):
                parts = line.strip().split("\t")
                if parts:
                    print(f"Instrument {i+1}: {parts[0]}")
    else:
        print("Instruments file not found")

    # Check features directories
    print("\n--- Features Directories ---")
    features_dir = Path("/app/qlib_data/features")
    if features_dir.exists():
        feature_dirs = [d for d in features_dir.iterdir() if d.is_dir()][:5]
        for fdir in feature_dirs:
            print(f"Feature dir: {fdir.name}")
    else:
        print("Features directory not found")

    # Compare formats
    print("\n--- Format Comparison ---")
    if csv_dir.exists() and instruments_file.exists() and features_dir.exists():
        # Get first CSV file name (without .csv extension)
        csv_files = list(csv_dir.glob("*.csv"))
        if csv_files:
            csv_name = csv_files[0].stem  # Remove .csv extension
            print(f"CSV filename format: {csv_name}")

        # Get first instrument
        with open(instruments_file, "r") as f:
            first_line = f.readline().strip()
            if first_line:
                instrument_name = first_line.split("\t")[0]
                print(f"Instrument format: {instrument_name}")

        # Get first feature directory
        feature_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
        if feature_dirs:
            feature_name = feature_dirs[0].name
            print(f"Feature dir format: {feature_name}")

        # Check if they match
        if csv_files and feature_dirs:
            csv_name = csv_files[0].stem
            feature_name = feature_dirs[0].name
            instrument_name = first_line.split("\t")[0] if first_line else ""

            print(f"\nFormat matching:")
            print(
                f"CSV vs Feature: {csv_name} vs {feature_name} -> {'✓' if csv_name.lower() == feature_name.lower() else '✗'}"
            )
            print(
                f"Instrument vs Feature: {instrument_name} vs {feature_name} -> {'✓' if instrument_name.lower() == feature_name.lower() else '✗'}"
            )
            print(
                f"CSV vs Instrument: {csv_name} vs {instrument_name} -> {'✓' if csv_name.lower() == instrument_name.lower() else '✗'}"
            )


if __name__ == "__main__":
    debug_file_formats()
