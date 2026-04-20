#!/usr/bin/env python3
"""
为回测功能执行routine生成信号
确保有足够的信号数据用于Enhanced Indexing Strategy回测
"""

import requests
import time


def execute_routine():
    """执行routine生成信号"""
    print("🚀 执行routine生成信号...")

    try:
        start_time = time.time()

        response = requests.post(
            "http://localhost:8000/api/v1/online/routine",
            json={},
            timeout=600,  # 10分钟超时
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"   ✅ Routine执行成功 (耗时: {duration:.2f}s)")
            print(f"      • success: {result.get('success', False)}")
            print(f"      • executed_at: {result.get('executed_at', 'N/A')}")
            print(f"      • signal_count: {result.get('signal_count', 'N/A')}")

            # 显示步骤耗时
            steps = result.get("steps", [])
            if steps:
                print(f"   📊 步骤耗时:")
                for step in steps:
                    step_name = step.get("step", "Unknown")
                    step_duration = step.get("duration_seconds", 0)
                    print(f"      • {step_name}: {step_duration:.2f}s")

            return result
        else:
            print(f"   ❌ Routine执行失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"   ❌ Routine执行异常: {e}")
        return None


def check_status_after_routine():
    """检查routine执行后的状态"""
    print("\n🔍 检查routine执行后的状态...")

    try:
        time.sleep(3)  # 等待状态更新

        response = requests.get(
            "http://localhost:8000/api/v1/online/status", timeout=30
        )
        if response.status_code == 200:
            status = response.json()

            print("   📊 更新后的状态:")
            print(f"      • is_initialized: {status.get('is_initialized', False)}")
            print(f"      • signal_count: {status.get('signal_count', 'N/A')}")
            print(
                f"      • last_routine_time: {status.get('last_routine_time', 'N/A')}"
            )

            return status
        else:
            print(f"   ❌ 状态检查失败")
            return None
    except Exception as e:
        print(f"   ❌ 状态检查异常: {e}")
        return None


def main():
    """主执行流程"""
    print("🔧 为Enhanced Indexing Strategy回测准备信号数据")
    print("=" * 50)

    # 1. 执行routine
    routine_result = execute_routine()

    if routine_result and routine_result.get("success"):
        # 2. 检查状态更新
        updated_status = check_status_after_routine()

        if updated_status and updated_status.get("is_initialized"):
            print("\n✅ Routine执行成功，OnlineManager已初始化")
            print("🎯 现在可以执行Enhanced Indexing Strategy回测")

            print("\n📋 下一步:")
            print(
                "   docker compose exec backend python /app/temp_scripts/run_enhanced_backtest_test.py"
            )
        else:
            print("\n⚠️  Routine执行成功但OnlineManager未初始化")
            print("🔧 可能需要检查初始化逻辑")
    else:
        print("\n❌ Routine执行失败")
        print("🔧 需要检查routine执行问题")

    print("\n" + "=" * 50)
    print("🔧 信号准备完成")


if __name__ == "__main__":
    main()
