"""
Factor Incremental Computation Manager

This module implements intelligent incremental computation logic for factors,
determining what data needs to be computed based on existing data status.

Educational Notes:
- Manages incremental vs full computation decisions
- Tracks data freshness and completeness
- Optimizes computation by avoiding redundant calculations
- Integrates with FactorStorage for data state analysis
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path

from qlib.data import D
from qlib.log import get_module_logger
from qlib.config import C

from .factor_storage import FactorStorage
from ..models import Factor, FactorStatus, ComputationStatus
from ..core.db import engine
from sqlmodel import Session, select

logger = get_module_logger("FactorIncremental")


class FactorIncrementalManager:
    """
    Factor Incremental Computation Manager

    This class determines when and how to perform incremental computation
    for factors based on data freshness and completeness analysis.

    Educational Notes:
    - Analyzes existing factor data to determine computation strategy
    - Supports both incremental and full recomputation
    - Tracks data gaps and freshness
    - Optimizes computation performance
    """

    def __init__(self, freq: str = "day"):
        """
        Initialize Incremental Computation Manager

        Args:
            freq: Data frequency (only 'day' is supported)
        """
        self.freq = freq
        self.storage = FactorStorage(freq=freq)

        logger.info(f"FactorIncrementalManager initialized: freq={freq}")

    def analyze_computation_strategy(
        self,
        factor_name: str,
        target_start_time: Union[str, datetime, date],
        target_end_time: Union[str, datetime, date],
        force_full: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze and determine the optimal computation strategy

        Args:
            factor_name: Name of the factor to analyze
            target_start_time: Desired start time for computation
            target_end_time: Desired end time for computation
            force_full: Force full recomputation regardless of existing data

        Returns:
            Dictionary containing computation strategy and analysis
        """
        try:
            logger.info(f"Analyzing computation strategy for factor '{factor_name}'")

            # Convert to pandas datetime
            target_start = pd.to_datetime(target_start_time)
            target_end = pd.to_datetime(target_end_time)

            strategy = {
                "factor_name": factor_name,
                "target_range": {"start": target_start, "end": target_end},
                "strategy": "full",  # Default to full computation
                "computation_ranges": [],
                "existing_data_info": None,
                "reasons": [],
            }

            if force_full:
                strategy["strategy"] = "full"
                strategy["computation_ranges"] = [
                    {"start": target_start, "end": target_end}
                ]
                strategy["reasons"].append("Force full computation requested")
                return strategy

            # Check if factor data exists
            existing_data = self.storage.load_factor_data(factor_name)

            if existing_data is None or existing_data.empty:
                strategy["strategy"] = "full"
                strategy["computation_ranges"] = [
                    {"start": target_start, "end": target_end}
                ]
                strategy["reasons"].append("No existing data found")
                return strategy

            # Analyze existing data
            data_analysis = self._analyze_existing_data(
                existing_data, target_start, target_end
            )
            strategy["existing_data_info"] = data_analysis

            # Determine computation strategy based on analysis
            if data_analysis["coverage_ratio"] < 0.8:  # Less than 80% coverage
                strategy["strategy"] = "full"
                strategy["computation_ranges"] = [
                    {"start": target_start, "end": target_end}
                ]
                strategy["reasons"].append(
                    f"Low data coverage: {data_analysis['coverage_ratio']:.2%}"
                )

            elif data_analysis["has_gaps"]:
                strategy["strategy"] = "incremental"
                strategy["computation_ranges"] = (
                    data_analysis["gap_ranges"] + data_analysis["extension_ranges"]
                )
                strategy["reasons"].append(
                    "Data gaps detected, incremental computation needed"
                )

            elif data_analysis["needs_extension"]:
                strategy["strategy"] = "incremental"
                strategy["computation_ranges"] = data_analysis["extension_ranges"]
                strategy["reasons"].append("Data extension needed for new time range")

            else:
                strategy["strategy"] = "skip"
                strategy["computation_ranges"] = []
                strategy["reasons"].append("Existing data is complete and up-to-date")

            logger.info(
                f"Strategy for '{factor_name}': {strategy['strategy']} - {', '.join(strategy['reasons'])}"
            )
            return strategy

        except Exception as e:
            logger.error(
                f"Failed to analyze computation strategy for '{factor_name}': {e}"
            )
            # Fallback to full computation
            return {
                "factor_name": factor_name,
                "target_range": {"start": target_start, "end": target_end},
                "strategy": "full",
                "computation_ranges": [{"start": target_start, "end": target_end}],
                "existing_data_info": None,
                "reasons": [f"Analysis failed: {e}"],
            }

    def _analyze_existing_data(
        self,
        existing_data: pd.DataFrame,
        target_start: pd.Timestamp,
        target_end: pd.Timestamp,
    ) -> Dict[str, Any]:
        """
        Analyze existing factor data for completeness and freshness

        Args:
            existing_data: Existing factor DataFrame
            target_start: Target start time
            target_end: Target end time

        Returns:
            Analysis results dictionary
        """
        try:
            # Get time index from existing data
            if hasattr(existing_data.index, "get_level_values"):
                time_index = existing_data.index.get_level_values(0)
            else:
                time_index = existing_data.index

            existing_start = time_index.min()
            existing_end = time_index.max()

            # Generate expected time range based on frequency
            expected_times = self._generate_expected_times(target_start, target_end)
            existing_times = set(time_index.unique())

            # Calculate coverage
            expected_in_range = [
                t for t in expected_times if existing_start <= t <= existing_end
            ]
            covered_times = [t for t in expected_in_range if t in existing_times]
            coverage_ratio = (
                len(covered_times) / len(expected_in_range) if expected_in_range else 0
            )

            # Detect gaps
            missing_times = [t for t in expected_in_range if t not in existing_times]
            gap_ranges = (
                self._group_consecutive_dates(missing_times) if missing_times else []
            )

            # Check if extension is needed
            extension_ranges = []
            if target_start < existing_start:
                extension_ranges.append(
                    {"start": target_start, "end": existing_start - timedelta(days=1)}
                )
            if target_end > existing_end:
                extension_ranges.append(
                    {"start": existing_end + timedelta(days=1), "end": target_end}
                )

            analysis = {
                "existing_range": {"start": existing_start, "end": existing_end},
                "data_shape": existing_data.shape,
                "coverage_ratio": coverage_ratio,
                "has_gaps": len(gap_ranges) > 0,
                "gap_ranges": gap_ranges,
                "needs_extension": len(extension_ranges) > 0,
                "extension_ranges": extension_ranges,
                "missing_dates_count": len(missing_times),
                "total_expected_dates": len(expected_times),
            }

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze existing data: {e}")
            return {
                "existing_range": None,
                "data_shape": (
                    existing_data.shape if existing_data is not None else (0, 0)
                ),
                "coverage_ratio": 0.0,
                "has_gaps": True,
                "gap_ranges": [],
                "needs_extension": True,
                "extension_ranges": [],
                "missing_dates_count": 0,
                "total_expected_dates": 0,
            }

    def _generate_expected_times(
        self, start_time: pd.Timestamp, end_time: pd.Timestamp
    ) -> List[pd.Timestamp]:
        """
        Generate expected time points based on frequency

        Args:
            start_time: Start time
            end_time: End time

        Returns:
            List of expected timestamps
        """
        try:
            # Generate business days (only daily frequency is supported)
            return pd.bdate_range(start=start_time, end=end_time, freq="B").tolist()

        except Exception as e:
            logger.error(f"Failed to generate expected times: {e}")
            return []

    def _group_consecutive_dates(
        self, dates: List[pd.Timestamp]
    ) -> List[Dict[str, pd.Timestamp]]:
        """
        Group consecutive dates into ranges

        Args:
            dates: List of timestamps

        Returns:
            List of date ranges
        """
        if not dates:
            return []

        dates = sorted(dates)
        ranges = []
        current_start = dates[0]
        current_end = dates[0]

        for i in range(1, len(dates)):
            if (dates[i] - current_end).days <= 1:  # Consecutive or same day
                current_end = dates[i]
            else:
                ranges.append({"start": current_start, "end": current_end})
                current_start = dates[i]
                current_end = dates[i]

        ranges.append({"start": current_start, "end": current_end})
        return ranges

    def update_computation_status(
        self,
        factor_name: str,
        status: ComputationStatus,
        computation_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update factor computation status in database

        Args:
            factor_name: Name of the factor
            status: New computation status
            computation_info: Additional computation information

        Returns:
            True if update successful
        """
        try:
            with Session(engine) as session:
                statement = select(Factor).where(Factor.name == factor_name)
                factor = session.exec(statement).first()

                if factor:
                    factor.computation_status = status
                    factor.updated_at = datetime.now()

                    if computation_info:
                        # Store computation info in a JSON field if available
                        # This would require adding a computation_info field to the Factor model
                        pass

                    session.add(factor)
                    session.commit()

                    logger.info(
                        f"Updated computation status for '{factor_name}' to {status}"
                    )
                    return True
                else:
                    logger.warning(f"Factor '{factor_name}' not found in database")
                    return False

        except Exception as e:
            logger.error(
                f"Failed to update computation status for '{factor_name}': {e}"
            )
            return False

    def get_computation_summary(
        self, factor_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get computation status summary for factors

        Args:
            factor_names: List of factor names to analyze (None for all)

        Returns:
            Summary of computation status
        """
        try:
            summary = {"total_factors": 0, "by_status": {}, "factors": []}

            with Session(engine) as session:
                if factor_names:
                    statement = select(Factor).where(Factor.name.in_(factor_names))
                else:
                    statement = select(Factor).where(
                        Factor.status == FactorStatus.ACTIVE
                    )

                factors = session.exec(statement).all()
                summary["total_factors"] = len(factors)

                for factor in factors:
                    # Get storage info
                    metadata = self.storage.get_factor_metadata(factor.name)

                    factor_info = {
                        "name": factor.name,
                        "status": factor.status,
                        "computation_status": factor.computation_status,
                        "has_stored_data": metadata is not None,
                        "last_updated": factor.updated_at,
                        "data_info": metadata,
                    }

                    summary["factors"].append(factor_info)

                    # Count by status
                    status_key = str(factor.computation_status)
                    summary["by_status"][status_key] = (
                        summary["by_status"].get(status_key, 0) + 1
                    )

            return summary

        except Exception as e:
            logger.error(f"Failed to get computation summary: {e}")
            return {"error": str(e)}
