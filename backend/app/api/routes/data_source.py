"""
Data source management API routes.

Educational Notes:
- Provides REST API endpoints for data source operations
- Follows FastAPI best practices with proper response model
- Implements the optimized data flow: clear -> download -> convert
- Uses service layer pattern for business logic separation
"""

from fastapi import APIRouter, HTTPException
import logging
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
        logger.info(
            f"Starting data download via pipeline: source={request.source}, symbols={len(request.stock_pool)}"
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
