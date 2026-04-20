"""
Fixed comprehensive backtest test with error handling.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/fixed_backtest_test.py
"""

import requests
import json
import time

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def check_system_status():
    """Check if system needs routine to be run first."""
    print("=" * 60)
    print("SYSTEM STATUS CHECK")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        ready = data.get("ready", False)
        message = data.get("message", "No message")
        signal_count = data.get("signal_count")

        print(f"Ready: {ready}")
        print(f"Message: {message}")
        print(f"Signal Count: {signal_count if signal_count is not None else 'None'}")

        if not ready:
            print("\n⚠️ System not ready. Triggering routine...")
            return trigger_routine()
        else:
            print("✅ System is ready")
            return True
    else:
        print(f"❌ Status check failed: {response.text}")
        return False


def trigger_routine():
    """Trigger routine to initialize system."""
    print("\n--- Triggering Routine ---")

    response = requests.post(f"{BASE_URL}/online/routine")
    print(f"Routine Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        success = data.get("success", False)
        message = data.get("message", "No message")

        print(f"Routine Success: {success}")
        print(f"Routine Message: {message}")

        if success:
            print("✅ Routine completed successfully")
            # Wait a moment for initialization
            print("Waiting 3 seconds for system initialization...")
            time.sleep(3)
            return True
        else:
            print("⚠️ Routine completed but success flag not set")
            return False
    else:
        print(f"❌ Routine failed: {response.text}")
        return False


def test_backtest_config():
    """Test backtest configuration endpoint."""
    print("\n" + "=" * 60)
    print("TEST 1: BACKTEST CONFIGURATION")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/config")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")

        config = data.get("config", {})
        print(f"Config Keys: {list(config.keys())}")

        # Display strategy config
        strategy_config = config.get("strategy", {})
        print(f"\n--- Strategy Configuration ---")
        print(f"Class: {strategy_config.get('class')}")
        print(f"Module: {strategy_config.get('module')}")
        print(f"Kwargs: {strategy_config.get('kwargs', {})}")

        # Display backtest config
        backtest_config = config.get("backtest", {})
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
    """Test backtest status endpoint with error handling."""
    print("\n" + "=" * 60)
    print("TEST 2: BACKTEST STATUS")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        ready = data.get("ready", False)
        message = data.get("message", "No message")
        signal_count = data.get("signal_count")

        print(f"Ready: {ready}")
        print(f"Message: {message}")

        # Safe formatting for signal_count
        if signal_count is not None:
            print(f"Signal Count: {signal_count:,}")
        else:
            print("Signal Count: None")

        if ready:
            print("✅ Status test passed - System ready")
            return True
        else:
            print("⚠️ Status test warning - System not ready")
            return False
    else:
        print(f"❌ Status test failed: {response.text}")
        return False


def test_backtest_run():
    """Test backtest run with default parameters."""
    print("\n" + "=" * 60)
    print("TEST 3: BACKTEST RUN")
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
        status = data.get("status", "unknown")
        print(f"Status: {status}")

        # Basic info
        print(f"\n--- Basic Information ---")
        print(f"Strategy: {data.get('strategy', 'N/A')}")
        print(f"Benchmark: {data.get('benchmark', 'N/A')}")
        print(f"Trading Days: {data.get('trading_days', 'N/A')}")

        # Performance metrics with safe access
        print(f"\n--- Performance Metrics ---")
        total_return = data.get("total_return")
        net_return = data.get("net_return")
        excess_return = data.get("excess_return")

        print(
            f"Total Return: {total_return:.4f if total_return is not None else 'N/A'}"
        )
        print(f"Net Return: {net_return:.4f if net_return is not None else 'N/A'}")
        print(
            f"Excess Return: {excess_return:.4f if excess_return is not None else 'N/A'}"
        )

        # Risk metrics with safe access
        risk_metrics = data.get("risk_metrics", {})
        if risk_metrics:
            print(f"\n--- Risk Metrics ---")
            sharpe = risk_metrics.get("sharpe_ratio")
            drawdown = risk_metrics.get("max_drawdown")
            volatility = risk_metrics.get("volatility")
            win_rate = risk_metrics.get("win_rate")
            pl_ratio = risk_metrics.get("profit_loss_ratio")

            print(f"Sharpe Ratio: {sharpe:.4f if sharpe is not None else 'N/A'}")
            print(f"Max Drawdown: {drawdown:.4f if drawdown is not None else 'N/A'}")
            print(f"Volatility: {volatility:.4f if volatility is not None else 'N/A'}")
            print(f"Win Rate: {win_rate:.4f if win_rate is not None else 'N/A'}")
            print(f"P/L Ratio: {pl_ratio:.4f if pl_ratio is not None else 'N/A'}")

        # Signal time range
        signal_range = data.get("signal_time_range", {})
        if signal_range:
            print(f"\n--- Signal Time Range ---")
            print(f"Start: {signal_range.get('start', 'N/A')}")
            print(f"End: {signal_range.get('end', 'N/A')}")
            print(f"Total Days: {signal_range.get('total_days', 'N/A')}")

        print("\n✅ Backtest test passed")
        return True, data

    else:
        print(f"❌ Backtest test failed: {response.text}")
        return False, None


def test_latest_result():
    """Test getting latest backtest result."""
    print("\n" + "=" * 60)
    print("TEST 4: LATEST BACKTEST RESULT")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/latest")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        status = data.get("status", "unknown")
        print(f"Status: {status}")

        result = data.get("result")
        if result:
            print(f"\n--- Latest Result Summary ---")
            print(f"Strategy: {result.get('strategy', 'N/A')}")

            total_return = result.get("total_return")
            print(
                f"Total Return: {total_return:.4f if total_return is not None else 'N/A'}"
            )

            print(f"Trading Days: {result.get('trading_days', 'N/A')}")
            print(f"Generated At: {result.get('generated_at', 'N/A')}")

            print("\n✅ Latest result test passed")
            return True
        else:
            print("⚠️ No latest result available")
            return False
    else:
        print(f"❌ Latest result test failed: {response.text}")
        return False


def main():
    """Run comprehensive backtest test suite with error handling."""
    print("\n" + "=" * 60)
    print("FIXED BACKTEST TEST SUITE")
    print("=" * 60)

    # Step 1: Check system status and initialize if needed
    system_ready = check_system_status()
    if not system_ready:
        print("\n❌ System initialization failed, stopping tests")
        return

    test_results = []

    # Test 1: Configuration
    config_success = test_backtest_config()
    test_results.append(("Configuration", config_success))

    # Test 2: Status (should be ready now)
    status_success = test_backtest_status()
    test_results.append(("Status", status_success))

    if not status_success:
        print("\n❌ System still not ready after initialization")
        return

    # Test 3: Backtest run
    backtest_success, backtest_result = test_backtest_run()
    test_results.append(("Backtest Run", backtest_success))

    # Test 4: Latest result
    latest_success = test_latest_result()
    test_results.append(("Latest Result", latest_success))

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
