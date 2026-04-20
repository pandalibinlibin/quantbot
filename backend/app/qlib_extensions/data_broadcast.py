"""
Data Broadcast Utilities for Qlib

This module provides utilities for broadcasting data across different dimensions:
1. Time broadcast: Convert non-daily data (monthly, weekly, quarterly) to daily frequency
2. Stock broadcast: Replicate macro data to all stocks

These utilities are used when importing new data (e.g., M2, CPI) from Tushare
before storing it in Qlib data directory.

Usage:
    from app.qlib_extensions.data_broadcast import time_broadcast, stock_broadcast

    # Convert monthly M2 data to daily
    daily_m2 = time_broadcast(monthly_m2_df, freq="M", calendar=trading_calendar)

    # Broadcast macro data to all stocks
    all_stocks_m2 = stock_broadcast(daily_m2, instruments=["000001.SZ", "000002.SZ", ...])
"""

import pandas as pd
import numpy as np
from typing import List, Union, Optional


def time_broadcast(
    df: pd.DataFrame, freq: str, calendar: pd.DatetimeIndex, method: str = "ffill"
) -> pd.DataFrame:
    """
    Broadcast non-daily data to daily frequency using forward fill.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe with DatetimeIndex
        Columns are the data fields to broadcast
    freq : str
        Original data frequency:
        - "M" or "monthly": Monthly data
        - "W" or "weekly": Weekly data
        - "Q" or "quarterly": Quarterly data
    calendar : pd.DatetimeIndex
        Trading calendar (list of trading days)
    method : str
        Fill method (default: "ffill" - forward fill)

    Returns
    -------
    pd.DataFrame
        Daily frequency dataframe aligned to trading calendar

    Example
    -------
    >>> monthly_m2 = pd.DataFrame({
    ...     "m2_yoy": [8.5, 8.7, 8.9]
    ... }, index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]))
    >>>
    >>> trading_days = pd.date_range("2024-01-01", "2024-03-31", freq="B")
    >>> daily_m2 = time_broadcast(monthly_m2, freq="M", calendar=trading_days)
    >>> # Result: daily_m2 has values for each trading day, forward filled
    """
    if df.empty:
        return df

    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Reindex directly to trading calendar and forward fill
    # This avoids the FutureWarning from concat with empty/all-NA entries
    result = df.reindex(df.index.union(calendar)).sort_index()

    # Forward fill to propagate values
    if method == "ffill":
        result = result.ffill()
    elif method == "bfill":
        result = result.bfill()

    # Keep only trading days
    result = result.reindex(calendar)

    return result


def stock_broadcast(df: pd.DataFrame, instruments: List[str]) -> pd.DataFrame:
    """
    Broadcast data to all stocks (for macro data that applies to all stocks).

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe with DatetimeIndex
        Columns are the data fields to broadcast
    instruments : List[str]
        List of instrument codes to broadcast to

    Returns
    -------
    pd.DataFrame
        MultiIndex dataframe with (datetime, instrument) index
        Same values replicated for all instruments on each date

    Example
    -------
    >>> daily_m2 = pd.DataFrame({
    ...     "m2_yoy": [8.5, 8.5, 8.7]
    ... }, index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
    >>>
    >>> instruments = ["000001.SZ", "000002.SZ", "600000.SH"]
    >>> all_stocks_m2 = stock_broadcast(daily_m2, instruments)
    >>> # Result: MultiIndex dataframe with m2_yoy for each stock on each day
    """
    if df.empty or not instruments:
        return df

    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Create MultiIndex
    dates = df.index
    multi_index = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )

    # Create result dataframe
    result = pd.DataFrame(index=multi_index, columns=df.columns)

    # Fill values: for each date, all instruments get the same value
    for col in df.columns:
        for date in dates:
            value = df.loc[date, col]
            result.loc[(date, slice(None)), col] = value

    return result


def broadcast_macro_data(
    df: pd.DataFrame, freq: str, calendar: pd.DatetimeIndex, instruments: List[str]
) -> pd.DataFrame:
    """
    Complete broadcast pipeline for macro data.

    Combines time_broadcast and stock_broadcast:
    1. First broadcast to daily frequency
    2. Then broadcast to all stocks

    Parameters
    ----------
    df : pd.DataFrame
        Input macro data with DatetimeIndex
    freq : str
        Original data frequency ("M", "W", "Q")
    calendar : pd.DatetimeIndex
        Trading calendar
    instruments : List[str]
        List of instrument codes

    Returns
    -------
    pd.DataFrame
        MultiIndex dataframe ready for Qlib storage

    Example
    -------
    >>> # Monthly M2 data
    >>> monthly_m2 = pd.DataFrame({
    ...     "m2_yoy": [8.5, 8.7, 8.9]
    ... }, index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]))
    >>>
    >>> # Broadcast to all stocks and all trading days
    >>> result = broadcast_macro_data(
    ...     monthly_m2,
    ...     freq="M",
    ...     calendar=trading_calendar,
    ...     instruments=all_stock_codes
    ... )
    """
    # Step 1: Time broadcast (non-daily -> daily)
    daily_df = time_broadcast(df, freq=freq, calendar=calendar)

    # Step 2: Stock broadcast (single series -> all stocks)
    result = stock_broadcast(daily_df, instruments=instruments)

    return result


def broadcast_industry_data(
    df: pd.DataFrame,
    industry_mapping: dict,
    calendar: pd.DatetimeIndex,
    freq: str = "D",
) -> pd.DataFrame:
    """
    Broadcast industry-level data to stocks based on industry mapping.

    Parameters
    ----------
    df : pd.DataFrame
        Input industry data with DatetimeIndex
        Columns should be industry codes
    industry_mapping : dict
        Mapping from instrument to industry code
        e.g., {"000001.SZ": "bank", "600000.SH": "bank", "000002.SZ": "real_estate"}
    calendar : pd.DatetimeIndex
        Trading calendar
    freq : str
        Original data frequency (default: "D" for daily)

    Returns
    -------
    pd.DataFrame
        MultiIndex dataframe with (datetime, instrument) index
        Each stock gets the value of its industry

    Example
    -------
    >>> # Industry sentiment data
    >>> industry_data = pd.DataFrame({
    ...     "bank": [0.8, 0.7, 0.9],
    ...     "real_estate": [0.3, 0.4, 0.2]
    ... }, index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
    >>>
    >>> mapping = {"000001.SZ": "bank", "000002.SZ": "real_estate"}
    >>> result = broadcast_industry_data(industry_data, mapping, calendar)
    """
    if df.empty or not industry_mapping:
        return df

    # Time broadcast if needed
    if freq != "D":
        df = time_broadcast(df, freq=freq, calendar=calendar)

    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Get unique instruments and dates
    instruments = list(industry_mapping.keys())
    dates = df.index

    # Create MultiIndex
    multi_index = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )

    # Create result with a single column for the industry value
    result = pd.DataFrame(index=multi_index, columns=["industry_value"])

    # Fill values based on industry mapping
    for instrument, industry in industry_mapping.items():
        if industry in df.columns:
            for date in dates:
                if date in df.index:
                    value = df.loc[date, industry]
                    result.loc[(date, instrument), "industry_value"] = value

    return result
