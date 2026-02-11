"""
Custom Factor Handler for QuantBot
Extends Qlib's DataHandlerLP to support user-defined factor expressions.
Educational Notes:
- Inherits from DataHandlerLP following Qlib's extension conventions
- Supports loading custom factors from database
- Implements standard Qlib DataHandler interface methods
- Follows Alpha158 implementation pattern for factor definition
"""

import logging
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from qlib.data.dataset.handler import DataHandlerLP
from qlib.log import get_module_logger

logger = get_module_logger(__name__)


class CustomFactorHandler(DataHandlerLP):
    """
    Custom Factor Handler - Qlib-compliant factor engine with database support

    This handler extends Qlib's DataHandlerLP to support user-defined factors
    loaded from database. It follows the same pattern as Alpha158  but allows
    dynamic factor definition through database storage.

    Key Design Principles:
    - Follows Qlib's DataHandler extension conventions
    - Loads custom factors from database as initialization
    - Defines factors as expression strings (like Alpha158)
    - Implements standard DataHandler interface methods
    - Supports both built-in and user-defined factors

    Educational Notes:
    - DataHandlerLP = Data Handler with Learnable Processors
    - Learnable processors can be fitted on training data
    - This enables normalization, feature selection, etc.
    - Database integration allows dynamic factor management
    """

    def __init__(
        self,
        start_time: str,
        end_time: str,
        fit_start_time: str,
        fit_end_time: str,
        instruments: Union[str, List[str]] = "csi300",
        custom_factors: Optional[List[Dict[str, str]]] = None,
        include_basic_factors: bool = True,
        factor_db_service=None,  # Will be injected for database access
        infer_processors: Optional[List] = None,
        learn_processors: Optional[List] = None,
        shared_processors: Optional[List] = None,
        **kwargs,
    ):
        """
        Initialize Custom Factor Handler with database support

        Educational Notes:
        - factor_db_service: Database service for loading global factors
        - custom_factors: Direct factor input (for testing/fallback)
        - Dependency injection pattern for better testability
        - All factors are global (no user isolation needed)

        Args:
            start_time: Start time for data range (e.g., "2020-01-01")
            end_time: End time for data range (e.g., "2023-12-31")
            fit_start_time: Start time for fitting processors
            fit_end_time: End time for fitting processors
            instruments: Stock instruments or universe name
            custom_factors: Direct custom factor definitions (fallback)
                Format: [{"name": "factor_name", "expression": "qlib_expression"}]
            include_basic_factors: Whether to include basic price/volume factors
            factor_db_service: Database service for factor management
            infer_processors: Processors for inference phase
            learn_processors: Processors for learning phase
            shared_processors: Processors shared between phases
            **kwargs: Additional arguments
        """

        # Store configuration
        self.include_basic_factors = include_basic_factors
        self.factor_db_service = factor_db_service

        # Load custom factors from database or use provided ones
        self.custom_factors = self._load_custom_factors(custom_factors)

        # Validate custom factors
        self._validate_custom_factors()

        # Build factor field definitions (following Alpha158 pattern)
        self._build_factor_fields()

        logger.info(
            f"CustomFactorHandler initialized with {len(self.get_feature_names())} factors"
        )
        logger.info(f"Custom factors: {len(self.custom_factors)}")

        # Initialize parent DataHandlerLP
        super().__init__(
            start_time=start_time,
            end_time=end_time,
            fit_start_time=fit_start_time,
            fit_end_time=fit_end_time,
            instruments=instruments,
            infer_processors=infer_processors,
            learn_processors=learn_processors,
            shared_processors=shared_processors,
            **kwargs,
        )

    def _load_custom_factors(
        self, fallback_factors: Optional[List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """
        Load custom factors from database or use fallback

        Educational Notes:
        - Database-first approach: Try to load from DB, fallback to direct input
        - This pattern allows both programmatic and UI-driven factor management
        - All factors are global (no user isolation)
        - Future: Will integrate with FactorExpressionManager service

        Args:
            fallback_factors: Fallback factors if database loading fails

        Returns:
            List of custom factor definitions
        """
        if self.factor_db_service:
            try:
                # TODO: Implement database loading in next steps
                # factors = self.factor_db_service.get_all_factors()
                logger.info("Database factor loading will be implemented in step 2")
                return fallback_factors or []
            except Exception as e:
                logger.warning(f"Failed to load factors from database: {e}")
                return fallback_factors or []
        else:
            logger.info("Using fallback factors (no database service)")
            return fallback_factors or []

    def _validate_custom_factors(self) -> None:
        """
        Validate custom factor definitions

        Educational Notes:
        - Ensures each factor has required fields
        - Validates factor names are unique
        - Prevents conflicts with built-in factor names
        - TODO: Add Qlib expression syntax validation in step 3
        """
        factor_names = set()

        # Reserved names for basic factors
        reserved_names = {
            "close",
            "open",
            "high",
            "low",
            "volume",
            "intraday_return",
            "volatility_proxy",
            "volume_ratio",
        }

        for i, factor in enumerate(self.custom_factors):
            if not isinstance(factor, dict):
                raise ValueError(f"Custom factor {i} must be a dictionary")

            if "name" not in factor:
                raise ValueError(f"Custom factor {i} missing 'name' field")

            if "expression" not in factor:
                raise ValueError(f"Custom factor {i} missing 'expression' field")

            # Check for duplicate names
            name = factor["name"]
            if name in factor_names:
                raise ValueError(f"Duplicate factor name: {name}")

            # Check for reserved names
            if name in reserved_names:
                raise ValueError(f"Factor name '{name}' is reserved")

            factor_names.add(name)
            logger.debug(f"Validated custom factor: {name}")

    def _build_factor_fields(self) -> None:
        """
        Build factor field definitions following Qlib conventions

        Educational Notes:
        - Qlib DataHandlers define factors as expression lists
        - Each factor is a string expression in Qlib syntax
        - Features and labels are defined separately
        - This follows the Alpha158 implementation pattern
        """
        # Basic price and volume factors (similar to Alpha158 basics)
        basic_factors = []
        if self.include_basic_factors:
            basic_factors = [
                # Basic OHLCV data
                "$close",
                "$open",
                "$high",
                "$low",
                "$volume",
                # Simple derived factors
                "$close/$open",  # Intraday return
                "($high-$low)/$close",  # Volatility proxy
                "$volume/Mean($volume, 20)",  # Volume ratio to 20-day average
            ]

        # Add custom factors
        custom_expressions = [factor["expression"] for factor in self.custom_factors]

        # Combine all factors
        self.feature_expressions = basic_factors + custom_expressions

        # Standard label (following Alpha158 convention)
        # Ref($close, -2)/Ref($close, -1) - 1 means T+1 to T+2 return
        self.label_expressions = ["Ref($close, -2)/Ref($close, -1) - 1"]

        logger.info(
            f"Built {len(self.feature_expressions)} features and {len(self.label_expressions)} labels"
        )

    def get_feature_names(self) -> List[str]:
        """
        Get feature names for the factors

        Educational Notes:
        - Maps factor expressions to human-readable names
        - Used for column naming in output DataFrames
        - Combines basic and custom factor names

        Returns:
            List of feature names
        """
        names = []

        # Basic factor names
        if self.include_basic_factors:
            names.extend(
                [
                    "close",
                    "open",
                    "high",
                    "low",
                    "volume",
                    "intraday_return",
                    "volatility_proxy",
                    "volume_ratio",
                ]
            )

        # Custom factor names
        names.extend([factor["name"] for factor in self.custom_factors])

        return names

    def get_label_names(self) -> List[str]:
        """
        Get label names

        Returns:
            List of label names
        """
        return ["label"]

    def get_cols(self) -> List[str]:
        """
        Get column names for the processed data

        Required by Qlib's DataHandler interface.
        This method is called by Qlib to understand the data structure.

        Educational Notes:
        - Standard Qlib DataHandler interface method
        - Returns all column names (features + labels)
        - Used by Qlib for data validation and processing

        Returns:
            List of column names
        """
        feature_names = self.get_feature_names()
        label_names = self.get_label_names()
        return feature_names + label_names

    def setup_data(self, **kwargs) -> None:
        """
        Set up data for the handler

        This method is called by Qlib to prepare data.
        Implements the required DataHandler interface.

        Educational Notes:
        - Standard Qlib DataHandler interface method
        - Loads and processes data using Qlib's data infrastructure
        - Stores processed data in self._data for later access
        - TODO: Will be enhanced with actual data loading logic
        """
        try:
            logger.info("Setting up CustomFactorHandler data...")

            # Get all expressions (features + labels)
            all_expressions = self.feature_expressions + self.label_expressions

            if not all_expressions:
                logger.warning("No factors configured - using minimal setup")
                all_expressions = ["$close", "Ref($close, -2)/Ref($close, -1) - 1"]

            logger.info(
                f"Loading data with {len(self.feature_expressions)} features and {len(self.label_expressions)} labels"
            )

            # TODO: Implement actual data loading using Qlib's data interface
            # This will be completed after we have the database models
            logger.info(
                "Data loading implementation will be completed in subsequent steps"
            )

            # Placeholder: Create empty DataFrame with correct structure
            columns = self.get_cols()
            self._data = pd.DataFrame(columns=columns)

            logger.info(f"Data setup completed: {self._data.shape}")

        except Exception as e:
            logger.error(f"Failed to setup data: {str(e)}")
            raise

    def fetch(self, col_set: str = "feature", **kwargs) -> pd.DataFrame:
        """
        Fetch processed data

        Required by Qlib's DataHandler interface.
        This method is called by Qlib to get the actual data.

        Educational Notes:
        - Standard Qlib DataHandler interface method
        - col_set parameter: "feature", "label", or None (all)
        - Returns processed DataFrame ready for ML models

        Args:
            col_set: Which columns to fetch ("feature", "label", or None for all)
            **kwargs: Additional arguments

        Returns:
            Processed DataFrame with requested columns
        """
        if not hasattr(self, "_data") or self._data is None:
            raise ValueError("Data not set up. Call setup_data() first.")

        if col_set == "feature":
            feature_names = self.get_feature_names()
            return self._data[feature_names] if not self._data.empty else self._data
        elif col_set == "label":
            label_names = self.get_label_names()
            return self._data[label_names] if not self._data.empty else self._data
        else:
            # Return all columns
            return self._data

    def config(self, **kwargs) -> Dict[str, Any]:
        """
        Get handler configuration

        Required by Qlib's DataHandler interface for serialization.
        This allows Qlib to save and restore handler configurations.

        Educational Notes:
        - Standard Qlib DataHandler interface method
        - Used for workflow serialization and caching
        - Must include all parameters needed to recreate the handler

        Returns:
            Configuration dictionary
        """
        return {
            "class": "CustomFactorHandler",
            "module_path": "app.services.custom_factor_handler",
            "kwargs": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "fit_start_time": self.fit_start_time,
                "fit_end_time": self.fit_end_time,
                "instruments": self.instruments,
                "custom_factors": self.custom_factors,
                "include_basic_factors": self.include_basic_factors,
                # Note: factor_db_service is not serialized (will be re-injected)
            },
        }


# Factory function for easy instantiation
def create_custom_factor_handler(**kwargs) -> CustomFactorHandler:
    """
    Factory function to create CustomFactorHandler instance

    This provides a convenient way to create handlers with validation.
    Follows the factory pattern for better object creation control.

    Educational Notes:
    - Factory pattern: Encapsulates object creation logic
    - Allows for validation and default parameter handling
    - Makes testing easier by centralizing creation logic

    Args:
        **kwargs: Handler configuration parameters

    Returns:
        Configured CustomFactorHandler instance
    """
    logger.info("Creating CustomFactorHandler instance")
    return CustomFactorHandler(**kwargs)
