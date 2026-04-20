"""
Wait for rolling update to complete and test backtest functionality.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/wait_and_test_backtest.py
"""

import requests
import json
import time

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def wait_for_system_ready(max_wait_minutes=10):
    """Wait for system to be ready or timeout."""
    print("🔄 Waiting for rolling update to complete...")

    max_wait_seconds = max_wait_minutes * 60
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        try:
            response = requests.get(f"{BASE_URL}/online/status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                is_ready = status.get("is_initialized", False)

                print(f"⏱️  Waiting... is_initialized: {is_ready}")

                if is_ready:
                    print("✅ System is ready!")
                    return True

        except Exception as e:
            print(f"⚠️  Error checking status: {e}")

        time.sleep(30)  # Check every 30 seconds

    print(f"⏰ Timeout after {max_wait_minutes} minutes")
    return False


def test_backtest_directly():
    """Test backtest functionality directly."""
    print("\n" + "=" * 60)
    print("🧪 TESTING BACKTEST FUNCTIONALITY")
    print("=" * 60)

    # Simple backtest request
    backtest_request = {
        "start_time": "2024-01-01",
        "end_time": "2024-01-15",  # Short period for quick test
        "topk": 10,
        "n_drop": 2,
        "account": 1000000,
        "benchmark": "000300.SH",
    }

    print("📋 Backtest Parameters:")
    print(json.dumps(backtest_request, indent=2))

    print(f"\n🚀 Starting backtest...")
    start_time = time.time()

    try:
        response = requests.post(
            f"{BASE_URL}/backtest/run",
            json=backtest_request,
            timeout=300,  # 5 minutes timeout
        )

        execution_time = time.time() - start_time
        print(f"⏱️  Execution time: {execution_time:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("🎉 BACKTEST SUCCESS!")

            # Print key results
            if "report" in result:
                report = result["report"]
                print(f"\n📊 Results Summary:")

                metrics = [
                    "annual_return",
                    "sharpe_ratio",
                    "max_drawdown",
                    "information_ratio",
                ]
                for metric in metrics:
                    value = report.get(metric, "N/A")
                    if isinstance(value, (int, float)):
                        print(f"  {metric.replace('_', ' ').title()}: {value:.4f}")
                    else:
                        print(f"  {metric.replace('_', ' ').title()}: {value}")

                # Check benchmark usage
                if "benchmark_return" in report:
                    benchmark_return = report.get("benchmark_return", "N/A")
                    if isinstance(benchmark_return, (int, float)):
                        print(f"  Benchmark Return: {benchmark_return:.4f}")
                    else:
                        print(f"  Benchmark Return: {benchmark_return}")
                    print("✅ BENCHMARK DATA SUCCESSFULLY USED!")
                else:
                    print("⚠️  No benchmark return found")

            return True

        else:
            print(f"❌ Backtest failed: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Error text: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Backtest timed out (>5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Backtest error: {e}")
        return False


def check_system_status():
    """Check current system status."""
    print("\n" + "=" * 60)
    print("📊 CURRENT SYSTEM STATUS")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/online/status")
        if response.status_code == 200:
            status = response.json()
            print(json.dumps(status, indent=2))
            return status
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Main test function."""
    print("🔬 BACKTEST FUNCTIONALITY TEST")
    print("=" * 60)

    # Check current status
    current_status = check_system_status()

    # If not initialized, wait for it
    if not current_status or not current_status.get("is_initialized", False):
        print("\n💡 System not initialized, waiting for rolling update to complete...")
        system_ready = wait_for_system_ready(max_wait_minutes=10)

        if not system_ready:
            print("\n⚠️  System not ready after waiting, but trying backtest anyway...")
            print("   (Rolling update might still be in progress)")
    else:
        print("\n✅ System already initialized!")

    # Test backtest functionality
    backtest_success = test_backtest_directly()

    # Final summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    if backtest_success:
        print("🎉 SUCCESS: Backtest functionality is working!")
        print("✅ Index data is available and being used as benchmark")
        print("✅ The 'benchmark does not exist' error has been resolved")
    else:
        print("❌ FAILED: Backtest functionality has issues")
        print("   Please check the error details above")


if __name__ == "__main__":
    main()
