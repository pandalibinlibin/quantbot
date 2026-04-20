#!/usr/bin/env python3
"""
测试回测配置API和数据一致性

执行命令：
docker compose exec backend python /app/temp_scripts/test_backtest_config_api.py
"""

import requests
import json


def test_backtest_config_api():
    """测试回测配置API"""
    print("🔍 Testing Backtest Configuration API")
    print("=" * 50)

    try:
        # 测试配置API
        response = requests.get("http://localhost:8000/api/v1/backtest/config")
        print(f"Config API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Config API working")

            config = data.get("config", {})
            strategy = config.get("strategy", {})
            backtest = config.get("backtest", {})

            print(f"\nStrategy Configuration:")
            print(f"  Class: {strategy.get('class', 'N/A')}")
            print(f"  Module: {strategy.get('module_path', 'N/A')}")
            print(
                f"  Max Deviation: {strategy.get('kwargs', {}).get('max_deviation', 'N/A')}"
            )
            print(
                f"  Min Weight: {strategy.get('kwargs', {}).get('min_weight', 'N/A')}"
            )
            print(f"  Benchmark: {strategy.get('kwargs', {}).get('benchmark', 'N/A')}")

            print(f"\nBacktest Parameters:")
            print(f"  Account: {backtest.get('account', 'N/A')}")
            print(f"  Benchmark: {backtest.get('benchmark', 'N/A')}")

        else:
            print(f"❌ Config API failed: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Config API error: {e}")

    try:
        # 测试状态API
        response = requests.get("http://localhost:8000/api/v1/backtest/status")
        print(f"\nStatus API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Status API working")
            print(f"Ready: {data.get('ready', 'N/A')}")
            print(f"Message: {data.get('message', 'N/A')}")
        else:
            print(f"❌ Status API failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Status API error: {e}")


def test_backtest_execution():
    """测试回测执行"""
    print("\n🚀 Testing Backtest Execution")
    print("=" * 50)

    try:
        payload = {"benchmark": "SH000300"}

        response = requests.post(
            "http://localhost:8000/api/v1/backtest/run",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        print(f"Backtest API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Backtest API working")

            if data.get("status") == "success":
                result = data.get("result", {})
                print(f"\n📊 Backtest Results:")
                trading_days = result.get("trading_days", "N/A")
                total_return = result.get("total_return", "N/A")
                net_return = result.get("net_return", "N/A")
                final_value = result.get("final_account_value", 0)

                print(f"  Trading Days: {trading_days}")
                if isinstance(total_return, (int, float)):
                    print(f"  Total Return: {total_return:.4f}")
                else:
                    print(f"  Total Return: {total_return}")

                if isinstance(net_return, (int, float)):
                    print(f"  Net Return: {net_return:.4f}")
                else:
                    print(f"  Net Return: {net_return}")

                if isinstance(final_value, (int, float)):
                    print(f"  Final Value: ¥{final_value:,.0f}")
                else:
                    print(f"  Final Value: {final_value}")
            else:
                print(f"❌ Backtest failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Backtest API failed: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Backtest execution error: {e}")


if __name__ == "__main__":
    test_backtest_config_api()
    test_backtest_execution()
