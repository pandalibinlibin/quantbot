"""
Pipeline stage implementations.

Educational Notes:
- Implement the three core stages: collect, normalize, dump
- Integrates with existing services and collectors
- Follows Qlib's standard data processing workflow
"""

import logging
from mailbox import Message
from pathlib import Path
from typing import List
from app.models import PipelineStage, PipelineStageResult, PipelineWorkspace

logger = logging.getLogger(__name__)


class CollectStage:
    """
    Data collection stage following Qlib Yahoo collector pattern.

    Educational Notes:
    - Follows Qlib's proven Yahoo collector implementation
    - Simple and direct approach without over-engineering
    - Supports multiple collectors through direct instantiation
    """

    @staticmethod
    def execute(
        workspace: PipelineWorkspace,
        source: str,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str = "1d",
    ) -> PipelineStageResult:
        """Execute data collection stage"""
        try:
            logger.info(
                f"Starting collection stage: {len(symbols)} symbols from {source}"
            )

            # Simple collector selection (following Qlib's direct approach)
            if source.lower() == "yahoo":
                from app.services.data_collectors.yahoo_collector import (
                    YahooDataCollector,
                )

                collector = YahooDataCollector(
                    save_dir=str(workspace.temp_csv_dir),
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    max_workers=1,
                )
            else:
                return PipelineStageResult(
                    stage=PipelineStage.COLLECT,
                    success=False,
                    message=f"Unsupported data source: {source}",
                    error=f"Currently only 'yahoo' is supported",
                )

            # Execute collection (same as Qlib Yahoo collector)
            collector.instrument_list = symbols
            collector.collector_data()

            # Verify results
            csv_files = list(workspace.temp_csv_dir.glob("*.csv"))
            successful_count = len(csv_files)

            if successful_count == 0:
                return PipelineStageResult(
                    stage=PipelineStage.COLLECT,
                    success=False,
                    message="No data collected",
                    error="No CSV files were generated",
                )

            message = f"Successfully collected {successful_count}/{len(symbols)} symbols from {source}"
            logger.info(message)

            return PipelineStageResult(
                stage=PipelineStage.COLLECT, success=True, message=message
            )

        except Exception as e:
            error_msg = f"Collection stage failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return PipelineStageResult(
                stage=PipelineStage.COLLECT,
                success=False,
                message="Collection stage failed",
                error=error_msg,
            )


class NormalizeStage:
    """
    Data normalization stage using UniversalNormalize.

    Educational Notes:
    - Uses our implemented UniversalNormalize class
    - Integrates with Qlib's Normalize workflow
    - Processes collected CSV files into standardized format
    """

    @staticmethod
    def execute(workspace: PipelineWorkspace) -> PipelineStageResult:
        """Execute data normalization stage"""
        try:
            logger.info("Starting normalization stage")

            # Check if we have CSV files to normalize
            csv_files = list(workspace.temp_csv_dir.glob("*.csv"))
            if not csv_files:
                return PipelineStageResult(
                    stage=PipelineStage.NORMALIZE,
                    success=False,
                    message="No CSV files found to normalize",
                    error="Collection stage must be completed first",
                )

            # Import required classes
            from app.services.data_collectors.normalize import UniversalNormalize
            from app.services.data_collectors.base import Normalize

            # Use Qlib's Normalize workflow with our UniversalNormalize
            normalizer = Normalize(
                source_dir=workspace.temp_csv_dir,
                target_dir=workspace.normalized_dir,
                normalize_class=UniversalNormalize,
                max_workers=4,
                date_field_name="date",
                symbol_field_name="symbol",
            )

            # Execute normalization
            normalizer.normalize()

            # Check results
            normalized_files = list(workspace.normalized_dir.glob("*.csv"))
            if not normalized_files:
                return PipelineStageResult(
                    stage=PipelineStage.NORMALIZE,
                    success=False,
                    message="Normalization produced no output files",
                    error="Normalize process completed but no files were generated",
                )

            message = f"Successfully normalized {len(normalized_files)} files"
            logger.info(message)

            return PipelineStageResult(
                stage=PipelineStage.NORMALIZE, success=True, message=message
            )

        except Exception as e:
            error_msg = f"Normalization stage failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return PipelineStageResult(
                stage=PipelineStage.NORMALIZE,
                success=False,
                message="Normalization stage failed",
                error=error_msg,
            )


class DumpStage:
    """
    Data dumping stage to Qlib binary format.

    Educational Notes:
    - Converts normalized CSV to Qlib .bin format
    - Uses Qlib's dump_bin functionality
    - Creates final Qlib-compatible data structure
    """

    @staticmethod
    def execute(workspace: PipelineWorkspace) -> PipelineStageResult:
        """Execute data dumping stage"""
        try:
            logger.info("Starting dump stage")

            # Check if we have normalized files
            normalized_files = list(workspace.normalized_dir.glob("*.csv"))
            if not normalized_files:
                return PipelineStageResult(
                    stage=PipelineStage.DUMP,
                    success=False,
                    message="No normalized files found to dump",
                    error="Normalization stage must be completed first",
                )

            # Detect data frequency from the first CSV file
            import pandas as pd

            freq = "day"  # Default frequency
            try:
                # Read first few rows of first CSV file to detect frequency
                sample_file = normalized_files[0]
                sample_df = pd.read_csv(sample_file, nrows=5)

                if "date" in sample_df.columns:
                    # Parse date column to detect if it contains time information
                    sample_dates = pd.to_datetime(sample_df["date"])

                    # Check if any timestamp has non-zero time component
                    has_time = any(
                        date.hour != 0 or date.minute != 0 or date.second != 0
                        for date in sample_dates
                        if pd.notna(date)
                    )

                    if has_time:
                        freq = "1min"
                        logger.info("Detected minute-level data, using freq='1min'")
                    else:
                        freq = "day"
                        logger.info("Detected daily data, using freq='day'")

            except Exception as e:
                logger.warning(
                    f"Could not detect frequency from data, using default 'day': {e}"
                )
                freq = "day"

            # Import Qlib's dump functionality
            import sys
            from pathlib import Path

            # Add qlib-source to path to access dump_bin
            qlib_source_path = (
                Path(__file__).parent.parent.parent.parent.parent / "qlib-source"
            )
            if str(qlib_source_path) not in sys.path:
                sys.path.insert(0, str(qlib_source_path))

            from scripts.dump_bin import DumpDataAll

            # Use Qlib's DumpDataAll for binary conversion with detected frequency
            dumper = DumpDataAll(
                data_path=str(workspace.normalized_dir),
                qlib_dir=str(workspace.qlib_data_dir),
                freq=freq,
                max_workers=4,
                date_field_name="date",
                symbol_field_name="symbol",
                exclude_fields="symbol,date",
            )

            # Execute dump
            dumper.dump()

            # Verify results
            features_dir = workspace.qlib_data_dir / "features"
            if not features_dir.exists():
                return PipelineStageResult(
                    stage=PipelineStage.DUMP,
                    success=False,
                    message="Dump completed but no features directory created",
                    error="Qlib data structure was not properly generated",
                )

            bin_files = list(features_dir.rglob("*.bin"))
            message = f"Successfully dumped {len(normalized_files)} files to Qlib format ({len(bin_files)} .bin files created)"
            logger.info(message)

            return PipelineStageResult(
                stage=PipelineStage.DUMP, success=True, message=message
            )

        except Exception as e:
            error_msg = f"Dump stage failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return PipelineStageResult(
                stage=PipelineStage.DUMP,
                success=False,
                message="Dump stage failed",
                error=error_msg,
            )
