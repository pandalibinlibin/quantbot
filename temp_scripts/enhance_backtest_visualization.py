#!/usr/bin/env python3
"""
Enhanced Indexing Strategy 回测结果可视化增强
为回测结果添加专业的图表数据生成功能
"""

import requests
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def test_current_chart_data():
    """测试当前回测的图表数据生成"""
    print("🔍 测试当前回测图表数据...")

    try:
        # 执行回测获取结果
        response = requests.post(
            "http://localhost:8000/api/v1/backtest/run",
            json={"benchmark": "SH000300"},  # 使用可用的基准格式
            timeout=300,
        )

        if response.status_code == 200:
            result = response.json()

            if result.get("status") == "success":
                print("   ✅ 回测执行成功")

                # 检查当前图表数据
                charts = result.get("charts", {})
                print(f"   📊 当前图表数据: {len(charts)} 个图表")

                for chart_name, chart_data in charts.items():
                    if isinstance(chart_data, list):
                        print(f"      • {chart_name}: {len(chart_data)} 数据点")
                    elif isinstance(chart_data, dict):
                        print(f"      • {chart_name}: {len(chart_data)} 字段")
                        # 显示字段详情
                        for key, value in chart_data.items():
                            if isinstance(value, list):
                                print(f"        - {key}: {len(value)} 项")
                            else:
                                print(f"        - {key}: {type(value).__name__}")
                    else:
                        print(f"      • {chart_name}: {type(chart_data).__name__}")

                return result
            else:
                print(f"   ❌ 回测失败: {result.get('error', 'Unknown error')}")
                return None
        else:
            print(f"   ❌ API调用失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"   ❌ 测试异常: {e}")
        return None


def design_enhanced_chart_data():
    """设计增强的图表数据结构"""
    print("\n🎨 设计增强的图表数据结构...")

    # 定义我们需要的专业图表
    enhanced_charts = {
        "equity_curve": {
            "title": "净值曲线对比",
            "description": "策略净值 vs 基准净值",
            "data_structure": {
                "dates": ["2024-01-01", "2024-01-02", "..."],
                "strategy_nav": [1.0, 1.001, "..."],
                "benchmark_nav": [1.0, 0.999, "..."],
                "excess_return": [0.0, 0.002, "..."],
            },
            "chart_type": "line",
            "priority": "high",
        },
        "drawdown_curve": {
            "title": "回撤曲线",
            "description": "策略回撤 vs 基准回撤",
            "data_structure": {
                "dates": ["2024-01-01", "2024-01-02", "..."],
                "strategy_drawdown": [0.0, -0.01, "..."],
                "benchmark_drawdown": [0.0, -0.005, "..."],
                "max_drawdown_date": "2024-06-15",
            },
            "chart_type": "area",
            "priority": "high",
        },
        "return_distribution": {
            "title": "收益分布",
            "description": "日收益率分布直方图",
            "data_structure": {
                "bins": [-0.05, -0.04, "...", 0.04, 0.05],
                "strategy_counts": [2, 5, "...", 8, 3],
                "benchmark_counts": [3, 7, "...", 6, 2],
                "statistics": {
                    "strategy_mean": 0.0008,
                    "strategy_std": 0.015,
                    "benchmark_mean": 0.0005,
                    "benchmark_std": 0.012,
                },
            },
            "chart_type": "histogram",
            "priority": "medium",
        },
        "rolling_metrics": {
            "title": "滚动指标",
            "description": "滚动夏普比率、波动率等",
            "data_structure": {
                "dates": ["2024-01-01", "2024-01-02", "..."],
                "rolling_sharpe": [0.5, 0.6, "..."],
                "rolling_volatility": [0.12, 0.13, "..."],
                "rolling_alpha": [0.02, 0.03, "..."],
                "rolling_beta": [0.95, 0.96, "..."],
            },
            "chart_type": "line",
            "priority": "medium",
        },
        "sector_attribution": {
            "title": "行业归因分析",
            "description": "行业配置对收益的贡献",
            "data_structure": {
                "sectors": ["金融", "科技", "消费", "..."],
                "allocation_effect": [0.002, 0.005, -0.001, "..."],
                "selection_effect": [0.001, -0.002, 0.003, "..."],
                "total_effect": [0.003, 0.003, 0.002, "..."],
            },
            "chart_type": "bar",
            "priority": "low",
        },
        "risk_metrics_radar": {
            "title": "风险指标雷达图",
            "description": "多维度风险指标对比",
            "data_structure": {
                "metrics": ["收益", "风险", "夏普", "最大回撤", "胜率", "稳定性"],
                "strategy_scores": [0.8, 0.7, 0.9, 0.6, 0.75, 0.85],
                "benchmark_scores": [0.6, 0.8, 0.5, 0.7, 0.65, 0.8],
                "max_scores": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            },
            "chart_type": "radar",
            "priority": "low",
        },
    }

    print("   📋 设计的增强图表:")
    for chart_name, chart_info in enhanced_charts.items():
        priority_icon = (
            "🔴"
            if chart_info["priority"] == "high"
            else "🟡" if chart_info["priority"] == "medium" else "🟢"
        )
        print(f"   {priority_icon} {chart_info['title']} ({chart_name})")
        print(f"      描述: {chart_info['description']}")
        print(f"      类型: {chart_info['chart_type']}")
        print()

    return enhanced_charts


def create_sample_chart_data():
    """创建示例图表数据"""
    print("\n🔧 创建示例图表数据...")

    # 生成示例数据
    dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
    n_days = len(dates)

    # 模拟策略和基准收益率
    np.random.seed(42)
    strategy_returns = np.random.normal(0.0008, 0.015, n_days)  # 年化18%，波动15%
    benchmark_returns = np.random.normal(0.0005, 0.012, n_days)  # 年化12%，波动12%

    # 计算累积净值
    strategy_nav = (1 + pd.Series(strategy_returns)).cumprod()
    benchmark_nav = (1 + pd.Series(benchmark_returns)).cumprod()

    # 计算回撤
    strategy_peak = strategy_nav.expanding().max()
    benchmark_peak = benchmark_nav.expanding().max()
    strategy_drawdown = (strategy_nav - strategy_peak) / strategy_peak
    benchmark_drawdown = (benchmark_nav - benchmark_peak) / benchmark_peak

    # 构建增强图表数据
    enhanced_chart_data = {
        "equity_curve": {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "strategy_nav": strategy_nav.tolist(),
            "benchmark_nav": benchmark_nav.tolist(),
            "excess_return": (strategy_nav - benchmark_nav).tolist(),
        },
        "drawdown_curve": {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "strategy_drawdown": strategy_drawdown.tolist(),
            "benchmark_drawdown": benchmark_drawdown.tolist(),
            "max_drawdown_date": dates[strategy_drawdown.idxmin()].strftime("%Y-%m-%d"),
        },
        "return_distribution": {
            "strategy_returns": strategy_returns.tolist(),
            "benchmark_returns": benchmark_returns.tolist(),
            "bins": np.linspace(-0.06, 0.06, 25).tolist(),
            "statistics": {
                "strategy_mean": float(strategy_returns.mean()),
                "strategy_std": float(strategy_returns.std()),
                "benchmark_mean": float(benchmark_returns.mean()),
                "benchmark_std": float(benchmark_returns.std()),
            },
        },
        "rolling_metrics": {
            "dates": [d.strftime("%Y-%m-%d") for d in dates[30:]],  # 30天滚动
            "rolling_sharpe": (
                pd.Series(strategy_returns).rolling(30).mean()
                / pd.Series(strategy_returns).rolling(30).std()
                * np.sqrt(252)
            )[30:].tolist(),
            "rolling_volatility": (
                pd.Series(strategy_returns).rolling(30).std() * np.sqrt(252)
            )[30:].tolist(),
        },
    }

    print("   ✅ 示例图表数据创建完成")
    print(
        f"      • equity_curve: {len(enhanced_chart_data['equity_curve']['dates'])} 数据点"
    )
    print(
        f"      • drawdown_curve: {len(enhanced_chart_data['drawdown_curve']['dates'])} 数据点"
    )
    print(
        f"      • return_distribution: {len(enhanced_chart_data['return_distribution']['strategy_returns'])} 收益率"
    )
    print(
        f"      • rolling_metrics: {len(enhanced_chart_data['rolling_metrics']['dates'])} 数据点"
    )

    return enhanced_chart_data


def suggest_backend_implementation():
    """建议后端实现方案"""
    print("\n💡 后端图表数据生成实现建议:")

    implementation_plan = {
        "file_to_modify": "backend/app/services/online_serving_service.py",
        "function_to_enhance": "_generate_backtest_charts",
        "implementation_steps": [
            {
                "step": 1,
                "title": "扩展图表数据生成函数",
                "description": "在_generate_backtest_charts中添加更多图表类型",
                "code_location": "第1131行附近",
            },
            {
                "step": 2,
                "title": "添加净值曲线计算",
                "description": "基于report_df计算策略和基准的累积净值",
                "implementation": "使用report_df['return']计算累积收益",
            },
            {
                "step": 3,
                "title": "添加回撤曲线计算",
                "description": "计算滚动最大值和回撤比例",
                "implementation": "使用expanding().max()计算峰值",
            },
            {
                "step": 4,
                "title": "添加收益分布分析",
                "description": "计算日收益率的分布统计",
                "implementation": "使用numpy.histogram分析收益分布",
            },
            {
                "step": 5,
                "title": "添加滚动指标计算",
                "description": "计算滚动夏普比率、波动率等",
                "implementation": "使用pandas.rolling计算滚动统计",
            },
        ],
    }

    print(f"   📁 修改文件: {implementation_plan['file_to_modify']}")
    print(f"   🔧 增强函数: {implementation_plan['function_to_enhance']}")
    print(f"\n   📋 实施步骤:")

    for step_info in implementation_plan["implementation_steps"]:
        print(f"      {step_info['step']}. {step_info['title']}")
        print(f"         描述: {step_info['description']}")
        if "implementation" in step_info:
            print(f"         实现: {step_info['implementation']}")
        if "code_location" in step_info:
            print(f"         位置: {step_info['code_location']}")
        print()

    return implementation_plan


def suggest_frontend_implementation():
    """建议前端实现方案"""
    print("\n💡 前端图表组件实现建议:")

    frontend_plan = {
        "file_to_modify": "frontend/src/routes/_layout/backtest.tsx",
        "components_to_add": [
            {
                "component": "EquityCurveChart",
                "description": "净值曲线对比图表",
                "library": "Recharts LineChart",
                "data_source": "result.charts.equity_curve",
            },
            {
                "component": "DrawdownChart",
                "description": "回撤曲线图表",
                "library": "Recharts AreaChart",
                "data_source": "result.charts.drawdown_curve",
            },
            {
                "component": "ReturnDistributionChart",
                "description": "收益分布直方图",
                "library": "Recharts BarChart",
                "data_source": "result.charts.return_distribution",
            },
            {
                "component": "RollingMetricsChart",
                "description": "滚动指标图表",
                "library": "Recharts LineChart",
                "data_source": "result.charts.rolling_metrics",
            },
        ],
        "layout_suggestion": "使用Grid布局，2x2排列图表组件",
    }

    print(f"   📁 修改文件: {frontend_plan['file_to_modify']}")
    print(f"   📐 布局建议: {frontend_plan['layout_suggestion']}")
    print(f"\n   🧩 需要添加的组件:")

    for comp in frontend_plan["components_to_add"]:
        print(f"      • {comp['component']}")
        print(f"        描述: {comp['description']}")
        print(f"        技术: {comp['library']}")
        print(f"        数据: {comp['data_source']}")
        print()

    return frontend_plan


def main():
    """主增强流程"""
    print("🎨 Enhanced Indexing Strategy 回测结果可视化增强")
    print("=" * 60)

    # 1. 测试当前图表数据
    current_result = test_current_chart_data()

    # 2. 设计增强图表结构
    enhanced_charts = design_enhanced_chart_data()

    # 3. 创建示例数据
    sample_data = create_sample_chart_data()

    # 4. 建议后端实现
    backend_plan = suggest_backend_implementation()

    # 5. 建议前端实现
    frontend_plan = suggest_frontend_implementation()

    print("\n" + "=" * 60)
    print("🎉 回测可视化增强方案设计完成")

    print("\n📋 实施优先级:")
    print("   🔴 高优先级: 净值曲线、回撤曲线")
    print("   🟡 中优先级: 收益分布、滚动指标")
    print("   🟢 低优先级: 行业归因、风险雷达图")

    print("\n🚀 建议实施顺序:")
    print("   1. 先实现后端图表数据生成增强")
    print("   2. 再实现前端图表组件")
    print("   3. 最后优化图表交互和样式")

    print("\n💾 示例数据已生成，可用于前端开发测试")


if __name__ == "__main__":
    main()
