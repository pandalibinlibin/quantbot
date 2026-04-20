"""
Trigger routine to initialize OnlineManager and then test backtest API.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/trigger_routine_and_test_backtest.py
"""

import requests
import json
import time

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def trigger_routine():
    """Trigger routine to initialize OnlineManager."""
    print("=" * 60)
    print("STEP 1: TRIGGERING ROUTINE")
    print("=" * 60)

    response = requests.post(f"{BASE_URL}/online/routine")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")

        if data.get("status") == "success":
            print("✅ Routine completed successfully")
            return True
        else:
            print(f"⚠️ Routine status: {data.get('status')}")
            return False
    else:
        print(f"❌ Routine failed: {response.text}")
        return False


def check_backtest_status():
    """Check if backtest is ready."""
    print("\n" + "=" * 60)
    print("STEP 2: CHECKING BACKTEST STATUS")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Ready: {data.get('ready')}")
        print(f"Message: {data.get('message')}")
        print(f"Signal Count: {data.get('signal_count')}")

        if data.get("ready"):
            print("✅ Backtest is ready")
            return True
        else:
            print(f"⚠️ Backtest not ready: {data.get('message')}")
            return False
    else:
        print(f"❌ Status check failed: {response.text}")
        return False


def run_backtest():
    """Run backtest with default parameters."""
    print("\n" + "=" * 60)
    print("STEP 3: RUNNING BACKTEST")
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
        print(f"\n--- Strategy Information ---")
        print(f"Strategy: {data.get('strategy')}")
        print(f"Max Deviation: {data.get('max_deviation')}")
        print(f"Benchmark: {data.get('benchmark')}")

        # Print key metrics
        print(f"\n--- Performance Metrics ---")
        print(f"Trading Days: {data.get('trading_days')}")
        print(f"Total Return: {data.get('total_return')}")
        print(f"Net Return: {data.get('net_return')}")

        if data.get("risk_metrics"):
            print(f"\n--- Risk Metrics ---")
            rm = data["risk_metrics"]
            print(f"Sharpe Ratio: {rm.get('sharpe_ratio')}")
            print(f"Max Drawdown: {rm.get('max_drawdown')}")
            print(f"Win Rate: {rm.get('win_rate')}")
            print(f"Profit/Loss Ratio: {rm.get('profit_loss_ratio')}")

        if data.get("signal_time_range"):
            print(f"\n--- Signal Time Range ---")
            str_range = data["signal_time_range"]
            print(f"Start: {str_range.get('start')}")
            print(f"End: {str_range.get('end')}")

        print("\n✅ Backtest completed successfully!")
        return True

    else:
        print(f"❌ Backtest failed: {response.text}")
        return False


def main():
    print("\n" + "=" * 60)
    print("ROUTINE + BACKTEST INTEGRATION TEST")
    print("=" * 60)

    # Step 1: Trigger routine
    routine_success = trigger_routine()
    if not routine_success:
        print("\n❌ Routine failed, cannot proceed with backtest")
        return

    # Wait a moment for initialization
    print("\nWaiting 5 seconds for OnlineManager initialization...")
    time.sleep(5)

    # Step 2: Check backtest status
    backtest_ready = check_backtest_status()
    if not backtest_ready:
        print("\n❌ Backtest not ready, cannot run test")
        return

    # Step 3: Run backtest
    backtest_success = run_backtest()

    print("\n" + "=" * 60)
    if backtest_success:
        print("🎉 ALL TESTS PASSED!")
        print("Backtest API is working correctly")
    else:
        print("❌ BACKTEST TEST FAILED")
    print("=" * 60)


if __name__ == "__main__":
    main()
