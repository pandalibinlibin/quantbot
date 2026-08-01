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
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
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

        # Compute and save factor bin files
        try:
            compute_result = factor_service.compute_and_save_factor(factor.id)
            if compute_result.get("status") == "success":
                logger.info(
                    f"Factor '{factor.name}' bin files computed: "
                    f"{compute_result.get('symbols_written', 0)} symbols"
                )
            else:
                logger.warning(
                    f"Factor '{factor.name}' bin file computation failed: "
                    f"{compute_result.get('error', 'unknown error')}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to compute bin files for factor '{factor.name}': {e}"
            )

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


# Specific routes must come before generic path parameters
@router.get("/builtin-libraries/alpha158")
async def get_alpha158_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get Alpha158 factor library information and status

    Returns:
        Alpha158 configuration, status, and factor list
    """
    import yaml
    from pathlib import Path

    logger.info(f"Getting Alpha158 info for user {current_user.id}")

    try:
        # Load system config
        config_paths = [
            Path("/app/app/config/qlib/system_config.yaml"),
            Path(__file__).parent.parent.parent
            / "config"
            / "qlib"
            / "system_config.yaml",
        ]

        config = {}
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                break

        # Get Alpha158 config
        alpha158_config = config.get("builtin_factor_libraries", {}).get("alpha158", {})
        enabled = alpha158_config.get("enabled", False)
        description = alpha158_config.get(
            "description", "158 classic technical factors for tree-based models"
        )
        data_requirements = alpha158_config.get(
            "data_requirements", ["open", "high", "low", "close", "volume", "vwap"]
        )

        # Get Alpha158 factor list from Qlib
        factors = _get_alpha158_factors()

        return {
            "name": "alpha158",
            "display_name": "Alpha158",
            "enabled": enabled,
            "description": description,
            "factor_count": len(factors),
            "data_requirements": data_requirements,
            "factors": factors,
        }

    except Exception as e:
        logger.error(f"Failed to get Alpha158 info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Alpha158 info: {str(e)}",
        )


@router.get("/label-config")
async def get_label_config(
    current_user: User = Depends(get_current_user),
):
    """
    Get current label configuration based on market region

    Returns:
        Label configuration including expression and description
    """
    import yaml
    from pathlib import Path

    logger.info(f"Getting label config for user {current_user.id}")

    try:
        # Load system config
        config_paths = [
            Path("/app/app/config/qlib/system_config.yaml"),
            Path(__file__).parent.parent.parent
            / "config"
            / "qlib"
            / "system_config.yaml",
        ]

        config = {}
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                break

        # Get current region
        region = config.get("data", {}).get("region", "cn")

        # Get label config for region
        label_config = config.get("label_config", {})
        region_label = label_config.get(region, {})

        if region_label:
            expression = region_label.get("expression", "")
            description = region_label.get("description", "")
            evaluation_return = region_label.get("evaluation_return", "")
            evaluation_horizon_days = region_label.get("evaluation_horizon_days")
        else:
            # Fallback defaults (keep in sync with system_config.yaml label_config)
            if region == "cn":
                expression = (
                    "(Ref($close, -6) / Ref($open, -1) - 1) / "
                    "Greater(Std($close / Ref($close, 1) - 1, 20), 0.0015)"
                )
                description = (
                    "Executable 5d return from T+1 open to T+6 close, "
                    "scaled by max(20d return vol, 0.15%)"
                )
                evaluation_return = "Ref($close, -6) / Ref($open, -1) - 1"
                evaluation_horizon_days = 5
            else:
                expression = "Ref($close, -1)/$close - 1"
                description = "T+1 return for US stocks (T+0 trading rule)"
                evaluation_return = expression
                evaluation_horizon_days = 1

        return {
            "region": region,
            "expression": expression,
            "evaluation_return": evaluation_return,
            "evaluation_horizon_days": evaluation_horizon_days,
            "description": description,
            "name": "LABEL0",
            "editable": False,  # Labels are not user-editable
        }

    except Exception as e:
        logger.error(f"Failed to get label config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get label config: {str(e)}",
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

        # Update factor with recompute (handles bin file update if expression changed)
        result = factor_service.update_factor_with_recompute(factor_id, factor_data)

        if result.get("status") == "error":
            logger.warning(f"Factor {factor_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", f"Factor with ID {factor_id} not found"),
            )

        factor = result.get("factor")
        if result.get("recomputed"):
            logger.info(
                f"Factor '{factor.name}' updated and recomputed: "
                f"{result.get('symbols_written', 0)} symbols"
            )
        else:
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
    Delete factor and clean up bin files

    Educational Notes:
    - Uses DELETE method for resource deletion
    - Returns 204 No Content on successful deletion
    - Performs hard delete from database
    - Also deletes associated bin files from Qlib data directory

    Args:
        factor_id: Factor UUID
        current_user: Authenticated user
        factor_service: Injected factor service

    Raises:
        HTTPException: If factor not found or deletion fails
    """
    logger.info(f"Deleting factor {factor_id} for user {current_user.id}")

    try:
        result = factor_service.delete_factor_with_cleanup(factor_id)

        if result.get("status") == "error":
            logger.warning(f"Factor {factor_id} deletion failed: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", f"Factor with ID {factor_id} not found"),
            )

        logger.info(
            f"Factor {factor_id} deleted successfully. "
            f"Bin files deleted: {result.get('bin_files_deleted', 0)}"
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

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


def _get_alpha158_factors() -> List[dict]:
    """
    Get list of Alpha158 factors with their expressions and categories

    Returns:
        List of factor dictionaries with name, expression, and category
    """
    try:
        from qlib.contrib.data.loader import Alpha158DL

        # Get Alpha158 feature config
        fields, names = Alpha158DL.get_feature_config()

        factors = []
        for i, (field, name) in enumerate(zip(fields, names)):
            # Determine category based on factor name pattern
            category = _categorize_alpha158_factor(name)
            factors.append(
                {
                    "name": name,
                    "expression": field,
                    "category": category,
                }
            )

        return factors

    except Exception as e:
        logger.error(f"Failed to get Alpha158 factors: {e}")
        return []


def _categorize_alpha158_factor(name: str) -> str:
    """
    Categorize Alpha158 factor based on its name pattern

    Args:
        name: Factor name (e.g., "KMID", "ROC5", "MA10")

    Returns:
        Category string: "kbar", "price", "volume", or "rolling"
    """
    # K-bar factors
    kbar_factors = [
        "KMID",
        "KLEN",
        "KMID2",
        "KUP",
        "KUP2",
        "KLOW",
        "KLOW2",
        "KSFT",
        "KSFT2",
    ]
    if name in kbar_factors:
        return "kbar"

    # Price factors (OPEN0, HIGH0, LOW0, CLOSE0, VWAP0, etc.)
    price_prefixes = ["OPEN", "HIGH", "LOW", "CLOSE", "VWAP"]
    for prefix in price_prefixes:
        if name.startswith(prefix) and name[len(prefix) :].isdigit():
            return "price"

    # Volume factors
    if name.startswith("VOLUME") and name[6:].isdigit():
        return "volume"

    # Rolling factors (everything else with numbers)
    return "rolling"
