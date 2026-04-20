#!/usr/bin/env python3
"""
测试Strategy Configuration显示修复

执行命令：
docker compose exec backend python /app/temp_scripts/test_strategy_config_display.py
"""

import requests
import json


def test_strategy_config_display():
    """测试策略配置显示"""
    print("🔍 Testing Strategy Configuration Display")
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

                print(f"\n📋 Strategy Configuration:")
                print(f"  Class: {strategy.get('class', 'N/A')}")
                print(f"  Module Path: {strategy.get('module_path', 'N/A')}")

                # Check if kwargs exist (should be removed)
                kwargs = strategy.get("kwargs", {})
                if kwargs:
                    print(f"  ❌ Strategy Parameters (should be removed):")
                    for key, value in kwargs.items():
                        print(f"    {key}: {value}")
                else:
                    print(f"  ✅ Strategy Parameters: None (correctly simplified)")

                print(f"\n📋 Backtest Parameters:")
                print(f"  Account: {backtest.get('account', 'N/A')}")
                print(f"  Benchmark: {backtest.get('benchmark', 'N/A')}")

                # Trading costs (these are acceptable to show)
                trading_costs = backtest.get("trade", {})
                if trading_costs:
                    print(f"\n📋 Trading Costs:")
                    for key, value in trading_costs.items():
                        print(f"  {key}: {value}")

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


def main():
    """主函数"""
    success = test_strategy_config_display()

    print("\n" + "=" * 50)
    if success:
        print("✅ Strategy Configuration显示测试完成")
        print("💡 前端应该只显示策略名称和模块路径，不显示具体参数")
    else:
        print("❌ Strategy Configuration显示测试失败")


if __name__ == "__main__":
    main()
