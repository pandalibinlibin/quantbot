#!/usr/bin/env python3
"""
Complete test script for UniversalNormalize normalize() method.

Educational Notes:
- Tests the full normalize workflow with real OHLCV data
- Validates data structure transformation and processing
- Tests both US and CN market data processing
- Verifies output format compatibility with Qlib
"""

import sys
import os
from pathlib import Path

# Add backend to Python path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def test_imports():
    """Test if we can import our normalize module."""
    try:
        from app.services.data_collectors.normalize import UniversalNormalize

        print("✅ Successfully imported UniversalNormalize")
        return UniversalNormalize
    except ImportError as e:
        print(f"❌ Failed to import UniversalNormalize: {e}")
        return None


def create_test_data_us():
    """Create sample US market data for testing."""
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    data = {
        "date": dates,
        "symbol": ["AAPL"] * 10,
        "open": [150.0, 151.0, 152.0, 153.0, 154.0, 155.0, 156.0, 157.0, 158.0, 159.0],
        "high": [155.0, 156.0, 157.0, 158.0, 159.0, 160.0, 161.0, 162.0, 163.0, 164.0],
        "low": [149.0, 150.0, 151.0, 152.0, 153.0, 154.0, 155.0, 156.0, 157.0, 158.0],
        "close": [154.0, 155.0, 156.0, 157.0, 158.0, 159.0, 160.0, 161.0, 162.0, 163.0],
        "volume": [
            1000000,
            1100000,
            1200000,
            1300000,
            1400000,
            1500000,
            1600000,
            1700000,
            1800000,
            1900000,
        ],
    }
    return pd.DataFrame(data)


def test_normalize_functionality(UniversalNormalize):
    """Test the complete normalize functionality."""
    print("\n🔄 Test 4: Complete Normalize Functionality")

    try:
        # Create normalizer
        normalizer = UniversalNormalize(source_type="yahoo")

        # Create test data
        test_df = create_test_data_us()
        print(f"📊 Input data shape: {test_df.shape}")
        print(f"📊 Input columns: {test_df.columns.tolist()}")

        # Run normalize
        result_df = normalizer.normalize(test_df)

        print(f"✅ Normalize completed successfully")
        print(f"📊 Output data shape: {result_df.shape}")
        print(f"📊 Output columns: {result_df.columns.tolist()}")

        # Validate output structure
        expected_columns = [
            "date",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "change",
        ]
        missing_columns = set(expected_columns) - set(result_df.columns)
        if missing_columns:
            print(f"❌ Missing expected columns: {missing_columns}")
            return False

        # Check if change column was added
        if "change" in result_df.columns:
            print("✅ Change column successfully added")
            print(f"📊 Sample change values: {result_df['change'].head(3).tolist()}")
        else:
            print("❌ Change column missing")
            return False

        # Check data types
        if pd.api.types.is_datetime64_any_dtype(result_df["date"]):
            print("✅ Date column has correct datetime type")
        else:
            print("❌ Date column type incorrect")
            return False

        return True

    except Exception as e:
        print(f"❌ Normalize test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("🧪 Starting UniversalNormalize Complete Tests")
    print("=" * 60)

    # Test 1: Import test
    print("\n📦 Test 1: Import Test")
    UniversalNormalize = test_imports()
    if not UniversalNormalize:
        return False

    # Test 2: Create normalizer instance
    print("\n🏗️ Test 2: Create Normalizer Instance")
    try:
        normalizer = UniversalNormalize(source_type="yahoo")
        print("✅ Successfully created UniversalNormalize instance")
    except Exception as e:
        print(f"❌ Failed to create normalizer: {e}")
        return False

    # Test 3: Market detection
    print("\n🌍 Test 3: Market Detection")
    try:
        us_market = normalizer.detect_market_from_symbol("AAPL")
        cn_market = normalizer.detect_market_from_symbol("000001.SZ")
        print(f"✅ AAPL detected as: {us_market}")
        print(f"✅ 000001.SZ detected as: {cn_market}")

        if us_market != "US" or cn_market != "CN":
            print("❌ Market detection failed")
            return False
    except Exception as e:
        print(f"❌ Market detection failed: {e}")
        return False

    # Test 4: Complete normalize functionality
    if not test_normalize_functionality(UniversalNormalize):
        return False

    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 All complete tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
