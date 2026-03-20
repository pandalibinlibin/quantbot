"""
Factor Full Computation Manager

This module implements full computation logic for factors,
handling complete recalculation of factor data from scratch.

Educational Notes:
- Manages complete factor recalculation
- Handles large-scale data processing
- Integrates with FactorProcessor and FactorStorage
- Provides progress tracking and error recovery
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from qlib.data import D
from qlib.log import get_module_logger
from qlib.config import C

from .factor_processor import FactorProcessor
from .factor_storage import FactorStorage
from .factor_incremental import FactorIncrementalManager
from ..models import Factor, FactorStatus, ComputationStatus
from ..core.db import engine
from sqlmodel import Session, select

logger = get_module_logger("FactorFullComputation")


class FactorFullComputationManager:
    """
    Factor Full Computation Manager

    This class handles complete recalculation of factor data,
    including batch processing, progress tracking, and error recovery.

    Educational Notes:
    - Manages full factor computation workflow
    - Supports batch processing for multiple factors
    - Provides detailed progress tracking
    - Handles computation errors gracefully
    """

    def __init__(self, freq: str = "day", max_workers: int = 1):
        """
        Initialize Full Computation Manager

        Args:
            freq: Data frequency (day, 1min, etc.)
            max_workers: Maximum number of concurrent workers (set to 1 to avoid Redis lock conflicts)
        """
        self.freq = freq
        # Force sequential processing to avoid Qlib Redis lock conflicts
        self.max_workers = 1

        # Initialize components
        self.processor = FactorProcessor(freq=freq)
        self.storage = FactorStorage(freq=freq)
        self.incremental_manager = FactorIncrementalManager(freq=freq)

        logger.info(
            f"FactorFullComputationManager initialized: freq={freq}, max_workers={max_workers}"
        )

    def compute_single_factor_full(
        self,
        factor_name: str,
        start_time: Union[str, datetime, date],
        end_time: Union[str, datetime, date],
        instruments: Optional[List[str]] = None,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform full computation for a single factor

        Args:
            factor_name: Name of the factor to compute
            start_time: Start time for computation
            end_time: End time for computation
            instruments: List of instruments (None for all)
            overwrite: Whether to overwrite existing data

        Returns:
            Dictionary with computation results
        """
        try:
            logger.info(f"=== FULL COMPUTATION START for '{factor_name}' ===")
            logger.info(f"freq: {self.freq}")
            logger.info(f"start_time: {start_time}, end_time: {end_time}")
            logger.info(f"instruments: {instruments}")
            logger.info(f"overwrite: {overwrite}")

            # Update status to computing
            self.incremental_manager.update_computation_status(
                factor_name, ComputationStatus.COMPUTING
            )

            start_timestamp = pd.to_datetime(start_time)
            end_timestamp = pd.to_datetime(end_time)

            result = {
                "factor_name": factor_name,
                "status": "success",
                "computation_type": "full",
                "time_range": {"start": start_timestamp, "end": end_timestamp},
                "data_info": None,
                "error": None,
                "duration_seconds": 0,
            }

            computation_start = datetime.now()

            # Step 1: Load factor definition from database
            logger.info(f"Step 1: Loading factor config for '{factor_name}'")
            factor_config = self._load_factor_config(factor_name)
            if not factor_config:
                logger.error(f"Factor '{factor_name}' not found in database")
                result["status"] = "error"
                result["error"] = f"Factor '{factor_name}' not found in database"
                return result
            logger.info(
                f"Factor config loaded: expression={factor_config.get('expression', 'N/A')}"
            )

            # Step 2: Compute factor data
            logger.info(f"Step 2: Computing factor data for '{factor_name}'")
            logger.info(
                f"Calling processor.compute_single_factor with freq={self.processor.freq}"
            )

            factor_data = self.processor.compute_single_factor(
                factor_name=factor_name,
                expression=factor_config["expression"],
                start_time=start_time,
                end_time=end_time,
                instruments=instruments,
            )

            logger.info(f"Step 2 result: factor_data is None={factor_data is None}")
            if factor_data is not None:
                logger.info(
                    f"Step 2 result: factor_data.empty={factor_data.empty}, shape={factor_data.shape}"
                )

            if factor_data is None or factor_data.empty:
                logger.error(
                    f"Factor computation returned empty data for '{factor_name}'"
                )
                result["status"] = "error"
                result["error"] = "Factor computation returned empty data"
                self.incremental_manager.update_computation_status(
                    factor_name, ComputationStatus.FAILED
                )
                return result

            # Step 3: Validate computed data
            validation_result = self.processor.validate_factor_data(
                factor_data, factor_name
            )
            if not validation_result:
                result["status"] = "error"
                result["error"] = "Data validation failed"
                self.incremental_manager.update_computation_status(
                    factor_name, ComputationStatus.FAILED
                )
                return result

            # Step 4: Save computed data
            logger.info(f"Saving computed data for factor '{factor_name}'")
            save_success = self.storage.save_factor_data(
                factor_name=factor_name,
                factor_data=factor_data,
                instruments=instruments,
                overwrite=overwrite,
            )

            if not save_success:
                result["status"] = "error"
                result["error"] = "Failed to save computed factor data"
                self.incremental_manager.update_computation_status(
                    factor_name, ComputationStatus.FAILED
                )
                return result

            # Step 5: Update computation status
            computation_end = datetime.now()
            duration = (computation_end - computation_start).total_seconds()

            result["duration_seconds"] = duration
            result["data_info"] = {
                "shape": factor_data.shape,
                "columns": list(factor_data.columns),
                "non_null_ratio": float(factor_data.count().sum() / factor_data.size),
                "date_range": {
                    "start": (
                        factor_data.index.get_level_values(0).min()
                        if hasattr(factor_data.index, "get_level_values")
                        else factor_data.index.min()
                    ),
                    "end": (
                        factor_data.index.get_level_values(0).max()
                        if hasattr(factor_data.index, "get_level_values")
                        else factor_data.index.max()
                    ),
                },
            }

            self.incremental_manager.update_computation_status(
                factor_name, ComputationStatus.COMPLETED
            )

            logger.info(
                f"✓ Full computation completed for '{factor_name}' in {duration:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"Full computation failed for factor '{factor_name}': {e}")

            self.incremental_manager.update_computation_status(
                factor_name, ComputationStatus.FAILED
            )

            result["status"] = "error"
            result["error"] = str(e)
            return result

    def compute_batch_factors_full(
        self,
        factor_names: List[str],
        start_time: Union[str, datetime, date],
        end_time: Union[str, datetime, date],
        instruments: Optional[List[str]] = None,
        overwrite: bool = True,
        parallel: bool = False,
    ) -> Dict[str, Any]:
        """
        Perform full computation for multiple factors

        Args:
            factor_names: List of factor names to compute
            start_time: Start time for computation
            end_time: End time for computation
            instruments: List of instruments (None for all)
            overwrite: Whether to overwrite existing data
            parallel: Whether to use parallel processing

        Returns:
            Dictionary with batch computation results
        """
        try:
            logger.info(
                f"Starting batch full computation for {len(factor_names)} factors"
            )

            batch_start = datetime.now()

            batch_result = {
                "total_factors": len(factor_names),
                "successful": 0,
                "failed": 0,
                "results": {},
                "summary": {
                    "start_time": batch_start,
                    "end_time": None,
                    "duration_seconds": 0,
                },
            }

            if parallel and len(factor_names) > 1:
                # Parallel computation
                results = self._compute_batch_parallel(
                    factor_names, start_time, end_time, instruments, overwrite
                )
            else:
                # Sequential computation
                results = self._compute_batch_sequential(
                    factor_names, start_time, end_time, instruments, overwrite
                )

            # Process results
            for factor_name, result in results.items():
                batch_result["results"][factor_name] = result
                if result["status"] == "success":
                    batch_result["successful"] += 1
                else:
                    batch_result["failed"] += 1

            batch_end = datetime.now()
            batch_duration = (batch_end - batch_start).total_seconds()

            batch_result["summary"]["end_time"] = batch_end
            batch_result["summary"]["duration_seconds"] = batch_duration

            logger.info(
                f"✓ Batch computation completed: {batch_result['successful']} successful, "
                f"{batch_result['failed']} failed in {batch_duration:.2f}s"
            )

            return batch_result

        except Exception as e:
            logger.error(f"Batch full computation failed: {e}")
            return {
                "total_factors": len(factor_names),
                "successful": 0,
                "failed": len(factor_names),
                "results": {},
                "error": str(e),
            }

    def _compute_batch_parallel(
        self,
        factor_names: List[str],
        start_time: Union[str, datetime, date],
        end_time: Union[str, datetime, date],
        instruments: Optional[List[str]],
        overwrite: bool,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute factors in parallel using ThreadPoolExecutor

        Args:
            factor_names: List of factor names
            start_time: Start time for computation
            end_time: End time for computation
            instruments: List of instruments
            overwrite: Whether to overwrite existing data

        Returns:
            Dictionary mapping factor names to results
        """
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all computation tasks
            future_to_factor = {
                executor.submit(
                    self.compute_single_factor_full,
                    factor_name,
                    start_time,
                    end_time,
                    instruments,
                    overwrite,
                ): factor_name
                for factor_name in factor_names
            }

            # Collect results as they complete
            for future in as_completed(future_to_factor):
                factor_name = future_to_factor[future]
                try:
                    result = future.result()
                    results[factor_name] = result
                    logger.info(
                        f"Completed computation for factor '{factor_name}': {result['status']}"
                    )
                except Exception as e:
                    logger.error(f"Computation failed for factor '{factor_name}': {e}")
                    results[factor_name] = {
                        "factor_name": factor_name,
                        "status": "error",
                        "error": str(e),
                    }

        return results

    def _compute_batch_sequential(
        self,
        factor_names: List[str],
        start_time: Union[str, datetime, date],
        end_time: Union[str, datetime, date],
        instruments: Optional[List[str]],
        overwrite: bool,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute factors sequentially

        Args:
            factor_names: List of factor names
            start_time: Start time for computation
            end_time: End time for computation
            instruments: List of instruments
            overwrite: Whether to overwrite existing data

        Returns:
            Dictionary mapping factor names to results
        """
        results = {}

        for i, factor_name in enumerate(factor_names, 1):
            logger.info(f"Computing factor {i}/{len(factor_names)}: '{factor_name}'")

            result = self.compute_single_factor_full(
                factor_name, start_time, end_time, instruments, overwrite
            )

            results[factor_name] = result
            logger.info(f"Factor '{factor_name}' computation: {result['status']}")

        return results

    def _load_factor_config(self, factor_name: str) -> Optional[Dict[str, Any]]:
        """
        Load factor configuration from database

        Args:
            factor_name: Name of the factor

        Returns:
            Factor configuration dictionary or None
        """
        try:
            with Session(engine) as session:
                statement = select(Factor).where(
                    Factor.name == factor_name, Factor.status == FactorStatus.ACTIVE
                )
                factor = session.exec(statement).first()

                if factor:
                    return {
                        "name": factor.name,
                        "expression": factor.expression,
                        "description": factor.description,
                        "freq": self.freq,
                    }
                else:
                    logger.warning(f"Factor '{factor_name}' not found or inactive")
                    return None

        except Exception as e:
            logger.error(f"Failed to load factor config for '{factor_name}': {e}")
            return None

    def get_computation_progress(
        self, factor_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get current computation progress for factors

        Args:
            factor_names: List of factor names to check (None for all)

        Returns:
            Progress information dictionary
        """
        try:
            return self.incremental_manager.get_computation_summary(factor_names)
        except Exception as e:
            logger.error(f"Failed to get computation progress: {e}")
            return {"error": str(e)}

    def cancel_computation(self, factor_name: str) -> bool:
        """
        Cancel ongoing computation for a factor

        Args:
            factor_name: Name of the factor

        Returns:
            True if cancellation successful
        """
        try:
            # Update status to cancelled
            success = self.incremental_manager.update_computation_status(
                factor_name, ComputationStatus.PENDING
            )

            if success:
                logger.info(f"Computation cancelled for factor '{factor_name}'")

            return success

        except Exception as e:
            logger.error(f"Failed to cancel computation for '{factor_name}': {e}")
            return False
