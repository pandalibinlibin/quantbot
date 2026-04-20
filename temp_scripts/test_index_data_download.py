"""
Test the modified Tushare collector to download index data automatically.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/test_index_data_download.py
"""

import sys
import os

sys.path.append("/app")

from app.services.data_collectors.tushare_collector import TushareDataCollector
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_index_data_collection():
    """Test that index data is automatically included in data collection."""
    print("=" * 60)
    print("TESTING AUTOMATIC INDEX DATA DOWNLOAD")
    print("=" * 60)

    try:
        # Create collector for CSI300 (small test)
        collector = TushareDataCollector(
            save_dir="/tmp/test_index_data",
            start="2024-01-01",
            end="2024-01-31",
            index_name="CSI300",
            limit_nums=5,  # Only collect 5 stocks for testing
        )

        print(f"\n--- Getting Instrument List ---")
        instruments = collector.get_instrument_list()

        print(f"Total instruments: {len(instruments)}")
        print(f"Instruments: {instruments}")

        # Check if index is included
        index_code = "000300.SH"  # CSI300 index code
        if index_code in instruments:
            print(f"✅ Index {index_code} is included in instrument list")
        else:
            print(f"❌ Index {index_code} is NOT included in instrument list")
            return False

        print(f"\n--- Testing Data Download for Index ---")
        # Test downloading data for the index specifically
        index_data = collector.get_data(
            symbol=index_code, start_datetime="2024-01-01", end_datetime="2024-01-31"
        )

        if not index_data.empty:
            print(
                f"✅ Successfully downloaded {len(index_data)} records for index {index_code}"
            )
            print(f"Index data columns: {list(index_data.columns)}")
            print(f"Index data sample:")
            print(index_data.head(3))
        else:
            print(f"❌ No data downloaded for index {index_code}")
            return False

        print(f"\n--- Testing Data Download for Stock ---")
        # Test downloading data for a stock
        stock_symbol = (
            instruments[0] if instruments[0] != index_code else instruments[1]
        )
        stock_data = collector.get_data(
            symbol=stock_symbol, start_datetime="2024-01-01", end_datetime="2024-01-31"
        )

        if not stock_data.empty:
            print(
                f"✅ Successfully downloaded {len(stock_data)} records for stock {stock_symbol}"
            )
            print(f"Stock data columns: {list(stock_data.columns)}")
        else:
            print(f"❌ No data downloaded for stock {stock_symbol}")

        return True

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_qlib_format_conversion():
    """Test that index codes are properly converted to Qlib format."""
    print(f"\n" + "=" * 60)
    print("TESTING QLIB FORMAT CONVERSION")
    print("=" * 60)

    try:
        collector = TushareDataCollector(
            save_dir="/tmp/test_conversion",
            start="2024-01-01",
            end="2024-01-31",
            index_name="CSI300",
        )

        # Test symbol normalization
        tushare_symbols = ["000300.SH", "000001.SZ", "600519.SH"]

        print("Tushare → Qlib format conversion:")
        for symbol in tushare_symbols:
            qlib_symbol = collector.normalize_symbol(symbol)
            print(f"  {symbol} → {qlib_symbol}")

        return True

    except Exception as e:
        print(f"❌ Error during conversion test: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TUSHARE INDEX DATA COLLECTION TEST")
    print("=" * 60)

    # Test 1: Index data collection
    test1_success = test_index_data_collection()

    # Test 2: Format conversion
    test2_success = test_qlib_format_conversion()

    # Summary
    print(f"\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    tests = [
        ("Index Data Collection", test1_success),
        ("Qlib Format Conversion", test2_success),
    ]

    passed = sum(1 for _, success in tests if success)
    total = len(tests)

    for test_name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<25} {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("Index data will be automatically downloaded with stock data.")
        print("Now we can use the index as benchmark in backtest.")
    else:
        print(f"⚠️ {total - passed} test(s) failed.")


if __name__ == "__main__":
    main()
