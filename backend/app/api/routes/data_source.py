"""
Data source management API routes.

Educational Notes:
- Provides REST API endpoints for data source operations
- Follows FastAPI best practices with proper response model
- Implements the optimized data flow: clear -> download -> convert
- Uses service layer pattern for business logic separation
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import logging
import os
from datetime import datetime
from pathlib import Path
import tempfile
import pandas as pd
from app.core.config import settings
from app.models import (
    DataSourceStatus,
    DownloadDataRequest,
    DownloadTaskResponse,
    ClearDataResponse,
    DataHealthMetrics,
)
from app.services.data_utils import (
    clear_qlib_data,
    execute_yahoo_data_collector,
    execute_yahoo_data_collector_impl,
    convert_csv_to_qlib_format,
    get_data_source_status,
)
from app.services.data_collectors.pipeline import execute_data_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=DataSourceStatus)
def get_data_source_status_endpoint():
    """
    Get current data source status.

    Educational Notes:
    - Simple API endpoint following clean architecture
    - Delegates business logic to service layer
    - Convert dict response to Pydantic model
    """
    try:
        status_data = get_data_source_status()
        return DataSourceStatus(**status_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.delete("/clear", response_model=ClearDataResponse)
def clear_data_source_endpoint():
    """
    Clear all data in both qlib_data and csv_data directories.

    Educational Notes:
    - Use DELETE method following RESTful conventions for resource deletion
    - Clears both final data (.bin) and intermediate data (CSV) for complete reset
    - Calls service layer for business logic separation
    - Returns detailed information about the clearing operation
    - Implements proper error handling with user-friendly messages
    """
    try:
        success, message, freed_space_mb = clear_qlib_data()

        if success:
            return ClearDataResponse(
                success=True, message=message, cleared_size_mb=freed_space_mb
            )
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to clear data: {message}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error clearing data source: {str(e)}"
        )


@router.post("/download", response_model=DownloadTaskResponse)
def download_data_source_endpoint(request: DownloadDataRequest):
    """
    Download data from specified source using the new pipeline.

    Educational Notes:
    - Uses the new unified pipeline: collect → normalize → dump
    - Maintains API compatibility with existing frontend
    - Provides better error handling and progress tracking
    - Automatically manages workspace and cleanup
    """
    try:
        from app.services.data_source_manager import data_source_manager

        current_source = data_source_manager.get_current_source()
        logger.info(
            f"Starting data download via pipeline: source={current_source}, symbols={len(request.stock_pool)}"
        )

        # Execute the complete pipeline
        response = execute_data_pipeline(request)

        logger.info(
            f"Pipeline execution completed: task_id={response.task_id}, status={response.status}"
        )
        return response

    except Exception as e:
        # Generate task ID for error tracking
        import uuid

        task_id = str(uuid.uuid4())

        logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)

        return DownloadTaskResponse(
            task_id=task_id,
            status="error",
            message=f"Pipeline execution failed: {str(e)}",
        )


@router.post("/export-data")
def export_data_endpoint():
    """
    Export all feature data from qlib bin files to CSV

    Educational Notes:
    - Directly reads binary files from qlib_data directory
    - Bypasses Qlib API to avoid initialization issues
    - Returns as downloadable CSV file
    - Useful for data analysis and backup

    Returns:
        CSV file with all feature data
    """
    import struct
    import numpy as np

    try:
        logger.info("Starting data export (direct binary reading)")

        # Get qlib data path
        qlib_data_path = Path(settings.QLIB_DATA_PATH)
        features_dir = qlib_data_path / "features"
        calendars_dir = qlib_data_path / "calendars"
        instruments_dir = qlib_data_path / "instruments"

        # Check if data exists
        if not features_dir.exists():
            raise HTTPException(
                status_code=404, detail="No data found. Please download data first."
            )

        # Read calendar from day.txt
        calendar_file = calendars_dir / "day.txt"
        if not calendar_file.exists():
            raise HTTPException(status_code=404, detail="Calendar file not found")

        with open(calendar_file, "r") as f:
            calendar = [line.strip() for line in f if line.strip()]

        logger.info(f"Loaded calendar with {len(calendar)} trading days")

        # Read instruments from all.txt
        instruments_file = instruments_dir / "all.txt"
        if not instruments_file.exists():
            raise HTTPException(status_code=404, detail="Instruments file not found")

        with open(instruments_file, "r") as f:
            # Convert to lowercase to match directory names
            instruments = [
                line.strip().split("\t")[0].lower() for line in f if line.strip()
            ]

        logger.info(f"Loaded {len(instruments)} instruments")

        # Get feature names from first instrument directory
        instrument_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
        if not instrument_dirs:
            raise HTTPException(status_code=404, detail="No instrument data found")

        first_instrument_dir = instrument_dirs[0]
        feature_files = list(first_instrument_dir.glob("*.day.bin"))
        feature_names = [f.stem.replace(".day", "") for f in feature_files]

        if not feature_names:
            raise HTTPException(status_code=404, detail="No feature files found")

        logger.info(f"Found {len(feature_names)} features: {feature_names}")

        # Read all data directly from bin files
        all_rows = []

        for instrument in instruments:
            instrument_dir = features_dir / instrument
            if not instrument_dir.exists():
                continue

            # Read all features for this instrument
            feature_data = {}
            num_values = 0

            for feature_name in feature_names:
                bin_file = instrument_dir / f"{feature_name}.day.bin"
                if not bin_file.exists():
                    continue

                # Read binary data (Qlib uses float32)
                with open(bin_file, "rb") as f:
                    data = f.read()

                num_values = len(data) // 4
                values = struct.unpack(f"{num_values}f", data)
                feature_data[feature_name] = values

            # Create rows for each date
            for i in range(min(num_values, len(calendar))):
                row = {
                    "instrument": instrument,
                    "datetime": calendar[i],
                }
                for feature_name in feature_names:
                    if feature_name in feature_data and i < len(
                        feature_data[feature_name]
                    ):
                        row[feature_name] = feature_data[feature_name][i]
                    else:
                        row[feature_name] = np.nan
                all_rows.append(row)

        if not all_rows:
            raise HTTPException(
                status_code=404, detail="No data could be read from bin files"
            )

        # Convert to DataFrame
        df = pd.DataFrame(all_rows)

        logger.info(f"Loaded data shape: {df.shape}")

        # Create temporary CSV file
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        logger.info(
            f"Data exported successfully: {len(df)} rows, {len(df.columns)} columns"
        )

        # Generate filename with timestamp
        filename = (
            f"qlib_data_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        # Return file
        return FileResponse(
            path=temp_file.name,
            filename=filename,
            media_type="text/csv",
            background=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")


@router.get("/health", response_model=DataHealthMetrics)
def get_data_health_endpoint():
    """
    Get data health metrics.

    Educational Notes:
    - Provides comprehensive data quality analysis
    - Checks for missing data, anomalies, and integrity issues
    - Based on Qlib's DataHealthChecker
    - Results are cached from routine execution
    """
    try:
        from app.services.data_health_service import get_data_health_service
        from app.config.qlib import qlib_config

        health_service = get_data_health_service()
        freq = qlib_config.freq

        # Perform health check
        health_metrics = health_service.check_data_health(freq=freq)

        return DataHealthMetrics(**health_metrics)

    except Exception as e:
        logger.error(f"Failed to get data health: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get data health: {str(e)}"
        )
