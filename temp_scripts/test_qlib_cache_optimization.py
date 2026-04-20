#!/usr/bin/env python3
"""
测试Qlib内置缓存优化效果

重点验证启用DiskExpressionCache和DiskDatasetCache后的性能提升
"""

import sys
import time
import requests
from datetime import datetime

sys.path.append("/app")


def check_qlib_cache_config():
    """检查Qlib缓存配置"""
    print("🔍 检查Qlib缓存配置...")

    try:
        import qlib
        from qlib.config import C

        print(f"   📊 Qlib已初始化: {qlib.config.C.registered}")

        # 检查缓存配置
        if hasattr(C, "expression_cache") and C.expression_cache:
            print(
                f"   ✅ 表达式缓存已启用: {C.expression_cache.get('class', 'Unknown')}"
            )
        else:
            print(f"   ❌ 表达式缓存未启用")

        if hasattr(C, "dataset_cache") and C.dataset_cache:
            print(f"   ✅ 数据集缓存已启用: {C.dataset_cache.get('class', 'Unknown')}")
        else:
            print(f"   ❌ 数据集缓存未启用")

        # 检查Redis连接
        if hasattr(C, "redis_host") and C.redis_host:
            print(f"   🔗 Redis配置: {C.redis_host}:{C.redis_port}")
        else:
            print(f"   ⚠️  Redis未配置")

        return True

    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        return False


def check_cache_directories():
    """检查缓存目录"""
    print("\n📁 检查缓存目录...")

    try:
        from pathlib import Path

        # Qlib数据目录
        qlib_data_dir = Path("/app/qlib_data")
        if qlib_data_dir.exists():
            cache_dirs = list(qlib_data_dir.glob("*cache*"))
            print(f"   📂 Qlib数据目录: {qlib_data_dir}")
            print(f"   🗂️  缓存子目录: {len(cache_dirs)} 个")
            for cache_dir in cache_dirs[:3]:  # 显示前3个
                cache_files = list(cache_dir.glob("*"))
                print(f"      • {cache_dir.name}: {len(cache_files)} 文件")
        else:
            print(f"   ❌ Qlib数据目录不存在: {qlib_data_dir}")

        # 检查可能的缓存位置
        possible_cache_dirs = [
            Path("/app/.qlib_cache"),
            Path("/app/cache"),
            Path("/tmp/qlib_cache"),
        ]

        for cache_dir in possible_cache_dirs:
            if cache_dir.exists():
                cache_files = list(cache_dir.glob("**/*"))
                print(f"   📂 发现缓存目录: {cache_dir} ({len(cache_files)} 文件)")

    except Exception as e:
        print(f"   ❌ 检查缓存目录失败: {e}")


def test_routine_performance():
    """测试routine性能"""
    print("\n🚀 测试routine性能...")

    base_url = "http://localhost:8000/api/v1"

    # 第一次执行 - 可能需要构建缓存
    print("   🔄 第一次routine执行 (构建缓存)...")
    start_time = time.time()

    try:
        response = requests.post(f"{base_url}/online/routine", timeout=900)
        first_duration = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            backend_duration = result.get("total_duration_seconds", 0)

            print(
                f"   ✅ 第一次完成: {first_duration:.2f}s (后端: {backend_duration:.2f}s)"
            )

            # 分析步骤
            if "steps" in result:
                for step in result["steps"]:
                    duration = step.get("duration_seconds", 0)
                    print(f"      • {step['step']}: {duration:.2f}s")
        else:
            print(f"   ❌ 第一次失败: {response.status_code}")
            return

    except Exception as e:
        print(f"   ❌ 第一次执行错误: {e}")
        return

    # 等待一段时间，让缓存生效
    print("   ⏳ 等待10秒让缓存生效...")
    time.sleep(10)

    # 第二次执行 - 应该使用缓存
    print("   🔄 第二次routine执行 (使用缓存)...")
    start_time = time.time()

    try:
        response = requests.post(f"{base_url}/online/routine", timeout=900)
        second_duration = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            backend_duration = result.get("total_duration_seconds", 0)

            print(
                f"   ✅ 第二次完成: {second_duration:.2f}s (后端: {backend_duration:.2f}s)"
            )

            # 计算性能提升
            if first_duration > 0:
                improvement = (
                    (first_duration - second_duration) / first_duration
                ) * 100
                print(f"\n🎉 性能提升分析:")
                print(f"   📈 时间节省: {first_duration - second_duration:.2f}s")
                print(f"   📊 性能提升: {improvement:.1f}%")

                if improvement > 70:
                    print(f"   🚀 Qlib缓存效果显著!")
                elif improvement > 30:
                    print(f"   ✅ Qlib缓存效果良好")
                elif improvement > 10:
                    print(f"   📊 有一定缓存效果")
                else:
                    print(f"   ⚠️  缓存效果不明显，可能需要更多时间构建")

            # 分析第二次的步骤
            if "steps" in result:
                print(f"   📋 第二次步骤分析:")
                for step in result["steps"]:
                    duration = step.get("duration_seconds", 0)
                    print(f"      • {step['step']}: {duration:.2f}s")
        else:
            print(f"   ❌ 第二次失败: {response.status_code}")

    except Exception as e:
        print(f"   ❌ 第二次执行错误: {e}")


