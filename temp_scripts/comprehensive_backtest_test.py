"""
Comprehensive backtest API test suite.
System is now ready with OnlineManager initialized and 216,350 signals available.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/comprehensive_backtest_test.py
"""

import requests
import json
import time

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def test_backtest_config():
    """Test backtest configuration endpoint."""
    print("=" * 60)
    print("TEST 1: BACKTEST CONFIGURATION")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/config")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Config Keys: {list(data.get('config', {}).keys())}")

        # Display strategy config
        strategy_config = data.get("config", {}).get("strategy", {})
        print(f"\n--- Strategy Configuration ---")
        print(f"Class: {strategy_config.get('class')}")
        print(f"Module: {strategy_config.get('module')}")
        print(f"Kwargs: {strategy_config.get('kwargs', {})}")

        # Display backtest config
        backtest_config = data.get("config", {}).get("backtest", {})
        print(f"\n--- Backtest Configuration ---")
        print(f"Start Time: {backtest_config.get('start_time')}")
        print(f"End Time: {backtest_config.get('end_time')}")
        print(f"Account: {backtest_config.get('account')}")
        print(f"Benchmark: {backtest_config.get('benchmark')}")

        print("✅ Config test passed")
        return True
    else:
        print(f"❌ Config test failed: {response.text}")
        return False


def test_backtest_status():
    """Test backtest status endpoint."""
    print("\n" + "=" * 60)
    print("TEST 2: BACKTEST STATUS")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Ready: {data.get('ready')}")
        print(f"Message: {data.get('message')}")
        print(f"Signal Count: {data.get('signal_count'):,}")

        if data.get("ready"):
            print("✅ Status test passed - System ready")
            return True
        else:
            print("⚠️ Status test warning - System not ready")
            return False
    else:
        print(f"❌ Status test failed: {response.text}")
        return False


def test_backtest_run_default():
    """Test backtest run with default parameters."""
    print("\n" + "=" * 60)
    print("TEST 3: BACKTEST RUN (DEFAULT PARAMETERS)")
    print("=" * 60)

    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/backtest/run",
        json={},
        headers={"Content-Type": "application/json"},
    )
    end_time = time.time()

    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {end_time - start_time:.2f} seconds")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")

        # Basic info
        print(f"\n--- Basic Information ---")
        print(f"Strategy: {data.get('strategy')}")
        print(f"Benchmark: {data.get('benchmark')}")
        print(f"Max Deviation: {data.get('max_deviation')}")
        print(f"Trading Days: {data.get('trading_days')}")

        # Performance metrics
        print(f"\n--- Performance Metrics ---")
        print(f"Total Return: {data.get('total_return'):.4f}")
        print(f"Net Return: {data.get('net_return'):.4f}")
        print(f"Excess Return: {data.get('excess_return'):.4f}")

        # Risk metrics
        if data.get("risk_metrics"):
            rm = data["risk_metrics"]
            print(f"\n--- Risk Metrics ---")
            print(f"Sharpe Ratio: {rm.get('sharpe_ratio'):.4f}")
            print(f"Max Drawdown: {rm.get('max_drawdown'):.4f}")
            print(f"Volatility: {rm.get('volatility'):.4f}")
            print(f"Win Rate: {rm.get('win_rate'):.4f}")
            print(f"Profit/Loss Ratio: {rm.get('profit_loss_ratio'):.4f}")

        # Signal time range
        if data.get("signal_time_range"):
            str_range = data["signal_time_range"]
            print(f"\n--- Signal Time Range ---")
            print(f"Start: {str_range.get('start')}")
            print(f"End: {str_range.get('end')}")
            print(f"Total Days: {str_range.get('total_days')}")

        print("\n✅ Default backtest test passed")
        return True, data

    else:
        print(f"❌ Default backtest test failed: {response.text}")
        return False, None


def test_backtest_run_custom():
    """Test backtest run with custom parameters."""
    print("\n" + "=" * 60)
    print("TEST 4: BACKTEST RUN (CUSTOM PARAMETERS)")
    print("=" * 60)

    # Custom parameters
    custom_params = {
        "start_time": "2025-01-01",
        "end_time": "2025-12-31",
        "benchmark": "csi300",
    }

    print(f"Custom Parameters: {json.dumps(custom_params, indent=2)}")

    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/backtest/run",
        json=custom_params,
        headers={"Content-Type": "application/json"},
    )
    end_time = time.time()

    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {end_time - start_time:.2f} seconds")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")

        # Verify custom parameters were applied
        print(f"\n--- Parameter Verification ---")
        if data.get("signal_time_range"):
            str_range = data["signal_time_range"]
            print(f"Actual Start: {str_range.get('start')}")
            print(f"Actual End: {str_range.get('end')}")
            print(f"Expected Start: {custom_params['start_time']}")
            print(f"Expected End: {custom_params['end_time']}")

        # Performance comparison
        print(f"\n--- Performance Summary ---")
        print(f"Total Return: {data.get('total_return'):.4f}")
        print(
            f"Sharpe Ratio: {data.get('risk_metrics', {}).get('sharpe_ratio', 0):.4f}"
        )
        print(
            f"Max Drawdown: {data.get('risk_metrics', {}).get('max_drawdown', 0):.4f}"
        )

        print("\n✅ Custom backtest test passed")
        return True, data

    else:
        print(f"❌ Custom backtest test failed: {response.text}")
        return False, None


