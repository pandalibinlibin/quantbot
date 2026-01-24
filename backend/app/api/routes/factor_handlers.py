"""
Factor calculation API routes.
This module provides RESTful API endpoints for factor calculation and management.
Follows the same pattern as data_collection.py for consistency.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import (
    FactorCalculationRequest,
    FactorCalculationResponse,
    FactorDataFetchRequest,
    FactorDataFetchResponse,
    FactorHandlerInfo,
    FactorHandlersInfoResponse,
    FeatureInfo,
)
from app.services.factor_handler_service import get_factor_handler_service

router = APIRouter()


@router.post(
    "/calculate",
    response_model=FactorCalculationResponse,
    summary="Calculate factors",
    description="Trigger factor calculation for specified instruments and date range",
)
def calculate_factors(
    request: FactorCalculationRequest,
    current_user: CurrentUser,
) -> Any:
    """
    Calculate factors using specified handler.
    Educational Notes:
    - This endpoint triggers factor calculation
    - Qlib will automatically cache results for future queries
    - Requires authentication (any logged-in user can access)
    Args:
        request: Factor calculation request with handler name, instruments, and date range
        current_user: Current authenticated user (injected by FastAPI)
    Returns:
        FactorCalculationResponse with calculation status and metadata
    Raises:
        HTTPException: If calculation fails
    """
    try:
        # Get factor handler service with configured region
        from app.core.config import settings

        service = get_factor_handler_service(region=settings.QLIB_REGION)
        # Calculate factors
        result = service.calculate_factors(
            handler_name=request.handler_name,
            instruments=request.instruments,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        # If calculation failed, return appropriate HTTP error
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            # Check if it's a data availability issue (client error)
            if "No data available" in error_msg or "can't find a freq" in error_msg:
                raise HTTPException(
                    status_code=400,  # Bad Request - missing data
                    detail=error_msg,
                )
            else:
                # Other errors (server error)
                raise HTTPException(
                    status_code=500,
                    detail=error_msg,
                )

        return result
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Factor calculation failed: {str(e)}",
        )


@router.get(
    "/handlers",
    response_model=FactorHandlersInfoResponse,
    summary="List factor handlers",
    description="Get information about all registered factor handlers",
)
def get_handlers_info(
    current_user: CurrentUser,
) -> Any:
    """
    Get information about all registered factor handlers.
    Educational Notes:
    - Lists all available factor handlers (alpha158, alpha191, etc.)
    - Provides metadata about each handler
    - Useful for API discovery and UI building
    Args:
        current_user: Current authenticated user (injected by FastAPI)
    Returns:
        FactorHandlersInfoResponse with list of handlers and their metadata
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from app.core.config import settings

        service = get_factor_handler_service(region=settings.QLIB_REGION)
        handlers_info = service.get_handlers_info()
        return FactorHandlersInfoResponse(
            total_handlers=len(handlers_info),
            handlers=[
                FactorHandlerInfo(
                    name=info["name"],
                    description=info["description"],
                    features_count=info["features_count"],
                )
                for info in handlers_info
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve handlers info: {str(e)}",
        )


@router.get(
    "/handlers/{handler_name}/features",
    response_model=list[FeatureInfo],
    summary="Get handler features",
    description="Get detailed information about features provided by a specific handler",
)
def get_handler_features(
    handler_name: str,
    current_user: CurrentUser,
) -> Any:
    """
    Get feature information for a specific handler.
    Educational Notes:
    - Returns metadata for all features (e.g., 158 features for alpha158)
    - Includes feature name, description, and category
    - Helps users understand what each feature represents
    Args:
        handler_name: Name of the factor handler (e.g., "alpha158")
        current_user: Current authenticated user (injected by FastAPI)
    Returns:
        List of FeatureInfo with feature metadata
    Raises:
        HTTPException: If handler not found or retrieval fails
    """
    try:
        from app.core.config import settings

        service = get_factor_handler_service(region=settings.QLIB_REGION)
        features_info = service.get_handler_features(handler_name)
        return [
            FeatureInfo(
                name=info["name"],
                description=info["description"],
                category=info["category"],
            )
            for info in features_info
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve features info: {str(e)}",
        )


@router.post(
    "/fetch-data",
    response_model=FactorDataFetchResponse,
    summary="Fetch actual factor data",
    description="Fetch actual calculated factor values as evidence of computation",
)
def fetch_factor_data(
    request: FactorDataFetchRequest,
    current_user: CurrentUser,
) -> Any:
    """
    Fetch actual factor data values.

    Educational Notes:
    - Returns actual calculated factor values (not just metadata)
    - Provides evidence that real computation occurred
    - Useful for verification and debugging

    Args:
        request: Factor data fetch request
        current_user: Current authenticated user

    Returns:
        FactorDataFetchResponse with actual factor values

    Raises:
        HTTPException: If fetch fails
    """
    try:
        from app.core.config import settings

        service = get_factor_handler_service(region=settings.QLIB_REGION)

        # Fetch actual factor data
        result = service.fetch_factor_data(
            handler_name=request.handler_name,
            instruments=request.instruments,
            start_date=request.start_date,
            end_date=request.end_date,
            features=request.features,
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to fetch factor data"),
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch factor data: {str(e)}",
        )
