"""
Data Health Service for Qlib data quality checking.

Educational Notes:
- Integrates Qlib's DataHealthChecker logic
- Provides data quality metrics for monitoring
- Checks for missing data, anomalies, and integrity issues
- Based on qlib-source/scripts/check_data_health.py
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import pandas as pd
from loguru import logger

import qlib
from qlib.data import D

from app.config.qlib import qlib_config
from app.core.config import settings


class DataHealthService:
    """
    Service for checking Qlib data health and quality.

    Provides comprehensive data quality checks including:
    - Missing data detection
    - Large step changes (anomalies)
    - Required columns validation
    - Factor column validation
    - Directory naming validation
    """

    def __init__(self):
        """Initialize the data health service with config values."""
        self.large_step_threshold_price = qlib_config.data_quality.get(
            "large_step_threshold_price", 0.5
        )
        self.large_step_threshold_volume = qlib_config.data_quality.get(
            "large_step_threshold_volume", 3.0
        )
        self.missing_data_threshold = qlib_config.data_quality.get(
            "missing_data_threshold", 0
        )

    def check_data_health(
        self, qlib_data_path: Optional[str] = None, freq: str = "day"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive data health check.

        Args:
            qlib_data_path: Path to qlib data directory (default: from settings)
            freq: Data frequency (only 'day' is supported)

        Returns:
            Dictionary containing health metrics and details
        """
        if qlib_data_path is None:
            qlib_data_path = settings.QLIB_DATA_PATH

        qlib_dir = Path(qlib_data_path)

        # Check if data exists
        if not self._has_complete_data_structure(qlib_dir):
            return {
                "data_exists": False,
                "completeness_percentage": 0.0,
                "missing_data_count": 0,
                "missing_data_details": [],
                "anomaly_count": 0,
                "anomalies": [],
                "integrity_checks": {
                    "required_columns": False,
                    "factor_column": False,
                    "directory_case": False,
                },
                "checked_at": datetime.utcnow().isoformat(),
            }

        try:
            # Initialize Qlib
            qlib.init(provider_uri=str(qlib_dir), region=qlib_config.region)

            # Load data for all instruments
            data = self._load_qlib_data(freq)

            if not data:
                logger.warning("No data loaded for health check")
                return self._empty_health_result()

            # Perform checks
            missing_data_result = self._check_missing_data(data)
            anomalies_result = self._check_large_step_changes(data)
            required_columns_result = self._check_required_columns(data)
            factor_column_result = self._check_missing_factor(data)
            directory_case_result = self._check_features_dir_lowercase(qlib_dir)

            # Calculate completeness percentage
            total_instruments = len(data)
            instruments_with_issues = len(missing_data_result)
            completeness_percentage = (
                (total_instruments - instruments_with_issues) / total_instruments * 100
                if total_instruments > 0
                else 100.0
            )

            return {
                "data_exists": True,
                "completeness_percentage": round(completeness_percentage, 2),
                "missing_data_count": len(missing_data_result),
                "missing_data_details": missing_data_result,
                "anomaly_count": len(anomalies_result),
                "anomalies": anomalies_result,
                "integrity_checks": {
                    "required_columns": len(required_columns_result) == 0,
                    "factor_column": len(factor_column_result) == 0,
                    "directory_case": len(directory_case_result) == 0,
                },
                "checked_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to check data health: {e}")
            return self._empty_health_result()

    def _has_complete_data_structure(self, path: Path) -> bool:
        """Check if directory has complete Qlib data structure."""
        if not path.exists():
            return False
        calendars = path / "calendars"
        instruments = path / "instruments"
        features = path / "features"
        return calendars.exists() and instruments.exists() and features.exists()

    def _load_qlib_data(self, freq: str) -> Dict[str, pd.DataFrame]:
        """
        Load Qlib data for all instruments.

        Returns:
            Dictionary mapping instrument names to DataFrames
        """
        data = {}
        try:
            instruments = D.instruments(market="all")
            instrument_list = D.list_instruments(
                instruments=instruments, as_list=True, freq=freq
            )

            required_fields = ["$open", "$close", "$low", "$high", "$volume", "$factor"]

            # Check all instruments
            for instrument in instrument_list:
                try:
                    df = D.features([instrument], required_fields, freq=freq)
                    if df is not None and not df.empty:
                        df.rename(
                            columns={
                                "$open": "open",
                                "$close": "close",
                                "$low": "low",
                                "$high": "high",
                                "$volume": "volume",
                                "$factor": "factor",
                            },
                            inplace=True,
                        )
                        data[instrument] = df
                except Exception as e:
                    logger.warning(f"Failed to load data for {instrument}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to load instruments: {e}")

        return data

    def _check_missing_data(
        self, data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """Check for missing data in OHLCV columns (excluding factor)."""
        result = []
        for instrument, df in data.items():
            # Only check OHLCV columns, not factor (factor is checked separately)
            ohlcv_columns = ["open", "high", "low", "close", "volume"]
            missing_counts = df[ohlcv_columns].isnull().sum()

            # Only report if there are missing values in OHLCV columns
            if missing_counts.sum() > self.missing_data_threshold:
                result.append(
                    {
                        "instrument": instrument,
                        "open": int(missing_counts.get("open", 0)),
                        "high": int(missing_counts.get("high", 0)),
                        "low": int(missing_counts.get("low", 0)),
                        "close": int(missing_counts.get("close", 0)),
                        "volume": int(missing_counts.get("volume", 0)),
                    }
                )
        return result

    def _check_large_step_changes(
        self, data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """Check for large step changes (anomalies) in price columns only."""
        result = []
        for instrument, df in data.items():
            # Only check price columns (OHLC), not volume
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    # Calculate percentage change, replace inf with 0
                    pct_change = df[col].pct_change().abs()
                    pct_change = pct_change.replace([float("inf"), float("-inf")], 0)
                    threshold = self.large_step_threshold_price

                    if pct_change.max() > threshold:
                        large_steps = pct_change[pct_change > threshold]
                        if not large_steps.empty:
                            # Get first occurrence
                            first_idx = large_steps.index[0]
                            date_str = (
                                first_idx[1].strftime("%Y-%m-%d")
                                if isinstance(first_idx, tuple)
                                else str(first_idx)
                            )
                            result.append(
                                {
                                    "instrument": instrument,
                                    "column": col,
                                    "date": date_str,
                                    "pct_change": round(float(pct_change.max()), 4),
                                }
                            )
        return result

    def _check_required_columns(
        self, data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """Check if required OHLCV columns exist."""
        required_columns = ["open", "high", "low", "close", "volume"]
        result = []
        for instrument, df in data.items():
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                result.append(
                    {"instrument": instrument, "missing_columns": missing_cols}
                )
        return result

    def _check_missing_factor(
        self, data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """Check if factor column exists and has data."""
        result = []
        for instrument, df in data.items():
            # Skip index instruments
            if any(idx in instrument for idx in ["000300", "000903", "000905"]):
                continue

            if "factor" not in df.columns:
                result.append(
                    {
                        "instrument": instrument,
                        "missing_factor_col": True,
                        "missing_factor_data": False,
                    }
                )
            elif df["factor"].isnull().all():
                result.append(
                    {
                        "instrument": instrument,
                        "missing_factor_col": False,
                        "missing_factor_data": True,
                    }
                )
        return result

    def _check_features_dir_lowercase(self, qlib_dir: Path) -> List[str]:
        """Check if all feature directories are lowercase."""
        features_dir = qlib_dir / "features"
        if not features_dir.exists():
            return []

        bad_dirs = []
        for name in os.listdir(features_dir):
            full_path = features_dir / name
            if full_path.is_dir() and name != name.lower():
                bad_dirs.append(name)

        return bad_dirs

    def _empty_health_result(self) -> Dict[str, Any]:
        """Return empty health result when no data available."""
        return {
            "data_exists": False,
            "completeness_percentage": 0.0,
            "missing_data_count": 0,
            "missing_data_details": [],
            "anomaly_count": 0,
            "anomalies": [],
            "integrity_checks": {
                "required_columns": False,
                "factor_column": False,
                "directory_case": False,
            },
            "checked_at": datetime.utcnow().isoformat(),
        }


# Singleton instance
_data_health_service: Optional[DataHealthService] = None


def get_data_health_service() -> DataHealthService:
    """Get or create the data health service singleton."""
    global _data_health_service
    if _data_health_service is None:
        _data_health_service = DataHealthService()
    return _data_health_service
