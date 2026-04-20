#!/usr/bin/env python3
"""
Test the specific issue in factor processor
"""

import sys
import os

sys.path.append("/app")

import qlib
from qlib import init
from qlib.data import D
import pandas as pd


def test_factor_processor_issue():
    """Test the specific factor processor issue"""

    print("=== Factor Processor Issue Test ===")

    # Initialize Qlib
    try:
        qlib_data_path = "/app/qlib_data"
        init(
            provider_uri=qlib_data_path,
            region="cn",
            expression_cache=None,
        )
        print(f"✓ Qlib initialized")
    except Exception as e:
        print(f"✗ Qlib initialization failed: {e}")
        return

    # Test the exact same calls as factor processor
    print("\n=== Test Factor Processor Logic ===")

    # This is what factor processor does:
    # 1. Get instruments for market
    try:
        instruments = D.instruments(market="csi300")
        print(f"✓ Got {len(instruments)} instruments from CSI300 market")
        print(f"Sample instruments: {instruments[:5]}")
    except Exception as e:
        print(f"✗ Failed to get CSI300 instruments: {e}")
        return

    # 2. Try to compute factor with all instruments
    print(f"\n=== Test Factor Computation with All {len(instruments)} Instruments ===")

    try:
        factor_data = D.features(
            instruments=instruments,  # All 300 instruments
            fields=["($high + $low) / 2"],  # Simple HL_Mid_Price
            start_time="2026-02-11",
            end_time="2026-02-11",
            freq="1min",
        )

        if factor_data is not None and not factor_data.empty:
            print(
                f"✓ Successfully computed factor for all instruments: shape={factor_data.shape}"
            )
            print(
                f"Unique instruments in result: {len(factor_data.index.get_level_values('instrument').unique())}"
            )
        else:
            print("✗ Factor computation returned empty data")

    except Exception as e:
        print(f"✗ Factor computation failed: {e}")

    # 3. Test with smaller subset
    print(f"\n=== Test Factor Computation with Small Subset (5 instruments) ===")

    try:
        small_instruments = instruments[:5]
        factor_data_small = D.features(
            instruments=small_instruments,
            fields=["($high + $low) / 2"],
            start_time="2026-02-11",
            end_time="2026-02-11",
            freq="1min",
        )

        if factor_data_small is not None and not factor_data_small.empty:
            print(
                f"✓ Successfully computed factor for 5 instruments: shape={factor_data_small.shape}"
            )
            print(
                f"Instruments in result: {factor_data_small.index.get_level_values('instrument').unique().tolist()}"
            )
        else:
            print("✗ Small subset factor computation returned empty data")

    except Exception as e:
        print(f"✗ Small subset factor computation failed: {e}")

    # 4. Check which instruments have data
    print(f"\n=== Check Data Availability for Each Instrument ===")

    available_instruments = []
    missing_instruments = []

    for i, instrument in enumerate(instruments[:10]):  # Test first 10
        try:
            data = D.features(
                instruments=[instrument],
                fields=["$close"],
                start_time="2026-02-11",
                end_time="2026-02-11",
                freq="1min",
            )

            if data is not None and not data.empty:
                available_instruments.append(instrument)
                if i < 3:  # Show details for first 3
                    print(f"✓ {instrument}: {data.shape[0]} records")
            else:
                missing_instruments.append(instrument)
                if i < 3:  # Show details for first 3
                    print(f"✗ {instrument}: No data")

        except Exception as e:
            missing_instruments.append(instrument)
            if i < 3:  # Show details for first 3
                print(f"✗ {instrument}: Error - {e}")

    print(f"\nSummary (first 10 instruments):")
    print(f"✓ Available: {len(available_instruments)}")
    print(f"✗ Missing: {len(missing_instruments)}")

    if missing_instruments:
        print(f"Missing instruments: {missing_instruments}")


if __name__ == "__main__":
    test_factor_processor_issue()
