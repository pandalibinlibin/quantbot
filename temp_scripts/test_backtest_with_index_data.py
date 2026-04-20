"""
Test backtest functionality with index data included.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/test_backtest_with_index_data.py
"""

import requests
import json
import time

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def test_system_status():
    """Check if system is ready."""
    print("=" * 60)
    print("CHECKING SYSTEM STATUS")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/online/status")
    if response.status_code == 200:
        status = response.json()
        print(f"System Status: {status.get('status', 'Unknown')}")
        print(f"OnlineManager Ready: {status.get('online_manager_ready', False)}")
        print(f"Signal Count: {status.get('signal_count', 0)}")
        print(f"Last Update: {status.get('last_update_time', 'Never')}")
        return status.get("online_manager_ready", False)
    else:
        print(f"❌ Failed to get system status: {response.status_code}")
        return False


def test_backtest_config():
    """Test backtest configuration."""
    print("\n" + "=" * 60)
    print("TESTING BACKTEST CONFIGURATION")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/config")
    if response.status_code == 200:
        config = response.json()
        print("✅ Backtest config retrieved successfully")
        print(f"Benchmark: {config.get('benchmark', 'Not specified')}")
        print(f"Account: {config.get('account', 'Not specified')}")
        print(f"Strategy: {config.get('strategy', {}).get('class', 'Not specified')}")
        return True
    else:
        print(f"❌ Failed to get backtest config: {response.status_code}")
        if response.text:
            print(f"Error: {response.text}")
        return False


def test_backtest_execution():
    """Test backtest execution with index benchmark."""
    print("\n" + "=" * 60)
    print("TESTING BACKTEST EXECUTION")
    print("=" * 60)

    # Test with default configuration (should use 000300.SH benchmark)
    backtest_request = {
        "start_time": "2024-01-01",
        "end_time": "2024-02-01",
        "topk": 20,
        "n_drop": 5,
        "account": 1000000,
        "benchmark": "000300.SH",  # Explicitly specify the benchmark
    }

    print("Backtest parameters:")
    print(json.dumps(backtest_request, indent=2))

    print(f"\n--- Starting Backtest ---")
    start_time = time.time()

    response = requests.post(
        f"{BASE_URL}/backtest/run",
        json=backtest_request,
        timeout=300,  # 5 minutes timeout
    )

    execution_time = time.time() - start_time
    print(f"Execution time: {execution_time:.2f} seconds")

    if response.status_code == 200:
        result = response.json()
        print("✅ Backtest completed successfully!")

        # Print key metrics
        if "report" in result:
            report = result["report"]
            print(f"\n📊 Backtest Results:")
            print(
                f"Annual Return: {report.get('annual_return', 'N/A'):.4f}"
                if isinstance(report.get("annual_return"), (int, float))
                else f"Annual Return: {report.get('annual_return', 'N/A')}"
            )
            print(
                f"Sharpe Ratio: {report.get('sharpe_ratio', 'N/A'):.4f}"
                if isinstance(report.get("sharpe_ratio"), (int, float))
                else f"Sharpe Ratio: {report.get('sharpe_ratio', 'N/A')}"
            )
            print(
                f"Max Drawdown: {report.get('max_drawdown', 'N/A'):.4f}"
                if isinstance(report.get("max_drawdown"), (int, float))
                else f"Max Drawdown: {report.get('max_drawdown', 'N/A')}"
            )
            print(
                f"Information Ratio: {report.get('information_ratio', 'N/A'):.4f}"
                if isinstance(report.get("information_ratio"), (int, float))
                else f"Information Ratio: {report.get('information_ratio', 'N/A')}"
            )

            # Check if benchmark data was used
            if "benchmark_return" in report:
                print(
                    f"Benchmark Return: {report.get('benchmark_return', 'N/A'):.4f}"
                    if isinstance(report.get("benchmark_return"), (int, float))
                    else f"Benchmark Return: {report.get('benchmark_return', 'N/A')}"
                )
                print("✅ Benchmark data successfully used in backtest!")
            else:
                print("⚠️  No benchmark return found in results")

        return True
    else:
        print(f"❌ Backtest failed: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"Error details: {json.dumps(error_detail, indent=2)}")
        except:
            print(f"Error text: {response.text}")
        return False


def test_latest_result():
    """Test retrieving latest backtest result."""
    print("\n" + "=" * 60)
    print("TESTING LATEST BACKTEST RESULT")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/latest")
    if response.status_code == 200:
        result = response.json()
        print("✅ Latest backtest result retrieved successfully")

        if "timestamp" in result:
            print(f"Timestamp: {result['timestamp']}")
        if "report" in result and result["report"]:
            report = result["report"]
            print(f"Annual Return: {report.get('annual_return', 'N/A')}")
            print(f"Sharpe Ratio: {report.get('sharpe_ratio', 'N/A')}")

        return True
    else:
        print(f"❌ Failed to get latest result: {response.status_code}")
        return False


def main():
    """Run comprehensive backtest test."""
    print("🧪 COMPREHENSIVE BACKTEST TEST WITH INDEX DATA")
    print("=" * 60)

    # Test results
    results = {
        "system_status": False,
        "backtest_config": False,
        "backtest_execution": False,
        "latest_result": False,
    }

    # 1. Check system status
    results["system_status"] = test_system_status()

    if not results["system_status"]:
        print(
            "\n❌ System not ready. Please ensure routine has completed successfully."
        )
        return

    # 2. Test backtest configuration
    results["backtest_config"] = test_backtest_config()

    # 3. Test backtest execution
    results["backtest_execution"] = test_backtest_execution()

    # 4. Test latest result retrieval
    results["latest_result"] = test_latest_result()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed_tests = sum(results.values())
    total_tests = len(results)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():<25} {status}")

    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("Backtest functionality is working correctly with index data.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()
