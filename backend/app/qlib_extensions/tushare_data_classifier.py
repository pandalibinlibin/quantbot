"""
Tushare Data Type Classifier

This module automatically detects the type of Tushare data and applies
the appropriate broadcast mechanism based on data structure analysis.

Data Types:
1. Stock-level data: Has ts_code + trade_date (no broadcast needed)
2. Macro data: Has time field (m/q/y) but no ts_code (time + stock broadcast)
3. Industry data: Has industry_code + time field (time + industry broadcast)

Usage:
    classifier = TushareDataClassifier()
    data_type = classifier.classify_data(df, api_name="cn_cpi")
    broadcast_config = classifier.get_broadcast_config(data_type)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Tuple
from enum import Enum
import re


class TushareDataType(Enum):
    """Tushare data type enumeration"""

    STOCK_DAILY = "stock_daily"  # Stock-level daily data (no broadcast)
    MACRO_MONTHLY = "macro_monthly"  # Macro monthly data (time + stock broadcast)
    MACRO_QUARTERLY = "macro_quarterly"  # Macro quarterly data (time + stock broadcast)
    MACRO_YEARLY = "macro_yearly"  # Macro yearly data (time + stock broadcast)
    INDUSTRY_DAILY = "industry_daily"  # Industry daily data (industry broadcast)
    INDUSTRY_MONTHLY = (
        "industry_monthly"  # Industry monthly data (time + industry broadcast)
    )
    UNKNOWN = "unknown"  # Unknown type (no broadcast)


class TushareDataClassifier:
    """
    Automatic classifier for Tushare data types.

    This classifier analyzes DataFrame structure and API names to determine:
    1. Data frequency (daily, monthly, quarterly, yearly)
    2. Data scope (stock-level, macro, industry)
    3. Required broadcast mechanism
    """

    def __init__(self):
        # API name patterns for different data types
        self.macro_apis = {
            # Monthly macro data
            "monthly": [
                "cn_cpi",
                "cn_ppi",
                "cn_gdp",
                "cn_m",
                "shibor",
                "libor",
                "hibor",
                "us_cpi",
                "us_ppi",
                "us_gdp",
                "eu_cpi",
                "jp_cpi",
            ],
            # Quarterly macro data
            "quarterly": ["cn_gdp", "us_gdp", "eu_gdp", "jp_gdp"],
            # Yearly macro data
            "yearly": ["cn_gdp_year", "population"],
        }

        self.industry_apis = [
            "index_classify",
            "sw_daily",
            "sw_member",
            "ths_daily",
            "ths_member",
            "concept_detail",
            "concept",
            "block_trade",
            "fund_flow",
        ]

        # Column patterns for data type detection
        self.stock_columns = ["ts_code", "stock_code", "symbol"]
        self.time_columns = {
            "daily": ["trade_date", "cal_date", "date"],
            "monthly": ["m", "month", "report_date"],
            "quarterly": ["q", "quarter", "end_date"],
            "yearly": ["y", "year"],
        }
        self.industry_columns = [
            "industry_code",
            "index_code",
            "sw_code",
            "concept_code",
        ]

    def classify_data(self, df: pd.DataFrame, api_name: str = "") -> TushareDataType:
        """
        Classify Tushare data type based on DataFrame structure and API name.

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe from Tushare API
        api_name : str
            Tushare API name (e.g., "daily", "cn_cpi", "sw_daily")

        Returns
        -------
        TushareDataType
            Detected data type
        """
        if df.empty:
            return TushareDataType.UNKNOWN

        columns = [col.lower() for col in df.columns]

        # Step 1: Check if it's stock-level data
        has_stock_code = any(col in columns for col in self.stock_columns)
        has_daily_time = any(col in columns for col in self.time_columns["daily"])

        if has_stock_code and has_daily_time:
            return TushareDataType.STOCK_DAILY

        # Step 2: Check if it's macro data
        if api_name in self.macro_apis["monthly"]:
            return TushareDataType.MACRO_MONTHLY
        elif api_name in self.macro_apis["quarterly"]:
            return TushareDataType.MACRO_QUARTERLY
        elif api_name in self.macro_apis["yearly"]:
            return TushareDataType.MACRO_YEARLY

        # Step 3: Check by column patterns for macro data
        has_monthly_time = any(col in columns for col in self.time_columns["monthly"])
        has_quarterly_time = any(
            col in columns for col in self.time_columns["quarterly"]
        )
        has_yearly_time = any(col in columns for col in self.time_columns["yearly"])

        if not has_stock_code:  # No stock code = macro data
            if has_monthly_time:
                return TushareDataType.MACRO_MONTHLY
            elif has_quarterly_time:
                return TushareDataType.MACRO_QUARTERLY
            elif has_yearly_time:
                return TushareDataType.MACRO_YEARLY

        # Step 4: Check if it's industry data
        has_industry_code = any(col in columns for col in self.industry_columns)

        if has_industry_code:
            if has_daily_time:
                return TushareDataType.INDUSTRY_DAILY
            elif has_monthly_time:
                return TushareDataType.INDUSTRY_MONTHLY

        return TushareDataType.UNKNOWN

    def get_broadcast_config(self, data_type: TushareDataType) -> Dict[str, any]:
        """
        Get broadcast configuration for a given data type.

        Parameters
        ----------
        data_type : TushareDataType
            Detected data type

        Returns
        -------
        Dict
            Broadcast configuration with:
            - needs_time_broadcast: bool
            - needs_stock_broadcast: bool
            - needs_industry_broadcast: bool
            - time_freq: str (original frequency)
            - target_freq: str (target frequency)
        """
        config = {
            "needs_time_broadcast": False,
            "needs_stock_broadcast": False,
            "needs_industry_broadcast": False,
            "time_freq": "D",  # Default daily
            "target_freq": "D",
        }

        if data_type == TushareDataType.STOCK_DAILY:
            # Stock daily data - no broadcast needed
            pass

        elif data_type == TushareDataType.MACRO_MONTHLY:
            config.update(
                {
                    "needs_time_broadcast": True,
                    "needs_stock_broadcast": True,
                    "time_freq": "M",
                    "target_freq": "D",
                }
            )

        elif data_type == TushareDataType.MACRO_QUARTERLY:
            config.update(
                {
                    "needs_time_broadcast": True,
                    "needs_stock_broadcast": True,
                    "time_freq": "Q",
                    "target_freq": "D",
                }
            )

        elif data_type == TushareDataType.MACRO_YEARLY:
            config.update(
                {
                    "needs_time_broadcast": True,
                    "needs_stock_broadcast": True,
                    "time_freq": "Y",
                    "target_freq": "D",
                }
            )

        elif data_type == TushareDataType.INDUSTRY_DAILY:
            config.update(
                {"needs_industry_broadcast": True, "time_freq": "D", "target_freq": "D"}
            )

        elif data_type == TushareDataType.INDUSTRY_MONTHLY:
            config.update(
                {
                    "needs_time_broadcast": True,
                    "needs_industry_broadcast": True,
                    "time_freq": "M",
                    "target_freq": "D",
                }
            )

        return config

    def apply_broadcast(
        self,
        df: pd.DataFrame,
        data_type: TushareDataType,
        calendar: pd.DatetimeIndex,
        instruments: List[str],
        industry_mapping: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        """
        Apply appropriate broadcast mechanism based on data type.

        Parameters
        ----------
        df : pd.DataFrame
            Input Tushare data
        data_type : TushareDataType
            Detected data type
        calendar : pd.DatetimeIndex
            Trading calendar
        instruments : List[str]
            List of all instrument codes
        industry_mapping : Dict[str, str], optional
            Mapping from instrument to industry code

        Returns
        -------
        pd.DataFrame
            Broadcasted data ready for Qlib storage
        """
        from .data_broadcast import (
            time_broadcast,
            stock_broadcast,
            broadcast_industry_data,
        )

        config = self.get_broadcast_config(data_type)
        result = df.copy()

        # Step 1: Time broadcast if needed
        if config["needs_time_broadcast"]:
            result = time_broadcast(result, freq=config["time_freq"], calendar=calendar)

        # Step 2: Stock broadcast if needed (for macro data)
        if config["needs_stock_broadcast"]:
            result = stock_broadcast(result, instruments)

        # Step 3: Industry broadcast if needed (for industry data)
        if config["needs_industry_broadcast"] and industry_mapping:
            result = broadcast_industry_data(
                result, industry_mapping, calendar, freq=config["time_freq"]
            )

        return result

    def detect_time_frequency(self, df: pd.DataFrame) -> str:
        """
        Detect the time frequency of the data by analyzing date patterns.

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe

        Returns
        -------
        str
            Detected frequency: "D", "M", "Q", "Y"
        """
        # Find time column
        time_col = None
        for col in df.columns:
            col_lower = col.lower()
            if any(
                time_pattern in col_lower
                for time_pattern in [
                    "date",
                    "time",
                    "m",
                    "q",
                    "y",
                    "month",
                    "quarter",
                    "year",
                ]
            ):
                time_col = col
                break

        if time_col is None:
            return "D"  # Default to daily

        # Analyze date patterns
        sample_values = df[time_col].dropna().head(10).astype(str)

        for value in sample_values:
            # Monthly pattern: YYYYMM or YYYY-MM
            if re.match(r"^\d{6}$", value) or re.match(r"^\d{4}-\d{2}$", value):
                return "M"
            # Quarterly pattern: YYYYQ1, YYYY-Q1
            elif re.match(r"^\d{4}Q\d$", value) or re.match(r"^\d{4}-Q\d$", value):
                return "Q"
            # Yearly pattern: YYYY
            elif re.match(r"^\d{4}$", value):
                return "Y"
            # Daily pattern: YYYYMMDD, YYYY-MM-DD
            elif re.match(r"^\d{8}$", value) or re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                return "D"

        return "D"  # Default to daily


def create_tushare_classifier() -> TushareDataClassifier:
    """
    Factory function to create TushareDataClassifier instance.

    Returns
    -------
    TushareDataClassifier
        Configured classifier ready for use
    """
    return TushareDataClassifier()


# Example usage and test cases
if __name__ == "__main__":
    classifier = TushareDataClassifier()

    # Test case 1: Stock daily data
    stock_data = pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "000002.SZ"],
            "trade_date": ["20240101", "20240101"],
            "close": [10.5, 20.3],
        }
    )

    stock_type = classifier.classify_data(stock_data, "daily")
    print(f"Stock data type: {stock_type}")
    print(f"Stock broadcast config: {classifier.get_broadcast_config(stock_type)}")

    # Test case 2: Macro monthly data
    macro_data = pd.DataFrame({"m": ["202401", "202402"], "cpi": [102.5, 103.1]})

    macro_type = classifier.classify_data(macro_data, "cn_cpi")
    print(f"Macro data type: {macro_type}")
    print(f"Macro broadcast config: {classifier.get_broadcast_config(macro_type)}")

    # Test case 3: Industry data
    industry_data = pd.DataFrame(
        {
            "industry_code": ["110000", "120000"],
            "trade_date": ["20240101", "20240101"],
            "index_value": [1000.5, 2000.3],
        }
    )

    industry_type = classifier.classify_data(industry_data, "sw_daily")
    print(f"Industry data type: {industry_type}")
    print(
        f"Industry broadcast config: {classifier.get_broadcast_config(industry_type)}"
    )
