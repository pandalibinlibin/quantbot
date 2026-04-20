#!/usr/bin/env python3
"""
Enhanced Indexing Strategy 回测功能完整测试
基于我们之前讨论的自定义指数增强策略进行回测测试
"""

import requests
import json
import time
from datetime import datetime


def check_online_serving_status():
    """检查Online Serving状态，确保有信号可用于回测"""
    print("🔍 检查Online Serving状态...")

    try:
        response = requests.get(
            "http://localhost:8000/api/v1/online/status", timeout=30
        )
        if response.status_code == 200:
            status = response.json()
            is_initialized = status.get("is_initialized", False)
            signal_count = status.get("signal_count", 0)

            print(f"   📊 初始化状态: {is_initialized}")
            print(f"   📈 信号数量: {signal_count}")

            if not is_initialized:
                print(f"   ⚠️  Online Serving未初始化")
                return False

            if signal_count == 0:
                print(f"   ⚠️  无可用信号")
                return False

            print(f"   ✅ Online Serving状态正常")
            return True
        else:
            print(f"   ❌ 状态检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 状态检查异常: {e}")
        return False


def get_backtest_config():
    """获取回测配置信息"""
    print("\n📋 获取回测配置...")

    try:
        response = requests.get(
            "http://localhost:8000/api/v1/backtest/config", timeout=30
        )
        if response.status_code == 200:
            config_data = response.json()
            print(f"   ✅ 配置获取成功")

            config = config_data.get("config", {})
            strategy_config = config.get("strategy", {})
            backtest_config = config.get("backtest", {})

            print(f"   🎯 策略配置:")
            print(f"      • 策略类: {strategy_config.get('class', 'N/A')}")
            print(f"      • 模块路径: {strategy_config.get('module_path', 'N/A')}")

            strategy_kwargs = strategy_config.get("kwargs", {})
            print(f"   📊 策略参数:")
            print(f"      • topk: {strategy_kwargs.get('topk', 'N/A')}")
            print(f"      • n_drop: {strategy_kwargs.get('n_drop', 'N/A')}")

            print(f"   💰 回测配置:")
            print(f"      • 基准指数: {backtest_config.get('benchmark', 'N/A')}")
            print(f"      • 初始资金: {backtest_config.get('account', 'N/A'):,}")

            exchange_kwargs = backtest_config.get("exchange_kwargs", {})
            print(f"   💸 交易成本:")
            print(f"      • 开仓费率: {exchange_kwargs.get('open_cost', 'N/A')}")
            print(f"      • 平仓费率: {exchange_kwargs.get('close_cost', 'N/A')}")
            print(f"      • 最小手续费: {exchange_kwargs.get('min_cost', 'N/A')}")

            return config_data
        else:
            print(f"   ❌ 配置获取失败: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ 配置获取异常: {e}")
        return None


def check_backtest_status():
    """检查回测准备状态"""
    print("\n🔍 检查回测准备状态...")

    try:
        response = requests.get(
            "http://localhost:8000/api/v1/backtest/status", timeout=30
        )
        if response.status_code == 200:
            status = response.json()
            ready = status.get("ready", False)
            message = status.get("message", "N/A")
            signal_count = status.get("signal_count", 0)

            print(f"   📊 准备状态: {ready}")
            print(f"   💬 状态消息: {message}")
            print(f"   📈 可用信号: {signal_count}")

            if ready:
                print(f"   ✅ 回测准备就绪")
                return True
            else:
                print(f"   ⚠️  回测未准备就绪")
                return False
        else:
            print(f"   ❌ 状态检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 状态检查异常: {e}")
        return False