def test_factor_cache_directly():
    """直接测试因子计算缓存效果"""
    print("\n🧮 直接测试因子计算缓存...")

    try:
        import qlib
        from qlib.data import D

        # 确保Qlib已初始化
        from app.services.qlib_init_service import get_qlib_init_service

        qlib_service = get_qlib_init_service()
        if not qlib_service.is_initialized():
            print("   🔄 初始化Qlib...")
            qlib_service.initialize()

        # 测试因子表达式计算
        instruments = ["SH600519", "SZ000858", "SH600036"]  # 几只测试股票
        fields = [
            "$close",
            "$volume",
            "Ref($close, 1)",
            "($close - Ref($close, 1)) / Ref($close, 1)",
        ]

        print(f"   📊 测试股票: {instruments}")
        print(f"   📈 测试因子: {len(fields)} 个")

        # 第一次计算
        print("   🔄 第一次因子计算...")
        start_time = time.time()

        data1 = D.features(
            instruments=instruments,
            fields=fields,
            start_time="2024-01-01",
            end_time="2024-01-31",
            freq="day",
        )

        first_calc_time = time.time() - start_time
        print(
            f"   ✅ 第一次完成: {first_calc_time:.3f}s, 数据量: {len(data1) if data1 is not None else 0}"
        )

        # 第二次计算 - 应该使用缓存
        print("   🔄 第二次因子计算 (缓存)...")
        start_time = time.time()

        data2 = D.features(
            instruments=instruments,
            fields=fields,
            start_time="2024-01-01",
            end_time="2024-01-31",
            freq="day",
        )

        second_calc_time = time.time() - start_time
        print(
            f"   ✅ 第二次完成: {second_calc_time:.3f}s, 数据量: {len(data2) if data2 is not None else 0}"
        )

        # 计算缓存效果
        if first_calc_time > 0:
            cache_speedup = (
                first_calc_time / second_calc_time
                if second_calc_time > 0
                else float("inf")
            )
            improvement = ((first_calc_time - second_calc_time) / first_calc_time) * 100

            print(f"   🎯 因子计算缓存效果:")
            print(f"      ⚡ 加速倍数: {cache_speedup:.1f}x")
            print(f"      📈 性能提升: {improvement:.1f}%")

            if cache_speedup > 10:
                print(f"      🚀 因子缓存效果极佳!")
            elif cache_speedup > 3:
                print(f"      ✅ 因子缓存效果很好")
            elif cache_speedup > 1.5:
                print(f"      📊 因子缓存有效果")
            else:
                print(f"      ⚠️  因子缓存效果不明显")

    except Exception as e:
        print(f"   ❌ 因子缓存测试失败: {e}")
        import traceback

        traceback.print_exc()


def main():
    """主函数"""
    print("🔧 QLIB内置缓存优化测试")
    print("=" * 50)

    # 1. 检查Qlib缓存配置
    cache_enabled = check_qlib_cache_config()

    # 2. 检查缓存目录
    check_cache_directories()

    if not cache_enabled:
        print("\n⚠️  Qlib缓存未正确配置，请检查初始化设置")
        return

    # 3. 测试因子计算缓存
    test_factor_cache_directly()

    # 4. 测试完整routine性能
    print(f"\n⚠️  即将执行完整routine性能测试")
    print(f"   预计耗时: 第一次2-10分钟，第二次应该显著更快")

    test_routine_performance()

    print("\n" + "=" * 50)
    print("🔧 Qlib缓存优化测试完成")
    print("\n💡 优化建议:")
    print("   • 如果缓存效果不明显，可能需要多次执行来预热缓存")
    print("   • 确保Redis服务正常运行以获得最佳缓存效果")
    print("   • 监控磁盘空间，Qlib缓存会占用一定存储空间")


if __name__ == "__main__":
    main()
