"""
Model handler API routes.
This module provides RESTful API endpoints for model handler management.
Follows the same pattern as factor_handlers.py for consistency.
"""

from typing import Any
from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser
from app.models import ModelHandlerInfo, ModelHandlersInfoResponse
from app.services.model_handler_service import get_model_handler_service

router = APIRouter()


@router.get(
    "/list",
    response_model=ModelHandlersInfoResponse,
    summary="List all model handlers",
    description="Get information about all registered model handlers",
)
def list_model_handlers(
    current_user: CurrentUser,
) -> Any:
    """
    List all available model handlers.

    Educational Notes:
    - Returns metadata about all registered model handlers
    - Helps users discover available models
    - Requires authentication (any logged-in user can access)

    Args:
        current_user: Current authenticated user (injected by FastAPI)

    Returns:
        ModelHandlersInfoResponse with list of all handlers
    """
    try:
        service = get_model_handler_service()
        handlers_info = service.get_handlers_info()

        return ModelHandlersInfoResponse(
            total_handlers=len(handlers_info),
            handlers=handlers_info,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve model handlers: {str(e)}",
        )
