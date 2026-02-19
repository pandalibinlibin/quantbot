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
        process_type=DataHandlerLP.PTYPE_A,
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

        # Store configuration for later use (needed by config() method)
        self.start_time = start_time
        self.end_time = end_time
        self.fit_start_time = fit_start_time
        self.fit_end_time = fit_end_time
        self.freq = freq
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
        Get feature configuration combining Alpha158 and pre-computed custom factors

        Educational Notes:
        - Follows Alpha158DL.get_feature_config() pattern exactly
        - Combines Alpha158 factors (if enabled) with pre-computed custom factors
        - Pre-computed factors are loaded using $field_name format (direct bin file access)
        - This avoids re-computing factors that are already stored as bin files

        Returns:
            List of factor expression strings in Qlib format
        """
        logger.info("Building feature configuration...")

        feature_expressions = []

        # Add Alpha158 factors if enabled (these will be computed on-the-fly)
        if self.enable_alpha158:
            logger.info("Loading Alpha158 factors...")
            try:
                from qlib.contrib.data.loader import Alpha158DL

                alpha158_config = Alpha158DL.get_feature_config()
                feature_expressions.extend(alpha158_config)
                logger.info(f"Added {len(alpha158_config)} Alpha158 factors")
            except Exception as e:
                logger.error(f"Failed to load Alpha158 factors: {e}")

        # Add pre-computed custom factors from bin files (using $field_name format)
        precomputed_factors = self._load_precomputed_factors()
        if precomputed_factors:
            feature_expressions.extend(precomputed_factors)
            logger.info(
                f"Added {len(precomputed_factors)} pre-computed factors from bin files"
            )

        logger.info(f"Total feature expressions: {len(feature_expressions)}")
        return feature_expressions

    def _load_precomputed_factors(self, include_ohlcv: bool = True):
        """
        Load pre-computed factor names from bin files and return as $field_name format.

        This method scans the features directory for bin files and returns them
        as $field_name expressions for direct loading.

        Args:
            include_ohlcv: Whether to include OHLCV raw data fields

        Returns:
            List of $field_name expressions for features
        """
        try:
            from .factor_storage import FactorStorage

            # Create storage instance with same frequency
            storage = FactorStorage(freq=self.freq if hasattr(self, "freq") else "day")

            feature_expressions = []

            # Add OHLCV raw data fields if requested
            if include_ohlcv:
                ohlcv_fields = ["$open", "$high", "$low", "$close", "$volume"]
                feature_expressions.extend(ohlcv_fields)
                logger.info(f"Added {len(ohlcv_fields)} OHLCV fields")

            # Get list of stored factors (excludes OHLCV raw data)
            stored_factors = storage.list_stored_factors()

            # Get the label name to exclude it from features
            label_name = self._load_label_from_db()

            # Convert to $field_name format and add to feature_expressions
            # IMPORTANT: Exclude label factor from features to avoid data leakage
            for factor_name in stored_factors:
                if label_name and factor_name == label_name:
                    logger.info(f"Excluding label '{factor_name}' from features")
                    continue
                feature_expressions.append(f"${factor_name}")

            logger.info(
                f"Found {len(stored_factors)} pre-computed factors: {stored_factors}"
            )
            logger.info(f"Total feature expressions: {len(feature_expressions)}")
            return feature_expressions

        except Exception as e:
            logger.error(f"Failed to load pre-computed factors: {e}")
            # Fallback to OHLCV only
            if include_ohlcv:
                return ["$open", "$high", "$low", "$close", "$volume"]
            return []

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
        - Loads pre-computed label from bin files (if available)
        - Falls back to expression-based calculation if no pre-computed label
        - Label is defined by user in database with factor_type='label'
        - Only one ACTIVE label is allowed at a time

        Returns:
            List of label expression strings in Qlib format
        """
        logger.info("Building label configuration...")

        # Try to load pre-computed label from database/bin files
        label_name = self._load_label_from_db()

        if label_name:
            # Use pre-computed label from bin file
            label_expressions = [f"${label_name}"]
            logger.info(f"Using pre-computed label: {label_expressions}")
        else:
            # Fallback to standard next-day return calculation
            # Ref($close, -1) gets tomorrow's close price
            label_expressions = ["Ref($close, -1)/$close - 1"]
            logger.info(
                f"No pre-computed label found, using default: {label_expressions}"
            )

        return label_expressions

    def _load_label_from_db(self):
        """
        Load the ACTIVE label name from database.

        Returns:
            Label name (str) if found, None otherwise
        """
        try:
            from sqlmodel import Session, select
            from ..core.db import engine
            from ..models import Factor, FactorStatus, FactorType

            with Session(engine) as session:
                # Query the single ACTIVE label
                statement = select(Factor).where(
                    Factor.factor_type == FactorType.LABEL,
                    Factor.status == FactorStatus.ACTIVE,
                )
                label = session.exec(statement).first()

                if label:
                    logger.info(f"Found ACTIVE label: {label.name}")
                    return label.name
                else:
                    logger.info("No ACTIVE label found in database")
                    return None

        except Exception as e:
            logger.error(f"Failed to load label from database: {e}")
            return None

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

    def setup_data(self, init_type: str = DataHandlerLP.IT_FIT_SEQ, **kwargs) -> None:
        """
        Set up data for the handler

        This method is called by Qlib to prepare data.
        Delegates to parent class DataHandlerLP.setup_data() which handles:
        - Loading raw data via data_loader
        - Running processors (fit and process)
        - Setting up _learn and _infer DataFrames

        Educational Notes:
        - MUST call parent class setup_data() to properly initialize _learn/_infer
        - Parent class handles all the complexity of data processing pipeline
        - Our customization is in get_feature_config() and get_label_config()
        """
        logger.info("Setting up CustomFactorHandler data...")
        logger.info(
            f"Loading data with {len(self.get_feature_config())} features and {len(self.get_label_config())} labels"
        )

        # Call parent class setup_data - this is CRITICAL
        # It loads data, runs processors, and sets up _learn/_infer attributes
        super().setup_data(init_type=init_type, **kwargs)

        logger.info("CustomFactorHandler data setup completed")

    # Note: fetch() method is inherited from DataHandlerLP
    # Do NOT override it - the parent class implementation handles all the complexity
    # of data fetching with proper selector, level, col_set, and data_key parameters

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
                "freq": self.freq,
                "enable_alpha158": self.enable_alpha158,
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
