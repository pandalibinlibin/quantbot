#!/usr/bin/env python3
"""
简化的routine性能测试脚本
直接调用routine API，避免复杂的前端缓存检查
"""

import time
import requests
import json


def test_routine_performance():
    """测试routine性能，对比两次执行时间"""

    print("🚀 简化Routine性能测试")
    print("=" * 50)

    base_url = "http://localhost:8000/api/v1"

    # 测试两次routine执行
    times = []

    for i in range(2):
        print(f"\n🔄 第{i+1}次routine执行...")

        start_time = time.time()

        try:
            response = requests.post(
                f"{base_url}/online/routine", json={}, timeout=600  # 10分钟超时
            )

            end_time = time.time()
            duration = end_time - start_time
            times.append(duration)

            if response.status_code == 200:
                result = response.json()
                backend_duration = result.get("total_duration_seconds", 0)

                print(
                    f"   ✅ 第{i+1}次完成: {duration:.2f}s (后端: {backend_duration:.2f}s)"
                )

                # 显示步骤详情
                steps = result.get("steps", [])
                for step in steps:
                    step_name = step.get("step", "Unknown")
                    step_duration = step.get("duration_seconds", 0)
                    print(f"      • {step_name}: {step_duration:.2f}s")

            else:
                print(f"   ❌ 第{i+1}次失败: HTTP {response.status_code}")
                print(f"      错误: {response.text}")

        except requests.exceptions.Timeout:
            print(f"   ⏰ 第{i+1}次超时 (>10分钟)")
            times.append(600)  # 记录为超时时间

        except Exception as e:
            print(f"   ❌ 第{i+1}次错误: {e}")
            times.append(0)

        # 第一次执行后等待缓存生效
        if i == 0:
            print("   ⏳ 等待10秒让缓存生效...")
            time.sleep(10)

    # 分析性能提升
    if len(times) == 2 and times[0] > 0 and times[1] > 0:
        time_saved = times[0] - times[1]
        improvement = (time_saved / times[0]) * 100

        print(f"\n🎉 性能提升分析:")
        print(f"   📈 时间节省: {time_saved:.2f}s")
        print(f"   📊 性能提升: {improvement:.1f}%")

        if improvement > 20:
            print("   🚀 缓存效果显著!")
        elif improvement > 10:
            print("   📊 有一定缓存效果")
        else:
            print("   ⚠️  缓存效果不明显")

    print("\n" + "=" * 50)
    print("🔧 简化Routine性能测试完成")


if __name__ == "__main__":
    test_routine_performance()
