"""
Debug routine API response to understand the actual format.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/debug_routine_response.py
"""

import requests
import json

# API base URL (inside Docker container)
BASE_URL = "http://localhost:8000/api/v1"


def debug_routine_response():
    """Debug the actual routine response format."""
    print("=" * 60)
    print("DEBUGGING ROUTINE API RESPONSE")
    print("=" * 60)

    response = requests.post(f"{BASE_URL}/online/routine")
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        try:
            data = response.json()
            print(f"\nResponse JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            print(
                f"\nResponse Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
            )

            # Check different possible status fields
            possible_status_fields = ["status", "success", "result", "state"]
            for field in possible_status_fields:
                if field in data:
                    print(f"Found {field}: {data[field]}")

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw response text: {response.text}")
    else:
        print(f"Error response: {response.text}")


def check_backtest_status_after_routine():
    """Check backtest status immediately after routine."""
    print(f"\n" + "=" * 60)
    print("CHECKING BACKTEST STATUS AFTER ROUTINE")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/backtest/status")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Backtest Ready: {data.get('ready')}")
        print(f"Message: {data.get('message')}")
        print(f"Signal Count: {data.get('signal_count')}")

        if data.get("ready"):
            print("✅ OnlineManager is now initialized!")
            return True
        else:
            print("⚠️ OnlineManager still not ready")
            return False
    else:
        print(f"❌ Status check failed: {response.text}")
        return False


def main():
    print("\n" + "=" * 60)
    print("ROUTINE RESPONSE DEBUG")
    print("=" * 60)

    # Debug routine response
    debug_routine_response()

    # Check if backtest is ready after routine
    is_ready = check_backtest_status_after_routine()

    if is_ready:
        print(f"\n🎉 SUCCESS: System is ready for backtest!")
        print("You can now run the backtest API test.")
    else:
        print(f"\n⚠️ ISSUE: System not ready yet.")
        print("May need to investigate OnlineManager initialization.")


if __name__ == "__main__":
    main()
