#!/usr/bin/env python3
"""
测试API路径是否正确

执行命令：
docker compose exec backend python /app/temp_scripts/test_api_paths.py
"""

import requests


def test_api_endpoints():
    """测试各个API端点"""
    print("🔍 Testing API Endpoints")
    print("=" * 50)

    endpoints = [
        ("Online Status", "GET", "http://localhost:8000/api/v1/online/status"),
        ("Online Routine", "POST", "http://localhost:8000/api/v1/online/routine"),
        ("Backtest Config", "GET", "http://localhost:8000/api/v1/backtest/config"),
        ("Backtest Status", "GET", "http://localhost:8000/api/v1/backtest/status"),
    ]

    for name, method, url in endpoints:
        try:
            if method == "GET":
                response = requests.get(url)
            else:
                response = requests.post(url, json={})

            print(
                f"{name:<20} | {method:<4} | {response.status_code:<3} | {'✅' if response.status_code == 200 else '❌'}"
            )

            if response.status_code == 200:
                data = response.json()
                if name == "Online Status":
                    status = data.get("status", "unknown")
                    is_initialized = data.get("is_initialized", False)
                    print(
                        f"                     Status: {status}, Initialized: {is_initialized}"
                    )
                elif name == "Backtest Config":
                    config = data.get("config", {})
                    strategy = config.get("strategy", {})
                    print(
                        f"                     Strategy: {strategy.get('class', 'N/A')}"
                    )
                elif name == "Backtest Status":
                    ready = data.get("ready", False)
                    message = data.get("message", "N/A")
                    print(f"                     Ready: {ready}, Message: {message}")
                elif name == "Online Routine":
                    routine_status = data.get("status", "unknown")
                    print(f"                     Routine Status: {routine_status}")
            else:
                print(f"                     Error: {response.text[:100]}")

        except Exception as e:
            print(f"{name:<20} | {method:<4} | ERR | ❌ - {str(e)[:50]}")

    print("\n" + "=" * 50)
    print("API路径测试完成")


if __name__ == "__main__":
    test_api_endpoints()
