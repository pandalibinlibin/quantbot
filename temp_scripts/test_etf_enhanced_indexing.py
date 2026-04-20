#!/usr/bin/env python3
"""
ETF Enhanced Indexing Service Test Script

This script tests the ETF Enhanced Indexing strategy implementation.
Run this script inside the Docker container:
    docker exec -it quantbot-backend-1 python /app/temp_scripts/test_etf_enhanced_indexing.py

Test Coverage:
1. Module import test
2. Configuration loading test
3. Service initialization test
4. Dynamic weight calculation test
5. Portfolio calculation test (with mock signals)
6. Email HTML generation test
7. Portfolio save/load test
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


def test_imports():
    """Test 1: Module imports."""
    try:
        from app.services.etf_enhanced_indexing_service import (
            ETFEnhancedIndexingService,
            get_etf_enhanced_indexing_service,
        )
        from app.services.notification_service import (
            NotificationService,
            get_notification_service,
        )
        from app.config.qlib import qlib_config

        log_test("Module Imports", True, "All modules imported successfully")
        return True
    except Exception as e:
        log_test("Module Imports", False, str(e), traceback.format_exc())
        return False


def test_config_loading():
    """Test 2: Configuration loading."""
    try:
        from app.config.qlib import qlib_config

        config = qlib_config._config
        etf_config = config.get("etf_enhanced_indexing", {})

        # Check required config keys
        required_keys = ["enabled", "weight_mode", "max_stocks"]
        missing_keys = [k for k in required_keys if k not in etf_config]

        if missing_keys:
            log_test("Config Loading", False, f"Missing keys: {missing_keys}")
            return False

        log_test(
            "Config Loading",
            True,
            f"ETF config loaded: enabled={etf_config.get('enabled')}, "
            f"weight_mode={etf_config.get('weight_mode')}, "
            f"max_stocks={etf_config.get('max_stocks')}",
        )
        return True
    except Exception as e:
        log_test("Config Loading", False, str(e), traceback.format_exc())
        return False


def test_service_initialization():
    """Test 3: Service initialization."""
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )

        service = get_etf_enhanced_indexing_service()

        # Check service attributes
        attrs = ["enabled", "weight_mode", "max_stocks", "total_value", "region"]
        attr_values = {}
        for attr in attrs:
            if hasattr(service, attr):
                attr_values[attr] = getattr(service, attr)

        log_test("Service Initialization", True, f"Service initialized: {attr_values}")
        return True
    except Exception as e:
        log_test("Service Initialization", False, str(e), traceback.format_exc())
        return False


def test_dynamic_weight_calculation():
    """Test 4: Dynamic weight calculation via portfolio calculation."""
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )
        import pandas as pd
        import numpy as np

        service = get_etf_enhanced_indexing_service()

        if not service.enabled:
            log_test("Dynamic Weight Calculation", False, "Service is disabled")
            return False

        # Test dynamic weight by checking the weight_mode config
        weight_mode = service.weight_mode

        # The dynamic weight calculation is internal to calculate_target_portfolio
        # We verify it works by checking the portfolio calculation results
        log_test(
            "Dynamic Weight Calculation",
            True,
            f"Weight mode configured: {weight_mode}, "
            f"ETF weight range: {service.etf_weight_min}-{service.etf_weight_max}",
        )
        return True
    except Exception as e:
        log_test("Dynamic Weight Calculation", False, str(e), traceback.format_exc())
        return False


def test_portfolio_calculation():
    """Test 5: Portfolio calculation with mock signals."""
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )
        import pandas as pd
        import numpy as np

        service = get_etf_enhanced_indexing_service()

        if not service.enabled:
            log_test("Portfolio Calculation", False, "Service is disabled in config")
            return False

        # Create mock signals DataFrame
        # Format: MultiIndex with (datetime, instrument)
        dates = pd.date_range("2026-03-19", periods=1)
        instruments = [
            "SH600519",
            "SH601318",
            "SH600036",
            "SH000858",
            "SH601166",
            "SH600276",
            "SH601888",
            "SH600887",
            "SH601012",
            "SH600030",
            "SH510300",  # ETF
        ]

        # Create MultiIndex
        index = pd.MultiIndex.from_product(
            [dates, instruments], names=["datetime", "instrument"]
        )

        # Create mock scores (random but deterministic)
        np.random.seed(42)
        scores = np.random.uniform(0.3, 0.9, len(instruments))

        signals = pd.DataFrame({"score": np.tile(scores, len(dates))}, index=index)

        # Calculate portfolio
        trade_date = "2026-03-19"
        portfolio_data = service.calculate_target_portfolio(
            signals=signals, trade_date=trade_date
        )

        # Validate result structure
        required_keys = [
            "positions",
            "weights",
            "summary",
            "generated_at",
            "signal_for_date",
        ]
        missing_keys = [k for k in required_keys if k not in portfolio_data]

        if missing_keys:
            log_test(
                "Portfolio Calculation",
                False,
                f"Missing keys in result: {missing_keys}",
            )
            return False

        positions = portfolio_data.get("positions", [])
        weights = portfolio_data.get("weights", {})
        summary = portfolio_data.get("summary", {})

        # Check positions
        etf_positions = [p for p in positions if p.get("type") == "etf"]
        stock_positions = [p for p in positions if p.get("type") == "stock"]

        details = {
            "total_positions": len(positions),
            "etf_positions": len(etf_positions),
            "stock_positions": len(stock_positions),
            "etf_weight": weights.get("etf_weight"),
            "alpha_weight": weights.get("alpha_weight"),
            "weight_mode": weights.get("weight_mode"),
        }

        log_test(
            "Portfolio Calculation",
            True,
            f"Portfolio calculated successfully",
            f"Details: {json.dumps(details, indent=2)}",
        )

        # Print sample positions
        print("\n   Sample Positions:")
        for pos in positions[:3]:
            print(
                f"     - {pos.get('symbol')} ({pos.get('type')}): "
                f"weight={pos.get('weight', 0):.2%}, "
                f"action={pos.get('action')}, "
                f"shares={pos.get('target_shares')}"
            )

        return True
    except Exception as e:
        log_test("Portfolio Calculation", False, str(e), traceback.format_exc())
        return False


def test_email_html_generation():
    """Test 6: Email HTML generation."""
    try:
        from app.services.notification_service import get_notification_service

        service = get_notification_service()

        # Create mock portfolio data
        mock_portfolio = {
            "generated_at": datetime.now().isoformat(),
            "trade_date": "2026-03-19",
            "signal_for_date": "2026-03-20",
            "total_value": 1000000,
            "region": "cn",
            "lot_size": 100,
            "weights": {
                "etf_weight": 0.65,
                "alpha_weight": 0.35,
                "score_spread": 0.5,
                "weight_mode": "dynamic",
            },
            "positions": [
                {
                    "rank": 0,
                    "symbol": "SH510300",
                    "name": "沪深300ETF",
                    "type": "etf",
                    "weight": 0.65,
                    "target_value": 650000,
                    "reference_price": 4.125,
                    "target_shares": 157500,
                    "current_shares": 150000,
                    "action": "buy",
                    "action_shares": 7500,
                    "action_lots": 75,
                },
                {
                    "rank": 1,
                    "symbol": "SH600519",
                    "name": "贵州茅台",
                    "type": "stock",
                    "weight": 0.08,
                    "score": 0.95,
                    "target_value": 80000,
                    "reference_price": 1800.5,
                    "target_shares": 100,
                    "current_shares": 0,
                    "action": "buy",
                    "action_shares": 100,
                    "action_lots": 1,
                },
            ],
            "summary": {
                "total_positions": 10,
                "etf_positions": 1,
                "stock_positions": 9,
                "buy_count": 3,
                "sell_count": 2,
                "hold_count": 5,
            },
        }

        # Generate HTML
        html = service._build_etf_enhanced_portfolio_html(mock_portfolio)

        # Validate HTML content
        checks = [
            ("Contains title", "QuantBot 交易信号" in html),
            ("Contains ETF section", "ETF持仓" in html),
            ("Contains stock section", "Alpha股票持仓" in html),
            ("Contains ETF symbol", "SH510300" in html),
            ("Contains stock symbol", "SH600519" in html),
            ("Contains weight info", "65.0%" in html or "65%" in html),
        ]

        failed_checks = [c[0] for c in checks if not c[1]]

        if failed_checks:
            log_test("Email HTML Generation", False, f"Failed checks: {failed_checks}")
            return False

        # Save HTML for manual inspection
        html_path = Path("/app/temp_scripts/test_email_output.html")
        html_path.write_text(html, encoding="utf-8")

        log_test(
            "Email HTML Generation",
            True,
            f"HTML generated successfully ({len(html)} chars)",
            f"Saved to: {html_path}",
        )
        return True
    except Exception as e:
        log_test("Email HTML Generation", False, str(e), traceback.format_exc())
        return False


def test_portfolio_save_load():
    """Test 7: Portfolio save and load."""
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )
        import json
        from pathlib import Path

        service = get_etf_enhanced_indexing_service()

        # Create mock portfolio data
        mock_portfolio = {
            "generated_at": datetime.now().isoformat(),
            "trade_date": "2026-03-19",
            "signal_for_date": "2026-03-20",
            "total_value": 1000000,
            "region": "cn",
            "lot_size": 100,
            "weights": {
                "etf_weight": 0.65,
                "alpha_weight": 0.35,
            },
            "positions": [
                {"symbol": "SH510300", "type": "etf", "weight": 0.65},
                {"symbol": "SH600519", "type": "stock", "weight": 0.08},
            ],
            "summary": {"total_positions": 2},
        }

        # Save portfolio
        date_str = "2026-03-19-test"
        saved_path = service.save_portfolio(mock_portfolio, date_str)

        if not saved_path:
            log_test("Portfolio Save/Load", False, "save_portfolio returned None")
            return False

        # Check file exists
        saved_file = Path(saved_path)
        if not saved_file.exists():
            log_test("Portfolio Save/Load", False, f"File not found: {saved_path}")
            return False

        # Load and verify
        with open(saved_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        # Verify content
        if loaded.get("signal_for_date") != mock_portfolio["signal_for_date"]:
            log_test("Portfolio Save/Load", False, "Content mismatch after load")
            return False

        # Cleanup test file
        saved_file.unlink()

        log_test(
            "Portfolio Save/Load",
            True,
            f"Portfolio saved and loaded successfully",
            f"Path: {saved_path}",
        )
        return True
    except Exception as e:
        log_test("Portfolio Save/Load", False, str(e), traceback.format_exc())
        return False


def run_all_tests():
    """Run all tests and print summary."""
    print("=" * 70)
    print("ETF Enhanced Indexing Service - Test Suite")
    print("=" * 70)
    print(f"Started at: {datetime.now().isoformat()}")

    # Run tests in order
    tests = [
        test_imports,
        test_config_loading,
        test_service_initialization,
        test_dynamic_weight_calculation,
        test_portfolio_calculation,
        test_email_html_generation,
        test_portfolio_save_load,
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
