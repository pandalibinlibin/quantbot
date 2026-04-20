#!/usr/bin/env python3
"""
完整的回测功能测试

执行命令：
docker compose exec backend python /app/temp_scripts/test_backtest_complete.py
"""

import requests
import json
import time


def test_routine_status():
    """检查routine状态"""
    print("🔍 Checking Routine Status")
    print("=" * 50)

    try:
        response = requests.get("http://localhost:8000/api/v1/online/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Online Serving Status: {data.get('status', 'unknown')}")

            if data.get("status") == "ready":
                print("✅ Routine is ready for backtest")
                return True
            else:
                print("❌ Routine not ready - need to run routine first")
                return False
        else:
            print(f"❌ Failed to get routine status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Routine status check failed: {e}")
        return False


def test_backtest_config_api():
    """测试回测配置API"""
    print("\n🔍 Testing Backtest Configuration API")
    print("=" * 50)

    try:
        response = requests.get("http://localhost:8000/api/v1/backtest/config")
        print(f"Config API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Config API working")

            if data.get("status") == "success":
                config = data.get("config", {})
                strategy = config.get("strategy", {})
                backtest = config.get("backtest", {})

                print(f"\nStrategy Configuration:")
                print(f"  Class: {strategy.get('class', 'N/A')}")
                print(f"  Module: {strategy.get('module_path', 'N/A')}")

                kwargs = strategy.get("kwargs", {})
                print(f"  Max Deviation: {kwargs.get('max_deviation', 'N/A')}")
                print(f"  Min Weight: {kwargs.get('min_weight', 'N/A')}")
                print(f"  Benchmark: {kwargs.get('benchmark', 'N/A')}")

                print(f"\nBacktest Parameters:")
                print(f"  Account: {backtest.get('account', 'N/A')}")
                print(f"  Benchmark: {backtest.get('benchmark', 'N/A')}")

                return True
            else:
                print(f"❌ Config API error: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Config API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Config API error: {e}")
        return False


def test_backtest_status_api():
    """测试回测状态API"""
    print("\n🔍 Testing Backtest Status API")
    print("=" * 50)

    try:
        response = requests.get("http://localhost:8000/api/v1/backtest/status")
        print(f"Status API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Status API working")
            print(f"Ready: {data.get('ready', 'N/A')}")
            print(f"Message: {data.get('message', 'N/A')}")
            return data.get("ready", False)
        else:
            print(f"❌ Status API failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Status API error: {e}")
        return False


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

                # 安全地显示结果
                trading_days = result.get("trading_days", "N/A")
                total_return = result.get("total_return", "N/A")
                net_return = result.get("net_return", "N/A")
                final_value = result.get("final_account_value", "N/A")

                print(f"  Trading Days: {trading_days}")

                if isinstance(total_return, (int, float)):
                    print(f"  Total Return: {total_return:.2%}")
                else:
                    print(f"  Total Return: {total_return}")

                if isinstance(net_return, (int, float)):
                    print(f"  Net Return: {net_return:.2%}")
                else:
                    print(f"  Net Return: {net_return}")

                if isinstance(final_value, (int, float)):
                    print(f"  Final Value: ¥{final_value:,.0f}")
                else:
                    print(f"  Final Value: {final_value}")

                # 显示性能指标
                metrics = result.get("metrics", {})
                if metrics:
                    print(f"\n📈 Performance Metrics:")
                    ann_return = metrics.get("annualized_return", "N/A")
                    sharpe = metrics.get("sharpe_ratio", "N/A")
                    max_dd = metrics.get("max_drawdown", "N/A")

                    if isinstance(ann_return, (int, float)):
                        print(f"  Annualized Return: {ann_return:.2%}")
                    else:
                        print(f"  Annualized Return: {ann_return}")

                    if isinstance(sharpe, (int, float)):
                        print(f"  Sharpe Ratio: {sharpe:.2f}")
                    else:
                        print(f"  Sharpe Ratio: {sharpe}")

                    if isinstance(max_dd, (int, float)):
                        print(f"  Max Drawdown: {max_dd:.2%}")
                    else:
                        print(f"  Max Drawdown: {max_dd}")

                return True
            else:
                print(f"❌ Backtest failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Backtest API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Backtest execution error: {e}")
        return False


def run_routine_if_needed():
    """如果需要，运行routine"""
    print("\n🔄 Checking if routine needs to be run")
    print("=" * 50)

    try:
        response = requests.post("http://localhost:8000/api/v1/online/routine")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print("✅ Routine executed successfully")
                print("⏳ Waiting 10 seconds for routine to complete...")
                time.sleep(10)
                return True
            else:
                print(f"❌ Routine failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Routine API failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Routine execution error: {e}")
        return False


def main():
    """主测试函数"""
    print("🧪 Complete Backtest Functionality Test")
    print("=" * 60)

    # 1. 检查routine状态
    routine_ready = test_routine_status()

    # 2. 如果routine未准备好，尝试运行routine
    if not routine_ready:
        print("\n🔄 Routine not ready, attempting to run routine...")
        if run_routine_if_needed():
            routine_ready = test_routine_status()

    # 3. 测试配置API
    config_ok = test_backtest_config_api()

    # 4. 测试状态API
    status_ok = test_backtest_status_api()

    # 5. 如果配置正常且状态准备就绪，测试回测执行
    if config_ok and status_ok:
        print("\n🚀 Prerequisites met, proceeding with backtest execution...")
        backtest_ok = test_backtest_execution()
    else:
        print("\n⚠️  Skipping backtest execution - prerequisites not met")
        print(f"    Config OK: {config_ok}, Status OK: {status_ok}")
        backtest_ok = False

    # 6. 总结
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"  Routine Ready: {'✅' if routine_ready else '❌'}")
    print(f"  Config API: {'✅' if config_ok else '❌'}")
    print(f"  Status API: {'✅' if status_ok else '❌'}")
    print(f"  Backtest Execution: {'✅' if backtest_ok else '❌'}")

    if all([routine_ready, config_ok, status_ok, backtest_ok]):
        print("\n🎉 All tests passed! Backtest functionality is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")


if __name__ == "__main__":
    main()
