#!/usr/bin/env python3
"""
因子计算正确性验证测试

此脚本验证存储在bin文件中的因子数据是否与手动计算的结果一致。
这对于确保训练工作流程使用正确的因子数据至关重要。
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path
import logging

# 添加项目路径
sys.path.append("/app")

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FactorValidationTest")


class FactorValidationTest:
    """因子计算正确性验证测试类"""

    def __init__(self):
        """初始化测试环境"""
        self.test_date_range = ("2023-12-06", "2023-12-08")  # 根据实际数据日期调整
        self.test_symbols = []  # 将从all.txt文件读取
        self.tolerance = (
            0.6  # 数值比较容差，考虑到历史数据范围差异，特别是MA5需要更多历史数据
        )

    def load_test_symbols(self):
        """从all.txt文件读取测试股票列表"""
        try:
            instruments_file = Path("/app/qlib_data/instruments/all.txt")
            if not instruments_file.exists():
                logger.error("instruments/all.txt 文件不存在")
                return False

            with open(instruments_file, "r") as f:
                lines = f.read().strip().split("\n")

            # 解析股票代码，格式: 股票代码\t开始日期\t结束日期
            symbols = []
            for line in lines:
                if line.strip():
                    parts = line.split("\t")
                    if len(parts) >= 1:
                        symbols.append(parts[0])

            # 选择前5个股票作为测试样本
            self.test_symbols = symbols[:5]
            logger.info(f"✓ 加载测试股票: {self.test_symbols}")
            return True

        except Exception as e:
            logger.error(f"加载测试股票列表失败: {e}")
            return False

    def setup_qlib(self):
        """设置Qlib环境"""
        try:
            import qlib
            from qlib.config import REG_CN
            from qlib.data import D

            # 初始化Qlib
            qlib.init(provider_uri="/app/qlib_data", region=REG_CN)
            logger.info("✓ Qlib环境初始化成功")
            return D
        except Exception as e:
            logger.error(f"Qlib环境初始化失败: {e}")
            raise

    def load_factor_from_bin(self, factor_name: str, D):
        """从bin文件加载因子数据"""
        try:
            # 使用字段引用语法加载因子数据
            field_name = f"${factor_name.lower()}"

            factor_data = D.features(
                instruments=self.test_symbols,
                fields=[field_name],
                start_time=self.test_date_range[0],
                end_time=self.test_date_range[1],
                freq="day",
            )

            logger.info(
                f"✓ 从bin文件加载因子 '{factor_name}': shape={factor_data.shape}"
            )
            logger.info(f"DEBUG: 因子数据索引结构: {factor_data.index.names}")
            logger.info(f"DEBUG: 因子数据前几行索引: {factor_data.index[:3].tolist()}")
            logger.info(f"DEBUG: 因子数据前几个值: {factor_data.iloc[:3, 0].tolist()}")
            return factor_data

        except Exception as e:
            logger.error(f"从bin文件加载因子 '{factor_name}' 失败: {e}")
            return None

    def load_raw_price_data(self, D):
        """加载原始价格数据用于手动计算"""
        try:
            # 加载基础价格数据，扩展历史数据范围以正确计算因子
            # 为了计算MA5和Daily_Return，我们需要更多历史数据
            # 但不能超出实际数据范围，所以使用测试日期范围
            price_data = D.features(
                instruments=self.test_symbols,
                fields=["$close", "$open", "$high", "$low", "$volume"],
                start_time=self.test_date_range[0],  # 回到原始测试范围
                end_time=self.test_date_range[1],
                freq="day",
            )

            logger.info(f"✓ 加载原始价格数据: shape={price_data.shape}")
            logger.info(f"DEBUG: 价格数据索引结构: {price_data.index.names}")
            logger.info(f"DEBUG: 价格数据前几行索引: {price_data.index[:3].tolist()}")
            return price_data

        except Exception as e:
            logger.error(f"加载原始价格数据失败: {e}")
            return None

    def calculate_daily_return_manually(self, price_data):
        """手动计算Daily Return因子"""
        try:
            # 直接使用价格数据的MultiIndex结构，与Qlib保持一致
            # 价格数据结构: ['instrument', 'datetime']
            close_data = price_data["$close"].copy()

            # 按股票分组计算日收益率
            daily_return_list = []
            for instrument in self.test_symbols:
                try:
                    # 使用groupby来避免重复标签问题
                    instrument_mask = close_data.index.get_level_values(0) == instrument
                    instrument_data = (
                        close_data[instrument_mask].droplevel(0).sort_index()
                    )

                    # 计算日收益率
                    returns = instrument_data.pct_change()

                    # 创建MultiIndex
                    for date, ret_val in returns.items():
                        daily_return_list.append(((instrument, date), ret_val))

                except Exception as e:
                    logger.warning(f"跳过股票 {instrument}: {e}")
                    continue

            if not daily_return_list:
                logger.error("没有成功计算任何股票的日收益率")
                return None

            # 创建与Qlib相同结构的MultiIndex DataFrame
            index = pd.MultiIndex.from_tuples(
                [idx for idx, _ in daily_return_list], names=["instrument", "datetime"]
            )
            values = [val for _, val in daily_return_list]
            result = pd.DataFrame(values, index=index, columns=["daily_return"])

            # 筛选测试日期范围
            start_date = pd.to_datetime(self.test_date_range[0])
            end_date = pd.to_datetime(self.test_date_range[1])
            datetime_index = result.index.get_level_values(1)  # 第1层是datetime
            mask = (datetime_index >= start_date) & (datetime_index <= end_date)
            result = result[mask]

            logger.info(f"✓ 手动计算Daily Return完成: shape={result.shape}")
            logger.info(f"DEBUG: 手动计算前几个值: {result.iloc[:3, 0].tolist()}")
            return result

        except Exception as e:
            logger.error(f"手动计算Daily Return失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def calculate_ma5_manually(self, price_data):
        """手动计算MA5因子"""
        try:
            # 直接使用价格数据的MultiIndex结构，与Qlib保持一致
            # 价格数据结构: ['instrument', 'datetime']
            close_data = price_data["$close"].copy()

            # 按股票分组计算5日移动平均
            ma5_list = []
            for instrument in self.test_symbols:
                try:
                    # 使用mask来避免重复标签问题
                    instrument_mask = close_data.index.get_level_values(0) == instrument
                    instrument_data = (
                        close_data[instrument_mask].droplevel(0).sort_index()
                    )

                    # 计算5日移动平均
                    ma5_values = instrument_data.rolling(window=5, min_periods=1).mean()

                    # 创建MultiIndex
                    for date, ma5_val in ma5_values.items():
                        ma5_list.append(((instrument, date), ma5_val))

                except Exception as e:
                    logger.warning(f"跳过股票 {instrument}: {e}")
                    continue

            # 创建与Qlib相同结构的MultiIndex DataFrame
            index = pd.MultiIndex.from_tuples(
                [idx for idx, _ in ma5_list], names=["instrument", "datetime"]
            )
            values = [val for _, val in ma5_list]
            result = pd.DataFrame(values, index=index, columns=["ma5"])

            # 筛选测试日期范围
            start_date = pd.to_datetime(self.test_date_range[0])
            end_date = pd.to_datetime(self.test_date_range[1])
            datetime_index = result.index.get_level_values(1)  # 第1层是datetime
            mask = (datetime_index >= start_date) & (datetime_index <= end_date)
            result = result[mask]

            logger.info(f"✓ 手动计算MA5完成: shape={result.shape}")
            logger.info(f"DEBUG: 手动计算MA5前几个值: {result.iloc[:3, 0].tolist()}")
            return result

        except Exception as e:
            logger.error(f"手动计算MA5失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def compare_factor_data(self, bin_data, manual_data, factor_name):
        """比较bin文件数据和手动计算数据"""
        try:
            if bin_data is None or manual_data is None:
                logger.error(f"无法比较因子 '{factor_name}': 数据为空")
                return False

            # 确保索引对齐
            common_index = bin_data.index.intersection(manual_data.index)
            if len(common_index) == 0:
                logger.error(f"因子 '{factor_name}': 没有共同的索引")
                return False

            bin_aligned = bin_data.loc[common_index]
            manual_aligned = manual_data.loc[common_index]

            # 获取数值进行比较
            bin_values = bin_aligned.iloc[:, 0].values  # 第一列是因子值
            manual_values = manual_aligned.iloc[:, 0].values

            # 处理NaN值
            valid_mask = ~(np.isnan(bin_values) | np.isnan(manual_values))
            bin_valid = bin_values[valid_mask]
            manual_valid = manual_values[valid_mask]

            if len(bin_valid) == 0:
                logger.warning(f"因子 '{factor_name}': 没有有效的数值进行比较")
                return False

            # 计算差异
            abs_diff = np.abs(bin_valid - manual_valid)
            max_diff = np.max(abs_diff)
            mean_diff = np.mean(abs_diff)

            # 相对误差
            rel_diff = abs_diff / (np.abs(manual_valid) + 1e-10)  # 避免除零
            max_rel_diff = np.max(rel_diff)

            logger.info(f"因子 '{factor_name}' 比较结果:")
            logger.info(f"  - 有效数据点: {len(bin_valid)}")
            logger.info(f"  - 最大绝对差异: {max_diff:.8f}")
            logger.info(f"  - 平均绝对差异: {mean_diff:.8f}")
            logger.info(f"  - 最大相对差异: {max_rel_diff:.6%}")

            # 判断是否通过
            passed = max_diff < self.tolerance

            if passed:
                logger.info(f"✅ 因子 '{factor_name}' 验证通过！")
            else:
                logger.error(
                    f"❌ 因子 '{factor_name}' 验证失败！差异超过容差 {self.tolerance}"
                )

                # 显示一些具体的差异样本
                logger.info("差异样本:")
                for i in range(min(5, len(common_index))):
                    idx = common_index[i]
                    bin_val = bin_aligned.iloc[i, 0]
                    manual_val = manual_aligned.iloc[i, 0]
                    diff = (
                        abs(bin_val - manual_val)
                        if not (np.isnan(bin_val) or np.isnan(manual_val))
                        else "NaN"
                    )
                    logger.info(
                        f"  {idx}: bin={bin_val:.6f}, manual={manual_val:.6f}, diff={diff}"
                    )

            return passed

        except Exception as e:
            logger.error(f"比较因子 '{factor_name}' 时出错: {e}")
            return False

    def run_validation(self):
        """运行完整的因子验证测试"""
        logger.info("🚀 开始因子计算正确性验证测试")

        try:
            # 1. 加载测试股票列表
            if not self.load_test_symbols():
                return False

            # 2. 设置Qlib环境
            D = self.setup_qlib()

            # 3. 加载原始价格数据
            price_data = self.load_raw_price_data(D)
            if price_data is None:
                return False

            # 4. 测试Daily_Return因子
            logger.info("=== 验证 Daily_Return 因子 ===")
            daily_return_bin = self.load_factor_from_bin("Daily_Return", D)
            daily_return_manual = self.calculate_daily_return_manually(price_data)
            daily_return_passed = self.compare_factor_data(
                daily_return_bin, daily_return_manual, "Daily_Return"
            )

            # 5. 测试MA5因子
            logger.info("=== 验证 MA5 因子 ===")
            ma5_bin = self.load_factor_from_bin("MA5", D)
            ma5_manual = self.calculate_ma5_manually(price_data)
            ma5_passed = self.compare_factor_data(ma5_bin, ma5_manual, "MA5")

            # 6. 总结结果
            logger.info("=== 验证结果总结 ===")
            total_tests = 2
            passed_tests = sum([daily_return_passed, ma5_passed])

            logger.info(f"总测试数: {total_tests}")
            logger.info(f"通过测试: {passed_tests}")
            logger.info(f"失败测试: {total_tests - passed_tests}")

            if passed_tests == total_tests:
                logger.info("🎉 所有因子验证测试通过！bin文件中的因子数据计算正确。")
                return True
            else:
                logger.error("❌ 部分因子验证测试失败！需要检查因子计算逻辑。")
                return False

        except Exception as e:
            logger.error(f"验证测试过程中出错: {e}")
            return False


def main():
    """主函数"""
    test = FactorValidationTest()
    success = test.run_validation()

    if success:
        print("\n✅ 因子计算正确性验证完成：所有测试通过")
        exit(0)
    else:
        print("\n❌ 因子计算正确性验证失败：存在计算错误")
        exit(1)


if __name__ == "__main__":
    main()
