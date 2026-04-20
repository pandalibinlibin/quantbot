"""
Data Preprocessing Pipeline for Qlib

This module implements custom data preprocessing processors that integrate with Qlib's
DataHandlerLP framework. The preprocessing pipeline includes:
1. EMA-5 smoothing to reduce noise
2. Relative change rate to calculate surprise values (eliminates scale differences)
3. Cross-sectional Z-Score normalization (using Qlib's built-in CSZScoreNorm)

Processing Flow:
    Raw Data -> EMA-5 Smoothing -> Relative Change Rate -> Cross-Sectional Z-Score -> Replace Original Fields

Usage:
    handler = PreprocessedDataHandler(
        instruments="csi300",
        start_time="2020-01-01",
        end_time="2023-12-31"
    )
    handler.fit_process_data()
    data = handler.fetch(col_set="feature")
"""

import numpy as np
import pandas as pd
from typing import Union, Text, List

from qlib.data.dataset.processor import Processor, get_group_columns
from qlib.data.dataset.handler import DataHandlerLP


# Small epsilon to prevent division by zero
EPS = 1e-8


class EMA5Processor(Processor):
    """
    5-day Exponential Moving Average (EMA) Processor.

    Applies EMA-5 smoothing to reduce noise in the data.

    Formula:
        EMA_t = alpha * Value_t + (1 - alpha) * EMA_{t-1}
        where alpha = 2 / (N + 1) = 2 / 6 ≈ 0.333

    Initialization:
        Day 1: EMA_1 = Value_1 (no data loss)

    Advantages:
        - Unified method for all data types (daily, weekly, monthly)
        - No data loss (first day uses original value)
        - Recent data has higher weight, faster response
    """

    def __init__(self, fields_group: str = "feature", window: int = 5):
        """
        Initialize the EMA processor.

        Parameters
        ----------
        fields_group : str
            The field group to process (default: "feature")
        window : int
            EMA window size (default: 5)
        """
        self.fields_group = fields_group
        self.window = window
        self.alpha = 2.0 / (window + 1)

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply EMA-5 smoothing to the dataframe.

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe with MultiIndex (datetime, instrument)

        Returns
        -------
        pd.DataFrame
            Processed dataframe with EMA-smoothed values
        """
        cols = get_group_columns(df, self.fields_group)

        def apply_ema(group: pd.DataFrame) -> pd.DataFrame:
            """Apply EMA to a single instrument's data"""
            result = group.copy()
            for col in cols:
                if col in result.columns:
                    # Use pandas ewm for efficient EMA calculation
                    # adjust=False means we use the recursive formula
                    result[col] = result[col].ewm(span=self.window, adjust=False).mean()
            return result

        # Apply EMA by instrument (maintaining time series order)
        df[cols] = (
            df[cols].groupby(level="instrument", group_keys=False).apply(apply_ema)
        )

        return df

    def readonly(self) -> bool:
        """This processor modifies data in-place"""
        return False


class RelativeChangeProcessor(Processor):
    """
    Relative Change Rate Processor (Surprise Calculator).

    Calculates surprise values as the relative change rate between current and previous values.
    This eliminates scale differences between stocks with different price levels.

    Formula:
        Surprise_t = (EMA_t - EMA_{t-1}) / (|EMA_{t-1}| + epsilon)

    Example:
        Stock A: price=1000, EMA_t=1000, EMA_{t-1}=800
                 Surprise = (1000-800)/(800+eps) = 0.25 = 25%

        Stock B: price=100, EMA_t=100, EMA_{t-1}=80
                 Surprise = (100-80)/(80+eps) = 0.25 = 25%

        Result: Both stocks have the same Surprise (25%), eliminating scale bias.

    Notes:
        - Day 1 Surprise is NaN (no previous value)
        - Positive values indicate unexpected increase
        - Negative values indicate unexpected decrease
        - Uses relative change rate instead of absolute difference to ensure fair comparison
    """

    def __init__(self, fields_group: str = "feature"):
        """
        Initialize the relative change processor.

        Parameters
        ----------
        fields_group : str
            The field group to process (default: "feature")
        """
        self.fields_group = fields_group

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply relative change rate calculation.

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe with MultiIndex (datetime, instrument)

        Returns
        -------
        pd.DataFrame
            Processed dataframe with relative change values
        """
        cols = get_group_columns(df, self.fields_group)

        def apply_relative_change(group: pd.DataFrame) -> pd.DataFrame:
            """Calculate relative change for a single instrument's data"""
            result = group.copy()
            for col in cols:
                if col in result.columns:
                    prev_values = result[col].shift(1)
                    # Relative change rate: (current - previous) / (|previous| + eps)
                    result[col] = (result[col] - prev_values) / (
                        prev_values.abs() + EPS
                    )
            return result

        # Apply relative change by instrument (maintaining time series order)
        df[cols] = (
            df[cols]
            .groupby(level="instrument", group_keys=False)
            .apply(apply_relative_change)
        )

        return df

    def readonly(self) -> bool:
        """This processor modifies data in-place"""
        return False


