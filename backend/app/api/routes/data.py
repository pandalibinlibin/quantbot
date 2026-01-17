"""
API routes for data management.
This module provides endpoints for:
- Checking data status
- Downloading market data
- Getting data information
"""

from typing import Any
from fastapi import APIRouter, HTTPException
from app.services.data_collector import DataCollectorService

router = APIRouter()


@router.get("/status/{region}")
def check_data_status(region: str) -> Any:
    """
    Check if market data exists for the specified region.

    Args:
        region: Market region ('cn' or 'us')

    Returns:
        Data status information

    Example:
        GET /api/v1/data/status/cn

        Response:
        {
            "region": "cn",
            "data_path": "/home/user/.qlib/qlib_data/cn_data",
            "data_exists": true,
            "message": "Data is ready"
        }
    """
    if region not in ["cn", "us"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid region: {region}. Must be 'cn' or 'us'."
        )

    service = DataCollectorService(region=region)
    return service.check_data_status()


@router.post("/download/{region}")
def download_data(
    region: str,
    source: str = "qlib_yahoo",
    method: str = "prebuilt",
) -> Any:
    """
    Download market data for the specified region.

    Args:
        region: Market region ('cn' or 'us')
        source: Data source name (default: 'qlib_yahoo')
        method: Download method (default: 'prebuilt')
            - 'prebuilt': Fast, pre-built data
            - 'yahoo': Slow, latest data from Yahoo Finance

    Returns:
        Download result with status and message

    Example:
        POST /api/v1/data/download/cn?method=prebuilt

        Response:
        {
            "status": "success",
            "message": "Pre-built data downloaded to /home/user/.qlib/qlib_data/cn_data",
            "qlib_initialized": true
        }
    """
    if region not in ["cn", "us"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid region: {region}. Must be 'cn' or 'us'."
        )

    service = DataCollectorService(region=region)
    result = service.download_data(source=source, method=method)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.get("/info/{region}")
def get_data_info(region: str) -> Any:
    """
    Get detailed information about downloaded data.

    Args:
        region: Market region ('cn' or 'us')

    Returns:
        Data information including subdirectories status

    Example:
        GET /api/v1/data/info/cn

        Response:
        {
            "status": "found",
            "data_path": "/home/user/.qlib/qlib_data/cn_data",
            "calendars_exist": true,
            "instruments_exist": true,
            "features_exist": true,
            "message": "Data directory found"
        }
    """
    if region not in ["cn", "us"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid region: {region}. Must be 'cn' or 'us'."
        )

    service = DataCollectorService(region=region)
    return service.get_data_info()
