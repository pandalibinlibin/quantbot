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
        enable_alpha158=None,  # Alpha158 integration switch (None = read from config)
        region=None,  # Market region for label selection (None = read from config)
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

        # Load system configuration for Alpha158 and Label settings
        self._system_config = self._load_system_config()

        # Store configuration for later use (needed by config() method)
        self.start_time = start_time
        self.end_time = end_time
        self.fit_start_time = fit_start_time
        self.fit_end_time = fit_end_time
        self.freq = freq

        # Determine Alpha158 setting: parameter > config > default (False)
        if enable_alpha158 is not None:
            self.enable_alpha158 = enable_alpha158
        else:
            self.enable_alpha158 = (
                self._system_config.get("builtin_factor_libraries", {})
                .get("alpha158", {})
                .get("enabled", False)
            )

        # Determine market region: parameter > config > default ("cn")
        if region is not None:
            self.region = region
        else:
            self.region = self._system_config.get("data", {}).get("region", "cn")

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
            Tuple of (expressions, names) following Qlib's QlibDataLoader format
        """
        logger.info("Building feature configuration...")

        feature_expressions = []
        feature_names = []

        # Add Alpha158 factors if enabled (these will be computed on-the-fly)
        if self.enable_alpha158:
            logger.info("Loading Alpha158 factors...")
            try:
                from qlib.contrib.data.loader import Alpha158DL

                # Alpha158DL.get_feature_config() returns (expressions, names) tuple
                alpha158_exprs, alpha158_names = Alpha158DL.get_feature_config()
                feature_expressions.extend(alpha158_exprs)
                feature_names.extend(alpha158_names)
                logger.info(f"Added {len(alpha158_exprs)} Alpha158 factors")
            except Exception as e:
                logger.error(f"Failed to load Alpha158 factors: {e}")

        # Add pre-computed custom factors from bin files (using $field_name format)
        precomputed_exprs, precomputed_names = self._load_precomputed_factors()
        if precomputed_exprs:
            feature_expressions.extend(precomputed_exprs)
            feature_names.extend(precomputed_names)
            logger.info(
                f"Added {len(precomputed_exprs)} pre-computed factors from bin files"
            )

        logger.info(f"Total feature expressions: {len(feature_expressions)}")
        return (feature_expressions, feature_names)

    def _load_precomputed_factors(self, include_ohlcv: bool = True):
        """
        Load pre-computed factor names from bin files and return as $field_name format.

        This method scans the features directory for bin files and returns them
        as $field_name expressions for direct loading.

        Args:
            include_ohlcv: Whether to include OHLCV raw data fields

        Returns:
            Tuple of (expressions, names) for features
        """
        try:
            from .factor_storage import FactorStorage

            # Create storage instance with same frequency
            storage = FactorStorage(freq=self.freq if hasattr(self, "freq") else "day")

            feature_expressions = []
            feature_names = []

            # Add OHLCV raw data fields if requested
            if include_ohlcv:
                ohlcv_fields = ["$open", "$high", "$low", "$close", "$volume"]
                ohlcv_names = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]
                feature_expressions.extend(ohlcv_fields)
                feature_names.extend(ohlcv_names)
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
                feature_names.append(factor_name.upper())

            logger.info(
                f"Found {len(stored_factors)} pre-computed factors: {stored_factors}"
            )
            logger.info(f"Total feature expressions: {len(feature_expressions)}")
            return (feature_expressions, feature_names)

        except Exception as e:
            logger.error(f"Failed to load pre-computed factors: {e}")
            # Fallback to OHLCV only
            if include_ohlcv:
                return (
                    ["$open", "$high", "$low", "$close", "$volume"],
                    ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"],
                )
            return ([], [])

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
        - Always uses region-specific label expression from config
        - A-shares (cn): T+2 return due to T+1 trading rule
        - US stocks (us): T+1 return due to T+0 trading rule
        - Label is NOT user-customizable, it's determined by market region

        Returns:
            Tuple of (expressions, names) in Qlib format
        """
        logger.info("Building label configuration...")

        # Ensure system config is loaded (may not exist after deserialization)
        if not hasattr(self, "_system_config") or self._system_config is None:
            self._system_config = self._load_system_config()

        # Ensure region is set
        if not hasattr(self, "region") or self.region is None:
            self.region = self._system_config.get("data", {}).get("region", "cn")

        # Use region-specific label expression from config
        label_config = self._system_config.get("label_config", {})
        region_config = label_config.get(self.region, {})

        if region_config:
            label_expression = region_config.get(
                "expression", "Ref($close, -1)/$close - 1"  # Default T+1 return
            )
            description = region_config.get("description", "")
            logger.info(
                f"Using region '{self.region}' label: {label_expression} ({description})"
            )
        else:
            # Fallback based on region
            if self.region == "cn":
                # A-shares: T+2 return (T+1 trading rule)
                label_expression = "Ref($close, -2)/Ref($close, -1) - 1"
                logger.info(f"Using default CN label (T+2): {label_expression}")
            else:
                # US stocks: T+1 return (T+0 trading rule)
                label_expression = "Ref($close, -1)/$close - 1"
                logger.info(f"Using default US label (T+1): {label_expression}")

        # Return in Qlib format: ([expressions], [names])
        return [label_expression], ["LABEL0"]

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

    def _load_system_config(self) -> Dict[str, Any]:
        """
        Load system configuration from YAML file.

        Returns:
            Dictionary containing system configuration
        """
        try:
            import yaml
            from pathlib import Path

            # Try multiple possible config paths
            possible_paths = [
                Path("/app/app/config/qlib/system_config.yaml"),  # Docker path
                Path(__file__).parent.parent
                / "config"
                / "qlib"
                / "system_config.yaml",  # Relative path
            ]

            for config_path in possible_paths:
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f)
                        logger.info(f"Loaded system config from {config_path}")
                        return config or {}

            logger.warning("System config file not found, using defaults")
            return {}

        except Exception as e:
            logger.error(f"Failed to load system config: {e}")
            return {}

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
