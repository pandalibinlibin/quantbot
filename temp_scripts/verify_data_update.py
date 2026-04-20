#!/usr/bin/env python3
"""
数据更新验证脚本
用于检查 bin 数据文件和因子计算是否正确更新
"""

import json
import struct
from pathlib import Path
from datetime import datetime


def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print("=" * 60)


def check_calendar():
    """检查日历文件最新日期"""
    print_section("1. 检查日历文件")

    qlib_dir = Path("/app/qlib_data")
    calendars_dir = qlib_dir / "calendars"
    cal_file = calendars_dir / "day.txt"

    if cal_file.exists():
        lines = cal_file.read_text().strip().split("\n")
        print(f"日历文件: {len(lines)} 个交易日")
        print(f"最早日期: {lines[0] if lines else 'empty'}")
        print(f"最新日期: {lines[-1] if lines else 'empty'}")
        print(f"最近5个交易日: {lines[-5:]}")
    else:
        print(f"日历文件不存在: {cal_file}")


def check_bin_files():
    """检查 bin 文件记录数"""
    print_section("2. 检查 OHLCV bin 文件")

    qlib_dir = Path("/app/qlib_data")
    features = ["open", "high", "low", "close", "volume"]
    symbols = ["sh600000", "sz000001", "sh600519", "sz300750"]

    for symbol in symbols:
        print(f"\n{symbol}:")
        for feature in features:
            bin_file = qlib_dir / "features" / symbol / f"{feature}.day.bin"
            if bin_file.exists():
                size = bin_file.stat().st_size
                num_records = size // 4  # float32 = 4 bytes
                print(f"  {feature}.day.bin: {num_records} 条记录")
            else:
                print(f"  {feature}.day.bin: 不存在")


def check_factor_files():
    """检查因子 bin 文件"""
    print_section("3. 检查因子 bin 文件")

    qlib_dir = Path("/app/qlib_data")
    factors = ["ma5", "daily_return", "hl_mid_price", "return_1d"]
    symbols = ["sh600000", "sz000001", "sh600519"]

    for symbol in symbols:
        print(f"\n{symbol}:")
        for factor in factors:
            factor_bin = qlib_dir / "features" / symbol / f"{factor}.day.bin"
            if factor_bin.exists():
                size = factor_bin.stat().st_size
                num_records = size // 4
                print(f"  {factor}.day.bin: {num_records} 条记录")
            else:
                print(f"  {factor}.day.bin: 不存在")


def check_qlib_data():
    """使用 Qlib API 验证数据"""
    print_section("4. 使用 Qlib API 验证数据")

    try:
        import qlib
        from qlib.data import D

        qlib.init(provider_uri="/app/qlib_data")

        # 获取日历范围
        cal = D.calendar(freq="day")
        print(f"日历范围: {cal[0]} 到 {cal[-1]}")
        print(f"总交易日数: {len(cal)}")

        # 获取一只股票的最新数据
        print("\n茅台(sh600519)最近数据:")
        df = D.features(
            ["sh600519"],
            ["$close", "$volume"],
            start_time="2026-02-20",
            end_time="2026-03-05",
        )
        if not df.empty:
            print(df.tail(10).to_string())
        else:
            print("  无数据")

        # 获取多只股票验证
        print("\n多只股票最新收盘价:")
        symbols = ["sh600000", "sz000001", "sh600519", "sz300750"]
        df2 = D.features(
            symbols, ["$close"], start_time="2026-02-28", end_time="2026-03-05"
        )
        if not df2.empty:
            print(df2.tail(20).to_string())
        else:
            print("  无数据")

    except Exception as e:
        print(f"Qlib 初始化或查询失败: {e}")


def check_portfolio():
    """检查目标组合文件"""
    print_section("5. 检查目标组合文件")

    portfolio_dir = Path("/app/data/target_portfolio")

    if not portfolio_dir.exists():
        print(f"目录不存在: {portfolio_dir}")
        return

    files = sorted(portfolio_dir.glob("*.json"))
    print(f"组合文件数量: {len(files)}")

    if files:
        print("\n最近5个文件:")
        for f in files[-5:]:
            print(f"  {f.name}")

        # 检查最新文件内容
        latest = files[-1]
        try:
            data = json.loads(latest.read_text())
            print(f"\n最新组合 ({latest.name}):")

            # 支持两种字段名: portfolio 或 positions
            portfolio = data.get("portfolio", data.get("positions", []))
            print(f"  持仓数量: {len(portfolio)}")

            if portfolio:
                print(f"  前5个持仓:")
                for pos in portfolio[:5]:
                    print(
                        f"    {pos.get('instrument', pos)}: weight={pos.get('target_weight', 'N/A')}"
                    )

            if "summary" in data:
                summary = data["summary"]
                print(f"\n  汇总信息:")
                print(
                    f"    基准: {summary.get('benchmark_name', summary.get('benchmark'))}"
                )
                print(f"    超配: {summary.get('overweight_count', 'N/A')} 只")
                print(f"    低配: {summary.get('underweight_count', 'N/A')} 只")
                print(f"    持平: {summary.get('neutral_count', 'N/A')} 只")
        except Exception as e:
            print(f"  读取文件失败: {e}")


def check_instruments():
    """检查 instruments 文件"""
    print_section("6. 检查 instruments 文件")

    qlib_dir = Path("/app/qlib_data")
    instruments_dir = qlib_dir / "instruments"

    if not instruments_dir.exists():
        print(f"目录不存在: {instruments_dir}")
        return

    for inst_file in sorted(instruments_dir.glob("*.txt"))[:5]:
        lines = inst_file.read_text().strip().split("\n")
        print(f"\n{inst_file.name}: {len(lines)} 只股票")
        if lines:
            # 显示第一行格式
            print(f"  格式示例: {lines[0]}")


def main():
    print("=" * 60)
    print(" QuantBot 数据更新验证脚本")
    print(f" 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    check_calendar()
    check_bin_files()
    check_factor_files()
    check_qlib_data()
    check_portfolio()
    check_instruments()

    print_section("验证完成")
    print("请检查以上输出，确认:")
    print("  1. 日历最新日期是否为今天或最近交易日")
    print("  2. bin 文件记录数是否一致")
    print("  3. 因子文件是否存在且记录数正确")
    print("  4. Qlib 能否读取最新数据")
    print("  5. 目标组合是否包含今天的文件")


if __name__ == "__main__":
    main()
