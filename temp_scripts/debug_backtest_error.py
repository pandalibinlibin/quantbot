"""
Debug backtest error to understand what's going wrong.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/debug_backtest_error.py
"""

import requests
import json

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def debug_backtest_error():
    """Debug the backtest error response."""
    print("=" * 60)
    print("DEBUGGING BACKTEST ERROR")
    print("=" * 60)

    # First check status
    print("--- Checking Status ---")
    status_response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {status_response.status_code}")

    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"Ready: {status_data.get('ready')}")
        print(f"Message: {status_data.get('message')}")
        print(f"Signal Count: {status_data.get('signal_count')}")

    # Now try backtest
    print(f"\n--- Running Backtest ---")
    backtest_response = requests.post(
        f"{BASE_URL}/backtest/run",
        json={},
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {backtest_response.status_code}")
    print(f"Response Headers: {dict(backtest_response.headers)}")

    if backtest_response.status_code == 200:
        try:
            data = backtest_response.json()
            print(f"\n--- Full Response ---")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # Check for error details
            if data.get("status") == "error":
                print(f"\n--- Error Details ---")
                print(f"Error Message: {data.get('message', 'No error message')}")
                print(f"Error Details: {data.get('error', 'No error details')}")
                print(f"Error Type: {data.get('error_type', 'No error type')}")

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw response: {backtest_response.text}")
    else:
        print(f"HTTP Error: {backtest_response.text}")


def check_online_manager_state():
    """Check the actual state of OnlineManager."""
    print(f"\n" + "=" * 60)
    print("CHECKING ONLINE MANAGER STATE")
    print("=" * 60)

    # Try to get signals directly
    try:
        response = requests.get(f"{BASE_URL}/online/signals")
        print(f"Signals endpoint status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Signals available: {len(data.get('signals', []))}")
        else:
            print(f"Signals error: {response.text}")
    except Exception as e:
        print(f"Signals check failed: {e}")

    # Check routine status
    try:
        response = requests.get(f"{BASE_URL}/online/status")
        print(f"Online status endpoint: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Online status: {json.dumps(data, indent=2)}")
        else:
            print(f"Online status error: {response.text}")
    except Exception as e:
        print(f"Online status check failed: {e}")


def main():
    print("\n" + "=" * 60)
    print("BACKTEST ERROR DEBUGGING")
    print("=" * 60)

    debug_backtest_error()
    check_online_manager_state()


if __name__ == "__main__":
    main()
