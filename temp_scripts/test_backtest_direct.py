#!/usr/bin/env python3
"""
直接测试回测功能

执行命令：
docker compose exec backend python /app/temp_scripts/test_backtest_direct.py
"""

import requests
import json


def test_backtest_direct():
    """直接测试回测功能"""
    print("🚀 Direct Backtest Test")
    print("=" * 50)

    # 1. 检查backtest状态
    try:
        response = requests.get("http://localhost:8000/api/v1/backtest/status")
        if response.status_code == 200:
            data = response.json()
            ready = data.get("ready", False)
            message = data.get("message", "N/A")
            print(f"✅ Backtest Status: Ready={ready}")
            print(f"   Message: {message}")

            if not ready:
                print("❌ Backtest not ready, cannot proceed")
                return False
        else:
            print(f"❌ Failed to get backtest status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backtest status check failed: {e}")
        return False

    # 2. 执行回测
    print("\n🔄 Executing backtest...")
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
            print("✅ Backtest API responded successfully")

            if data.get("status") == "success":
                result = data.get("result", {})
                print(f"\n📊 Backtest Results:")

                # 基本信息
                print(
                    f"  Data Period: {result.get('data_start_time', 'N/A')} to {result.get('data_end_time', 'N/A')}"
                )
                print(f"  Trading Days: {result.get('trading_days', 'N/A')}")

                # 收益指标
                total_return = result.get("total_return", "N/A")
                net_return = result.get("net_return", "N/A")
                final_value = result.get("final_account_value", "N/A")

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

                # 性能指标
                metrics = result.get("metrics", {})
                if metrics:
                    print(f"\n📈 Performance Metrics:")

                    ann_return = metrics.get("annualized_return", "N/A")
                    sharpe = metrics.get("sharpe_ratio", "N/A")
                    max_dd = metrics.get("max_drawdown", "N/A")
                    volatility = metrics.get("volatility", "N/A")

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

                    if isinstance(volatility, (int, float)):
                        print(f"  Volatility: {volatility:.2%}")
                    else:
                        print(f"  Volatility: {volatility}")

                # 图表数据
                charts = result.get("charts", {})
                if charts:
                    equity_curve = charts.get("equity_curve", [])
                    daily_returns = charts.get("daily_returns", [])
                    drawdown = charts.get("drawdown", [])

                    print(f"\n📊 Chart Data Available:")
                    print(f"  Equity Curve: {len(equity_curve)} points")
                    print(f"  Daily Returns: {len(daily_returns)} points")
                    print(f"  Drawdown: {len(drawdown)} points")

                print("\n🎉 Backtest completed successfully!")
                return True

            else:
                error_msg = data.get("error", "Unknown error")
                print(f"❌ Backtest failed: {error_msg}")
                return False

        else:
            print(f"❌ Backtest API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Backtest execution error: {e}")
        return False


def main():
    """主函数"""
    success = test_backtest_direct()

    print("\n" + "=" * 50)
    if success:
        print("✅ 回测功能测试成功！")
        print("💡 现在可以在前端 /backtest 页面使用回测功能了")
    else:
        print("❌ 回测功能测试失败")
        print("💡 请检查上述错误信息")


if __name__ == "__main__":
    main()