def execute_enhanced_indexing_backtest():
    """执行Enhanced Indexing Strategy回测"""
    print("\n🚀 执行Enhanced Indexing Strategy回测...")
    print("   📝 注意: 使用我们自定义的指数增强策略")
    print("   ⏱️  预计耗时: 30-60秒")

    try:
        start_time = time.time()

        # 使用默认参数执行回测（将使用Enhanced Indexing Strategy）
        response = requests.post(
            "http://localhost:8000/api/v1/backtest/run",
            json={},  # 使用默认配置
            timeout=300,  # 5分钟超时
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 回测执行成功 (耗时: {duration:.2f}s)")

            # 显示核心结果
            print(f"\n   📊 Enhanced Indexing Strategy 回测结果:")
            print(f"      • 执行状态: {result.get('status', 'N/A')}")
            print(f"      • 策略类型: {result.get('strategy', 'N/A')}")
            print(f"      • 基准指数: {result.get('benchmark', 'N/A')}")
            print(f"      • 最大偏离: {result.get('max_deviation', 'N/A')}")

            print(f"\n   📅 时间范围:")
            print(
                f"      • 回测期间: {result.get('start_time', 'N/A')} ~ {result.get('end_time', 'N/A')}"
            )
            print(
                f"      • 数据范围: {result.get('data_start_time', 'N/A')} ~ {result.get('data_end_time', 'N/A')}"
            )
            print(f"      • 频率: {result.get('freq', 'N/A')}")
            print(f"      • 交易天数: {result.get('trading_days', 'N/A')}")
            print(f"      • 信号数量: {result.get('signal_count', 'N/A')}")

            print(f"\n   💰 财务表现:")
            total_return = result.get("total_return", 0)
            total_cost = result.get("total_cost", 0)
            net_return = result.get("net_return", 0)
            final_account = result.get("final_account", 0)

            print(f"      • 总收益: {total_return:.4f}")
            print(f"      • 总成本: {total_cost:.4f}")
            print(f"      • 净收益: {net_return:.4f}")
            print(f"      • 最终账户: {final_account:,.2f}")

            # 计算收益率
            initial_account = 100000000  # 默认初始资金
            if final_account > 0:
                total_return_rate = (final_account - initial_account) / initial_account
                print(
                    f"      • 总收益率: {total_return_rate:.4f} ({total_return_rate*100:.2f}%)"
                )

            # 显示风险指标
            risk_metrics = result.get("risk_metrics", {})
            if risk_metrics:
                print(f"\n   📈 风险指标:")
                print(
                    f"      • 年化收益: {risk_metrics.get('annualized_return', 'N/A')}"
                )
                print(f"      • 最大回撤: {risk_metrics.get('max_drawdown', 'N/A')}")
                print(f"      • 夏普比率: {risk_metrics.get('sharpe_ratio', 'N/A')}")
                print(f"      • 波动率: {risk_metrics.get('volatility', 'N/A')}")
                print(f"      • 卡玛比率: {risk_metrics.get('calmar_ratio', 'N/A')}")
                print(f"      • 胜率: {risk_metrics.get('win_rate', 'N/A')}")
                print(f"      • 盈亏比: {risk_metrics.get('profit_loss_ratio', 'N/A')}")
            else:
                print(f"   ⚠️  风险指标未生成")

            # 检查图表数据
            charts = result.get("charts", {})
            if charts:
                print(f"\n   📊 图表数据:")
                for chart_name, chart_data in charts.items():
                    if isinstance(chart_data, list):
                        print(f"      • {chart_name}: {len(chart_data)} 数据点")
                    elif isinstance(chart_data, dict):
                        print(f"      • {chart_name}: {len(chart_data)} 字段")
                    else:
                        print(f"      • {chart_name}: {type(chart_data).__name__}")
            else:
                print(f"   ⚠️  图表数据未生成")

            return result

        else:
            print(f"   ❌ 回测执行失败: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"      错误详情: {error_data}")
            except:
                print(f"      错误内容: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print(f"   ⏰ 回测执行超时 (>5分钟)")
        return None
    except Exception as e:
        print(f"   ❌ 回测执行异常: {e}")
        return None


def verify_result_persistence():
    """验证回测结果持久化"""
    print("\n💾 验证回测结果持久化...")

    try:
        time.sleep(2)  # 等待结果保存
        response = requests.get(
            "http://localhost:8000/api/v1/backtest/latest-result", timeout=30
        )

        if response.status_code == 200:
            result_data = response.json()

            if result_data.get("status") == "success":
                result = result_data.get("result", {})
                print(f"   ✅ 结果持久化成功")
                print(f"   📊 最新结果可检索")
                print(f"      • 策略类型: {result.get('strategy', 'N/A')}")
                print(f"      • 净收益: {result.get('net_return', 0):.4f}")
                print(f"      • 交易天数: {result.get('trading_days', 'N/A')}")
                return True
            else:
                print(f"   ❌ 结果状态异常: {result_data.get('status', 'unknown')}")
                return False
        else:
            print(f"   ❌ 结果验证失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 结果验证异常: {e}")
        return False


def analyze_backtest_gaps(result):
    """分析回测功能缺口"""
    print("\n🔍 分析回测功能缺口...")

    gaps = []

    # 检查风险指标完整性
    risk_metrics = result.get("risk_metrics", {}) if result else {}
    expected_metrics = [
        "annualized_return",
        "max_drawdown",
        "sharpe_ratio",
        "volatility",
        "calmar_ratio",
        "win_rate",
        "profit_loss_ratio",
    ]

    missing_metrics = [m for m in expected_metrics if not risk_metrics.get(m)]
    if missing_metrics:
        gaps.append(f"缺失风险指标: {', '.join(missing_metrics)}")

    # 检查图表数据
    charts = result.get("charts", {}) if result else {}
    expected_charts = ["equity_curve", "drawdown_curve", "return_distribution"]

    missing_charts = [c for c in expected_charts if c not in charts]
    if missing_charts:
        gaps.append(f"缺失图表数据: {', '.join(missing_charts)}")

    # 检查策略参数配置
    if result and result.get("strategy") == "enhanced_indexing":
        if not result.get("max_deviation"):
            gaps.append("Enhanced Indexing参数未显示")

    # 输出分析结果
    if gaps:
        print(f"   📋 发现的功能缺口:")
        for i, gap in enumerate(gaps, 1):
            print(f"      {i}. {gap}")
    else:
        print(f"   ✅ 回测功能基本完整")

    return gaps


def suggest_enhancements():
    """建议回测功能增强方案"""
    print("\n💡 回测功能增强建议:")

    enhancements = [
        {
            "priority": "高",
            "title": "图表可视化增强",
            "description": "实现净值曲线、回撤曲线、收益分布等专业图表",
            "files": [
                "frontend/src/routes/_layout/backtest.tsx",
                "backend图表数据生成",
            ],
        },
        {
            "priority": "高",
            "title": "风险指标完善",
            "description": "补充信息比率、索提诺比率、VaR等高级风险指标",
            "files": ["backend/app/services/online_serving_service.py"],
        },
        {
            "priority": "中",
            "title": "参数配置界面",
            "description": "允许前端动态调整max_deviation、基准指数等参数",
            "files": ["frontend回测参数表单", "backend参数验证"],
        },
        {
            "priority": "中",
            "title": "多时间段回测",
            "description": "支持自定义时间范围的回测分析",
            "files": ["API参数扩展", "时间范围验证"],
        },
        {
            "priority": "低",
            "title": "策略对比分析",
            "description": "Enhanced Indexing vs TopkDropout策略对比",
            "files": ["多策略回测框架"],
        },
    ]

    for i, enhancement in enumerate(enhancements, 1):
        print(f"   {i}. 【{enhancement['priority']}优先级】{enhancement['title']}")
        print(f"      描述: {enhancement['description']}")
        print(f"      涉及文件: {', '.join(enhancement['files'])}")
        print()


def main():
    """主测试流程"""
    print("🔧 Enhanced Indexing Strategy 回测功能完整测试")
    print("=" * 60)

    # 1. 检查前置条件
    if not check_online_serving_status():
        print("\n❌ 前置条件不满足")
        print("💡 建议先执行routine生成信号:")
        print(
            "   docker compose exec backend python -c \"import requests; requests.post('http://localhost:8000/api/v1/online/routine')\""
        )
        return

    # 2. 获取配置信息
    config_data = get_backtest_config()
    if not config_data:
        print("\n❌ 无法获取回测配置")
        return

    # 3. 检查回测状态
    if not check_backtest_status():
        print("\n❌ 回测状态检查失败")
        return

    # 4. 执行Enhanced Indexing Strategy回测
    result = execute_enhanced_indexing_backtest()
    if not result:
        print("\n❌ Enhanced Indexing Strategy回测执行失败")
        return

    # 5. 验证结果持久化
    if not verify_result_persistence():
        print("\n⚠️  结果持久化可能有问题")

    # 6. 分析功能缺口
    gaps = analyze_backtest_gaps(result)

    # 7. 建议增强方案
    suggest_enhancements()

    print("\n" + "=" * 60)
    print("🎉 Enhanced Indexing Strategy 回测测试完成")

    if result.get("status") == "success":
        print("✅ 基础回测功能正常，可以开始功能增强")
        print("🎯 建议优先实现: 图表可视化增强")
    else:
        print("❌ 基础回测功能有问题，需要先修复")

    print("\n📋 下一步行动:")
    print("1. 如果回测成功 → 开始实现前端图表组件")
    print("2. 如果回测失败 → 检查Enhanced Indexing Service配置")
    print("3. 验证前端回测页面显示效果")


if __name__ == "__main__":
    main()
