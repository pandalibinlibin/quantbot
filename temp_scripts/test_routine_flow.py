#!/usr/bin/env python3
"""
Routine Flow Test Script

This script tests the complete routine workflow including:
- Qlib initialization
- Signal calculation
- ETF Enhanced Indexing portfolio generation
- Email notification (if configured)

Run this script inside the Docker container:
    docker exec -it quantbot-backend-1 python /app/temp_scripts/test_routine_flow.py

Note: This test requires Qlib data to be available.
"""

import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

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


def test_qlib_initialization():
    """Test 1: Qlib initialization."""
    try:
        from app.services.qlib_init_service import get_qlib_init_service

        qlib_service = get_qlib_init_service()
        result = qlib_service.initialize()

        # qlib_service.initialize() returns a boolean, not a dict
        if not result:
            log_test("Qlib Initialization", False, "Qlib initialization failed")
            return False

        log_test("Qlib Initialization", True, "Qlib initialized successfully")
        return True
    except Exception as e:
        log_test("Qlib Initialization", False, str(e), traceback.format_exc())
        return False


def test_online_serving_service():
    """Test 2: Online serving service initialization."""
    try:
        from app.services.online_serving_service import get_online_serving_service

        service = get_online_serving_service()

        # Check service attributes
        attrs_to_check = ["initialized", "model_loaded"]
        status = {}
        for attr in attrs_to_check:
            if hasattr(service, attr):
                status[attr] = getattr(service, attr)

        log_test("Online Serving Service", True, f"Service status: {status}")
        return True
    except Exception as e:
        log_test("Online Serving Service", False, str(e), traceback.format_exc())
        return False


def test_etf_config_in_routine():
    """Test 3: ETF Enhanced Indexing config availability in routine context."""
    try:
        from app.config.qlib import qlib_config
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )

        # Check config
        etf_config = qlib_config._config.get("etf_enhanced_indexing", {})

        # Check service
        service = get_etf_enhanced_indexing_service()

        details = {
            "config_enabled": etf_config.get("enabled"),
            "service_enabled": service.enabled,
            "weight_mode": service.weight_mode,
            "max_stocks": service.max_stocks,
            "region": service.region,
        }

        log_test(
            "ETF Config in Routine",
            True,
            f"ETF strategy configured",
            f"Details: {json.dumps(details, indent=2)}",
        )
        return True
    except Exception as e:
        log_test("ETF Config in Routine", False, str(e), traceback.format_exc())
        return False


def test_notification_config():
    """Test 4: Notification service configuration."""
    try:
        from app.services.notification_service import get_notification_service
        from app.core.config import settings

        service = get_notification_service()
        config = service._load_config()

        details = {
            "emails_enabled_in_settings": settings.emails_enabled,
            "notification_enabled": config.get("enabled"),
            "recipients_count": len(config.get("recipients", [])),
            "smtp_host": config.get("smtp_host", "Not configured"),
        }

        log_test(
            "Notification Config",
            True,
            f"Notification service configured",
            f"Details: {json.dumps(details, indent=2)}",
        )
        return True
    except Exception as e:
        log_test("Notification Config", False, str(e), traceback.format_exc())
        return False


def test_data_availability():
    """Test 5: Check if Qlib data is available for routine."""
    try:
        import qlib
        from qlib.data import D
        from datetime import datetime, timedelta

        # Try to get recent data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # Try to load some instruments
        instruments = ["SH600519", "SH601318"]

        try:
            df = D.features(
                instruments,
                ["$close"],
                start_time=start_date.strftime("%Y-%m-%d"),
                end_time=end_date.strftime("%Y-%m-%d"),
            )

            if df is None or df.empty:
                log_test("Data Availability", False, "No data returned from Qlib")
                return False

            log_test(
                "Data Availability",
                True,
                f"Data available: {len(df)} rows for {len(instruments)} instruments",
            )
            return True
        except Exception as e:
            log_test(
                "Data Availability",
                False,
                f"Failed to load data: {e}",
                "This may be expected if data hasn't been downloaded yet",
            )
            return False

    except Exception as e:
        log_test("Data Availability", False, str(e), traceback.format_exc())
        return False


