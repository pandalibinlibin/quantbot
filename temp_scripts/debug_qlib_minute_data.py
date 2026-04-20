#!/usr/bin/env python3
"""
Debug script to test Qlib minute data loading
"""

import sys
import os

sys.path.append("/app")

import qlib
from qlib import init
from qlib.data import D
import pandas as pd
from pathlib import Path


def test_qlib_minute_data():
    """Test Qlib minute data loading"""

    print("=== Qlib Minute Data Debug ===")

    # Initialize Qlib using the same method as main application
    try:
        qlib_data_path = "/app/qlib_data"
        # Use the same initialization as qlib_init_service
        init(
            provider_uri=qlib_data_path,  # Direct path, not file:// format
            region="cn",
            expression_cache=None,
        )
        print(f"✓ Qlib initialized with data path: {qlib_data_path}")
    except Exception as e:
        print(f"✗ Qlib initialization failed: {e}")
        return

    # Check data directory structure
    print("\n=== Data Directory Structure ===")
    qlib_path = Path(qlib_data_path)
    if qlib_path.exists():
        print(f"✓ Qlib data directory exists: {qlib_path}")

        # Check for minute data
        minute_features_path = qlib_path / "features" / "1min"
        if minute_features_path.exists():
            print(f"✓ Minute features directory exists: {minute_features_path}")

            # List some files
            files = list(minute_features_path.glob("*.bin"))[:5]
            print(f"Sample files: {[f.name for f in files]}")
        else:
            print(f"✗ Minute features directory not found: {minute_features_path}")

        # Check for day data (for comparison)
        day_features_path = qlib_path / "features" / "day"
        if day_features_path.exists():
            print(f"✓ Day features directory exists: {day_features_path}")
        else:
            print(f"✗ Day features directory not found: {day_features_path}")
    else:
        print(f"✗ Qlib data directory not found: {qlib_path}")
        return

    # Test basic data loading
    print("\n=== Test Basic Data Loading ===")

    # Get available instruments
    try:
        instruments = D.instruments(market="csi300")
        print(f"✓ Found {len(instruments)} instruments in CSI300")
        test_symbol = instruments[0] if instruments else None
        print(f"Test symbol: {test_symbol}")
    except Exception as e:
        print(f"✗ Failed to get instruments: {e}")
        return

    if not test_symbol:
        print("✗ No test symbol available")
        return

    # Test minute data loading
    print(f"\n=== Test Minute Data Loading for {test_symbol} ===")

    try:
        # Test basic fields
        data = D.features(
            instruments=[test_symbol],
            fields=["$close", "$high", "$low", "$open", "$volume"],
            start_time="2026-02-11",
            end_time="2026-02-11",
            freq="1min",
        )

        if data is not None and not data.empty:
            print(f"✓ Successfully loaded minute data: shape={data.shape}")
            print(f"Data columns: {list(data.columns)}")
            print(f"Data index: {data.index}")
            print(f"Sample data:\n{data.head()}")

            # Test factor expressions
            print(f"\n=== Test Factor Expressions ===")

            # Test Daily_Return expression
            try:
                daily_return_data = D.features(
                    instruments=[test_symbol],
                    fields=["($close / Ref($close, 1)) - 1"],
                    start_time="2026-02-11",
                    end_time="2026-02-11",
                    freq="1min",
                )

                if daily_return_data is not None and not daily_return_data.empty:
                    print(
                        f"✓ Daily_Return expression works: shape={daily_return_data.shape}"
                    )
                    print(f"Sample values:\n{daily_return_data.head()}")
                else:
                    print("✗ Daily_Return expression returned empty data")

            except Exception as e:
                print(f"✗ Daily_Return expression failed: {e}")

            # Test HL_Mid_Price expression
            try:
                hl_mid_data = D.features(
                    instruments=[test_symbol],
                    fields=["($high + $low) / 2"],
                    start_time="2026-02-11",
                    end_time="2026-02-11",
                    freq="1min",
                )

                if hl_mid_data is not None and not hl_mid_data.empty:
                    print(f"✓ HL_Mid_Price expression works: shape={hl_mid_data.shape}")
                    print(f"Sample values:\n{hl_mid_data.head()}")
                else:
                    print("✗ HL_Mid_Price expression returned empty data")

            except Exception as e:
                print(f"✗ HL_Mid_Price expression failed: {e}")

            # Test MA5 expression
            try:
                ma5_data = D.features(
                    instruments=[test_symbol],
                    fields=["Mean($close, 5)"],
                    start_time="2026-02-11",
                    end_time="2026-02-11",
                    freq="1min",
                )

                if ma5_data is not None and not ma5_data.empty:
                    print(f"✓ MA5 expression works: shape={ma5_data.shape}")
                    print(f"Sample values:\n{ma5_data.head()}")
                else:
                    print("✗ MA5 expression returned empty data")

            except Exception as e:
                print(f"✗ MA5 expression failed: {e}")

        else:
            print("✗ Failed to load minute data - empty result")

    except Exception as e:
        print(f"✗ Failed to load minute data: {e}")

    # Test day data for comparison
    print(f"\n=== Test Day Data Loading for {test_symbol} (Comparison) ===")

    try:
        day_data = D.features(
            instruments=[test_symbol],
            fields=["$close", "$high", "$low", "$open", "$volume"],
            start_time="2026-02-11",
            end_time="2026-02-11",
            freq="day",
        )

        if day_data is not None and not day_data.empty:
            print(f"✓ Successfully loaded day data: shape={day_data.shape}")
            print(f"Sample data:\n{day_data.head()}")
        else:
            print("✗ Failed to load day data - empty result")

    except Exception as e:
        print(f"✗ Failed to load day data: {e}")


if __name__ == "__main__":
    test_qlib_minute_data()
