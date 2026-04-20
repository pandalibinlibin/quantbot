#!/usr/bin/env python3
"""
Test script to verify factor computation fixes
"""

import sys

sys.path.append("/app")
import qlib
from app.services.factor_processor import FactorProcessor


def main():
    print("=== Testing Factor Computation Fixes ===")

    try:
        # Initialize Qlib
        print("Initializing Qlib...")
        qlib.init(provider_uri="/app/qlib_data", region="cn")
        print("✓ Qlib initialized successfully")

        # Test FactorProcessor with fixed instruments parameter
        print("\nTesting FactorProcessor...")
        processor = FactorProcessor()
        print("✓ FactorProcessor created successfully")

        # Test with a simple factor expression
        print("\nTesting factor computation with $close expression...")
        result = processor.compute_single_factor(
            factor_name="test_factor",
            expression="$close",
            instruments=None,  # This should now use D.instruments('all')
            start_time="2023-12-01",
            end_time="2023-12-08",
        )

        print(f"Result type: {type(result)}")
        if result is not None:
            print(f"✓ Factor computation successful!")
            print(f"Result shape: {result.shape}")
            print(f"Result columns: {list(result.columns)}")
            print(f"Result index type: {type(result.index)}")
            print("First few rows:")
            print(result.head())

            # Check for actual data
            non_null_count = result.count().sum()
            total_count = result.size
            print(f"\nData quality:")
            print(f"Non-null values: {non_null_count}/{total_count}")
            print(f"Coverage: {non_null_count/total_count*100:.1f}%")

        else:
            print("✗ Result is None - factor computation failed")

    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
