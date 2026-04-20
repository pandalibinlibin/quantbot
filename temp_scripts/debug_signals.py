#!/usr/bin/env python3
"""
Debug script to check signals from OnlineManager
"""

import sys
import os

sys.path.append("/app")

from app.services.online_serving_service import get_online_serving_service
import pandas as pd

print("=" * 60)
print("Signals Debug")
print("=" * 60)

# Get online service
online_service = get_online_serving_service()

print("\n1. OnlineManager Status:")
print(f"   OnlineManager exists: {online_service._online_manager is not None}")

# Test getting signals
print("\n2. Getting signals from OnlineManager:")
try:
    signals = online_service._online_manager.get_signals()

    print(f"   Signals type: {type(signals)}")
    print(f"   Signals is None: {signals is None}")

    if signals is not None:
        if isinstance(signals, pd.DataFrame):
            print(f"   Signals shape: {signals.shape}")
            print(f"   Signals empty: {signals.empty}")
            print(f"   Signals index: {signals.index}")
            print(f"   Signals columns: {signals.columns.tolist()}")

            if not signals.empty:
                print(f"   First 3 rows:")
                for i, (idx, row) in enumerate(signals.head(3).iterrows()):
                    print(f"     {idx}: {dict(row)}")
        else:
            print(f"   Signals content: {signals}")

except Exception as e:
    print(f"   ERROR getting signals: {e}")
    import traceback

    traceback.print_exc()

# Test the enhanced indexing calculation with actual signals
print("\n3. Testing enhanced indexing with actual signals:")
try:
    signals = online_service._online_manager.get_signals()

    if signals is not None and not (
        isinstance(signals, pd.DataFrame) and signals.empty
    ):
        result = online_service._calculate_enhanced_indexing(signals, "2026-03-20")

        print(f"   Enhanced indexing result:")
        print(f"     Success: {result.get('success')}")
        print(f"     Strategy: {result.get('strategy')}")
        print(
            f"     Target portfolio length: {len(result.get('target_portfolio', []))}"
        )

        if result.get("target_portfolio"):
            first_pos = result["target_portfolio"][0]
            print(f"     First position format check:")
            print(f"       Has 'symbol': {'symbol' in first_pos}")
            print(f"       Has 'instrument': {'instrument' in first_pos}")
            print(f"       Keys: {list(first_pos.keys())[:8]}")
    else:
        print("   No signals available for testing")

except Exception as e:
    print(f"   ERROR in enhanced indexing test: {e}")
    import traceback

    traceback.print_exc()

# Check if there are any saved portfolio files
print("\n4. Checking saved portfolio files:")
import glob

portfolio_files = glob.glob("/app/data/target_portfolio/*.json")
print(f"   Found {len(portfolio_files)} portfolio files:")
for f in sorted(portfolio_files)[-3:]:  # Show last 3 files
    print(f"     {f}")

print("\n" + "=" * 60)
print("Debug complete")
print("=" * 60)