class PreprocessedDataHandler(DataHandlerLP):
    """
    Integrated Preprocessing Data Handler.

    This handler implements the complete preprocessing pipeline:
    1. Handle infinite values and NaN
    2. Apply EMA-5 smoothing to reduce noise
    3. Calculate surprise values using relative change rate
    4. Apply cross-sectional Z-Score normalization

    The result is a standardized dataset where all features are:
    - Smoothed to reduce noise
    - Surprise-adjusted to focus on unexpected changes
    - Scale-normalized to eliminate price level bias
    - Cross-sectionally normalized for comparability

    After preprocessing, $close represents the preprocessed close price (not raw price).
    """

    def __init__(
        self,
        instruments: Union[str, List[str]] = "csi300",
        start_time: str = None,
        end_time: str = None,
        **kwargs
    ):
        """
        Initialize the preprocessed data handler.

        Parameters
        ----------
        instruments : str or list
            Universe of instruments to load (default: "csi300")
        start_time : str
            Start date for data loading
        end_time : str
            End date for data loading
        **kwargs
            Additional arguments passed to DataHandlerLP
        """

        # Define data loader configuration
        data_loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": self._get_feature_config(),
            },
        }

        # Define preprocessing pipeline
        infer_processors = [
            # Step 1: Handle infinite values
            {"class": "ProcessInf"},
            # Step 2: Fill NaN values with 0
            {"class": "Fillna"},
            # Step 3: Apply EMA-5 smoothing
            EMA5Processor(fields_group="feature", window=5),
            # Step 4: Calculate relative change rate (Surprise)
            RelativeChangeProcessor(fields_group="feature"),
            # Step 5: Apply cross-sectional Z-Score normalization (Qlib built-in)
            {"class": "CSZScoreNorm", "kwargs": {"fields_group": "feature"}},
        ]

        # Initialize parent class
        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=data_loader,
            infer_processors=infer_processors,
            **kwargs
        )

    def _get_feature_config(self):
        """
        Define the base features to load from Qlib data.

        Returns
        -------
        tuple
            (fields, names) where fields are Qlib expressions and names are feature names
        """
        # Define base OHLCV and derived features
        fields = [
            # Basic OHLCV
            "$close",
            "$volume",
            "$open",
            "$high",
            "$low",
            # Derived features
            "($close-$open)/$open",  # Intraday return
            "$volume/Ref($volume,1)",  # Volume change ratio
            "($high-$low)/$close",  # Daily range normalized by close
        ]

        # Corresponding feature names
        names = [
            "CLOSE",
            "VOLUME",
            "OPEN",
            "HIGH",
            "LOW",
            "INTRADAY_RET",
            "VOL_CHANGE",
            "DAILY_RANGE",
        ]

        return fields, names


def create_preprocessed_handler(
    instruments: Union[str, List[str]] = "csi300",
    start_time: str = "2020-01-01",
    end_time: str = "2023-12-31",
) -> PreprocessedDataHandler:
    """
    Convenience function to create a preprocessed data handler.

    Parameters
    ----------
    instruments : str or list
        Universe of instruments (default: "csi300")
    start_time : str
        Start date (default: "2020-01-01")
    end_time : str
        End date (default: "2023-12-31")

    Returns
    -------
    PreprocessedDataHandler
        Configured handler ready for use
    """
    return PreprocessedDataHandler(
        instruments=instruments, start_time=start_time, end_time=end_time
    )
