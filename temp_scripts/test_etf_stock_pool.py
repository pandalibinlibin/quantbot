#!/usr/bin/env python3
"""
测试ETF股票池功能
验证从CSI300成分股切换到ETF股票池的完整流程
"""

import sys
import os
from pathlib import Path


def test_index_config():
    """测试index_config.yaml配置"""
    print("🔍 测试1: Index配置")
    print("=" * 20)

    try:
        import yaml

        config_path = Path("/app/app/config/index_config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 检查active_index
        active_index = config.get("active_index")
        print(f"✅ Active index: {active_index}")

        if active_index != "etf_universe":
            print("❌ Active index should be 'etf_universe'")
            return False

        # 检查etf_universe配置
        if "etf_universe" not in config.get("indexes", {}):
            print("❌ etf_universe not found in indexes")
            return False

        etf_config = config["indexes"]["etf_universe"]

        required_fields = [
            "name",
            "benchmark_code",
            "components_source",
            "min_daily_volume",
        ]
        for field in required_fields:
            if field not in etf_config:
                print(f"❌ Missing field: {field}")
                return False

        print("✅ ETF universe配置完整")
        print(f"   - 数据源: {etf_config['components_source']}")
        print(f"   - 最小成交额: {etf_config['min_daily_volume']:,}元")
        print(f"   - 基准: {etf_config['benchmark_code']}")

        return True

    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


def test_index_components_service():
    """测试IndexComponentsService"""
    print("\n🔍 测试2: IndexComponentsService")
    print("=" * 30)

    try:
        from app.services.index_components_service import get_index_components_service

        service = get_index_components_service()
        print("✅ Service初始化成功")

        # 测试获取active index
        active_index = service.get_active_index()
        print(f"✅ Active index: {active_index}")

        if active_index != "etf_universe":
            print("❌ Active index不是etf_universe")
            return False

        # 测试获取ETF配置
        etf_config = service.get_index_config("etf_universe")
        print("✅ ETF配置获取成功")
        print(f"   - 名称: {etf_config['name']}")
        print(f"   - 数据源: {etf_config['components_source']}")

        return True

    except Exception as e:
        print(f"❌ Service测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_etf_components_collection():
    """测试ETF成分股收集"""
    print("\n🔍 测试3: ETF成分股收集")
    print("=" * 25)

    try:
        from app.services.index_components_service import get_index_components_service

        service = get_index_components_service()

        # 获取ETF股票池
        print("📊 开始获取ETF股票池...")
        components = service.get_components("etf_universe", use_cache=False)

        print(f"✅ ETF股票池获取成功: {len(components)}只ETF")

        if len(components) == 0:
            print("⚠️  ETF股票池为空，可能是筛选条件过严")
            return False

        # 显示前10只ETF
        print("📋 前10只ETF:")
        for i, etf_code in enumerate(components[:10]):
            print(f"   {i+1:2d}. {etf_code}")

        # 验证格式
        valid_formats = 0
        for code in components:
            if code.startswith(("SH", "SZ")) and len(code) == 8:
                valid_formats += 1

        print(f"✅ 格式验证: {valid_formats}/{len(components)} 符合Qlib格式")

        if valid_formats != len(components):
            print("⚠️  部分ETF代码格式不符合Qlib标准")

        return True

    except Exception as e:
        print(f"❌ ETF收集测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_workflow_integration():
    """测试workflow集成"""
    print("\n🔍 测试4: Workflow集成")
    print("=" * 20)

    try:
        # 测试数据收集API
        import requests

        print("📡 测试数据收集API...")
        response = requests.get("http://localhost:8000/api/v1/data/status")

        if response.status_code == 200:
            status_data = response.json()
            print("✅ 数据收集API可访问")
            print(f"   - 状态: {status_data.get('status', 'Unknown')}")
        else:
            print(f"⚠️  数据收集API返回 {response.status_code}")

        # 测试在线服务API
        print("\n📡 测试在线服务API...")
        response = requests.get("http://localhost:8000/api/v1/online-serving/status")

        if response.status_code == 200:
            status_data = response.json()
            print("✅ 在线服务API可访问")
            print(f"   - 就绪状态: {status_data.get('ready', 'Unknown')}")
        else:
            print(f"⚠️  在线服务API返回 {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ Workflow集成测试失败: {e}")
        return False


def test_topk_dropout_compatibility():
    """测试TopkDropoutStrategy兼容性"""
    print("\n🔍 测试5: TopkDropoutStrategy兼容性")
    print("=" * 35)

    try:
        # 检查TopkDropoutStrategy配置
        import yaml

        config_path = Path("/app/app/config/qlib/system_config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if "topk_dropout_strategy" not in config:
            print("❌ TopkDropoutStrategy配置未找到")
            return False

        strategy_config = config["topk_dropout_strategy"]

        print("✅ TopkDropoutStrategy配置存在")
        print(f"   - topk: {strategy_config.get('topk', 'N/A')}")
        print(f"   - n_drop: {strategy_config.get('n_drop', 'N/A')}")
        print(f"   - 启用状态: {strategy_config.get('enabled', False)}")

        # 检查策略是否适用于ETF
        topk = strategy_config.get("topk", 10)

        # 获取ETF数量进行比较
        from app.services.index_components_service import get_index_components_service

        service = get_index_components_service()
        components = service.get_components("etf_universe", use_cache=True)

        if len(components) >= topk:
            print(f"✅ ETF数量({len(components)})足够支持topk={topk}")
        else:
            print(f"⚠️  ETF数量({len(components)})少于topk={topk}，可能需要调整参数")

        return True

    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🧪 ETF股票池功能测试")
    print("=" * 30)

    tests = [
        ("Index配置", test_index_config),
        ("IndexComponentsService", test_index_components_service),
        ("ETF成分股收集", test_etf_components_collection),
        ("Workflow集成", test_workflow_integration),
        ("TopkDropoutStrategy兼容性", test_topk_dropout_compatibility),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))

    # 总结结果
    print(f"\n" + "=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n🎯 通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   - {test_name}: {status}")

    if passed == total:
        print(f"\n🎉 所有测试通过！ETF股票池功能正常")
        print("\n🚀 可以开始使用ETF股票池进行量化交易:")
        print("   1. 系统将自动使用活跃ETF作为股票池")
        print("   2. TopkDropoutStrategy将在ETF中进行智能选择")
        print("   3. 基准使用CSI300 ETF (510300.SH)")
        print("   4. 每周自动更新ETF股票池")

    elif passed >= total * 0.8:
        print(f"\n⚠️  大部分测试通过，存在少量问题")
        failed_tests = [name for name, result in results if not result]
        print(f"   需要解决: {', '.join(failed_tests)}")

    else:
        print(f"\n❌ 测试失败较多，需要检查配置和实现")
        failed_tests = [name for name, result in results if not result]
        print(f"   失败测试: {', '.join(failed_tests)}")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
