#!/usr/bin/env python3
"""
Test API endpoints for Factors page debugging
"""
import requests
import json
import sys


def get_auth_token():
    """Get authentication token"""
    try:
        # Try different login endpoints
        endpoints_to_try = [
            "/api/v1/login/access-token",
            "/api/v1/auth/login",
            "/api/v1/login",
        ]

        login_data = {"username": "admin@example.com", "password": "changethis"}

        for endpoint in endpoints_to_try:
            print(f"Trying login endpoint: {endpoint}")

            if endpoint == "/api/v1/login/access-token":
                # OAuth2 format for FastAPI
                oauth_data = {
                    "username": "admin@example.com",
                    "password": "changethis",
                    "grant_type": "password",
                }
                response = requests.post(
                    f"http://localhost:8000{endpoint}",
                    data=oauth_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            else:
                # Try form data first
                response = requests.post(
                    f"http://localhost:8000{endpoint}", data=login_data
                )

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                if access_token:
                    print(f"Login successful with {endpoint}")
                    return access_token

            # Try JSON data for non-OAuth endpoints
            if endpoint != "/api/v1/login/access-token":
                response = requests.post(
                    f"http://localhost:8000{endpoint}", json=login_data
                )

                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    if access_token:
                        print(f"Login successful with {endpoint} (JSON)")
                        return access_token

            print(f"  Failed: {response.status_code} - {response.text[:100]}")

        print("All login attempts failed")
        return None

    except Exception as e:
        print(f"Login error: {e}")
        return None


def test_api_endpoint(endpoint, token, description):
    """Test a specific API endpoint"""
    print(f"\n=== Testing {description} ===")
    print(f"Endpoint: {endpoint}")

    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"http://localhost:8000{endpoint}", headers=headers)

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")

        if response.status_code == 200:
            try:
                data = response.json()
                print("Response (JSON):")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except:
                print("Response (Text):")
                print(response.text[:500])
        else:
            print("Error Response:")
            print(response.text[:500])

    except Exception as e:
        print(f"Request error: {e}")


def main():
    print("Testing API endpoints for Factors page...")

    # Get authentication token
    token = get_auth_token()
    if not token:
        print("Failed to get authentication token")
        sys.exit(1)

    print(f"Got token: {token[:20]}...")

    # Test endpoints
    endpoints = [
        ("/api/v1/factors/label-config", "Label Config"),
        ("/api/v1/factors/builtin-libraries/alpha158", "Alpha158 Info"),
        ("/api/v1/factors/?factor_type=feature", "Custom Features"),
    ]

    for endpoint, description in endpoints:
        test_api_endpoint(endpoint, token, description)

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
