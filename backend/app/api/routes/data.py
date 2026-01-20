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


@router.get("/stocks/{region}")
def get_stock_list(region: str, source: str = "qlib_yahoo") -> Any:
    """
    Get stock list for the specified region.

    Args:
        region: Market region ('cn' or 'us')
        source: Data source name (default: 'qlib_yahoo')

    Returns:
        Stock list with count and instruments
    Example:
        GET /api/v1/data/stocks/cn
        Responses:
        {
            "status": "success",
            "count": 4000,
            "instruments": ["000001.SZ", "000002.SZ", ...],
            "message": "Found 4000 instruments in cn market"
        }
    """
    if region not in ["cn", "us"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid region: {region}. Must be 'cn' or 'us'."
        )

    service = DataCollectorService(region=region)
    result = service.get_stock_list(source=source)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.post("/daily/{region}")
def get_daily_data(
    region: str,
    symbols: list[str],
    start_date: str,
    end_date: str,
    fields: list[str] | None = None,
    source: str = "qlib_yahoo",
) -> Any:
    """
    Get daily data for specifed symbols.

    Args:
        region: Market region ('cn' or 'us')
        symbols: List of stock symbols (e.g., ["000001.SZ", "600000.SH"])
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        fields: Optional list of fields (default: ["$open", "$high", "$low", "$close", "$volume"])
        source: Data source name (default: 'qlib_yahoo')
    Returns:
        Daily data for the specified symbols
    Example:
        POST /api/v1/data/daily/cn
        Body: {
            "symbols": ["000001.SZ"],
            "start_date": "2020-01-01",
            "end_date": "2020-12-31"
        }
        Response:
        {
            "status": "success",
            "data": {...},
            "symbols": ["000001.SZ"],
            "fields": ["$open", "$high", "$low", "$close", "$volume"],
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "message": "Retrieve data for 1 symbols from 2020-01-01 to 2020-12-31"
        }
    """
    if region not in ["cn", "us"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid region: {region}. Must be 'cn' or 'us'."
        )

    service = DataCollectorService(region=region)
    result = service.get_daily_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        fields=fields,
        source=source,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.get("/calendar/{region}")
def get_trading_calendar(
    region: str,
    start_date: str,
    end_date: str,
    source: str = "qlib_yahoo",
) -> Any:
    """
    Get trading calendar for the specified region and date range.

    Args:
        region: Market region ('cn' or 'us')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Data source name (default: 'qlib_yahoo')
    Returns:
        Trading calendar with list of trading dates
    Example:
        GET /api/v1/data/calendar/cn?start_date=2020-01-01&end_date=2020-12-31
        Response:
        {
            "status": "success",
            "count": 244,
            "trading_dates": ["2020-01-02", "2020-01-03", ...],
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "message": "Found 244 trading days from 2020-01-01 to 2020-12-31"
        }
    """
    if region not in ["cn", "us"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid region: {region}. Must be 'cn' or 'us'."
        )

    service = DataCollectorService(region=region)
    result = service.get_trading_calendar(
        start_date=start_date, end_date=end_date, source=source
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result
