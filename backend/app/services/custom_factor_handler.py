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
        instruments="csi300",
        start_time=None,
        end_time=None,
        freq="day",
        infer_processors=[],
        learn_processors=None,
        fit_start_time=None,
        fit_end_time=None,
        process_type=None,
        filter_pipe=None,
        inst_processors=None,
        enable_alpha158=False,  # Alpha158 integration switch
        **kwargs,
    ):
        """
        Initialize Custom Factor Handler following Alpha158 pattern

        Educational Notes:
        - Follows Alpha158 implementation pattern exactly
        - Uses QlibDataLoader for standard Qlib data loading
        - Supports database-driven custom factors + Alpha158 integration
        - Implements check_transform_proc for processor validation

        Args:
            instruments: Stock universe (e.g., "csi300", "csi500")
            start_time: Start time for data range
            end_time: End time for data range
            freq: Data frequency ("day", "1min", etc.)
            infer_processors: Processors for inference phase
            learn_processors: Processors for learning phase
            fit_start_time: Start time for fitting processors
            fit_end_time: End time for fitting processors
            process_type: Processing type (inherited from DataHandlerLP)
            filter_pipe: Data filtering pipeline
            inst_processors: Instrument processors
            enable_alpha158: Whether to include Alpha158 factors
            **kwargs: Additional arguments
        """
        # Import check_transform_proc following Alpha158 pattern
        from qlib.contrib.data.handler import check_transform_proc

        # Store Alpha158 integration flag
        self.enable_alpha158 = enable_alpha158

        # Process processors following Alpha158 pattern
        if learn_processors is None:
            # Use default learn processors like Alpha158
            learn_processors = [
                {"class": "DropnaLabel"},
                {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}},
            ]

        infer_processors = check_transform_proc(
            infer_processors, fit_start_time, fit_end_time
        )
        learn_processors = check_transform_proc(
            learn_processors, fit_start_time, fit_end_time
        )

        # Create data_loader following Alpha158 pattern
        data_loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": self.get_feature_config(),
                    "label": kwargs.pop("label", self.get_label_config()),
                },
                "filter_pipe": filter_pipe,
                "freq": freq,
                "inst_processors": inst_processors,
            },
        }

        # Initialize parent DataHandlerLP following Alpha158 pattern
        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=data_loader,
            learn_processors=learn_processors,
            infer_processors=infer_processors,
            process_type=process_type,
            **kwargs,
        )

        logger.info(f"CustomFactorHandler initialized with Alpha158={enable_alpha158}")

    def get_feature_config(self):
        """
        Get feature configuration combining Alpha158 and custom factors

        Educational Notes:
        - Follows Alpha158DL.get_feature_config() pattern exactly
        - Combines Alpha158 factors (if enabled) with database custom factors
        - Returns list of Qlib expression strings
        - Database factors are loaded from Factor table with status=ACTIVE

        Returns:
            List of factor expression strings in Qlib format
        """
        logger.info("Building feature configuration...")

        feature_expressions = []

        # Add Alpha158 factors if enabled
        if self.enable_alpha158:
            logger.info("Loading Alpha158 factors...")
            try:
                # Import Alpha158DL to get standard Alpha158 factors
                from qlib.contrib.data.loader import Alpha158DL

                # Get Alpha158 standard configuration
                alpha158_config = Alpha158DL.get_feature_config()
                feature_expressions.extend(alpha158_config)

                logger.info(f"Added {len(alpha158_config)} Alpha158 factors")
            except Exception as e:
                logger.error(f"Failed to load Alpha158 factors: {e}")

        # Add custom factors from database
        custom_factors = self._load_custom_factors_from_db()
        if custom_factors:
            custom_expressions = [factor["expression"] for factor in custom_factors]
            feature_expressions.extend(custom_expressions)
            logger.info(f"Added {len(custom_expressions)} custom factors from database")

        logger.info(f"Total feature expressions: {len(feature_expressions)}")
        return feature_expressions

    def _load_custom_factors_from_db(self):
        """
        Load custom factors from database

        Educational Notes:
        - Loads all active factors from Factor table
        - Returns list of factor dictionaries with name and expression
        - This will be enhanced with actual database integration later
        - For now, returns empty list as placeholder

        Returns:
            List of factor dictionaries: [{"name": "factor_name", "expression": "qlib_expr"}]
        """
        try:
            # Import database dependencies
            from sqlmodel import Session, select
            from ..core.db import engine
            from ..models import Factor, FactorStatus

            logger.info("Loading custom factors from database...")

            # Create database session
            with Session(engine) as session:
                # Query active factors from database
                statement = select(Factor).where(Factor.status == FactorStatus.ACTIVE)
                factors = session.exec(statement).all()

                # Convert to factor dictionaries
                factor_list = []
                for factor in factors:
                    factor_dict = {
                        "name": factor.name,
                        "expression": factor.expression,
                        "description": factor.description,
                        "id": str(factor.id),
                    }
                    factor_list.append(factor_dict)

                logger.info(f"Loaded {len(factor_list)} active factors from database")

                # Log factor names for debugging
                if factor_list:
                    factor_names = [f["name"] for f in factor_list]
                    logger.info(f"Factor names: {factor_names}")

                return factor_list

        except Exception as e:
            logger.error(f"Failed to load custom factors from database: {e}")
            logger.warning("Falling back to empty factor list")
            return []

    def get_label_config(self):
        """
        Get label configuration for target prediction

        Educational Notes:
        - Follows Alpha158 standard label configuration
        - Predicts next-day return: (close_t+1 / close_t) - 1
        - Uses Ref($close, -1) to get next day's close price
        - Standard format for supervised learning in quantitative finance

        Returns:
            List of label expression strings in Qlib format
        """
        logger.info("Building label configuration...")

        # Standard next-day return prediction label
        # Ref($close, -1) gets tomorrow's close price
        # Divide by today's close and subtract 1 to get return rate
        label_expressions = ["Ref($close, -1)/$close - 1"]

        logger.info(f"Label configuration: {label_expressions}")
        return label_expressions

    def get_feature_names(self) -> List[str]:
        """
        Get feature column names

        Educational Notes:
        - Returns list of feature names based on loaded factors
        - Used by Qlib for data structure validation
        - Generates names from factor expressions or uses factor names

        Returns:
            List of feature column names
        """
        try:
            custom_factors = self._load_custom_factors_from_db()
            if custom_factors:
                # Use factor names as feature names
                return [factor["name"] for factor in custom_factors]
            else:
                # Fallback to generic names if no factors
                return ["feature_0"]
        except Exception as e:
            logger.error(f"Failed to get feature names: {e}")
            return ["feature_0"]

    def get_label_names(self) -> List[str]:
        """
        Get label column names

        Educational Notes:
        - Returns list of label names for supervised learning
        - Standard Qlib pattern for label identification
        - Used for data structure validation

        Returns:
            List of label column names
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
            all_expressions = self.get_feature_config() + self.get_label_config()

            if not all_expressions:
                logger.warning("No factors configured - using minimal setup")
                all_expressions = ["$close", "Ref($close, -2)/Ref($close, -1) - 1"]

            logger.info(
                f"Loading data with {len(self.get_feature_config())} features and {len(self.get_label_config())} labels"
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
