#!/usr/bin/env python3
"""
回测功能完整测试脚本
测试当前回测功能的各个方面，为后续增强做准备
"""

import requests
import json
import time
from datetime import datetime


def test_backtest_functionality():
    """测试回测功能的完整流程"""

    print("🔧 回测功能完整测试")
    print("=" * 50)

    base_url = "http://localhost:8000/api/v1"
    headers = {"Content-Type": "application/json"}

    # 1. 测试回测配置获取
    print("\n📋 1. 测试回测配置获取...")
    try:
        response = requests.get(
            f"{base_url}/backtest/config", headers=headers, timeout=30
        )
        if response.status_code == 200:
            config_data = response.json()
            print(f"   ✅ 配置获取成功")
            print(
                f"   📊 策略类型: {config_data.get('config', {}).get('strategy', {}).get('class', 'N/A')}"
            )

            # 显示关键配置
            strategy_config = (
                config_data.get("config", {}).get("strategy", {}).get("kwargs", {})
            )
            backtest_config = config_data.get("config", {}).get("backtest", {})

            print(f"   🎯 策略参数:")
            print(f"      • topk: {strategy_config.get('topk', 'N/A')}")
            print(f"      • n_drop: {strategy_config.get('n_drop', 'N/A')}")
            print(f"      • account: {backtest_config.get('account', 'N/A')}")
            print(f"      • benchmark: {backtest_config.get('benchmark', 'N/A')}")
        else:
            print(f"   ❌ 配置获取失败: HTTP {response.status_code}")
            print(f"      错误: {response.text}")
    except Exception as e:
        print(f"   ❌ 配置获取异常: {e}")

    # 2. 测试回测状态检查
    print("\n🔍 2. 测试回测状态检查...")
    try:
        response = requests.get(
            f"{base_url}/backtest/status", headers=headers, timeout=30
        )
        if response.status_code == 200:
            status_data = response.json()
            print(f"   ✅ 状态检查成功")
            print(f"   📊 准备状态: {status_data.get('ready', False)}")
            print(f"   💬 状态消息: {status_data.get('message', 'N/A')}")
            print(f"   📈 信号数量: {status_data.get('signal_count', 'N/A')}")

            if not status_data.get("ready", False):
                print(f"   ⚠️  回测未准备就绪，可能需要先执行routine")
                return False
        else:
            print(f"   ❌ 状态检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 状态检查异常: {e}")
        return False

    # 3. 测试最新回测结果获取
    print("\n📊 3. 测试最新回测结果获取...")
    try:
        response = requests.get(
            f"{base_url}/backtest/latest-result", headers=headers, timeout=30
        )
        if response.status_code == 200:
            result_data = response.json()
            print(f"   ✅ 结果获取成功")
            print(f"   📊 结果状态: {result_data.get('status', 'N/A')}")

            if result_data.get("status") == "success" and result_data.get("result"):
                result = result_data["result"]
                print(f"   📈 历史回测结果:")
                print(
                    f"      • 时间范围: {result.get('start_time', 'N/A')} ~ {result.get('end_time', 'N/A')}"
                )
                print(f"      • 总收益: {result.get('total_return', 0):.4f}")
                print(f"      • 净收益: {result.get('net_return', 0):.4f}")
                print(f"      • 交易天数: {result.get('trading_days', 'N/A')}")
            else:
                print(f"   ℹ️  暂无历史回测结果")
        else:
            print(f"   ❌ 结果获取失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ 结果获取异常: {e}")

    # 4. 执行新的回测
    print("\n🚀 4. 执行新的回测...")
    try:
        print("   🔄 开始回测执行...")
        start_time = time.time()

        # 使用默认参数执行回测
        response = requests.post(
            f"{base_url}/backtest/run",
            headers=headers,
            json={},  # 使用默认参数
            timeout=300,  # 5分钟超时
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 回测执行成功 (耗时: {duration:.2f}s)")

            # 显示详细结果
            print(f"   📊 回测结果详情:")
            print(f"      • 状态: {result.get('status', 'N/A')}")
            print(
                f"      • 时间范围: {result.get('start_time', 'N/A')} ~ {result.get('end_time', 'N/A')}"
            )
            print(
                f"      • 数据范围: {result.get('data_start_time', 'N/A')} ~ {result.get('data_end_time', 'N/A')}"
            )
            print(f"      • 频率: {result.get('freq', 'N/A')}")
            print(f"      • 交易天数: {result.get('trading_days', 'N/A')}")
            print(f"      • 信号数量: {result.get('signal_count', 'N/A')}")

            print(f"   💰 财务指标:")
            print(f"      • 总收益: {result.get('total_return', 0):.4f}")
            print(f"      • 总成本: {result.get('total_cost', 0):.4f}")
            print(f"      • 净收益: {result.get('net_return', 0):.4f}")
            print(f"      • 最终账户: {result.get('final_account', 0):,.2f}")

            print(f"   🎯 策略配置:")
            print(f"      • 策略类型: {result.get('strategy', 'N/A')}")
            print(f"      • 基准指数: {result.get('benchmark', 'N/A')}")
            print(f"      • 最大偏离: {result.get('max_deviation', 'N/A')}")

            # 检查风险指标
            risk_metrics = result.get("risk_metrics")
            if risk_metrics:
                print(f"   📈 风险指标:")
                print(
                    f"      • 年化收益: {risk_metrics.get('annualized_return', 'N/A')}"
                )
                print(f"      • 最大回撤: {risk_metrics.get('max_drawdown', 'N/A')}")
                print(f"      • 夏普比率: {risk_metrics.get('sharpe_ratio', 'N/A')}")
                print(f"      • 波动率: {risk_metrics.get('volatility', 'N/A')}")
            else:
                print(f"   ⚠️  风险指标未生成")

            # 检查图表数据
            charts = result.get("charts")
            if charts:
                print(f"   📊 图表数据:")
                for chart_name, chart_data in charts.items():
                    if isinstance(chart_data, list):
                        print(f"      • {chart_name}: {len(chart_data)} 数据点")
                    else:
                        print(f"      • {chart_name}: {type(chart_data).__name__}")
            else:
                print(f"   ⚠️  图表数据未生成")

            return True

        else:
            print(f"   ❌ 回测执行失败: HTTP {response.status_code}")
            print(f"      错误: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"   ⏰ 回测执行超时 (>5分钟)")
        return False
    except Exception as e:
        print(f"   ❌ 回测执行异常: {e}")
        return False

    # 5. 验证结果持久化
    print("\n💾 5. 验证结果持久化...")
    try:
        time.sleep(2)  # 等待结果保存
        response = requests.get(
            f"{base_url}/backtest/latest-result", headers=headers, timeout=30
        )
        if response.status_code == 200:
            result_data = response.json()
            if result_data.get("status") == "success":
                print(f"   ✅ 结果持久化成功")
                print(f"   📊 最新结果已保存并可检索")
            else:
                print(f"   ❌ 结果持久化失败")
        else:
            print(f"   ❌ 结果验证失败")
    except Exception as e:
        print(f"   ❌ 结果验证异常: {e}")


def test_online_serving_status():
    """测试Online Serving状态，确保回测有数据基础"""

    print("\n🔍 检查Online Serving状态...")

    try:
        response = requests.get(
            "http://localhost:8000/api/v1/online/status", timeout=30
        )
        if response.status_code == 200:
            status = response.json()
            print(f"   📊 Online Serving状态:")
            print(f"      • 初始化状态: {status.get('is_initialized', False)}")
            print(f"      • 信号数量: {status.get('signal_count', 0)}")

            if not status.get("is_initialized", False):
                print(f"   ⚠️  Online Serving未初始化，建议先执行routine")
                return False

            if status.get("signal_count", 0) == 0:
                print(f"   ⚠️  无可用信号，建议先执行routine")
                return False

            return True
        else:
            print(f"   ❌ 状态检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 状态检查异常: {e}")
        return False


def main():
    """主测试流程"""
    print("🔧 回测功能完整测试启动")
    print("=" * 50)

    # 首先检查Online Serving状态
    if not test_online_serving_status():
        print("\n❌ Online Serving状态不满足回测要求")
        print(
            "💡 建议先执行: docker compose exec backend python -c \"import requests; requests.post('http://localhost:8000/api/v1/online/routine')\""
        )
        return

    # 执行回测功能测试
    success = test_backtest_functionality()

    print("\n" + "=" * 50)
    if success:
        print("🎉 回测功能测试完成 - 基础功能正常")
        print("✅ 可以开始实施回测功能增强")
    else:
        print("❌ 回测功能测试失败 - 需要修复基础问题")
        print("🔧 建议检查系统状态和配置")

    print("\n📋 下一步建议:")
    print("1. 如果测试成功 - 开始实现图表可视化")
    print("2. 如果测试失败 - 修复基础功能问题")
    print("3. 检查前端回测页面显示效果")


if __name__ == "__main__":
    main()
