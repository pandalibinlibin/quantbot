"""
Data Collection API Routes.
This module provides API endpoints for data collection operations.

Educational Notes:
- RESTful API design principles
- Dependency injection with FastAPI Depends()
- Request validation with Pydantic models
- Error handling and logging
- Authentication with CurrentUser dependency
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser
from app.models import (
    DataCollectionRequest,
    DataCollectionResponse,
    CollectorInfo,
    CollectorsInfoResponse,
)
from app.services.data_collector_service import (
    DataCollectorService,
    get_data_collector_service,
)

router = APIRouter(prefix="/data-collection", tags=["data-collection"])


@router.post("/collect", response_model=DataCollectionResponse)
def collect_data(
    *,
    current_user: CurrentUser,
    request: DataCollectionRequest,
    service: DataCollectorService = Depends(get_data_collector_service),
):
    """
    Execute data collection task.

    This endpoint triggers data collection from the specified data source.

    Educational Notes:
    - POST method: Creates/triggers a new data collection task
    - Authentication required: Uses CurrentUser dependency
    - Request validation: Pydantic model validates input
    - Service layer: Business logic handled by DataCollectorService
    - Error handling: Returns appropriate HTTP status codes

    Workflow:
    1. Validate user authentication
    2. Validate request parameters (Pydantic)
    3. Call DataCollectorService.collect_data()
    4. Return result or error

    Args:
        current_user: Authenticated user (injected by FastAPI)
        request: Data collection request parameters
        service: DataCollectorService instance (injected by FastAPI)

    Returns:
        DataCollectionResponse with collection results

    Raises:
        HTTPException 400: Invalid collector name or parameters
        HTTPException 500: Internal server error during collection
    """
    try:
        result = service.collect_data(
            collector_name=request.collector_name,
            instruments=request.instruments,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return result
    except ValueError as e:
        # Invalid collector name or parameters
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected error
        raise HTTPException(status_code=500, detail=f"Data collection failed: {str(e)}")


@router.get("/collectors", response_model=CollectorsInfoResponse)
def get_collectors(
    *,
    current_user: CurrentUser,
    service: DataCollectorService = Depends(get_data_collector_service),
) -> Any:
    """
    Get information about all available data collectors.

    This endpoint returns metadata about all registered collectors,
    including their supported fields and capabilities.

    Educational Notes:
    - GET method: Retrieves information (read-only)
    - No request body needed
    - Returns registry information
    - Useful for API discovery

    Use Cases:
    - Frontend can display available data sources
    - Users can see which fields each collector supports
    - API documentation and discovery

    Args:
        current_user: Authenticated user (injected by FastAPI)
        service: DataCollectorService instance (injected by FastAPI)

    Returns:
        CollectorsInfoResponse with all collectors information
    """

    return service.get_collectors_info()


@router.get("/collectors/{collector_name}", response_model=CollectorInfo)
def get_collector(
    *,
    current_user: CurrentUser,
    collector_name: str,
    service: DataCollectorService = Depends(get_data_collector_service),
) -> Any:
    """
    Get information about a specific data collector.

    This endpoint returns detailed metadata about a single collector.

    Educational Notes:
    - Path parameter: collector_name from URL
    - Returns 404 if collector not found
    - Detailed information about one collector

    Args:
        current_user: Authenticated user (injected by FastAPI)
        collector_name: Name of the collector (e.g., 'yahoo')
        service: DataCollectorService instance (injected by FastAPI)

    Returns:
        CollectorInfo with collector metadata

    Raises:
        HTTPException 404: Collector not found
    """
    info = service.get_collector_info(collector_name)
    if info is None:
        raise HTTPException(
            status_code=404, detail=f"Collector '{collector_name}' not found"
        )
    return info
