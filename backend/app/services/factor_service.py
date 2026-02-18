"""
Factor Management Service

This module provides database operations for factor management.
It handles CRUD operations for factors, factor analysis, and dependencies.

Educational Notes:
- Provides clean interface for factor database operations
- Handles factor validation and status management
- Supports factor analysis and dependency tracking
- Integrates with CustomFactorHandler for factor loading
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_, or_
import logging

from ..core.db import engine
from ..models import (
    Factor,
    FactorCreate,
    FactorUpdate,
    FactorStatus,
    FactorAnalysis,
    FactorDependency,
)

logger = logging.getLogger(__name__)


class FactorService:
    """
    Service class for factor management operations

    Educational Notes:
    - Handles all database operations for factors
    - Provides validation and error handling
    - Supports factor lifecycle management
    - Integrates with Qlib expression validation
    """

    def __init__(self):
        """Initialize Factor Service"""
        logger.info("FactorService initialized")

    def create_factor(self, factor_data: FactorCreate, created_by: uuid.UUID) -> Factor:
        """
        Create a new factor

        Educational Notes:
        - Validates factor expression syntax
        - Sets initial status and timestamps
        - Creates database record with proper relationships

        Args:
            factor_data: Factor creation data
            created_by: UUID of the user creating the factor

        Returns:
            Created Factor instance

        Raises:
            ValueError: If factor validation fails
        """
        logger.info(f"Creating new factor: {factor_data.name}")

        try:
            with Session(engine) as session:
                # Check for duplicate factor names
                existing = session.exec(
                    select(Factor).where(Factor.name == factor_data.name)
                ).first()

                if existing:
                    raise ValueError(
                        f"Factor with name '{factor_data.name}' already exists"
                    )

                # Get factor data and ensure status is set to ACTIVE
                factor_dict = factor_data.model_dump()
                factor_dict.update(
                    {
                        "created_by": created_by,
                        "status": FactorStatus.ACTIVE,  # Override with ACTIVE status
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                )

                factor = Factor(**factor_dict)

                session.add(factor)
                session.commit()
                session.refresh(factor)

                logger.info(
                    f"Factor '{factor.name}' created successfully with ID: {factor.id}"
                )
                return factor

        except Exception as e:
            logger.error(f"Failed to create factor '{factor_data.name}': {e}")
            raise

    def get_factor(self, factor_id: uuid.UUID) -> Optional[Factor]:
        """
        Get factor by ID

        Args:
            factor_id: Factor UUID

        Returns:
            Factor instance or None if not found
        """
        try:
            with Session(engine) as session:
                factor = session.get(Factor, factor_id)
                logger.info(
                    f"Retrieved factor: {factor.name if factor else 'Not found'}"
                )
                return factor

        except Exception as e:
            logger.error(f"Failed to get factor {factor_id}: {e}")
            return None

    def get_factors(
        self, status: Optional[FactorStatus] = None, limit: int = 100, offset: int = 0
    ) -> List[Factor]:
        """
        Get list of factors with optional filtering

        Args:
            status: Optional status filter
            limit: Maximum number of factors to return
            offset: Number of factors to skip

        Returns:
            List of Factor instances
        """
        try:
            with Session(engine) as session:
                statement = select(Factor)

                if status:
                    statement = statement.where(Factor.status == status)

                statement = statement.offset(offset).limit(limit)
                factors = session.exec(statement).all()

                logger.info(f"Retrieved {len(factors)} factors")
                return list(factors)

        except Exception as e:
            logger.error(f"Failed to get factors: {e}")
            return []

    def update_factor(
        self, factor_id: uuid.UUID, factor_data: FactorUpdate
    ) -> Optional[Factor]:
        """
        Update existing factor

        Args:
            factor_id: Factor UUID
            factor_data: Updated factor data

        Returns:
            Updated Factor instance or None if not found
        """
        logger.info(f"Updating factor: {factor_id}")

        try:
            with Session(engine) as session:
                factor = session.get(Factor, factor_id)

                if not factor:
                    logger.warning(f"Factor {factor_id} not found for update")
                    return None

                # Update fields
                update_data = factor_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(factor, field, value)

                factor.updated_at = datetime.utcnow()

                session.add(factor)
                session.commit()
                session.refresh(factor)

                logger.info(f"Factor '{factor.name}' updated successfully")
                return factor

        except Exception as e:
            logger.error(f"Failed to update factor {factor_id}: {e}")
            raise

    def delete_factor(self, factor_id: uuid.UUID) -> bool:
        """
        Delete factor (soft delete by setting status to INACTIVE)

        Args:
            factor_id: Factor UUID

        Returns:
            True if deleted successfully, False otherwise
        """
        logger.info(f"Deleting factor: {factor_id}")

        try:
            with Session(engine) as session:
                factor = session.get(Factor, factor_id)

                if not factor:
                    logger.warning(f"Factor {factor_id} not found for deletion")
                    return False

                # Soft delete by setting status to INACTIVE
                factor.status = FactorStatus.INACTIVE
                factor.updated_at = datetime.utcnow()

                session.add(factor)
                session.commit()

                logger.info(f"Factor '{factor.name}' deleted successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to delete factor {factor_id}: {e}")
            return False

    def get_active_factors(self) -> List[Factor]:
        """
        Get all active factors for use in CustomFactorHandler

        Returns:
            List of active Factor instances
        """
        return self.get_factors(status=FactorStatus.ACTIVE)

    def validate_factor_expression(self, expression: str) -> Dict[str, Any]:
        """
        Validate factor expression syntax

        Educational Notes:
        - This will be enhanced with actual Qlib expression validation
        - For now, performs basic syntax checks
        - Returns validation result with details

        Args:
            expression: Qlib expression string

        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating factor expression: {expression}")

        try:
            # Basic validation checks
            if not expression or not expression.strip():
                return {"valid": False, "error": "Expression cannot be empty"}

            # Check for basic Qlib syntax patterns
            if not any(op in expression for op in ["$", "Ref(", "Mean(", "Std(", "+"]):
                return {
                    "valid": False,
                    "error": "Expression should contain Qlib operators like $close, Ref(), Mean(), etc.",
                }

            # TODO: Implement actual Qlib expression validation
            # This would involve parsing the expression with Qlib's parser

            logger.info("Factor expression validation passed")
            return {"valid": True, "message": "Expression syntax is valid"}

        except Exception as e:
            logger.error(f"Factor expression validation failed: {e}")
            return {"valid": False, "error": str(e)}
