"""
Factor Processor for computing and managing factor data

This module implements the core factor computation logic that integrates
with Qlib's data processing pipeline.

Educational Notes:
- FactorProcessor handles the computation of custom factors
- Integrates with Qlib's expression system for factor calculation
- Manages data flow from raw data to computed factor values
- Supports both batch and incremental factor computation
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date
import os
from pathlib import Path

from qlib.data import D
from qlib.utils.time import Freq
from qlib.log import get_module_logger

from ..models import Factor, FactorStatus
from ..core.db import engine
from sqlmodel import Session, select

logger = get_module_logger("FactorProcessor")


class FactorProcessor:
    """
    Factor Processor for computing custom factors

    This class handles the computation of factors based on expressions
    and manages the data processing pipeline for factor calculation.

    Educational Notes:
    - Uses Qlib's D.features() for data loading and computation
    - Supports both single factor and batch factor computation
    - Handles data validation and error management
    - Integrates with database for factor metadata management
    """

    def __init__(
        self, data_dir: Optional[str] = None, freq: str = "day", market: str = "all"
    ):
        """
        Initialize Factor Processor

        Args:
            data_dir: Directory for storing computed factor data
            freq: Data frequency (only 'day' is supported)
            market: Market identifier (all, etf_universe, etc.)
        """
        self.data_dir = Path(data_dir) if data_dir else Path("./factor_data")
        self.freq = freq
        self.market = market

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"FactorProcessor initialized: data_dir={self.data_dir}, freq={freq}, market={market}"
        )

    def load_factors_from_db(
        self, status: FactorStatus = FactorStatus.ACTIVE
    ) -> List[Dict[str, Any]]:
        """
        Load factor definitions from database

        Args:
            status: Filter factors by status

        Returns:
            List of factor dictionaries with metadata
        """
        try:
            with Session(engine) as session:
                statement = select(Factor).where(Factor.status == status)
                factors = session.exec(statement).all()

                factor_list = []
                for factor in factors:
                    factor_dict = {
                        "id": str(factor.id),
                        "name": factor.name,
                        "expression": factor.expression,
                        "description": factor.description,
                        "status": factor.status,
                        "computation_status": factor.computation_status,
                        "created_at": factor.created_at,
                        "updated_at": factor.updated_at,
                    }
                    factor_list.append(factor_dict)

                logger.info(f"Loaded {len(factor_list)} factors from database")
                return factor_list

        except Exception as e:
            logger.error(f"Failed to load factors from database: {e}")
            return []

    def compute_single_factor(
        self,
        factor_name: str,
        expression: str,
        instruments: Union[str, List[str]] = None,
        start_time: Union[str, datetime, date] = None,
        end_time: Union[str, datetime, date] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Compute a single factor using Qlib's expression system

        Args:
            factor_name: Name of the factor
            expression: Factor expression in Qlib format
            instruments: Stock instruments to compute
            start_time: Start time for computation
            end_time: End time for computation

        Returns:
            DataFrame with computed factor values
        """
        try:
            logger.info(
                f"Computing factor '{factor_name}' with expression: {expression}"
            )

            # Ensure Qlib is initialized before computing factors
            from app.services.qlib_init_service import get_qlib_init_service

            qlib_service = get_qlib_init_service()
            qlib_service.initialize()

            # Use default parameters if not provided
            start_time = start_time or "2020-01-01"
            end_time = end_time or "2023-12-31"

            # Get instruments list if not provided
            # Note: Only day-level data is supported in this stock selection system
            if instruments is None:
                # Read instruments directly from file to bypass Qlib's case-sensitive matching issue
                from app.core.config import settings

                qlib_data_dir = settings.QLIB_DATA_PATH
                instruments_file = Path(qlib_data_dir) / "instruments" / "all.txt"
                logger.info(
                    f"Looking for instruments file at: {instruments_file} (freq={self.freq})"
                )

                if instruments_file.exists():
                    with open(instruments_file, "r") as f:
                        # Extract instrument codes from the first column, convert to lowercase to match features directories
                        instruments = [
                            line.strip().split("\t")[0].lower()
                            for line in f.readlines()
                            if line.strip()
                        ]
                    logger.info(
                        f"Loaded {len(instruments)} instruments directly from file (converted to lowercase)"
                    )
                else:
                    logger.warning(
                        f"Instruments file not found at {instruments_file}, falling back to D.instruments"
                    )
                    instruments = D.instruments(market="all")
            elif isinstance(instruments, str):
                # If instruments is a string (like market name), get instruments for that market
                if instruments in ["all", "etf_universe"]:
                    # Load instruments from file (day-level data only)
                    from app.core.config import settings

                    qlib_data_dir = settings.QLIB_DATA_PATH
                    instruments_file = Path(qlib_data_dir) / "instruments" / "all.txt"
                    if instruments_file.exists():
                        with open(instruments_file, "r") as f:
                            instruments = [
                                line.strip().split("\t")[0].lower()
                                for line in f.readlines()
                                if line.strip()
                            ]
                        logger.info(
                            f"Loaded {len(instruments)} instruments for market (converted to lowercase)"
                        )
                    else:
                        instruments = D.instruments(market=instruments)
                else:
                    # Assume it's a single instrument code, convert to lowercase
                    instruments = [instruments.lower()]

            # Log parameters before D.features call
            logger.info(f"=== D.features call parameters ===")
            logger.info(
                f"instruments: {instruments[:5] if len(instruments) > 5 else instruments} (total: {len(instruments)})"
            )
            logger.info(f"fields: {[expression]}")
            logger.info(f"start_time: {start_time}")
            logger.info(f"end_time: {end_time}")
            logger.info(f"freq: {self.freq}")

            # Use Qlib's D.features to compute the factor
            try:
                factor_data = D.features(
                    instruments=instruments,
                    fields=[expression],
                    start_time=start_time,
                    end_time=end_time,
                    freq=self.freq,
                )

                # Log results after D.features call
                logger.info(f"=== D.features call results ===")
                logger.info(f"factor_data type: {type(factor_data)}")
                logger.info(
                    f"factor_data shape: {factor_data.shape if hasattr(factor_data, 'shape') else 'No shape attribute'}"
                )
                logger.info(
                    f"factor_data empty: {factor_data.empty if hasattr(factor_data, 'empty') else 'No empty attribute'}"
                )
                logger.info(
                    f"factor_data columns: {list(factor_data.columns) if hasattr(factor_data, 'columns') else 'No columns attribute'}"
                )
                if hasattr(factor_data, "head"):
                    logger.info(f"factor_data head:\n{factor_data.head()}")
                else:
                    logger.info(f"factor_data content: {factor_data}")

            except Exception as e:
                logger.error(f"D.features call failed: {str(e)}")
                logger.error(f"Exception type: {type(e)}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

            # Rename the column to factor name
            if not factor_data.empty and len(factor_data.columns) > 0:
                factor_data.columns = [factor_name]
                logger.info(
                    f"Successfully computed factor '{factor_name}': shape={factor_data.shape}"
                )
                return factor_data
            else:
                logger.warning(f"No data returned for factor '{factor_name}'")
                return None

        except Exception as e:
            logger.error(f"Failed to compute factor '{factor_name}': {e}")
            return None

    def compute_batch_factors(
        self,
        factors: List[Dict[str, Any]],
        instruments: Union[str, List[str]] = None,
        start_time: Union[str, datetime, date] = None,
        end_time: Union[str, datetime, date] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Compute multiple factors in batch

        Args:
            factors: List of factor dictionaries
            instruments: Stock instruments to compute
            start_time: Start time for computation
            end_time: End time for computation

        Returns:
            Dictionary mapping factor names to computed DataFrames
        """
        results = {}

        logger.info(f"Starting batch computation for {len(factors)} factors")

        for factor in factors:
            factor_name = factor["name"]
            expression = factor["expression"]

            try:
                result = self.compute_single_factor(
                    factor_name=factor_name,
                    expression=expression,
                    instruments=instruments,
                    start_time=start_time,
                    end_time=end_time,
                )

                if result is not None:
                    results[factor_name] = result
                    logger.info(f"✓ Factor '{factor_name}' computed successfully")
                else:
                    logger.warning(f"✗ Factor '{factor_name}' computation failed")

            except Exception as e:
                logger.error(f"✗ Error computing factor '{factor_name}': {e}")
                continue

        logger.info(
            f"Batch computation completed: {len(results)}/{len(factors)} factors successful"
        )
        return results

    def validate_factor_data(self, factor_data: pd.DataFrame, factor_name: str) -> bool:
        """
        Validate computed factor data

        Args:
            factor_data: Computed factor DataFrame
            factor_name: Name of the factor

        Returns:
            True if validation passes
        """
        try:
            # Check if data is empty
            if factor_data.empty:
                logger.warning(f"Factor '{factor_name}' data is empty")
                return False

            # Check for all NaN values
            if factor_data.isna().all().all():
                logger.warning(f"Factor '{factor_name}' contains only NaN values")
                return False

            # Check data types
            if not factor_data.select_dtypes(include=[np.number]).shape[1] > 0:
                logger.warning(f"Factor '{factor_name}' does not contain numeric data")
                return False

            # Log basic statistics
            non_null_count = factor_data.count().sum()
            total_count = factor_data.size
            coverage = non_null_count / total_count if total_count > 0 else 0

            logger.info(
                f"Factor '{factor_name}' validation: coverage={coverage:.2%}, shape={factor_data.shape}"
            )

            return True

        except Exception as e:
            logger.error(f"Error validating factor '{factor_name}': {e}")
            return False
