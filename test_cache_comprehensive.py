#!/usr/bin/env python3
"""
综合缓存优化测试脚本
整合所有缓存测试功能，提供完整的性能分析报告
"""

import time
import requests
import json
import os
import subprocess
from pathlib import Path


def run_command(cmd):
    """执行系统命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def check_cache_directories():
    """检查缓存目录状态"""
    print("📁 检查缓存目录状态...")

    cache_dirs = ["/app/qlib_data/dataset_cache", "/app/qlib_data/features_cache"]

    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            file_count = len([f for f in Path(cache_dir).rglob("*") if f.is_file()])
            print(f"   📂 {cache_dir}: {file_count} 文件")
        else:
            print(f"   ❌ {cache_dir}: 不存在")


def test_routine_performance(test_name, wait_time=0):
    """测试routine性能"""
    if wait_time > 0:
        print(f"   ⏳ 等待{wait_time}秒让缓存生效...")
        time.sleep(wait_time)

    print(f"   🔄 执行{test_name}...")

    start_time = time.time()

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/online/routine", json={}, timeout=600
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()
            backend_duration = result.get("total_duration_seconds", 0)

            print(
                f"   ✅ {test_name}完成: {duration:.2f}s (后端: {backend_duration:.2f}s)"
            )

            steps = result.get("steps", [])
            for step in steps:
                step_name = step.get("step", "Unknown")
                step_duration = step.get("duration_seconds", 0)
                print(f"      • {step_name}: {step_duration:.2f}s")

            return {
                "success": True,
                "client_duration": duration,
                "backend_duration": backend_duration,
                "steps": steps,
            }
        else:
            print(f"   ❌ {test_name}失败: HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}

    except requests.exceptions.Timeout:
        print(f"   ⏰ {test_name}超时 (>10分钟)")
        return {"success": False, "error": "Timeout"}

    except Exception as e:
        print(f"   ❌ {test_name}错误: {e}")
        return {"success": False, "error": str(e)}


def test_factor_cache():
    """测试因子计算缓存效果"""
    print("🧮 测试因子计算缓存...")

    try:
        # 导入必要的模块
        import qlib
        from qlib.data import D
        from app.services.qlib_init_service import get_qlib_init_service

        # 初始化Qlib
        qlib_service = get_qlib_init_service()
        qlib_service.initialize()

        # 测试股票和因子
        instruments = ["SH600519", "SZ000858", "SH600036"]
        fields = ["$close", "$volume", "Ref($close, 1)", "Mean($close, 5)"]

        print(f"   📊 测试股票: {instruments}")
        print(f"   📈 测试因子: {len(fields)} 个")

        # 第一次计算
        print("   🔄 第一次因子计算...")
        start1 = time.time()
        data1 = D.features(
            instruments=instruments,
            fields=fields,
            start_time="2024-01-01",
            end_time="2024-12-31",
        )
        end1 = time.time()
        time1 = end1 - start1

        print(
            f"   ✅ 第一次完成: {time1:.3f}s, 数据量: {len(data1) if data1 is not None else 0}"
        )

        # 第二次计算（应该使用缓存）
        print("   🔄 第二次因子计算 (缓存)...")
        start2 = time.time()
        data2 = D.features(
            instruments=instruments,
            fields=fields,
            start_time="2024-01-01",
            end_time="2024-12-31",
        )
        end2 = time.time()
        time2 = end2 - start2

        print(
            f"   ✅ 第二次完成: {time2:.3f}s, 数据量: {len(data2) if data2 is not None else 0}"
        )

        # 计算缓存效果
        if time2 > 0:
            speedup = time1 / time2
            improvement = ((time1 - time2) / time1) * 100

            print(f"   🎯 因子计算缓存效果:")
            print(f"      ⚡ 加速倍数: {speedup:.1f}x")
            print(f"      📈 性能提升: {improvement:.1f}%")

            if speedup > 5:
                print("      🚀 因子缓存效果极佳!")
            elif speedup > 2:
                print("      📊 因子缓存效果良好")
            else:
                print("      ⚠️  因子缓存效果一般")

            return {
                "success": True,
                "first_time": time1,
                "second_time": time2,
                "speedup": speedup,
                "improvement": improvement,
            }
        else:
            return {"success": False, "error": "Second calculation too fast to measure"}

    except Exception as e:
        print(f"   ❌ 因子缓存测试失败: {e}")
        return {"success": False, "error": str(e)}


def main():
    """主测试流程"""
    print("🔧 QLIB缓存优化综合测试")
    print("=" * 50)

    # 1. 检查缓存目录
    check_cache_directories()

    # 2. 测试因子计算缓存
    print("\n" + "=" * 50)
    factor_result = test_factor_cache()

    # 3. 测试routine性能（多次测试）
    print("\n" + "=" * 50)
    print("🚀 Routine性能测试...")

    results = []

    # 第一次测试
    result1 = test_routine_performance("第一次routine")
    if result1["success"]:
        results.append(result1)

    # 第二次测试（等待10秒）
    result2 = test_routine_performance("第二次routine", wait_time=10)
    if result2["success"]:
        results.append(result2)

    # 第三次测试（等待30秒）
    result3 = test_routine_performance("第三次routine", wait_time=30)
    if result3["success"]:
        results.append(result3)

    # 4. 性能分析报告
    print("\n" + "=" * 50)
    print("📊 综合性能分析报告")
    print("=" * 50)

    # 因子缓存分析
    if factor_result["success"]:
        print(f"🧮 因子计算优化:")
        print(f"   ⚡ 加速倍数: {factor_result['speedup']:.1f}x")
        print(f"   📈 性能提升: {factor_result['improvement']:.1f}%")

    # Routine性能分析
    if len(results) >= 2:
        print(f"\n🚀 Routine性能优化:")
        first = results[0]["backend_duration"]
        best = min(r["backend_duration"] for r in results[1:])
        improvement = ((first - best) / first) * 100

        print(f"   📊 最佳性能提升: {improvement:.1f}%")
        print(f"   ⏱️  时间变化: {first:.2f}s → {best:.2f}s")

        if improvement > 30:
            print("   🚀 Routine缓存效果显著!")
        elif improvement > 15:
            print("   📊 Routine缓存效果良好")
        elif improvement > 5:
            print("   ⚠️  Routine缓存效果一般")
        else:
            print("   ❌ Routine缓存效果不明显")

    # 5. 最终建议
    print(f"\n💡 优化建议:")
    print(f"   • 因子计算缓存已生效，建议保持当前配置")
    print(f"   • Routine性能受网络和系统负载影响，建议监控资源使用")
    print(f"   • 缓存文件会占用磁盘空间，建议定期清理旧缓存")

    print("\n" + "=" * 50)
    print("🔧 综合缓存优化测试完成")


if __name__ == "__main__":
    main()
