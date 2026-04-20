#!/usr/bin/env python3
"""
检查可用的股票数据和日期范围
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.append("/app")


def check_available_data():
    """检查可用的数据"""
    try:
        import qlib
        from qlib.config import REG_CN
        from qlib.data import D

        # 初始化Qlib
        qlib.init(provider_uri="/app/qlib_data", region=REG_CN)
        print("✓ Qlib环境初始化成功")

        # 1. 检查可用的股票代码
        print("\n=== 检查可用的股票代码 ===")
        instruments = D.instruments(market="all")
        print(f"instruments类型: {type(instruments)}")

        # 转换为列表
        if hasattr(instruments, "tolist"):
            instruments_list = instruments.tolist()
        elif hasattr(instruments, "__iter__"):
            instruments_list = list(instruments)
        else:
            instruments_list = [instruments]

        print(f"总共可用股票数量: {len(instruments_list)}")
        if len(instruments_list) > 0:
            print(f"前10个股票代码: {instruments_list[:10]}")
            print(f"后10个股票代码: {instruments_list[-10:]}")
        else:
            print("❌ 没有找到任何股票代码")

        # 2. 检查数据的日期范围
        print("\n=== 检查数据日期范围 ===")
        if len(instruments_list) > 0:
            # 选择前几个股票测试日期范围
            test_symbols = instruments_list[:5]
            print(f"测试股票: {test_symbols}")

            # 尝试加载一个较大的日期范围来找到实际的数据范围
            try:
                data = D.features(
                    instruments=test_symbols,
                    fields=["$close"],
                    start_time="2020-01-01",
                    end_time="2024-12-31",
                    freq="day",
                )

                if not data.empty:
                    dates = data.index.get_level_values(0).unique()
                    print(f"数据日期范围: {dates.min()} 到 {dates.max()}")
                    print(f"总交易日数: {len(dates)}")
                    print(f"最近10个交易日: {dates[-10:]}")

                    # 检查我们测试日期范围内的数据
                    test_start = "2023-12-01"
                    test_end = "2023-12-05"
                    test_data = D.features(
                        instruments=test_symbols,
                        fields=["$close"],
                        start_time=test_start,
                        end_time=test_end,
                        freq="day",
                    )
                    print(f"\n测试日期范围 {test_start} 到 {test_end} 的数据:")
                    print(f"数据shape: {test_data.shape}")
                    if not test_data.empty:
                        test_dates = test_data.index.get_level_values(0).unique()
                        print(f"测试范围内的交易日: {test_dates}")
                    else:
                        print("❌ 测试日期范围内没有数据！")
                else:
                    print("❌ 没有找到任何价格数据")

            except Exception as e:
                print(f"加载数据时出错: {e}")

        # 3. 检查因子数据
        print("\n=== 检查因子数据 ===")
        try:
            if len(instruments_list) > 0:
                # 检查Daily_Return因子
                daily_return_data = D.features(
                    instruments=instruments_list[:5],
                    fields=["$daily_return"],
                    start_time="2023-12-01",
                    end_time="2023-12-05",
                    freq="day",
                )
                print(f"Daily_Return因子数据shape: {daily_return_data.shape}")

                # 检查MA5因子
                ma5_data = D.features(
                    instruments=instruments_list[:5],
                    fields=["$ma5"],
                    start_time="2023-12-01",
                    end_time="2023-12-05",
                    freq="day",
                )
                print(f"MA5因子数据shape: {ma5_data.shape}")
            else:
                print("❌ 没有可用的股票代码来测试因子数据")

        except Exception as e:
            print(f"加载因子数据时出错: {e}")

        # 4. 检查qlib_data目录结构
        print("\n=== 检查qlib_data目录结构 ===")
        qlib_data_path = Path("/app/qlib_data")
        if qlib_data_path.exists():
            print(f"qlib_data目录存在: {qlib_data_path}")

            # 检查features目录
            features_path = qlib_data_path / "features"
            if features_path.exists():
                bin_files = list(features_path.glob("*.bin"))
                print(f"features目录中的bin文件数量: {len(bin_files)}")
                if len(bin_files) > 0:
                    print(f"前5个bin文件: {[f.name for f in bin_files[:5]]}")

                    # 查找因子相关的bin文件
                    daily_return_files = [
                        f for f in bin_files if "daily_return" in f.name.lower()
                    ]
                    ma5_files = [f for f in bin_files if "ma5" in f.name.lower()]
                    print(f"Daily_Return相关文件数量: {len(daily_return_files)}")
                    print(f"MA5相关文件数量: {len(ma5_files)}")
            else:
                print("❌ features目录不存在")
        else:
            print("❌ qlib_data目录不存在")

    except Exception as e:
        print(f"检查过程中出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_available_data()
