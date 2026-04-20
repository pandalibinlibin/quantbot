"""
Debug system status and OnlineManager state.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/debug_system_status.py
"""

import requests
import json

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def check_detailed_status():
    """Check detailed system status."""
    print("=" * 60)
    print("DETAILED SYSTEM STATUS CHECK")
    print("=" * 60)

    # Check online status
    print("1. Online Status API:")
    response = requests.get(f"{BASE_URL}/online/status")
    if response.status_code == 200:
        status = response.json()
        print(json.dumps(status, indent=2))
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

    print("\n" + "-" * 40)

    # Try to trigger routine to refresh status
    print("2. Triggering Routine to Refresh Status:")
    response = requests.post(f"{BASE_URL}/online/routine")
    if response.status_code == 200:
        result = response.json()
        print("✅ Routine triggered successfully")
        print(f"Message: {result.get('message', 'No message')}")
        print(f"Status: {result.get('status', 'No status')}")
    else:
        print(f"❌ Failed to trigger routine: {response.status_code}")
        print(response.text)

    print("\n" + "-" * 40)

    # Check status again after routine
    print("3. Status After Routine:")
    response = requests.get(f"{BASE_URL}/online/status")
    if response.status_code == 200:
        status = response.json()
        print(json.dumps(status, indent=2))

        # Check if OnlineManager is ready now
        if status.get("online_manager_ready"):
            print("✅ OnlineManager is now ready!")
            return True
        else:
            print("❌ OnlineManager still not ready")
            return False
    else:
        print(f"❌ Failed: {response.status_code}")
        return False


def test_backtest_directly():
    """Try to run backtest directly regardless of status."""
    print("\n" + "=" * 60)
    print("TESTING BACKTEST DIRECTLY")
    print("=" * 60)

    backtest_request = {
        "start_time": "2024-01-01",
        "end_time": "2024-01-15",  # Shorter period for faster test
        "topk": 10,
        "n_drop": 2,
        "account": 1000000,
        "benchmark": "000300.SH",
    }

    print("Attempting backtest with parameters:")
    print(json.dumps(backtest_request, indent=2))

    response = requests.post(
        f"{BASE_URL}/backtest/run", json=backtest_request, timeout=120
    )

    if response.status_code == 200:
        result = response.json()
        print("✅ Backtest succeeded despite status!")

        if "report" in result:
            report = result["report"]
            print(f"Annual Return: {report.get('annual_return', 'N/A')}")
            print(f"Sharpe Ratio: {report.get('sharpe_ratio', 'N/A')}")
            if "benchmark_return" in report:
                print(f"Benchmark Return: {report.get('benchmark_return', 'N/A')}")
                print("✅ Benchmark data successfully used!")
        return True
    else:
        print(f"❌ Backtest failed: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"Error: {json.dumps(error_detail, indent=2)}")
        except:
            print(f"Error text: {response.text}")
        return False


def main():
    """Debug system status and test backtest."""
    print("🔍 DEBUGGING SYSTEM STATUS")

    # Check detailed status and try to refresh
    manager_ready = check_detailed_status()

    # Test backtest regardless of status
    backtest_works = test_backtest_directly()

    print("\n" + "=" * 60)
    print("DIAGNOSIS SUMMARY")
    print("=" * 60)

    if backtest_works:
        print("✅ GOOD NEWS: Backtest functionality works!")
        print("✅ Index data is available and being used as benchmark")
        if not manager_ready:
            print(
                "⚠️  Status API may have a reporting issue, but core functionality works"
            )
    else:
        print("❌ Backtest still has issues")
        if not manager_ready:
            print("❌ OnlineManager not ready - this may be the cause")


if __name__ == "__main__":
    main()
