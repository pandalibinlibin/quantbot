#!/usr/bin/env python3
"""
Enhanced Indexing Strategy 回测功能完整测试脚本
基于我们之前讨论的自定义指数增强策略进行回测测试

执行命令: docker compose exec backend python /app/temp_scripts/run_enhanced_backtest_test.py
"""

import requests
import json
import time
from datetime import datetime


def check_prerequisites():
    """检查回测前置条件"""
    print("🔍 检查回测前置条件...")

    # 1. 检查Online Serving状态
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/online/status", timeout=30
        )
        if response.status_code == 200:
            status = response.json()
            is_initialized = status.get("is_initialized", False)
            signal_count = status.get("signal_count", 0)

            print(f"   📊 Online Serving:")
            print(
                f"      • 初始化状态: {'✅' if is_initialized else '❌'} {is_initialized}"
            )
            print(f"      • 信号数量: {signal_count}")

            if not is_initialized or signal_count == 0:
                print(f"   ⚠️  需要先执行routine生成信号")
                return False
        else:
            print(f"   ❌ Online状态检查失败")
            return False
    except Exception as e:
        print(f"   ❌ Online状态检查异常: {e}")
        return False

    # 2. 检查Enhanced Indexing Service配置
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/backtest/config", timeout=30
        )
        if response.status_code == 200:
            config_data = response.json()
            config = config_data.get("config", {})

            print(f"   🎯 Enhanced Indexing配置:")
            # 这里应该显示我们的Enhanced Indexing参数
            print(f"      • 配置状态: ✅ 已加载")

            return True
        else:
            print(f"   ❌ 配置检查失败")
            return False
    except Exception as e:
        print(f"   ❌ 配置检查异常: {e}")
        return False


