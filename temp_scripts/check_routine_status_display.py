#!/usr/bin/env python3
"""
检查Routine状态显示问题
诊断为什么前端显示"Last Executed"为空
"""

import requests
import json
from datetime import datetime


def check_online_status():
    """检查Online Serving状态"""
    print("🔍 检查Online Serving状态...")

    try:
        response = requests.get(
            "http://localhost:8000/api/v1/online/status", timeout=30
        )
        if response.status_code == 200:
            status = response.json()

            print("   📊 Online Serving状态详情:")
            print(f"      • is_initialized: {status.get('is_initialized', 'N/A')}")
            print(f"      • signal_count: {status.get('signal_count', 'N/A')}")
            print(f"      • last_executed: {status.get('last_executed', 'N/A')}")
            print(f"      • executed_at: {status.get('executed_at', 'N/A')}")
            print(f"      • cur_time: {status.get('cur_time', 'N/A')}")

            # 检查所有字段
            print(f"\n   📋 完整状态字段:")
            for key, value in status.items():
                print(f"      • {key}: {value}")

            return status
        else:
            print(f"   ❌ 状态获取失败: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ 状态检查异常: {e}")
        return None


def check_routine_result():
    """检查最新的routine执行结果"""
    print("\n🔍 检查最新routine执行结果...")

    try:
        # 检查是否有routine结果文件
        import os

        result_files = [
            "/app/mlruns/routine_results/latest_result.json",
            "/app/data/routine_results/latest_result.json",
            "/tmp/routine_result.json",
        ]

        for file_path in result_files:
            if os.path.exists(file_path):
                print(f"   📁 找到结果文件: {file_path}")
                with open(file_path, "r") as f:
                    data = json.load(f)
                    print(f"      • executed_at: {data.get('executed_at', 'N/A')}")
                    print(
                        f"      • total_duration_seconds: {data.get('total_duration_seconds', 'N/A')}"
                    )
                    return data
            else:
                print(f"   ❌ 结果文件不存在: {file_path}")

        print("   ⚠️  未找到routine结果文件")
        return None

    except Exception as e:
        print(f"   ❌ 结果检查异常: {e}")
        return None


def execute_routine_and_check():
    """执行routine并检查状态更新"""
    print("\n🚀 执行routine并检查状态更新...")

    try:
        print("   🔄 执行routine...")
        start_time = time.time()

        response = requests.post(
            "http://localhost:8000/api/v1/online/routine", json={}, timeout=600
        )

        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"   ✅ Routine执行成功 (耗时: {duration:.2f}s)")
            print(f"      • success: {result.get('success', False)}")
            print(f"      • executed_at: {result.get('executed_at', 'N/A')}")
            print(
                f"      • total_duration_seconds: {result.get('total_duration_seconds', 'N/A')}"
            )
            print(f"      • signal_count: {result.get('signal_count', 'N/A')}")

            # 等待状态更新
            print("   ⏳ 等待5秒让状态更新...")
            time.sleep(5)

            # 重新检查状态
            print("   🔄 重新检查Online状态...")
            updated_status = check_online_status()

            return result
        else:
            print(f"   ❌ Routine执行失败: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"   ❌ Routine执行异常: {e}")
        return None


def diagnose_frontend_display():
    """诊断前端显示问题"""
    print("\n🔍 诊断前端显示问题...")

    print("   📋 可能的原因:")
    print("      1. Online状态API未返回executed_at字段")
    print("      2. 前端缓存问题，未刷新最新状态")
    print("      3. 状态更新逻辑有延迟")
    print("      4. 前端组件未正确读取executed_at字段")

    print("   💡 建议解决方案:")
    print(
        "      1. 检查backend/app/services/online_serving_service.py中的get_status方法"
    )
    print("      2. 确认executed_at字段正确返回")
    print("      3. 检查前端routine.tsx组件的状态读取逻辑")
    print("      4. 清除浏览器缓存或强制刷新")


def main():
    """主诊断流程"""
    print("🔧 Routine状态显示问题诊断")
    print("=" * 50)

    # 1. 检查当前状态
    current_status = check_online_status()

    # 2. 检查routine结果文件
    routine_result = check_routine_result()

    # 3. 执行routine并检查状态更新
    if not current_status or not current_status.get("last_executed"):
        print("\n💡 尝试执行routine来更新状态...")
        new_result = execute_routine_and_check()

    # 4. 诊断前端显示问题
    diagnose_frontend_display()

    print("\n" + "=" * 50)
    print("🔧 诊断完成")

    print("\n📋 修复建议:")
    print("   1. 如果API返回executed_at但前端不显示 → 检查前端组件")
    print("   2. 如果API未返回executed_at → 检查后端get_status方法")
    print("   3. 如果状态更新有延迟 → 添加状态同步逻辑")


if __name__ == "__main__":
    main()
