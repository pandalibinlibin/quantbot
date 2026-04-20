"""
Test script for backtest API after code cleanup.

This script tests:
1. Backtest API endpoint works correctly
2. Response contains strategy and max_deviation fields
3. Response does NOT contain topk/n_drop fields

Run in Docker:
    docker compose exec backend python /app/../temp_scripts/test_backtest_api.py
"""

import requests
import json

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def test_backtest_config():
    """Test GET /backtest/config endpoint."""
    print("=" * 60)
    print("Test 1: GET /backtest/config")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/config")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")
        if data.get("config"):
            print("Config keys:", list(data["config"].keys()))
        print("PASS: Config endpoint works")
    else:
        print(f"FAIL: {response.text}")

    print()


def test_backtest_status():
    """Test GET /backtest/status endpoint."""
    print("=" * 60)
    print("Test 2: GET /backtest/status")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Ready: {data.get('ready')}")
        print(f"Message: {data.get('message')}")
        print(f"Signal Count: {data.get('signal_count')}")
        print("PASS: Status endpoint works")
    else:
        print(f"FAIL: {response.text}")

    print()
    return response.json().get("ready", False)


def test_backtest_run():
    """Test POST /backtest/run endpoint."""
    print("=" * 60)
    print("Test 3: POST /backtest/run")
    print("=" * 60)

    # Test with empty request body (use defaults)
    response = requests.post(
        f"{BASE_URL}/backtest/run",
        json={},
        headers={"Content-Type": "application/json"},
    )
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")

        # Check for new fields
        print(f"\n--- New Fields (should exist) ---")
        print(f"strategy: {data.get('strategy')}")
        print(f"max_deviation: {data.get('max_deviation')}")

        # Check that old fields are removed
        print(f"\n--- Old Fields (should be None/missing) ---")
        print(f"topk: {data.get('topk')}")
        print(f"n_drop: {data.get('n_drop')}")

        # Validate
        if data.get("strategy") == "enhanced_indexing":
            print("\nPASS: strategy field is correct")
        else:
            print(
                f"\nWARN: strategy field is '{data.get('strategy')}', expected 'enhanced_indexing'"
            )

        if data.get("max_deviation") is not None:
            print("PASS: max_deviation field exists")
        else:
            print("WARN: max_deviation field is None")

        if "topk" not in data or data.get("topk") is None:
            print("PASS: topk field removed/None")
        else:
            print(f"FAIL: topk field still exists: {data.get('topk')}")

        if "n_drop" not in data or data.get("n_drop") is None:
            print("PASS: n_drop field removed/None")
        else:
            print(f"FAIL: n_drop field still exists: {data.get('n_drop')}")

        # Print key metrics
        print(f"\n--- Key Metrics ---")
        print(f"Trading Days: {data.get('trading_days')}")
        print(f"Total Return: {data.get('total_return')}")
        print(f"Net Return: {data.get('net_return')}")
        print(f"Benchmark: {data.get('benchmark')}")

        if data.get("risk_metrics"):
            print(f"\n--- Risk Metrics ---")
            rm = data["risk_metrics"]
            print(f"Sharpe Ratio: {rm.get('sharpe_ratio')}")
            print(f"Max Drawdown: {rm.get('max_drawdown')}")
            print(f"Win Rate: {rm.get('win_rate')}")

    else:
        print(f"FAIL: {response.text}")

    print()


def test_latest_result():
    """Test GET /backtest/latest-result endpoint."""
    print("=" * 60)
    print("Test 4: GET /backtest/latest-result")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/latest-result")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")

        if data.get("result"):
            result = data["result"]
            print(f"strategy: {result.get('strategy')}")
            print(f"max_deviation: {result.get('max_deviation')}")
            print("PASS: Latest result endpoint works")
        else:
            print("No result found (this is OK if no backtest has been run)")
    else:
        print(f"FAIL: {response.text}")

    print()


def main():
    print("\n" + "=" * 60)
    print("BACKTEST API TEST SUITE")
    print("Testing after code cleanup (removed topk/n_drop)")
    print("=" * 60 + "\n")

    # Test 1: Config endpoint
    test_backtest_config()

    # Test 2: Status endpoint
    is_ready = test_backtest_status()

    if not is_ready:
        print("WARNING: Backtest not ready. Skipping run test.")
        print("Please run routine first to initialize OnlineManager.")
        print("\nTo run routine, use:")
        print("  curl -X POST http://localhost:8000/api/v1/online/routine")
        return

    # Test 3: Run backtest
    test_backtest_run()

    # Test 4: Latest result
    test_latest_result()

    print("=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
