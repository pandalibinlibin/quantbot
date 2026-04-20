#!/usr/bin/env python3
"""
测试缓存优化效果

对比优化前后的routine执行时间
"""

import sys
import time
import requests
from datetime import datetime

sys.path.append("/app")


def test_cache_optimization():
    """测试缓存优化效果"""

    print("🚀 测试缓存优化效果")
    print("=" * 50)

    base_url = "http://localhost:8000/api/v1"

    # 1. 检查缓存状态
    print("📊 检查缓存状态...")
    try:
        response = requests.get(f"{base_url}/cache/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ 缓存服务正常")
            cache_stats = stats.get("cache_stats", {})
            print(f"   📁 缓存目录: {cache_stats.get('cache_dir', 'N/A')}")
            print(f"   💾 缓存大小: {cache_stats.get('cache_size_mb', 0)} MB")
            print(f"   📦 缓存模型数: {len(cache_stats.get('cached_models', []))}")
        else:
            print(f"   ⚠️  缓存状态查询失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 缓存状态查询错误: {e}")

    # 2. 检查数据更新需求
    print(f"\n🔍 检查数据更新需求...")
    try:
        response = requests.get(f"{base_url}/cache/check-update")
        if response.status_code == 200:
            update_info = response.json()
            should_update = update_info.get("should_update", True)
            reason = update_info.get("reason", "Unknown")
            print(f"   📅 需要数据更新: {should_update}")
            print(f"   📝 原因: {reason}")
        else:
            print(f"   ⚠️  数据更新检查失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 数据更新检查错误: {e}")

    # 3. 执行第一次routine (可能触发完整更新)
    print(f"\n🔄 执行第一次routine...")
    start_time = time.time()
    start_datetime = datetime.now()

    try:
        response = requests.post(f"{base_url}/online/routine", timeout=900)
        end_time = time.time()
        end_datetime = datetime.now()

        first_duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()
            backend_duration = result.get("total_duration_seconds", 0)

            print(f"   ✅ 第一次routine完成")
            print(
                f"   ⏱️  客户端耗时: {first_duration:.2f}s ({first_duration/60:.2f}min)"
            )
            print(
                f"   🖥️  后端报告: {backend_duration:.2f}s ({backend_duration/60:.2f}min)"
            )

            # 分析步骤
            if "steps" in result:
                print(f"   📋 步骤分析:")
                for step in result["steps"]:
                    duration = step.get("duration_seconds", 0)
                    details = step.get("details", {})
                    cache_optimized = details.get("cache_optimized", False)
                    skipped = details.get("skipped", False)

                    status = "⚡" if cache_optimized else "🔄"
                    if skipped:
                        status = "⏭️ "

                    print(f"      {status} {step['step']}: {duration:.2f}s")

                    if cache_optimized:
                        print(f"         💡 缓存优化: {details.get('message', 'N/A')}")
        else:
            print(f"   ❌ 第一次routine失败: {response.status_code}")
            print(f"   📄 错误: {response.text}")
            return

    except Exception as e:
        print(f"   ❌ 第一次routine错误: {e}")
        return

    # 4. 等待一段时间后执行第二次routine (应该大部分被缓存)
    print(f"\n⏳ 等待10秒后执行第二次routine...")
    time.sleep(10)

    print(f"🔄 执行第二次routine (测试缓存效果)...")
    start_time = time.time()

    try:
        response = requests.post(f"{base_url}/online/routine", timeout=900)
        end_time = time.time()

        second_duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()
            backend_duration = result.get("total_duration_seconds", 0)

            print(f"   ✅ 第二次routine完成")
            print(
                f"   ⏱️  客户端耗时: {second_duration:.2f}s ({second_duration/60:.2f}min)"
            )
            print(
                f"   🖥️  后端报告: {backend_duration:.2f}s ({backend_duration/60:.2f}min)"
            )

            # 计算优化效果
            time_saved = first_duration - second_duration
            if first_duration > 0:
                improvement_pct = (time_saved / first_duration) * 100
                print(f"\n🎉 缓存优化效果:")
                print(f"   💾 节省时间: {time_saved:.2f}s ({time_saved/60:.2f}min)")
                print(f"   📈 性能提升: {improvement_pct:.1f}%")

                if improvement_pct > 50:
                    print(f"   🚀 优化效果显著!")
                elif improvement_pct > 20:
                    print(f"   ✅ 优化效果良好")
                elif improvement_pct > 0:
                    print(f"   📊 有一定优化效果")
                else:
                    print(f"   ⚠️  优化效果不明显")

            # 分析第二次的步骤
            if "steps" in result:
                print(f"   📋 第二次步骤分析:")
                cached_steps = 0
                total_steps = len(result["steps"])

                for step in result["steps"]:
                    duration = step.get("duration_seconds", 0)
                    details = step.get("details", {})
                    cache_optimized = details.get("cache_optimized", False)
                    skipped = details.get("skipped", False)

                    if skipped or (cache_optimized and duration < 1):
                        cached_steps += 1

                    status = "⚡" if cache_optimized else "🔄"
                    if skipped:
                        status = "⏭️ "

                    print(f"      {status} {step['step']}: {duration:.2f}s")

                    if cache_optimized and "message" in details:
                        print(f"         💡 {details['message']}")

                cache_ratio = (
                    (cached_steps / total_steps) * 100 if total_steps > 0 else 0
                )
                print(
                    f"   📊 缓存命中率: {cache_ratio:.1f}% ({cached_steps}/{total_steps})"
                )
        else:
            print(f"   ❌ 第二次routine失败: {response.status_code}")

    except Exception as e:
        print(f"   ❌ 第二次routine错误: {e}")

    print(f"\n" + "=" * 50)
    print(f"🔧 缓存优化测试完成")


def main():
    """主函数"""
    test_cache_optimization()


if __name__ == "__main__":
    main()
