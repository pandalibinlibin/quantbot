"""
Factor Pipeline Manager (Simplified)

This module implements a simplified factor computation pipeline that follows
the data collector's update mode (full/incremental).

Educational Notes:
- Follows data collector update mode for consistency
- Simplified strategy: no complex data analysis needed
- Clear mapping: full data update → full factor computation
- Clear mapping: incremental data update → incremental factor computation
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path
from enum import Enum

from qlib.data import D
from qlib.log import get_module_logger
from qlib.config import C

from .factor_processor import FactorProcessor
from .factor_storage import FactorStorage
from .factor_full_computation import FactorFullComputationManager
from ..models import Factor, FactorStatus, ComputationStatus
from ..core.db import engine
from sqlmodel import Session, select

logger = get_module_logger("FactorPipeline")


class UpdateMode(str, Enum):
    """Update mode enumeration - follows data collector pattern"""

    FULL = "full"  # Full update (complete recalculation)
    INCREMENTAL = "incremental"  # Incremental update (append new data)


class FactorPipeline:
    """
    Simplified Factor Pipeline Manager

    This class provides a simplified interface that follows the data collector's
    update pattern for consistent data and factor synchronization.

    Educational Notes:
    - Simplified strategy: follows data collector update mode
    - No complex data analysis - clear full/incremental mapping
    - Maintains consistency between data updates and factor computation
    """

    def __init__(self, freq: str = "day", max_workers: int = 4):
        """
        Initialize Simplified Factor Pipeline Manager

        Args:
            freq: Data frequency (day, 1min, etc.)
            max_workers: Maximum number of concurrent workers
        """
        self.freq = freq
        self.max_workers = max_workers

        # Initialize core components
        self.processor = FactorProcessor(freq=freq)
        self.storage = FactorStorage(freq=freq)
        self.computation_manager = FactorFullComputationManager(
            freq=freq, max_workers=max_workers
        )

        logger.info(
            f"FactorPipeline (Simplified) initialized: freq={freq}, max_workers={max_workers}"
        )

    def compute_factor(
        self,
        factor_name: str,
        start_time: Union[str, datetime, date],
        end_time: Union[str, datetime, date],
        update_mode: UpdateMode,
        instruments: Optional[List[str]] = None,
        overwrite: bool = None,
    ) -> Dict[str, Any]:
        """
        Compute a single factor following the specified update mode

        Args:
            factor_name: Name of the factor to compute
            start_time: Start time for computation
            end_time: End time for computation
            update_mode: Update mode (FULL or INCREMENTAL)
            instruments: List of instruments (None for all)
            overwrite: Whether to overwrite existing data (auto-determined if None)

        Returns:
            Dictionary with computation results
        """
        try:
            logger.info(f"Computing factor '{factor_name}' in {update_mode} mode")

            # Auto-determine overwrite based on update mode
            if overwrite is None:
                overwrite = update_mode == UpdateMode.FULL

            result = {
                "factor_name": factor_name,
                "update_mode": update_mode,
                "status": "success",
                "computation_results": None,
                "error": None,
                "duration_seconds": 0,
            }

            pipeline_start = datetime.now()

            # Execute computation based on update mode
            if update_mode == UpdateMode.FULL:
                logger.info(f"Performing FULL computation for '{factor_name}'")
                computation_result = (
                    self.computation_manager.compute_single_factor_full(
                        factor_name, start_time, end_time, instruments, overwrite=True
                    )
                )

            elif update_mode == UpdateMode.INCREMENTAL:
                logger.info(f"Performing INCREMENTAL computation for '{factor_name}'")
                # For incremental, we append new data without overwriting
                computation_result = (
                    self.computation_manager.compute_single_factor_full(
                        factor_name, start_time, end_time, instruments, overwrite=False
                    )
                )

            else:
                raise ValueError(f"Unsupported update mode: {update_mode}")

            result["computation_results"] = computation_result

            if computation_result["status"] != "success":
                result["status"] = "error"
                result["error"] = computation_result.get("error", "Computation failed")

            # Calculate duration
            pipeline_end = datetime.now()
            result["duration_seconds"] = (pipeline_end - pipeline_start).total_seconds()

            logger.info(
                f"✓ Factor computation completed for '{factor_name}': {result['status']}"
            )
            return result

        except Exception as e:
            logger.error(f"Factor computation failed for '{factor_name}': {e}")
            return {
                "factor_name": factor_name,
                "update_mode": update_mode,
                "status": "error",
                "computation_results": None,
                "error": str(e),
                "duration_seconds": 0,
            }

    def compute_batch_factors(
        self,
        factor_names: List[str],
        start_time: Union[str, datetime, date],
        end_time: Union[str, datetime, date],
        update_mode: UpdateMode,
        instruments: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """
        Compute multiple factors following the specified update mode

        Args:
            factor_names: List of factor names to compute
            start_time: Start time for computation
            end_time: End time for computation
            update_mode: Update mode (FULL or INCREMENTAL)
            instruments: List of instruments (None for all)
            parallel: Whether to use parallel processing

        Returns:
            Dictionary with batch computation results
        """
        try:
            logger.info(
                f"Batch computing {len(factor_names)} factors in {update_mode} mode"
            )

            batch_start = datetime.now()
            overwrite = update_mode == UpdateMode.FULL

            batch_result = {
                "total_factors": len(factor_names),
                "update_mode": update_mode,
                "successful": 0,
                "failed": 0,
                "results": {},
                "summary": {
                    "start_time": batch_start,
                    "end_time": None,
                    "duration_seconds": 0,
                },
            }

            # Use the existing batch computation logic
            if parallel and len(factor_names) > 1:
                # Parallel computation
                parallel_results = self.computation_manager.compute_batch_factors_full(
                    factor_names,
                    start_time,
                    end_time,
                    instruments,
                    overwrite,
                    parallel=True,
                )

                # Process parallel results
                for factor_name, result in parallel_results["results"].items():
                    batch_result["results"][factor_name] = {
                        "factor_name": factor_name,
                        "update_mode": update_mode,
                        "status": (
                            "success" if result["status"] == "success" else "error"
                        ),
                        "computation_results": result,
                        "error": result.get("error"),
                        "duration_seconds": result.get("duration_seconds", 0),
                    }

                    if result["status"] == "success":
                        batch_result["successful"] += 1
                    else:
                        batch_result["failed"] += 1

            else:
                # Sequential computation
                for factor_name in factor_names:
                    result = self.compute_factor(
                        factor_name, start_time, end_time, update_mode, instruments
                    )
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
            logger.error(f"Batch factor computation failed: {e}")
            return {
                "total_factors": len(factor_names),
                "update_mode": update_mode,
                "successful": 0,
                "failed": len(factor_names),
                "results": {},
                "error": str(e),
            }

    def sync_with_data_collector(
        self,
        factor_names: List[str],
        data_collector_mode: str,  # "full" or "incremental"
        start_time: Union[str, datetime, date],
        end_time: Union[str, datetime, date],
        instruments: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """
        Synchronize factor computation with data collector update mode

        Args:
            factor_names: List of factor names to compute
            data_collector_mode: Data collector update mode ("full" or "incremental")
            start_time: Start time for computation
            end_time: End time for computation
            instruments: List of instruments (None for all)
            parallel: Whether to use parallel processing

        Returns:
            Dictionary with synchronization results
        """
        try:
            logger.info(
                f"Syncing factors with data collector mode: {data_collector_mode}"
            )

            # Map data collector mode to factor update mode
            if data_collector_mode.lower() == "full":
                update_mode = UpdateMode.FULL
            elif data_collector_mode.lower() == "incremental":
                update_mode = UpdateMode.INCREMENTAL
            else:
                raise ValueError(
                    f"Unsupported data collector mode: {data_collector_mode}"
                )

            # Execute batch computation with mapped mode
            result = self.compute_batch_factors(
                factor_names, start_time, end_time, update_mode, instruments, parallel
            )

            # Add sync information
            result["sync_info"] = {
                "data_collector_mode": data_collector_mode,
                "factor_update_mode": update_mode,
                "sync_strategy": "follow_data_collector",
            }

            logger.info(
                f"✓ Factor sync completed: {data_collector_mode} → {update_mode}"
            )
            return result

        except Exception as e:
            logger.error(f"Factor sync failed: {e}")
            return {
                "total_factors": len(factor_names),
                "successful": 0,
                "failed": len(factor_names),
                "error": str(e),
                "sync_info": {
                    "data_collector_mode": data_collector_mode,
                    "error": str(e),
                },
            }

    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status and statistics

        Returns:
            Pipeline status dictionary
        """
        try:
            # Get storage statistics
            storage_stats = self.storage.get_storage_stats()

            # Get computation progress
            computation_progress = self.computation_manager.get_computation_progress()

            pipeline_status = {
                "pipeline_info": {
                    "type": "simplified",
                    "strategy": "follow_data_collector",
                    "freq": self.freq,
                    "max_workers": self.max_workers,
                    "components": {
                        "processor": "FactorProcessor",
                        "storage": "FactorStorage",
                        "computation_manager": "FactorFullComputationManager",
                    },
                },
                "computation_status": computation_progress,
                "storage_status": storage_stats,
            }

            return pipeline_status

        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {"error": str(e)}

    def cleanup_pipeline(self) -> Dict[str, Any]:
        """
        Cleanup pipeline resources and temporary files

        Returns:
            Cleanup results dictionary
        """
        try:
            logger.info("Starting pipeline cleanup")

            cleanup_results = {"status": "success", "actions_taken": [], "errors": []}

            # Cleanup temporary CSV files
            try:
                csv_temp_dir = self.storage.csv_temp_dir
                if csv_temp_dir.exists():
                    import shutil

                    shutil.rmtree(csv_temp_dir)
                    csv_temp_dir.mkdir(parents=True, exist_ok=True)
                    cleanup_results["actions_taken"].append(
                        "Cleaned temporary CSV directory"
                    )
            except Exception as e:
                cleanup_results["errors"].append(
                    f"Failed to clean CSV temp directory: {e}"
                )

            # Reset stuck computation statuses
            try:
                with Session(engine) as session:
                    statement = select(Factor).where(
                        Factor.computation_status == ComputationStatus.COMPUTING
                    )
                    stuck_factors = session.exec(statement).all()

                    for factor in stuck_factors:
                        factor.computation_status = ComputationStatus.PENDING
                        session.add(factor)

                    session.commit()

                    if stuck_factors:
                        cleanup_results["actions_taken"].append(
                            f"Reset {len(stuck_factors)} stuck computation statuses"
                        )

            except Exception as e:
                cleanup_results["errors"].append(
                    f"Failed to reset computation statuses: {e}"
                )

            if cleanup_results["errors"]:
                cleanup_results["status"] = "partial"

            logger.info(f"Pipeline cleanup completed: {cleanup_results['status']}")
            return cleanup_results

        except Exception as e:
            logger.error(f"Pipeline cleanup failed: {e}")
            return {"status": "error", "actions_taken": [], "errors": [str(e)]}
