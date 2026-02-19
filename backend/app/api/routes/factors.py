"""
Factor Management API Routes

This module provides REST API endpoints for factor management.
It exposes CRUD operations for factors with proper validation and error handling.

Educational Notes:
- Follows FastAPI best practices for API design
- Uses dependency injection for service layer
- Provides comprehensive error handling and validation
- Supports pagination and filtering
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
import logging

from ...models import Factor, FactorCreate, FactorUpdate, FactorStatus, FactorType
from ...services.factor_service import FactorService
from ...api.deps import get_current_user
from ...models import User

logger = logging.getLogger(__name__)

router = APIRouter()


def get_factor_service() -> FactorService:
    """
    Dependency to get FactorService instance

    Educational Notes:
    - Uses dependency injection pattern
    - Allows for easy testing and mocking
    - Centralizes service instantiation
    """
    return FactorService()


@router.post("/", response_model=Factor, status_code=status.HTTP_201_CREATED)
async def create_factor(
    factor_data: FactorCreate,
    current_user: User = Depends(get_current_user),
    factor_service: FactorService = Depends(get_factor_service),
):
    """
    Create a new factor

    Educational Notes:
    - Uses POST method for resource creation
    - Returns 201 Created status on success
    - Validates input data using Pydantic models
    - Requires user authentication

    Args:
        factor_data: Factor creation data
        current_user: Authenticated user from JWT token
        factor_service: Injected factor service

    Returns:
        Created Factor instance

    Raises:
        HTTPException: If factor creation fails
    """
    logger.info(f"Creating factor '{factor_data.name}' for user {current_user.id}")

    try:
        # Validate factor expression before creation
        validation_result = factor_service.validate_factor_expression(
            factor_data.expression
        )
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid factor expression: {validation_result['error']}",
            )

        # Create factor
        factor = factor_service.create_factor(factor_data, current_user.id)

        logger.info(f"Factor '{factor.name}' created successfully with ID: {factor.id}")
        return factor

    except ValueError as e:
        logger.warning(f"Factor creation validation failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create factor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during factor creation",
        )


@router.get("/", response_model=List[Factor])
async def get_factors(
    status_filter: Optional[FactorStatus] = Query(
        None, description="Filter by factor status"
    ),
    factor_type: Optional[FactorType] = Query(
        None, description="Filter by factor type (feature or label)"
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of factors to return"
    ),
    offset: int = Query(0, ge=0, description="Number of factors to skip"),
    current_user: User = Depends(get_current_user),
    factor_service: FactorService = Depends(get_factor_service),
):
    """
    Get list of factors with optional filtering

    Educational Notes:
    - Uses GET method for resource retrieval
    - Supports query parameters for filtering and pagination
    - Returns list of factors matching criteria
    - Requires user authentication
    - Use factor_type=feature for features (X), factor_type=label for labels (Y)

    Args:
        status_filter: Optional status filter (ACTIVE/INACTIVE)
        factor_type: Optional type filter (feature/label)
        limit: Maximum number of factors to return (1-1000)
        offset: Number of factors to skip for pagination
        current_user: Authenticated user
        factor_service: Injected factor service

    Returns:
        List of Factor instances
    """
    logger.info(
        f"Retrieving factors for user {current_user.id} with filters: status={status_filter}, type={factor_type}, limit={limit}, offset={offset}"
    )

    try:
        factors = factor_service.get_factors(
            status=status_filter, factor_type=factor_type, limit=limit, offset=offset
        )

        logger.info(f"Retrieved {len(factors)} factors")
        return factors

    except Exception as e:
        logger.error(f"Failed to retrieve factors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during factor retrieval",
        )


@router.get("/{factor_id}", response_model=Factor)
async def get_factor(
    factor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    factor_service: FactorService = Depends(get_factor_service),
):
    """
    Get factor by ID

    Educational Notes:
    - Uses GET method with path parameter
    - Returns single factor or 404 if not found
    - Validates UUID format automatically

    Args:
        factor_id: Factor UUID
        current_user: Authenticated user
        factor_service: Injected factor service

    Returns:
        Factor instance

    Raises:
        HTTPException: If factor not found
    """
    logger.info(f"Retrieving factor {factor_id} for user {current_user.id}")

    try:
        factor = factor_service.get_factor(factor_id)

        if not factor:
            logger.warning(f"Factor {factor_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Factor with ID {factor_id} not found",
            )

        logger.info(f"Retrieved factor '{factor.name}'")
        return factor

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve factor {factor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during factor retrieval",
        )


@router.put("/{factor_id}", response_model=Factor)
async def update_factor(
    factor_id: uuid.UUID,
    factor_data: FactorUpdate,
    current_user: User = Depends(get_current_user),
    factor_service: FactorService = Depends(get_factor_service),
):
    """
    Update existing factor

    Educational Notes:
    - Uses PUT method for resource update
    - Validates expression if provided
    - Returns updated factor or 404 if not found

    Args:
        factor_id: Factor UUID
        factor_data: Updated factor data
        current_user: Authenticated user
        factor_service: Injected factor service

    Returns:
        Updated Factor instance

    Raises:
        HTTPException: If factor not found or validation fails
    """
    logger.info(f"Updating factor {factor_id} for user {current_user.id}")

    try:
        # Validate expression if provided
        if factor_data.expression:
            validation_result = factor_service.validate_factor_expression(
                factor_data.expression
            )
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid factor expression: {validation_result['error']}",
                )

        # Update factor
        factor = factor_service.update_factor(factor_id, factor_data)

        if not factor:
            logger.warning(f"Factor {factor_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Factor with ID {factor_id} not found",
            )

        logger.info(f"Factor '{factor.name}' updated successfully")
        return factor

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update factor {factor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during factor update",
        )


@router.delete("/{factor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_factor(
    factor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    factor_service: FactorService = Depends(get_factor_service),
):
    """
    Delete factor (soft delete)

    Educational Notes:
    - Uses DELETE method for resource deletion
    - Returns 204 No Content on successful deletion
    - Performs soft delete (sets status to INACTIVE)

    Args:
        factor_id: Factor UUID
        current_user: Authenticated user
        factor_service: Injected factor service

    Raises:
        HTTPException: If factor not found or deletion fails
    """
    logger.info(f"Deleting factor {factor_id} for user {current_user.id}")

    try:
        success = factor_service.delete_factor(factor_id)

        if not success:
            logger.warning(f"Factor {factor_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Factor with ID {factor_id} not found",
            )

        logger.info(f"Factor {factor_id} deleted successfully")
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete factor {factor_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during factor deletion",
        )


@router.post("/validate-expression")
async def validate_factor_expression(
    expression: str,
    current_user: User = Depends(get_current_user),
    factor_service: FactorService = Depends(get_factor_service),
):
    """
    Validate factor expression syntax

    Educational Notes:
    - Provides standalone expression validation
    - Useful for frontend real-time validation
    - Returns detailed validation results

    Args:
        expression: Qlib expression string to validate
        current_user: Authenticated user
        factor_service: Injected factor service

    Returns:
        Validation result dictionary
    """
    logger.info(f"Validating factor expression for user {current_user.id}")

    try:
        result = factor_service.validate_factor_expression(expression)
        logger.info(f"Expression validation result: {result['valid']}")
        return result

    except Exception as e:
        logger.error(f"Failed to validate expression: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during expression validation",
        )
