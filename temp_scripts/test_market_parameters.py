#!/usr/bin/env python3
"""
Test different market parameters for D.instruments()
"""

import sys

sys.path.append("/app")

import qlib
from qlib.data import D


def test_market_parameters():
    """Test different market parameters"""

    print("=== Test Market Parameters ===")

    # Initialize Qlib
    try:
        qlib.init(provider_uri="/app/qlib_data", region="cn")
        print("✓ Qlib initialized successfully with region='cn'")
    except Exception as e:
        print(f"✗ Failed to initialize Qlib: {e}")
        return

    # Test different market parameters
    market_params = ["all", "cn", "csi300", "csi500", None]

    for market in market_params:
        print(f"\n--- Testing market='{market}' ---")
        try:
            if market is None:
                instruments = D.instruments()
            else:
                instruments = D.instruments(market=market)

            instruments_list = list(instruments)
            print(f"✓ Found {len(instruments_list)} instruments")

            if instruments_list:
                print("First 5 instruments:")
                for i, inst in enumerate(instruments_list[:5]):
                    print(f"  {i+1}. '{inst}'")
            else:
                print("  No instruments found")

        except Exception as e:
            print(f"✗ Error with market='{market}': {e}")

    # Test with specific stock pool
    print(f"\n--- Testing with stock_pool ---")
    try:
        # Try to get instruments without market parameter
        instruments = D.instruments()
        instruments_list = list(instruments)
        print(f"✓ D.instruments() (no params): {len(instruments_list)} instruments")

        if instruments_list:
            print("First 5 instruments:")
            for i, inst in enumerate(instruments_list[:5]):
                print(f"  {i+1}. '{inst}'")

    except Exception as e:
        print(f"✗ Error with D.instruments(): {e}")


if __name__ == "__main__":
    test_market_parameters()
