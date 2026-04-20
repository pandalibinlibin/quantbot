#!/usr/bin/env python3
"""
诊断 routine 实际执行时间 vs 前端显示时间
"""

import sys
import time
import requests
from datetime import datetime

sys.path.append("/app")


def test_routine_timing():
    """测试 routine 的实际执行时间"""

    print("🕐 开始测试 routine 实际执行时间...")

    # API 配置
    base_url = "http://localhost:8000/api/v1"

    # 记录开始时间
    client_start_time = time.time()
    start_datetime = datetime.now()

    print(f"⏰ 客户端开始时间: {start_datetime.strftime('%H:%M:%S')}")

    try:
        # 调用 routine API
        print("🚀 调用 routine API...")
        response = requests.post(
            f"{base_url}/online/routine", timeout=900
        )  # 15分钟超时

        # 记录结束时间
        client_end_time = time.time()
        end_datetime = datetime.now()

        print(f"⏰ 客户端结束时间: {end_datetime.strftime('%H:%M:%S')}")

        # 计算实际耗时
        actual_duration = client_end_time - client_start_time

        print(f"\n📊 时间统计对比:")
        print(
            f"   🕐 客户端实际耗时: {actual_duration:.2f} 秒 ({actual_duration/60:.2f} 分钟)"
        )

        if response.status_code == 200:
            result = response.json()
            backend_duration = result.get("total_duration_seconds", 0)

            print(
                f"   🖥️  后端报告耗时: {backend_duration:.2f} 秒 ({backend_duration/60:.2f} 分钟)"
            )
            print(f"   📈 时间差异: {abs(actual_duration - backend_duration):.2f} 秒")

            # 分析步骤耗时
            if "steps" in result:
                print(f"\n📋 步骤详细耗时:")
                total_steps_time = 0
                for step in result["steps"]:
                    step_duration = step.get("duration_seconds", 0)
                    total_steps_time += step_duration
                    print(f"   • {step['step']}: {step_duration:.2f}s")

                print(f"   📊 步骤总耗时: {total_steps_time:.2f}s")
                print(f"   🔍 未统计时间: {backend_duration - total_steps_time:.2f}s")

            # 检查是否有时间单位问题
            if abs(actual_duration - backend_duration) > 10:
                print(f"\n⚠️  发现时间统计异常!")
                print(f"   实际耗时与后端报告差异超过10秒")

                # 检查是否是毫秒/秒单位问题
                if abs(actual_duration - backend_duration / 1000) < 5:
                    print(f"   🐛 可能是毫秒/秒单位错误: {backend_duration/1000:.2f}s")
                elif abs(actual_duration * 1000 - backend_duration) < 5000:
                    print(f"   🐛 可能是秒/毫秒单位错误: {backend_duration/1000:.2f}s")
            else:
                print(f"\n✅ 时间统计基本准确")

        else:
            print(f"❌ API 调用失败: {response.status_code}")
            print(f"   错误信息: {response.text}")

    except requests.exceptions.Timeout:
        client_end_time = time.time()
        actual_duration = client_end_time - client_start_time
        print(
            f"⏰ 请求超时，实际耗时: {actual_duration:.2f} 秒 ({actual_duration/60:.2f} 分钟)"
        )

    except Exception as e:
        client_end_time = time.time()
        actual_duration = client_end_time - client_start_time
        print(f"❌ 测试失败: {e}")
        print(f"⏰ 实际耗时: {actual_duration:.2f} 秒 ({actual_duration/60:.2f} 分钟)")


def check_frontend_cache():
    """检查前端是否显示的是缓存数据"""
    print("\n🔍 检查前端缓存状态...")

    try:
        # 获取当前状态
        response = requests.get("http://localhost:8000/api/v1/online/status")
        if response.status_code == 200:
            status = response.json()
            last_routine_time = status.get("last_routine_time")

            if last_routine_time:
                print(f"📅 后端记录的最后执行时间: {last_routine_time}")

                # 解析时间
                try:
                    last_time = datetime.fromisoformat(
                        last_routine_time.replace("Z", "+00:00")
                    )
                    now = datetime.now()
                    time_diff = (now - last_time.replace(tzinfo=None)).total_seconds()

                    print(
                        f"⏱️  距离上次执行: {time_diff:.0f} 秒 ({time_diff/60:.1f} 分钟)"
                    )

                    if time_diff > 3600:  # 超过1小时
                        print("⚠️  前端可能显示的是旧的缓存数据")
                    else:
                        print("✅ 时间记录较新，应该不是缓存问题")

                except Exception as e:
                    print(f"❌ 时间解析失败: {e}")
            else:
                print("❌ 未找到最后执行时间记录")
        else:
            print(f"❌ 状态查询失败: {response.status_code}")

    except Exception as e:
        print(f"❌ 缓存检查失败: {e}")


def main():
    """主函数"""
    print("🔧 ROUTINE 时间统计诊断工具")
    print("=" * 50)

    # 检查前端缓存
    check_frontend_cache()

    # 询问是否执行实际测试
    print(f"\n⚠️  注意: 实际测试将执行完整的 routine 流程")
    print(f"   预计耗时: 2-10 分钟")
    print(f"   是否继续? (y/N): ", end="")

    # 在容器环境中直接执行，不等待输入
    print("y (自动执行)")

    # 执行实际时间测试
    test_routine_timing()

    print("\n" + "=" * 50)
    print("🔧 诊断完成")


if __name__ == "__main__":
    main()
