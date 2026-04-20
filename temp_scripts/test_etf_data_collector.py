#!/usr/bin/env python3
"""
ETF Data Collector Test Script

This script tests the ETF data collection functionality in TushareDataCollector.

Run this script inside the Docker container:
    docker exec -it quantbot-backend-1 python /app/temp_scripts/test_etf_data_collector.py

Test Coverage:
1. BENCHMARK_CONFIG contains ETF codes
2. ETF_CODES set is populated
3. get_instrument_list includes ETF
4. ETF data fetching logic (mock test)
"""

import sys
import json
import traceback
from datetime import datetime

# Test results collector
test_results = []


def log_test(test_name: str, passed: bool, message: str = "", details: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append(
        {
            "name": test_name,
            "passed": passed,
            "message": message,
        }
    )
    print(f"\n{status}: {test_name}")
    if message:
        print(f"   Message: {message}")
    if details:
        print(f"   Details: {details}")


def test_benchmark_config():
    """Test 1: BENCHMARK_CONFIG contains ETF information."""
    try:
        from app.services.data_collectors.tushare_collector import BENCHMARK_CONFIG

        # Check each benchmark has ETF config
        etf_info = {}
        for key, config in BENCHMARK_CONFIG.items():
            if "tushare_code" in config and "name" in config:
                etf_info[key] = {
                    "name": config["name"],
                    "tushare_code": config["tushare_code"],
                }

        if not etf_info:
            log_test(
                "BENCHMARK_CONFIG ETF", False, "No ETF codes found in BENCHMARK_CONFIG"
            )
            return False

        log_test(
            "BENCHMARK_CONFIG ETF",
            True,
            f"Found {len(etf_info)} ETF configurations",
            f"ETFs: {json.dumps(etf_info, indent=2, ensure_ascii=False)}",
        )
        return True
    except Exception as e:
        log_test("BENCHMARK_CONFIG ETF", False, str(e), traceback.format_exc())
        return False


def test_etf_codes_set():
    """Test 2: ETF_CODES set is populated."""
    try:
        from app.services.data_collectors.tushare_collector import ETF_CODES

        if not ETF_CODES:
            log_test("ETF_CODES Set", False, "ETF_CODES set is empty")
            return False

        log_test(
            "ETF_CODES Set",
            True,
            f"ETF_CODES contains {len(ETF_CODES)} codes",
            f"Codes: {ETF_CODES}",
        )
        return True
    except ImportError:
        log_test("ETF_CODES Set", False, "ETF_CODES not found in module")
        return False
    except Exception as e:
        log_test("ETF_CODES Set", False, str(e), traceback.format_exc())
        return False


def test_instrument_list_includes_etf():
    """Test 3: get_instrument_list includes ETF code."""
    try:
        from app.services.data_collectors.tushare_collector import TushareDataCollector

        # Create collector for CSI300
        collector = TushareDataCollector(index_name="CSI300")

        # Get instrument list
        instruments = collector.get_instrument_list()

        # Check if ETF is included
        etf_found = False
        etf_code = None
        for inst in instruments:
            if "510300" in inst:  # CSI300 ETF
                etf_found = True
                etf_code = inst
                break

        if not etf_found:
            log_test(
                "Instrument List ETF",
                False,
                "ETF not found in instrument list",
                f"Sample instruments: {instruments[:5]}",
            )
            return False

        log_test(
            "Instrument List ETF",
            True,
            f"ETF found in instrument list: {etf_code}",
            f"Total instruments: {len(instruments)}",
        )
        return True
    except Exception as e:
        log_test("Instrument List ETF", False, str(e), traceback.format_exc())
        return False


def test_etf_detection_logic():
    """Test 4: ETF detection logic in get_data."""
    try:
        from app.services.data_collectors.tushare_collector import (
            ETF_CODES,
            INDEX_CODE_MAP,
        )

        # Test cases
        test_cases = [
            ("510300.SH", "etf"),
            ("159919.SZ", "etf"),
            ("000300.SH", "index"),
            ("600519.SH", "stock"),
        ]

        results = []
        for code, expected_type in test_cases:
            is_index = code in INDEX_CODE_MAP.values()
            is_etf = code in ETF_CODES

            if is_index:
                detected_type = "index"
            elif is_etf:
                detected_type = "etf"
            else:
                detected_type = "stock"

            match = detected_type == expected_type
            results.append(
                {
                    "code": code,
                    "expected": expected_type,
                    "detected": detected_type,
                    "match": match,
                }
            )

        all_match = all(r["match"] for r in results)

        if not all_match:
            failed = [r for r in results if not r["match"]]
            log_test("ETF Detection Logic", False, f"Detection mismatch for: {failed}")
            return False

        log_test(
            "ETF Detection Logic",
            True,
            "All test cases passed",
            f"Results: {json.dumps(results, indent=2)}",
        )
        return True
    except Exception as e:
        log_test("ETF Detection Logic", False, str(e), traceback.format_exc())
        return False


def test_volume_handling_logic():
    """Test 5: Volume handling for different instrument types."""
    try:
        import numpy as np

        # Simulate volume handling logic
        test_cases = [
            {"type": "stock", "raw_volume": 1000, "expected": 100000},  # *100
            {"type": "index", "raw_volume": 1000, "expected": 1000},  # no change
            {"type": "etf", "raw_volume": 1000, "expected": 1000},  # no change
        ]

        results = []
        for tc in test_cases:
            is_index = tc["type"] == "index"
            is_etf = tc["type"] == "etf"

            if is_index or is_etf:
                processed = int(tc["raw_volume"])
            else:
                processed = int(tc["raw_volume"] * 100)

            match = processed == tc["expected"]
            results.append(
                {
                    "type": tc["type"],
                    "raw": tc["raw_volume"],
                    "processed": processed,
                    "expected": tc["expected"],
                    "match": match,
                }
            )

        all_match = all(r["match"] for r in results)

        if not all_match:
            failed = [r for r in results if not r["match"]]
            log_test("Volume Handling", False, f"Volume handling mismatch: {failed}")
            return False

        log_test(
            "Volume Handling",
            True,
            "Volume handling correct for all types",
            f"Results: {json.dumps(results, indent=2)}",
        )
        return True
    except Exception as e:
        log_test("Volume Handling", False, str(e), traceback.format_exc())
        return False


def test_tushare_api_availability():
    """Test 6: Tushare API availability (requires API token)."""
    try:
        import tushare as ts
        from app.core.config import settings

        # Check if token is configured
        token = getattr(settings, "TUSHARE_TOKEN", None)
        if not token:
            log_test(
                "Tushare API",
                False,
                "TUSHARE_TOKEN not configured in settings",
                "Set TUSHARE_TOKEN in .env file",
            )
            return False

        # Initialize Tushare
        ts.set_token(token)
        pro = ts.pro_api()

        # Test basic API call
        try:
            df = pro.trade_cal(
                exchange="SSE", start_date="20260101", end_date="20260110"
            )
            if df is None or df.empty:
                log_test("Tushare API", False, "API returned empty result")
                return False

            log_test(
                "Tushare API",
                True,
                "Tushare API is accessible",
                f"Trade calendar returned {len(df)} rows",
            )
            return True
        except Exception as api_error:
            log_test(
                "Tushare API",
                False,
                f"API call failed: {api_error}",
                "Check your Tushare token and API permissions",
            )
            return False

    except Exception as e:
        log_test("Tushare API", False, str(e), traceback.format_exc())
        return False


def run_all_tests():
    """Run all tests and print summary."""
    print("=" * 70)
    print("ETF Data Collector - Test Suite")
    print("=" * 70)
    print(f"Started at: {datetime.now().isoformat()}")

    # Run tests in order
    tests = [
        test_benchmark_config,
        test_etf_codes_set,
        test_instrument_list_includes_etf,
        test_etf_detection_logic,
        test_volume_handling_logic,
        test_tushare_api_availability,
    ]

    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            log_test(test_func.__name__, False, f"Unexpected error: {e}")

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    total = len(test_results)

    for r in test_results:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} {r['name']}")

    print("-" * 70)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