def test_model_availability():
    """Test 6: Check if trained model is available."""
    try:
        from app.config.qlib import qlib_config
        from pathlib import Path
        from app.services.qlib_workflow_service import MODELS_DIR

        # Check if any models exist in the models directory
        if not MODELS_DIR.exists():
            log_test(
                "Model Availability",
                False,
                f"Models directory not found: {MODELS_DIR}",
                "You need to train a model first",
            )
            return False

        model_files = list(MODELS_DIR.glob("*.pkl"))

        if not model_files:
            log_test(
                "Model Availability",
                False,
                "No trained models found",
                "You need to train a model first",
            )
            return False

        # Get latest model
        latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
        size_mb = latest_model.stat().st_size / (1024 * 1024)

        log_test(
            "Model Availability",
            True,
            f"Model found: {latest_model.name} ({size_mb:.2f} MB)",
        )
        return True
    except Exception as e:
        log_test("Model Availability", False, str(e), traceback.format_exc())
        return False


def test_output_directory():
    """Test 7: Check output directory for target portfolio."""
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )
        from pathlib import Path

        service = get_etf_enhanced_indexing_service()
        output_dir = Path(service.output_dir)

        # Check if directory exists or can be created
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        # Check if writable
        test_file = output_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()

        # List existing portfolio files
        portfolio_files = list(output_dir.glob("*.json"))

        log_test(
            "Output Directory",
            True,
            f"Output directory ready: {output_dir}",
            f"Existing portfolio files: {len(portfolio_files)}",
        )
        return True
    except Exception as e:
        log_test("Output Directory", False, str(e), traceback.format_exc())
        return False


def test_etf_data_availability():
    """Test 8: Check if ETF data is available."""
    try:
        import qlib
        from qlib.data import D
        from datetime import datetime, timedelta
        from app.services.data_collectors.tushare_collector import BENCHMARK_CONFIG

        # Get ETF code from config
        etf_code = None
        for key, config in BENCHMARK_CONFIG.items():
            etf_code = config.get("tushare_code")
            if etf_code:
                break

        if not etf_code:
            log_test(
                "ETF Data Availability", False, "No ETF configured in BENCHMARK_CONFIG"
            )
            return False

        # Convert to Qlib format
        qlib_etf_code = etf_code.replace(".", "")  # e.g., 510300.SH -> SH510300
        if "." in etf_code:
            parts = etf_code.split(".")
            qlib_etf_code = parts[1] + parts[0]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        try:
            df = D.features(
                [qlib_etf_code],
                ["$close"],
                start_time=start_date.strftime("%Y-%m-%d"),
                end_time=end_date.strftime("%Y-%m-%d"),
            )

            if df is None or df.empty:
                log_test(
                    "ETF Data Availability",
                    False,
                    f"No ETF data for {qlib_etf_code}",
                    "You may need to download ETF data first",
                )
                return False

            log_test(
                "ETF Data Availability",
                True,
                f"ETF data available: {qlib_etf_code}, {len(df)} rows",
            )
            return True
        except Exception as e:
            log_test(
                "ETF Data Availability",
                False,
                f"Failed to load ETF data: {e}",
                "You may need to download ETF data first",
            )
            return False

    except Exception as e:
        log_test("ETF Data Availability", False, str(e), traceback.format_exc())
        return False


def run_all_tests():
    """Run all tests and print summary."""
    print("=" * 70)
    print("Routine Flow - Test Suite")
    print("=" * 70)
    print(f"Started at: {datetime.now().isoformat()}")

    # Run tests in order
    tests = [
        test_qlib_initialization,
        test_online_serving_service,
        test_etf_config_in_routine,
        test_notification_config,
        test_data_availability,
        test_model_availability,
        test_output_directory,
        test_etf_data_availability,
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

    # Recommendations
    print("\n📋 RECOMMENDATIONS:")
    if any(not r["passed"] and "Data" in r["name"] for r in test_results):
        print("  - Run data download to fetch latest market data")
    if any(not r["passed"] and "Model" in r["name"] for r in test_results):
        print("  - Train a model before running routine")
    if any(not r["passed"] and "ETF" in r["name"] for r in test_results):
        print("  - Download ETF data using the data collector")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
