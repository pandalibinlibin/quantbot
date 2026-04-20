#!/usr/bin/env python3
"""
修复Enhanced Indexing Strategy回测中的benchmark问题
诊断并修复"benchmark does not exist"错误
"""

import requests
import time


def check_benchmark_data():
    """检查基准数据可用性"""
    print("🔍 检查基准数据可用性...")

    try:
        # 导入Qlib相关模块
        import qlib
        from qlib.data import D
        from app.services.qlib_init_service import get_qlib_init_service

        # 确保Qlib已初始化
        print("   🔄 初始化Qlib...")
        qlib_service = get_qlib_init_service()
        if not qlib_service.initialize():
            print("   ❌ Qlib初始化失败")
            return []

        print("   ✅ Qlib初始化成功")

        # 测试不同的基准格式
        benchmark_formats = [
            "000300.SH",  # Qlib标准格式
            "SH000300",  # Tushare格式
            "000300",  # 简化格式
            "SH000300.SH",  # 混合格式
        ]

        print("   📊 测试基准数据格式:")

        available_benchmarks = []

        for benchmark in benchmark_formats:
            try:
                # 尝试获取基准数据
                data = D.features(
                    instruments=[benchmark],
                    fields=["$close"],
                    start_time="2024-01-01",
                    end_time="2024-01-31",
                )

                if data is not None and len(data) > 0:
                    print(f"      ✅ {benchmark}: {len(data)} 数据点")
                    available_benchmarks.append(benchmark)
                else:
                    print(f"      ❌ {benchmark}: 无数据")

            except Exception as e:
                print(f"      ❌ {benchmark}: 错误 - {str(e)[:50]}...")

        print(f"\n   📋 可用基准格式: {available_benchmarks}")
        return available_benchmarks

    except Exception as e:
        print(f"   ❌ 基准数据检查失败: {e}")
        return []


def check_instruments_data():
    """检查可用的股票数据"""
    print("\n🔍 检查可用股票数据...")

    try:
        import qlib
        from qlib.data import D
        from app.services.qlib_init_service import get_qlib_init_service

        # 确保Qlib已初始化
        qlib_service = get_qlib_init_service()
        if not qlib_service.is_initialized():
            print("   🔄 初始化Qlib...")
            if not qlib_service.initialize():
                print("   ❌ Qlib初始化失败")
                return []

        # 获取所有可用股票
        instruments = D.instruments(market="all")
        print(f"   📊 总股票数量: {len(instruments) if instruments else 0}")

        if instruments and len(instruments) > 0:
            # 显示前10个股票
            sample_instruments = list(instruments)[:10]
            print(f"   📋 样本股票: {sample_instruments}")

            # 检查是否包含指数数据
            index_instruments = [
                inst for inst in instruments if "000300" in inst or "SH000300" in inst
            ]
            print(f"   📈 指数相关股票: {index_instruments}")

            return instruments
        else:
            print(f"   ❌ 无可用股票数据")
            return []

    except Exception as e:
        print(f"   ❌ 股票数据检查失败: {e}")
        return []


def test_benchmark_conversion():
    """测试基准格式转换"""
    print("\n🔧 测试基准格式转换...")

    def convert_tushare_to_qlib(symbol):
        """将Tushare格式转换为Qlib格式"""
        if symbol.startswith("SH") or symbol.startswith("SZ"):
            return symbol[2:] + "." + symbol[:2]
        return symbol

    def convert_qlib_to_tushare(symbol):
        """将Qlib格式转换为Tushare格式"""
        if "." in symbol:
            code, market = symbol.split(".")
            return market + code
        return symbol

    test_cases = [
        ("SH000300", "000300.SH"),
        ("000300.SH", "SH000300"),
        ("SZ399006", "399006.SZ"),
        ("399006.SZ", "SZ399006"),
    ]

    print("   📊 格式转换测试:")
    for input_format, expected in test_cases:
        if input_format.startswith("SH") or input_format.startswith("SZ"):
            result = convert_tushare_to_qlib(input_format)
        else:
            result = convert_qlib_to_tushare(input_format)

        status = "✅" if result == expected else "❌"
        print(f"      {status} {input_format} → {result} (期望: {expected})")


