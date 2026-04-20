#!/usr/bin/env python3
"""
详细检查Qlib数据结构和实际存储的数据
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append("/app")


def check_qlib_data_structure():
    """详细检查Qlib数据结构"""
    try:
        print("=== 检查Qlib数据目录结构 ===")
        qlib_data_path = Path("/app/qlib_data")

        if not qlib_data_path.exists():
            print("❌ /app/qlib_data 目录不存在")
            return

        print(f"✓ Qlib数据目录存在: {qlib_data_path}")

        # 递归列出所有文件和目录
        def list_directory_tree(path, level=0):
            indent = "  " * level
            if path.is_dir():
                print(f"{indent}{path.name}/")
                try:
                    for item in sorted(path.iterdir()):
                        if level < 3:  # 限制递归深度
                            list_directory_tree(item, level + 1)
                        elif item.is_file():
                            print(f"{indent}  {item.name}")
                except PermissionError:
                    print(f"{indent}  [权限错误]")
            else:
                size = path.stat().st_size if path.exists() else 0
                print(f"{indent}{path.name} ({size} bytes)")

        print("\n目录树结构:")
        list_directory_tree(qlib_data_path)

        # 检查特定的重要目录
        important_dirs = ["features", "instruments", "calendars"]
        for dir_name in important_dirs:
            dir_path = qlib_data_path / dir_name
            print(f"\n=== 检查 {dir_name} 目录 ===")
            if dir_path.exists():
                files = list(dir_path.glob("*"))
                print(f"✓ {dir_name} 目录存在，包含 {len(files)} 个文件")
                if len(files) > 0:
                    print(f"文件列表: {[f.name for f in files[:10]]}")  # 显示前10个文件
                    if len(files) > 10:
                        print(f"... 还有 {len(files) - 10} 个文件")
            else:
                print(f"❌ {dir_name} 目录不存在")

        # 尝试用不同的方法初始化Qlib并获取信息
        print("\n=== 尝试初始化Qlib ===")
        import qlib
        from qlib.config import REG_CN

        qlib.init(provider_uri="/app/qlib_data", region=REG_CN)
        print("✓ Qlib初始化成功")

        # 尝试不同的方法获取股票列表
        from qlib.data import D

        print("\n=== 尝试获取股票列表 ===")

        # 方法1: D.instruments()
        try:
            instruments_result = D.instruments()
            print(f"D.instruments() 结果类型: {type(instruments_result)}")
            print(f"D.instruments() 结果: {instruments_result}")
        except Exception as e:
            print(f"D.instruments() 失败: {e}")

        # 方法2: D.instruments(market="all")
        try:
            instruments_all = D.instruments(market="all")
            print(f"D.instruments(market='all') 结果类型: {type(instruments_all)}")
            print(f"D.instruments(market='all') 结果: {instruments_all}")
        except Exception as e:
            print(f"D.instruments(market='all') 失败: {e}")

        # 方法3: 检查instruments目录中的文件
        instruments_dir = qlib_data_path / "instruments"
        if instruments_dir.exists():
            print(f"\n=== instruments目录内容 ===")
            for file in instruments_dir.glob("*"):
                print(f"文件: {file.name}")
                if file.suffix == ".txt":
                    try:
                        with open(file, "r") as f:
                            content = f.read().strip()
                            lines = content.split("\n")
                            print(f"  内容行数: {len(lines)}")
                            if len(lines) > 0:
                                print(f"  前5行: {lines[:5]}")
                    except Exception as e:
                        print(f"  读取文件失败: {e}")

        # 检查是否有任何实际的股票数据文件
        print("\n=== 搜索所有.bin文件 ===")
        bin_files = list(qlib_data_path.rglob("*.bin"))
        print(f"找到 {len(bin_files)} 个.bin文件")
        if len(bin_files) > 0:
            for bin_file in bin_files[:10]:  # 显示前10个
                rel_path = bin_file.relative_to(qlib_data_path)
                size = bin_file.stat().st_size
                print(f"  {rel_path} ({size} bytes)")

        print("\n=== 搜索所有.txt文件 ===")
        txt_files = list(qlib_data_path.rglob("*.txt"))
        print(f"找到 {len(txt_files)} 个.txt文件")
        if len(txt_files) > 0:
            for txt_file in txt_files[:5]:  # 显示前5个
                rel_path = txt_file.relative_to(qlib_data_path)
                print(f"  {rel_path}")

    except Exception as e:
        print(f"检查过程中出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_qlib_data_structure()
