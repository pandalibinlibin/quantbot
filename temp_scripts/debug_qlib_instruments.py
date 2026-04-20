#!/usr/bin/env python3
"""
Debug Qlib instruments loading
"""

import sys

sys.path.append("/app")

import qlib
from qlib.data import D
from pathlib import Path


def debug_qlib_instruments():
    """Debug how Qlib loads instruments"""

    print("=== Debug Qlib Instruments Loading ===")

    # Initialize Qlib
    try:
        qlib.init(provider_uri="/app/qlib_data", region="cn")
        print("✓ Qlib initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Qlib: {e}")
        return

    # Check instruments file directly
    print("\n--- Direct File Check ---")
    instruments_file = Path("/app/qlib_data/instruments/all.txt")
    if instruments_file.exists():
        with open(instruments_file, "r") as f:
            lines = f.readlines()
            print(f"Instruments file has {len(lines)} lines")
            print("First 5 lines:")
            for i, line in enumerate(lines[:5]):
                parts = line.strip().split("\t")
                if parts:
                    print(
                        f"  {i+1}. {parts[0]} | {parts[1] if len(parts) > 1 else 'N/A'} | {parts[2] if len(parts) > 2 else 'N/A'}"
                    )
    else:
        print("✗ Instruments file not found")
        return

    # Check what D.instruments() returns
    print("\n--- D.instruments() Check ---")
    try:
        instruments = D.instruments(market="all")
        instruments_list = list(instruments)
        print(f"D.instruments() returned {len(instruments_list)} instruments")
        print("First 10 instruments:")
        for i, inst in enumerate(instruments_list[:10]):
            print(f"  {i+1}. '{inst}' (type: {type(inst)})")
    except Exception as e:
        print(f"✗ Failed to get instruments: {e}")

    # Check features directory
    print("\n--- Features Directory Check ---")
    features_dir = Path("/app/qlib_data/features")
    if features_dir.exists():
        feature_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
        print(f"Features directory has {len(feature_dirs)} subdirectories")
        print("First 5 feature directories:")
        for i, fdir in enumerate(feature_dirs[:5]):
            bin_files = list(fdir.glob("*.1min.bin"))
            print(f"  {i+1}. {fdir.name}/ ({len(bin_files)} bin files)")
    else:
        print("✗ Features directory not found")

    # Try to match instruments with features
    print("\n--- Matching Analysis ---")
    if instruments_file.exists() and features_dir.exists():
        # Get instruments from file
        with open(instruments_file, "r") as f:
            file_instruments = [
                line.strip().split("\t")[0] for line in f.readlines() if line.strip()
            ]

        # Get feature directories
        feature_dirs = [d.name for d in features_dir.iterdir() if d.is_dir()]

        print(f"Instruments in file: {len(file_instruments)}")
        print(f"Feature directories: {len(feature_dirs)}")

        # Check if any match (case-insensitive)
        matches = 0
        for inst in file_instruments[:10]:  # Check first 10
            for fdir in feature_dirs:
                if inst.lower() == fdir.lower():
                    matches += 1
                    break

        print(f"Case-insensitive matches (first 10): {matches}/10")

        # Show format examples
        if file_instruments and feature_dirs:
            print(f"Example instrument format: '{file_instruments[0]}'")
            print(f"Example feature dir format: '{feature_dirs[0]}'")

    # Check Qlib configuration
    print("\n--- Qlib Configuration Check ---")
    try:
        from qlib import C

        print(f"Qlib data path: {C.get('data_path', 'Not set')}")
        print(f"Qlib provider URI: {C.get('provider_uri', 'Not set')}")
        print(f"Qlib region: {C.get('region', 'Not set')}")
    except Exception as e:
        print(f"✗ Failed to get Qlib config: {e}")


if __name__ == "__main__":
    debug_qlib_instruments()