def fix_benchmark_in_backtest():
    """修复回测中的基准问题"""
    print("\n🔧 修复Enhanced Indexing回测基准问题...")

    # 1. 检查可用的基准格式
    available_benchmarks = check_benchmark_data()

    if not available_benchmarks:
        print("   ❌ 无可用基准数据，需要重新收集数据")
        return False

    # 2. 选择最佳基准格式
    preferred_benchmark = None

    # 优先选择标准Qlib格式
    if "000300.SH" in available_benchmarks:
        preferred_benchmark = "000300.SH"
    elif "SH000300" in available_benchmarks:
        preferred_benchmark = "SH000300"
    elif available_benchmarks:
        preferred_benchmark = available_benchmarks[0]

    if not preferred_benchmark:
        print("   ❌ 无法确定可用基准")
        return False

    print(f"   ✅ 选择基准格式: {preferred_benchmark}")

    # 3. 使用正确的基准格式执行回测
    print(f"   🚀 使用 {preferred_benchmark} 执行回测...")

    try:
        start_time = time.time()

        response = requests.post(
            "http://localhost:8000/api/v1/backtest/run",
            json={"benchmark": preferred_benchmark},  # 使用可用的基准格式
            timeout=300,
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()

            if result.get("status") == "success":
                print(f"   ✅ 回测成功! (耗时: {duration:.2f}s)")

                print(f"\n   📊 Enhanced Indexing Strategy结果:")
                print(f"      • 策略类型: {result.get('strategy', 'N/A')}")
                print(f"      • 基准指数: {result.get('benchmark', 'N/A')}")
                print(f"      • 最大偏离: {result.get('max_deviation', 'N/A')}")
                print(f"      • 交易天数: {result.get('trading_days', 'N/A')}")
                print(f"      • 净收益: {result.get('net_return', 0):.4f}")

                # 显示风险指标
                risk_metrics = result.get("risk_metrics", {})
                if risk_metrics:
                    print(f"   📈 风险指标:")
                    print(
                        f"      • 年化收益: {risk_metrics.get('annualized_return', 'N/A')}"
                    )
                    print(
                        f"      • 最大回撤: {risk_metrics.get('max_drawdown', 'N/A')}"
                    )
                    print(
                        f"      • 夏普比率: {risk_metrics.get('sharpe_ratio', 'N/A')}"
                    )

                return result
            else:
                print(f"   ❌ 回测失败: {result.get('error', 'Unknown error')}")
                return None
        else:
            print(f"   ❌ API调用失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"   ❌ 回测执行异常: {e}")
        return None


def suggest_permanent_fix():
    """建议永久修复方案"""
    print("\n💡 建议永久修复方案:")

    print("   🔧 方案1: 在Enhanced Indexing Service中添加基准格式转换")
    print("      • 修改文件: backend/app/services/enhanced_indexing_service.py")
    print("      • 添加基准格式检测和转换逻辑")
    print("      • 确保与Qlib数据格式兼容")

    print("   🔧 方案2: 在回测API中添加基准验证")
    print("      • 修改文件: backend/app/api/routes/backtest.py")
    print("      • 在执行回测前验证基准数据存在性")
    print("      • 自动选择可用的基准格式")

    print("   🔧 方案3: 更新配置文件")
    print("      • 修改文件: backend/app/config/backtest_config.yaml")
    print("      • 使用经过验证的基准格式")
    print("      • 添加备选基准列表")


def main():
    """主修复流程"""
    print("🔧 Enhanced Indexing Strategy 基准问题修复")
    print("=" * 50)

    # 1. 检查股票数据
    instruments = check_instruments_data()
    if not instruments:
        print("\n❌ 无股票数据，需要先执行数据收集")
        return

    # 2. 检查基准数据并修复
    result = fix_benchmark_in_backtest()

    # 3. 建议永久修复方案
    suggest_permanent_fix()

    print("\n" + "=" * 50)

    if result:
        print("🎉 Enhanced Indexing Strategy回测修复成功!")
        print("✅ 可以继续进行回测功能增强开发")

        print("\n📋 下一步建议:")
        print("   1. 实现永久修复方案")
        print("   2. 开始图表可视化增强")
        print("   3. 完善风险指标计算")
    else:
        print("❌ Enhanced Indexing Strategy回测仍有问题")
        print("🔧 需要进一步诊断和修复")


if __name__ == "__main__":
    main()
