"""
Data source management API routes.

Educational Notes:
- Provides REST API endpoints for data source operations
- Follows FastAPI best practices with proper response model
- Implements the optimized data flow: clear -> download -> convert
- Uses service layer pattern for business logic separation
"""

from fastapi import APIRouter, HTTPException
import os
from datetime import datetime
from pathlib import Path
from app.core.config import settings
from app.models import (
    DataSourceStatus,
    DownloadDataRequest,
    DownloadTaskResponse,
    ClearDataResponse,
)
from app.services.data_utils import (
    clear_qlib_data,
    execute_yahoo_data_collector,
    execute_yahoo_data_collector_impl,
    convert_csv_to_qlib_format,
    get_data_source_status,
)

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
    Download data from specified source with complete refresh.

    Educational Notes:
    - Uses POST method for creating a new download task
    - Follows the optimized data flow: clear → download → convert
    - Returns immediately with task_id for tracking
    - Ensures data consistency by clearing before download
    - Implements comprehensive error handling
    """
    try:
        # Generate unique task ID
        import uuid

        task_id = str(uuid.uuid4())

        # Step 1: Clear existing data for consistency
        clear_success, clear_message, cleared_mb = clear_qlib_data()
        if not clear_success:
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message=f"Failed to clear existing data: {clear_message}",
            )

        # Step 2: Download CSV data based on source
        if request.source.lower() == "yahoo":
            download_success, download_message = execute_yahoo_data_collector_impl(
                target_dir=f"{settings.CSV_DATA_PATH}/cn_data",
                file_name=settings.DEFAULT_CSV_FILE_NAME,
                instruments=request.instruments,
                start_date=request.start_date,
                end_date=request.end_date,
                region=request.region,
            )
        elif request.source.lower() == "tushare":
            # Future implementation
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message="Tushare data source not yet implemented",
            )
        elif request.source.lower() == "akshare":
            # Future implementation
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message="AkShare data source not yet implemented",
            )
        else:
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message=f"Unsupported data source: {request.source}",
            )

        # Check download result
        if not download_success:
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message=f"Download failed: {download_message}",
            )

        # Step 3: Convert to Qlib format
        convert_success, convert_message = convert_csv_to_qlib_format()
        if not convert_success:
            return DownloadTaskResponse(
                task_id=task_id,
                status="partial",
                message=f"Downloaded CSV but conversion failed: {convert_message}",
            )

        # All steps successful
        return DownloadTaskResponse(
            task_id=task_id,
            status="completed",
            message=f"Successfully completed full data refresh: cleared {cleared_mb} MB, downloaded and converted new data",
        )

    except Exception as e:
        # Generate task ID even for errors
        import uuid

        task_id = str(uuid.uuid4())

        return DownloadTaskResponse(
            task_id=task_id,
            status="error",
            message=f"Error during data refresh: {str(e)}",
        )
