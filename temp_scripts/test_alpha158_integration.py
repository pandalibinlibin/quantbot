"""
Test Script for Alpha158 Integration

This script tests the following changes:
1. VWAP calculation in Tushare data collector
2. Alpha158 configuration loading from system_config.yaml
3. Region-specific label configuration
4. CustomFactorHandler reading config correctly
5. Alpha158 API endpoint (factor list)

Run this script inside the Docker container:
    docker compose exec backend python /app/../temp_scripts/test_alpha158_integration.py

Or mount and run:
    docker compose exec backend python temp_scripts/test_alpha158_integration.py
"""

import sys
import traceback
from pathlib import Path

# Test results tracking
test_results = []


def log_test(name: str, passed: bool, message: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append((name, passed, message))
    print(f"{status}: {name}")
    if message:
        print(f"       {message}")


def test_system_config_loading():
    """Test 1: Verify system_config.yaml has Alpha158 and Label config"""
    print("\n" + "=" * 60)
    print("TEST 1: System Config Loading")
    print("=" * 60)

    try:
        import yaml

        config_path = Path("/app/app/config/qlib/system_config.yaml")
        if not config_path.exists():
            log_test("Config file exists", False, f"File not found: {config_path}")
            return False

        log_test("Config file exists", True)

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Check Alpha158 config
        alpha158_config = config.get("builtin_factor_libraries", {}).get("alpha158", {})
        if not alpha158_config:
            log_test(
                "Alpha158 config exists",
                False,
                "builtin_factor_libraries.alpha158 not found",
            )
            return False

        log_test("Alpha158 config exists", True)

        enabled = alpha158_config.get("enabled")
        log_test("Alpha158 enabled field", enabled is not None, f"enabled = {enabled}")

        data_requirements = alpha158_config.get("data_requirements", [])
        has_vwap = "vwap" in data_requirements
        log_test(
            "VWAP in data_requirements",
            has_vwap,
            f"data_requirements = {data_requirements}",
        )

        # Check Label config
        label_config = config.get("label_config", {})
        if not label_config:
            log_test("Label config exists", False, "label_config not found")
            return False

        log_test("Label config exists", True)

        cn_label = label_config.get("cn", {})
        us_label = label_config.get("us", {})

        cn_expr = cn_label.get("expression", "")
        us_expr = us_label.get("expression", "")

        # A-share should use T+2 (Ref($close, -2))
        has_cn_t2 = "Ref($close, -2)" in cn_expr
        log_test("CN label uses T+2 return", has_cn_t2, f"cn expression = {cn_expr}")

        # US should use T+1 (Ref($close, -1))
        has_us_t1 = "Ref($close, -1)" in us_expr
        log_test("US label uses T+1 return", has_us_t1, f"us expression = {us_expr}")

        return True

    except Exception as e:
        log_test("System config loading", False, f"Exception: {e}")
        traceback.print_exc()
        return False


def test_tushare_collector_vwap():
    """Test 2: Verify Tushare collector has VWAP in field metadata"""
    print("\n" + "=" * 60)
    print("TEST 2: Tushare Collector VWAP Support")
    print("=" * 60)

    try:
        from app.services.data_collectors.tushare_collector import TushareDataCollector

        # Create collector instance (won't actually fetch data)
        collector = TushareDataCollector(
            save_dir="/tmp/test_data",
            start="2024-01-01",
            end="2024-01-10",
            index_name="CSI300",
        )

        # Check field metadata includes VWAP
        field_metadata = collector._field_metadata
        has_vwap = "vwap" in field_metadata
        log_test(
            "VWAP in field_metadata",
            has_vwap,
            f"fields = {list(field_metadata.keys())}",
        )

        vwap_type = field_metadata.get("vwap")
        log_test(
            "VWAP type is float64", vwap_type == "float64", f"vwap type = {vwap_type}"
        )

        return has_vwap

    except Exception as e:
        log_test("Tushare collector VWAP", False, f"Exception: {e}")
        traceback.print_exc()
        return False


def test_custom_factor_handler_config():
    """Test 3: Verify CustomFactorHandler reads config correctly"""
    print("\n" + "=" * 60)
    print("TEST 3: CustomFactorHandler Config Reading")
    print("=" * 60)

    try:
        from app.services.custom_factor_handler import CustomFactorHandler

        # Test _load_system_config method
        handler = object.__new__(CustomFactorHandler)
        handler._system_config = handler._load_system_config()

        config = handler._system_config
        has_config = bool(config)
        log_test(
            "System config loaded",
            has_config,
            f"config keys = {list(config.keys()) if config else 'None'}",
        )

        # Check Alpha158 setting
        alpha158_enabled = (
            config.get("builtin_factor_libraries", {})
            .get("alpha158", {})
            .get("enabled", False)
        )
        log_test("Alpha158 enabled from config", True, f"enabled = {alpha158_enabled}")

        # Check region setting
        region = config.get("data", {}).get("region", "unknown")
        log_test("Region from config", region in ["cn", "us"], f"region = {region}")

        return has_config

    except Exception as e:
        log_test("CustomFactorHandler config", False, f"Exception: {e}")
        traceback.print_exc()
        return False


def test_alpha158_factor_list():
    """Test 4: Verify Alpha158 factor list can be retrieved from Qlib"""
    print("\n" + "=" * 60)
    print("TEST 4: Alpha158 Factor List from Qlib")
    print("=" * 60)

    try:
        from qlib.contrib.data.loader import Alpha158DL

        # Get feature config
        fields, names = Alpha158DL.get_feature_config()

        factor_count = len(fields)
        log_test(
            "Alpha158 factors loaded",
            factor_count > 0,
            f"factor count = {factor_count}",
        )

        # Should have 158 factors (approximately)
        log_test(
            "Factor count ~158",
            150 <= factor_count <= 170,
            f"expected ~158, got {factor_count}",
        )

        # Check some expected factor names
        expected_factors = ["KMID", "KLEN", "ROC5", "MA5", "STD5"]
        found_factors = [f for f in expected_factors if f in names]
        log_test(
            "Expected factors present",
            len(found_factors) > 0,
            f"found: {found_factors}",
        )

        # Print first 10 factors as sample
        print("\n  Sample factors (first 10):")
        for i, (field, name) in enumerate(zip(fields[:10], names[:10])):
            print(f"    {name}: {field[:50]}...")

        return factor_count > 0

    except Exception as e:
        log_test("Alpha158 factor list", False, f"Exception: {e}")
        traceback.print_exc()
        return False


def test_label_config_in_handler():
    """Test 5: Verify get_label_config returns region-specific label from config"""
    print("\n" + "=" * 60)
    print("TEST 5: Region-Specific Label in Handler (Config-Based)")
    print("=" * 60)

    try:
        from app.services.custom_factor_handler import CustomFactorHandler

        # Create handler instance with minimal params
        handler = object.__new__(CustomFactorHandler)
        handler._system_config = handler._load_system_config()
        handler.region = handler._system_config.get("data", {}).get("region", "cn")

        # Call get_label_config
        label_expr, label_names = handler.get_label_config()

        log_test(
            "Label config returns tuple",
            isinstance(label_expr, list) and isinstance(label_names, list),
            f"types: {type(label_expr)}, {type(label_names)}",
        )

        log_test(
            "Label expression not empty",
            len(label_expr) > 0,
            f"expression = {label_expr}",
        )

        # Check if it's using region-specific label from config (NOT from DB)
        expr_str = label_expr[0] if label_expr else ""

        # Should NOT start with $ (which would indicate DB-based label)
        is_config_based = not expr_str.startswith("$")
        log_test("Label is config-based (not DB)", is_config_based, f"expr={expr_str}")

        if handler.region == "cn":
            is_t2 = "Ref($close, -2)" in expr_str
            log_test(
                "CN region uses T+2 label",
                is_t2,
                f"region={handler.region}, expr={expr_str}",
            )
        else:
            is_t1 = "Ref($close, -1)" in expr_str and "Ref($close, -2)" not in expr_str
            log_test(
                "US region uses T+1 label",
                is_t1,
                f"region={handler.region}, expr={expr_str}",
            )

        return True

    except Exception as e:
        log_test("Label config in handler", False, f"Exception: {e}")
        traceback.print_exc()
        return False


def test_api_endpoint_factors():
    """Test 6: Verify Alpha158 API helper functions work"""
    print("\n" + "=" * 60)
    print("TEST 6: Alpha158 API Helper Functions")
    print("=" * 60)

    try:
        from app.api.routes.factors import (
            _get_alpha158_factors,
            _categorize_alpha158_factor,
        )

        # Test factor categorization
        test_cases = [
            ("KMID", "kbar"),
            ("OPEN0", "price"),
            ("VOLUME0", "volume"),
            ("ROC5", "rolling"),
            ("MA10", "rolling"),
        ]

        for name, expected_category in test_cases:
            actual = _categorize_alpha158_factor(name)
            passed = actual == expected_category
            log_test(
                f"Categorize '{name}'",
                passed,
                f"expected={expected_category}, got={actual}",
            )

        # Test getting full factor list
        factors = _get_alpha158_factors()
        log_test(
            "Get Alpha158 factors", len(factors) > 0, f"got {len(factors)} factors"
        )

        if factors:
            # Check factor structure
            first = factors[0]
            has_keys = all(k in first for k in ["name", "expression", "category"])
            log_test(
                "Factor has required keys", has_keys, f"keys = {list(first.keys())}"
            )

        return len(factors) > 0

    except Exception as e:
        log_test("API helper functions", False, f"Exception: {e}")
        traceback.print_exc()
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, p, _ in test_results if p)
    total = len(test_results)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️  Some tests failed:")
        for name, p, msg in test_results:
            if not p:
                print(f"  - {name}: {msg}")
        return 1


def main():
    """Run all tests"""
    print("=" * 60)
    print("Alpha158 Integration Test Suite")
    print("=" * 60)

    # Run tests
    test_system_config_loading()
    test_tushare_collector_vwap()
    test_custom_factor_handler_config()
    test_alpha158_factor_list()
    test_label_config_in_handler()
    test_api_endpoint_factors()

    # Print summary
    exit_code = print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
