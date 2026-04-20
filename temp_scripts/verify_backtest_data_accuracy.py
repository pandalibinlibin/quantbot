#!/usr/bin/env python3
"""
验证回测结果数据准确性

这个脚本用于：
1. 执行一次新的回测
2. 获取详细的回测结果
3. 验证前端显示数据的准确性
4. 对比配置文件和实际执行的策略
"""

import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def check_backend_status():
    """检查后端服务状态"""
    try:
        response = requests.get("http://localhost:8000/api/v1/online-serving/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Backend not responding: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False


def get_backtest_config():
    """获取回测配置"""
    try:
        response = requests.get("http://localhost:8000/api/v1/backtest/config")
        if response.status_code == 200:
            data = response.json()
            print("✅ Backtest Configuration Retrieved")

            config = data.get("config", {})
            strategy = config.get("strategy", {})
            backtest = config.get("backtest", {})

            print(f"Strategy Class: {strategy.get('class', 'N/A')}")
            print(f"Module Path: {strategy.get('module_path', 'N/A')}")
            print(f"Strategy Kwargs: {strategy.get('kwargs', {})}")
            print(f"Benchmark: {backtest.get('benchmark', 'N/A')}")
            print(f"Account: {backtest.get('account', 'N/A')}")

            return data
        else:
            print(f"❌ Failed to get config: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Config request failed: {e}")
        return None


def execute_backtest():
    """执行回测"""
    try:
        # 使用正确的基准参数
        payload = {"benchmark": "SH000300"}

        response = requests.post(
            "http://localhost:8000/api/v1/backtest/run",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Backtest Executed Successfully")

            if data.get("status") == "success":
                result = data.get("result", {})
                print("\n📊 Backtest Results Summary:")
                print(
                    f"Data Period: {result.get('data_start_time')} to {result.get('data_end_time')}"
                )
                print(f"Trading Days: {result.get('trading_days', 'N/A')}")
                print(f"Total Return: {result.get('total_return', 'N/A')}")
                print(f"Net Return: {result.get('net_return', 'N/A')}")
                print(f"Total Cost: {result.get('total_cost', 'N/A')}")
                print(
                    f"Final Account Value: {result.get('final_account_value', 'N/A')}"
                )

                # 详细指标
                if "metrics" in result:
                    metrics = result["metrics"]
                    print(f"\n📈 Performance Metrics:")
                    print(
                        f"Annualized Return: {metrics.get('annualized_return', 'N/A')}"
                    )
                    print(f"Volatility: {metrics.get('volatility', 'N/A')}")
                    print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}")
                    print(f"Max Drawdown: {metrics.get('max_drawdown', 'N/A')}")
                    print(
                        f"Information Ratio: {metrics.get('information_ratio', 'N/A')}"
                    )

                return data
            else:
                print(f"❌ Backtest failed: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"❌ Backtest request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Backtest execution failed: {e}")
        return None


def get_latest_result():
    """获取最新回测结果"""
    try:
        response = requests.get("http://localhost:8000/api/v1/backtest/latest-result")
        if response.status_code == 200:
            data = response.json()
            print("✅ Latest Result Retrieved")
            return data
        else:
            print(f"❌ Failed to get latest result: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Latest result request failed: {e}")
        return None


def verify_data_accuracy(backtest_result):
    """验证数据准确性"""
    print("\n🔍 Data Accuracy Verification:")

    if not backtest_result or backtest_result.get("status") != "success":
        print("❌ No valid backtest result to verify")
        return False

    result = backtest_result.get("result", {})

    # 验证基本数据
    checks = []

    # 检查交易天数
    trading_days = result.get("trading_days")
    if trading_days and isinstance(trading_days, int) and trading_days > 0:
        checks.append(f"✅ Trading Days: {trading_days} (valid)")
    else:
        checks.append(f"❌ Trading Days: {trading_days} (invalid)")

    # 检查收益率
    total_return = result.get("total_return")
    net_return = result.get("net_return")
    if total_return is not None and net_return is not None:
        if isinstance(total_return, (int, float)) and isinstance(
            net_return, (int, float)
        ):
            checks.append(
                f"✅ Returns: Total {total_return:.2%}, Net {net_return:.2%} (valid)"
            )
        else:
            checks.append(f"❌ Returns: Invalid format")
    else:
        checks.append(f"❌ Returns: Missing data")

    # 检查账户价值
    final_value = result.get("final_account_value")
    if final_value and isinstance(final_value, (int, float)) and final_value > 0:
        checks.append(f"✅ Final Account Value: ¥{final_value:,.0f} (valid)")
    else:
        checks.append(f"❌ Final Account Value: {final_value} (invalid)")

    # 检查成本
    total_cost = result.get("total_cost")
    if total_cost is not None and isinstance(total_cost, (int, float)):
        cost_pct = total_cost * 100
        checks.append(f"✅ Total Cost: {cost_pct:.2f}% (valid)")
    else:
        checks.append(f"❌ Total Cost: {total_cost} (invalid)")

    # 检查图表数据
    charts = result.get("charts", {})
    if charts:
        equity_curve = charts.get("equity_curve", [])
        daily_returns = charts.get("daily_returns", [])
        drawdown = charts.get("drawdown", [])

        checks.append(
            f"✅ Chart Data: Equity({len(equity_curve)}), Returns({len(daily_returns)}), Drawdown({len(drawdown)})"
        )
    else:
        checks.append(f"❌ Chart Data: Missing")

    for check in checks:
        print(check)

    # 计算验证通过率
    passed = sum(1 for check in checks if check.startswith("✅"))
    total = len(checks)
    accuracy = passed / total * 100

    print(
        f"\n📊 Verification Summary: {passed}/{total} checks passed ({accuracy:.1f}%)"
    )

    return accuracy >= 80  # 80%以上通过率认为数据准确


def compare_frontend_backend_data():
    """对比前端显示和后端实际数据"""
    print("\n🔄 Frontend vs Backend Data Comparison:")

    # 前端显示的数据（从截图中获取）
    frontend_data = {
        "strategy_class": "TopkDropoutStrategy",  # 前端显示错误
        "trading_days": 724,
        "total_return": 0.5570,  # 55.70%
        "net_return": 0.1320,  # 13.20%
        "total_cost": 0.4249,  # 42.49%
        "final_account_value": 109175027,
        "benchmark": "000300.SH",
    }

    # 获取后端实际数据
    latest_result = get_latest_result()
    if latest_result and latest_result.get("status") == "success":
        backend_result = latest_result.get("result", {})

        comparisons = [
            (
                "Trading Days",
                frontend_data["trading_days"],
                backend_result.get("trading_days"),
            ),
            (
                "Total Return",
                f"{frontend_data['total_return']:.2%}",
                f"{backend_result.get('total_return', 0):.2%}",
            ),
            (
                "Net Return",
                f"{frontend_data['net_return']:.2%}",
                f"{backend_result.get('net_return', 0):.2%}",
            ),
            (
                "Total Cost",
                f"{frontend_data['total_cost']:.2%}",
                f"{backend_result.get('total_cost', 0)*100:.2f}%",
            ),
            (
                "Final Account Value",
                f"¥{frontend_data['final_account_value']:,}",
                f"¥{backend_result.get('final_account_value', 0):,.0f}",
            ),
        ]

        print("Field | Frontend | Backend | Match")
        print("-" * 50)

        matches = 0
        for field, frontend_val, backend_val in comparisons:
            match = "✅" if str(frontend_val) == str(backend_val) else "❌"
            if match == "✅":
                matches += 1
            print(f"{field:<20} | {frontend_val:<12} | {backend_val:<12} | {match}")

        print(f"\nData Consistency: {matches}/{len(comparisons)} fields match")

        return matches == len(comparisons)
    else:
        print("❌ Cannot get backend data for comparison")
        return False


def main():
    """主函数"""
    print("🔍 Backtest Data Accuracy Verification")
    print("=" * 50)

    # 1. 检查后端状态
    if not check_backend_status():
        return

    print("\n" + "=" * 50)

    # 2. 获取配置信息
    config_data = get_backtest_config()

    print("\n" + "=" * 50)

    # 3. 执行新的回测
    backtest_result = execute_backtest()

    print("\n" + "=" * 50)

    # 4. 验证数据准确性
    is_accurate = verify_data_accuracy(backtest_result)

    print("\n" + "=" * 50)

    # 5. 对比前端后端数据
    is_consistent = compare_frontend_backend_data()

    print("\n" + "=" * 50)
    print("📋 Final Assessment:")

    if config_data:
        strategy_class = (
            config_data.get("config", {}).get("strategy", {}).get("class", "Unknown")
        )
        print(f"Strategy Configuration: {strategy_class}")
        if strategy_class == "EnhancedIndexingStrategy":
            print("✅ Strategy configuration is now correct")
        else:
            print("❌ Strategy configuration still shows wrong strategy")

    if is_accurate:
        print("✅ Backtest data accuracy is good")
    else:
        print("❌ Backtest data accuracy needs improvement")

    if is_consistent:
        print("✅ Frontend and backend data are consistent")
    else:
        print("❌ Frontend and backend data are inconsistent")

    print("\n🎯 Recommendations:")
    if strategy_class != "EnhancedIndexingStrategy":
        print("- Update backtest_config.yaml to show Enhanced Indexing Strategy")
    if not is_accurate:
        print("- Investigate data calculation issues in backend")
    if not is_consistent:
        print("- Check frontend data binding and API responses")
        print("- Refresh frontend cache after backend config changes")


if __name__ == "__main__":
    main()
