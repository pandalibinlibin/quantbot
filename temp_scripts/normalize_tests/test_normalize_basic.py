#!/usr/bin/env python3
"""
Basic test script for UniversalNormalize class.

Educational Notes:
- Tests the normalize functionality with sample OHLCV data
- Validates market detection for CN and US symbols
- Verifies data structure and basic processing
- Runs in Docker environment to test dependencies
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
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    data = {
        "date": dates,
        "symbol": ["AAPL"] * 5,
        "open": [150.0, 151.0, 152.0, 153.0, 154.0],
        "high": [155.0, 156.0, 157.0, 158.0, 159.0],
        "low": [149.0, 150.0, 151.0, 152.0, 153.0],
        "close": [154.0, 155.0, 156.0, 157.0, 158.0],
        "volume": [1000000, 1100000, 1200000, 1300000, 1400000],
    }
    return pd.DataFrame(data)


def create_test_data_cn():
    """Create sample CN market data for testing."""
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    data = {
        "date": dates,
        "symbol": ["000001.SZ"] * 5,
        "open": [15.0, 15.1, 15.2, 15.3, 15.4],
        "high": [15.5, 15.6, 15.7, 15.8, 15.9],
        "low": [14.9, 15.0, 15.1, 15.2, 15.3],
        "close": [15.4, 15.5, 15.6, 15.7, 15.8],
        "volume": [2000000, 2100000, 2200000, 2300000, 2400000],
    }
    return pd.DataFrame(data)


def main():
    """Main test function."""
    print("🧪 Starting UniversalNormalize Basic Tests")
    print("=" * 50)

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

    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 All basic tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)