def test_enhanced_indexing_backtest():
    """测试Enhanced Indexing Strategy回测"""
    print("\n🚀 执行Enhanced Indexing Strategy回测...")
    print("   📝 策略特点:")
    print("      • 基于指数增强算法，不是简单的TopkDropout")
    print("      • 使用AI信号调整基准指数权重")
    print("      • 通过max_deviation控制跟踪误差")
    print("      • 支持动态权重优化")

    try:
        start_time = time.time()

        # 执行回测 - 将使用Enhanced Indexing Strategy
        response = requests.post(
            "http://localhost:8000/api/v1/backtest/run",
            json={
                # 使用默认参数，这些参数来自system_config.yaml
                # "benchmark": "000300.SH",  # 基准指数
                # "account": 100000000,      # 初始资金
            },
            timeout=300,
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()

            if result.get("status") == "success":
                print(f"   ✅ Enhanced Indexing回测成功 (耗时: {duration:.2f}s)")

                # 验证是否使用了Enhanced Indexing Strategy
                strategy_type = result.get("strategy", "unknown")
                print(f"\n   🎯 策略验证:")
                print(f"      • 策略类型: {strategy_type}")

                if strategy_type == "enhanced_indexing":
                    print(f"      ✅ 确认使用Enhanced Indexing Strategy")

                    # 显示Enhanced Indexing特有参数
                    max_deviation = result.get("max_deviation")
                    if max_deviation is not None:
                        print(
                            f"      • 最大偏离度: {max_deviation:.4f} ({max_deviation*100:.2f}%)"
                        )

                else:
                    print(
                        f"      ⚠️  策略类型异常，期望: enhanced_indexing，实际: {strategy_type}"
                    )

                # 显示回测核心结果
                print(f"\n   📊 回测结果:")
                print(f"      • 基准指数: {result.get('benchmark', 'N/A')}")
                print(
                    f"      • 时间范围: {result.get('start_time', 'N/A')} ~ {result.get('end_time', 'N/A')}"
                )
                print(f"      • 交易天数: {result.get('trading_days', 'N/A')}")
                print(f"      • 信号数量: {result.get('signal_count', 'N/A')}")

                print(f"\n   💰 财务表现:")
                total_return = result.get("total_return", 0)
                net_return = result.get("net_return", 0)
                final_account = result.get("final_account", 0)

                print(f"      • 总收益: {total_return:.4f}")
                print(f"      • 净收益: {net_return:.4f}")
                print(f"      • 最终账户: {final_account:,.0f}")

                # 计算收益率
                if final_account > 0:
                    initial_account = 100000000
                    return_rate = (final_account - initial_account) / initial_account
                    print(f"      • 总收益率: {return_rate*100:.2f}%")

                # 显示风险指标
                risk_metrics = result.get("risk_metrics", {})
                if risk_metrics:
                    print(f"\n   📈 Enhanced Indexing风险指标:")
                    metrics = [
                        ("年化收益", "annualized_return"),
                        ("最大回撤", "max_drawdown"),
                        ("夏普比率", "sharpe_ratio"),
                        ("波动率", "volatility"),
                        ("卡玛比率", "calmar_ratio"),
                        ("胜率", "win_rate"),
                        ("盈亏比", "profit_loss_ratio"),
                    ]

                    for name, key in metrics:
                        value = risk_metrics.get(key)
                        if value is not None:
                            if isinstance(value, float):
                                print(f"      • {name}: {value:.4f}")
                            else:
                                print(f"      • {name}: {value}")
                        else:
                            print(f"      • {name}: N/A")
                else:
                    print(f"   ⚠️  风险指标未生成")

                # 检查图表数据
                charts = result.get("charts", {})
                if charts:
                    print(f"\n   📊 可视化数据:")
                    for chart_name, chart_data in charts.items():
                        if isinstance(chart_data, list):
                            print(f"      • {chart_name}: {len(chart_data)} 数据点")
                        elif isinstance(chart_data, dict):
                            print(f"      • {chart_name}: {len(chart_data)} 字段")
                        else:
                            print(f"      • {chart_name}: {type(chart_data).__name__}")
                else:
                    print(f"   ⚠️  图表数据未生成 - 这是主要的增强点")

                return result
            else:
                print(f"   ❌ 回测失败: {result.get('error', 'Unknown error')}")
                return None
        else:
            print(f"   ❌ API调用失败: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"      错误: {error_data}")
            except:
                print(f"      错误: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ 回测执行异常: {e}")
        return None


def analyze_enhancement_needs(result):
    """分析回测功能增强需求"""
    print("\n🔍 分析Enhanced Indexing回测增强需求...")

    needs = []

    if result:
        # 检查图表数据完整性
        charts = result.get("charts", {})
        expected_charts = [
            "equity_curve",  # 净值曲线
            "drawdown_curve",  # 回撤曲线
            "return_distribution",  # 收益分布
            "benchmark_comparison",  # 基准对比
        ]

        missing_charts = [c for c in expected_charts if c not in charts]
        if missing_charts:
            needs.append(
                {
                    "priority": "高",
                    "category": "可视化",
                    "title": "图表数据生成",
                    "description": f"缺失图表: {', '.join(missing_charts)}",
                    "impact": "用户无法直观看到回测表现",
                }
            )

        # 检查风险指标完整性
        risk_metrics = result.get("risk_metrics", {})
        advanced_metrics = ["information_ratio", "sortino_ratio", "var_95", "cvar_95"]

        missing_metrics = [m for m in advanced_metrics if not risk_metrics.get(m)]
        if missing_metrics:
            needs.append(
                {
                    "priority": "中",
                    "category": "风险分析",
                    "title": "高级风险指标",
                    "description": f"缺失指标: {', '.join(missing_metrics)}",
                    "impact": "风险分析不够全面",
                }
            )

        # 检查Enhanced Indexing特有功能
        if result.get("strategy") == "enhanced_indexing":
            if not result.get("max_deviation"):
                needs.append(
                    {
                        "priority": "中",
                        "category": "策略参数",
                        "title": "Enhanced Indexing参数显示",
                        "description": "max_deviation等参数未在结果中显示",
                        "impact": "用户无法了解策略配置",
                    }
                )
    else:
        needs.append(
            {
                "priority": "高",
                "category": "基础功能",
                "title": "回测执行失败",
                "description": "Enhanced Indexing Strategy回测无法正常执行",
                "impact": "核心功能不可用",
            }
        )

    # 通用增强需求
    needs.extend(
        [
            {
                "priority": "中",
                "category": "用户体验",
                "title": "参数配置界面",
                "description": "前端缺少动态调整max_deviation、基准指数等参数的界面",
                "impact": "用户无法灵活配置策略",
            },
            {
                "priority": "低",
                "category": "高级功能",
                "title": "多策略对比",
                "description": "无法对比Enhanced Indexing vs TopkDropout等不同策略",
                "impact": "无法评估策略优劣",
            },
        ]
    )

    # 输出分析结果
    print(f"   📋 发现 {len(needs)} 个增强需求:")

    for i, need in enumerate(needs, 1):
        priority_icon = (
            "🔴"
            if need["priority"] == "高"
            else "🟡" if need["priority"] == "中" else "🟢"
        )
        print(f"   {i}. {priority_icon} 【{need['priority']}】{need['title']}")
        print(f"      分类: {need['category']}")
        print(f"      描述: {need['description']}")
        print(f"      影响: {need['impact']}")
        print()

    return needs


def suggest_implementation_plan(needs):
    """建议实施计划"""
    print("📋 Enhanced Indexing回测增强实施计划:")

    # 按优先级分组
    high_priority = [n for n in needs if n["priority"] == "高"]
    medium_priority = [n for n in needs if n["priority"] == "中"]
    low_priority = [n for n in needs if n["priority"] == "低"]

    print(f"\n   🔴 第一阶段 - 高优先级 ({len(high_priority)}项):")
    for i, need in enumerate(high_priority, 1):
        print(f"      {i}. {need['title']} - {need['description']}")

    print(f"\n   🟡 第二阶段 - 中优先级 ({len(medium_priority)}项):")
    for i, need in enumerate(medium_priority, 1):
        print(f"      {i}. {need['title']} - {need['description']}")

    print(f"\n   🟢 第三阶段 - 低优先级 ({len(low_priority)}项):")
    for i, need in enumerate(low_priority, 1):
        print(f"      {i}. {need['title']} - {need['description']}")

    print(f"\n   💡 建议开发顺序:")
    print(f"      1. 先确保Enhanced Indexing Strategy正常工作")
    print(f"      2. 实现核心图表可视化 (净值曲线、回撤曲线)")
    print(f"      3. 完善风险指标计算")
    print(f"      4. 添加前端参数配置界面")


def main():
    """主测试流程"""
    print("🔧 Enhanced Indexing Strategy 回测功能完整测试")
    print("=" * 60)
    print("📝 基于我们之前讨论的自定义指数增强策略方案")
    print("=" * 60)

    # 1. 检查前置条件
    if not check_prerequisites():
        print("\n❌ 前置条件不满足")
        print("\n💡 解决方案:")
        print("   1. 执行routine生成信号:")
        print(
            "      docker compose exec backend python -c \"import requests; resp = requests.post('http://localhost:8000/api/v1/online/routine'); print('Routine结果:', resp.status_code)\""
        )
        print("   2. 然后重新运行此测试")
        return

    print("   ✅ 前置条件满足")

    # 2. 执行Enhanced Indexing Strategy回测
    result = test_enhanced_indexing_backtest()

    # 3. 分析增强需求
    needs = analyze_enhancement_needs(result)

    # 4. 建议实施计划
    suggest_implementation_plan(needs)

    # 5. 验证结果持久化
    print("\n💾 验证结果持久化...")
    try:
        time.sleep(2)
        response = requests.get(
            "http://localhost:8000/api/v1/backtest/latest-result", timeout=30
        )
        if response.status_code == 200:
            latest_data = response.json()
            if latest_data.get("status") == "success":
                print("   ✅ 结果持久化正常")
            else:
                print("   ❌ 结果持久化失败")
        else:
            print("   ❌ 结果检索失败")
    except Exception as e:
        print(f"   ❌ 持久化验证异常: {e}")

    print("\n" + "=" * 60)
    print("🎉 Enhanced Indexing Strategy 回测测试完成")

    if result and result.get("status") == "success":
        print("✅ Enhanced Indexing Strategy回测功能基本正常")
        print("🎯 可以开始实施功能增强")
        print("\n📋 建议下一步:")
        print("   1. 实现图表可视化组件")
        print("   2. 完善风险指标计算")
        print("   3. 添加前端参数配置")
    else:
        print("❌ Enhanced Indexing Strategy回测有问题")
        print("🔧 需要先修复基础功能")


if __name__ == "__main__":
    main()
