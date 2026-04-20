"""
Test backtest after fixing benchmark code.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/test_fixed_backtest.py
"""

import requests
import json
import time

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def test_backtest_after_fix():
    """Test backtest after fixing benchmark code."""
    print("=" * 60)
    print("TESTING BACKTEST AFTER BENCHMARK FIX")
    print("=" * 60)

    # First check status
    print("--- Checking System Status ---")
    status_response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {status_response.status_code}")

    if status_response.status_code == 200:
        status_data = status_response.json()
        ready = status_data.get("ready", False)
        message = status_data.get("message", "No message")
        signal_count = status_data.get("signal_count")

        print(f"Ready: {ready}")
        print(f"Message: {message}")
        print(f"Signal Count: {signal_count if signal_count is not None else 'None'}")

        if not ready:
            print("\n⚠️ System not ready. Triggering routine...")
            routine_response = requests.post(f"{BASE_URL}/online/routine")
            if routine_response.status_code == 200:
                routine_data = routine_response.json()
                print(f"Routine Success: {routine_data.get('success')}")
                print("Waiting 3 seconds for initialization...")
                time.sleep(3)
            else:
                print(f"❌ Routine failed: {routine_response.text}")
                return False

    # Check config to verify benchmark fix
    print(f"\n--- Checking Updated Configuration ---")
    config_response = requests.get(f"{BASE_URL}/backtest/config")
    if config_response.status_code == 200:
        config_data = config_response.json()
        benchmark = config_data.get("config", {}).get("backtest", {}).get("benchmark")
        print(f"Benchmark: {benchmark}")

        if benchmark == "000300.SH":
            print("✅ Benchmark correctly updated to 000300.SH")
        else:
            print(f"⚠️ Benchmark still shows: {benchmark}")

    # Now test backtest
    print(f"\n--- Running Backtest ---")
    start_time = time.time()
    backtest_response = requests.post(
        f"{BASE_URL}/backtest/run",
        json={},
        headers={"Content-Type": "application/json"},
    )
    end_time = time.time()

    print(f"Status Code: {backtest_response.status_code}")
    print(f"Response Time: {end_time - start_time:.2f} seconds")

    if backtest_response.status_code == 200:
        try:
            data = backtest_response.json()
            status = data.get("status", "unknown")
            print(f"Status: {status}")

            if status == "success":
                print(f"\n🎉 BACKTEST SUCCESS!")

                # Display key results
                print(f"\n--- Performance Summary ---")
                print(f"Strategy: {data.get('strategy', 'N/A')}")
                print(f"Benchmark: {data.get('benchmark', 'N/A')}")
                print(f"Trading Days: {data.get('trading_days', 'N/A')}")

                # Performance metrics
                total_return = data.get("total_return")
                net_return = data.get("net_return")
                excess_return = data.get("excess_return")

                if total_return is not None:
                    print(f"Total Return: {total_return:.4f} ({total_return*100:.2f}%)")
                if net_return is not None:
                    print(f"Net Return: {net_return:.4f} ({net_return*100:.2f}%)")
                if excess_return is not None:
                    print(
                        f"Excess Return: {excess_return:.4f} ({excess_return*100:.2f}%)"
                    )

                # Risk metrics
                risk_metrics = data.get("risk_metrics", {})
                if risk_metrics:
                    print(f"\n--- Risk Metrics ---")
                    sharpe = risk_metrics.get("sharpe_ratio")
                    drawdown = risk_metrics.get("max_drawdown")
                    volatility = risk_metrics.get("volatility")
                    win_rate = risk_metrics.get("win_rate")

                    if sharpe is not None:
                        print(f"Sharpe Ratio: {sharpe:.4f}")
                    if drawdown is not None:
                        print(f"Max Drawdown: {drawdown:.4f} ({drawdown*100:.2f}%)")
                    if volatility is not None:
                        print(f"Volatility: {volatility:.4f} ({volatility*100:.2f}%)")
                    if win_rate is not None:
                        print(f"Win Rate: {win_rate:.4f} ({win_rate*100:.2f}%)")

                # Time range
                signal_range = data.get("signal_time_range", {})
                if signal_range:
                    print(f"\n--- Time Range ---")
                    print(f"Start: {signal_range.get('start', 'N/A')}")
                    print(f"End: {signal_range.get('end', 'N/A')}")
                    print(f"Total Days: {signal_range.get('total_days', 'N/A')}")

                return True

            elif status == "error":
                print(f"\n❌ BACKTEST ERROR:")
                print(f"Error: {data.get('error', 'No error message')}")
                print(f"Message: {data.get('message', 'No message')}")

                # Show full error response for debugging
                print(f"\n--- Full Error Response ---")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return False
            else:
                print(f"\n⚠️ Unknown status: {status}")
                return False

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw response: {backtest_response.text}")
            return False
    else:
        print(f"❌ HTTP Error: {backtest_response.text}")
        return False


def test_latest_result():
    """Test getting latest backtest result."""
    print(f"\n" + "=" * 60)
    print("TESTING LATEST RESULT")
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
            if total_return is not None:
                print(f"Total Return: {total_return:.4f} ({total_return*100:.2f}%)")

            print(f"Trading Days: {result.get('trading_days', 'N/A')}")
            print(f"Generated At: {result.get('generated_at', 'N/A')}")

            print("✅ Latest result retrieved successfully")
            return True
        else:
            print("⚠️ No latest result available")
            return False
    else:
        print(f"❌ Latest result failed: {response.text}")
        return False


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("BACKTEST FUNCTIONALITY TEST")
    print("Fixed benchmark code: SH000300 → 000300.SH")
    print("=" * 60)

    # Test backtest
    backtest_success = test_backtest_after_fix()

    if backtest_success:
        # Test latest result
        latest_success = test_latest_result()

        if latest_success:
            print(f"\n🎉 ALL TESTS PASSED!")
            print("Backtest API is fully functional.")
        else:
            print(f"\n⚠️ Backtest works but latest result has issues.")
    else:
        print(f"\n❌ Backtest still has issues. Check error details above.")


if __name__ == "__main__":
    main()