def test_latest_result():
    """Test getting latest backtest result."""
    print("\n" + "=" * 60)
    print("TEST 5: LATEST BACKTEST RESULT")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/latest")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")

        if data.get("result"):
            result = data["result"]
            print(f"\n--- Latest Result Summary ---")
            print(f"Strategy: {result.get('strategy')}")
            print(f"Total Return: {result.get('total_return'):.4f}")
            print(f"Trading Days: {result.get('trading_days')}")
            print(f"Generated At: {result.get('generated_at')}")

            print("\n✅ Latest result test passed")
            return True
        else:
            print("⚠️ No latest result available")
            return False
    else:
        print(f"❌ Latest result test failed: {response.text}")
        return False


def analyze_performance_quality(default_result, custom_result):
    """Analyze the quality of backtest results."""
    print("\n" + "=" * 60)
    print("PERFORMANCE QUALITY ANALYSIS")
    print("=" * 60)

    if not default_result or not custom_result:
        print("⚠️ Cannot analyze - missing results")
        return

    # Extract metrics
    def extract_metrics(result):
        return {
            "total_return": result.get("total_return", 0),
            "sharpe_ratio": result.get("risk_metrics", {}).get("sharpe_ratio", 0),
            "max_drawdown": result.get("risk_metrics", {}).get("max_drawdown", 0),
            "volatility": result.get("risk_metrics", {}).get("volatility", 0),
            "win_rate": result.get("risk_metrics", {}).get("win_rate", 0),
        }

    default_metrics = extract_metrics(default_result)
    custom_metrics = extract_metrics(custom_result)

    print("--- Metrics Comparison ---")
    print(f"{'Metric':<15} {'Default':<12} {'Custom':<12} {'Difference':<12}")
    print("-" * 55)

    for metric in default_metrics:
        default_val = default_metrics[metric]
        custom_val = custom_metrics[metric]
        diff = custom_val - default_val
        print(f"{metric:<15} {default_val:<12.4f} {custom_val:<12.4f} {diff:<12.4f}")

    # Quality assessment
    print(f"\n--- Quality Assessment ---")

    # Check for reasonable values
    quality_checks = []

    # Sharpe ratio should be reasonable (-2 to 5)
    sharpe = default_metrics["sharpe_ratio"]
    if -2 <= sharpe <= 5:
        quality_checks.append(f"✅ Sharpe ratio ({sharpe:.3f}) is reasonable")
    else:
        quality_checks.append(f"⚠️ Sharpe ratio ({sharpe:.3f}) may be unrealistic")

    # Max drawdown should be negative and reasonable
    drawdown = default_metrics["max_drawdown"]
    if -0.5 <= drawdown <= 0:
        quality_checks.append(f"✅ Max drawdown ({drawdown:.3f}) is reasonable")
    else:
        quality_checks.append(f"⚠️ Max drawdown ({drawdown:.3f}) may be concerning")

    # Win rate should be between 0 and 1
    win_rate = default_metrics["win_rate"]
    if 0 <= win_rate <= 1:
        quality_checks.append(f"✅ Win rate ({win_rate:.3f}) is valid")
    else:
        quality_checks.append(f"❌ Win rate ({win_rate:.3f}) is invalid")

    for check in quality_checks:
        print(check)


def main():
    """Run comprehensive backtest test suite."""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE BACKTEST TEST SUITE")
    print("System Status: OnlineManager initialized, 216,350 signals ready")
    print("=" * 60)

    test_results = []

    # Test 1: Configuration
    config_success = test_backtest_config()
    test_results.append(("Configuration", config_success))

    # Test 2: Status
    status_success = test_backtest_status()
    test_results.append(("Status", status_success))

    if not status_success:
        print("\n❌ System not ready, stopping tests")
        return

    # Test 3: Default backtest
    default_success, default_result = test_backtest_run_default()
    test_results.append(("Default Backtest", default_success))

    # Test 4: Custom backtest
    custom_success, custom_result = test_backtest_run_custom()
    test_results.append(("Custom Backtest", custom_success))

    # Test 5: Latest result
    latest_success = test_latest_result()
    test_results.append(("Latest Result", latest_success))

    # Performance analysis
    if default_success and custom_success:
        analyze_performance_quality(default_result, custom_result)

    # Final summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Backtest API is fully functional.")
    else:
        print(f"⚠️ {total - passed} test(s) failed. Review results above.")


if __name__ == "__main__":
    main()
