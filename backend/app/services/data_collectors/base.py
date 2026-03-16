"""
Base data collector module for Qlib-compliant data collection.
This module provides the foundation for all data collectors in the system,
inheriting from Qlib's BaseCollector to ensure full compatibility with
Qlib's data processing pipeline and binary format optimization.

Educational Notes:
- Inherits from Qlib's BaseCollector abstract base class
- Implements Qlib's standard data collection workflow
- Provides common functionality for all data collections
- Ensures compatibility with Qlib's binary format and caching system
- Supports field metadata for frontend dynamic display
- get_data() returns DataFrame - this is the correct Qlib standard interface
- Binary conversion is handled automatically by Qlib's dump_bin.py
"""

import abc
import pandas as pd
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Import Qlib's BaseCollector
try:
    from qlib.data.data import BaseCollector
    from qlib.utils import get_or_create_path

    QLIB_AVAILABLE = True
except ImportError:
    # Fallback for development/testing without full Qlib installation
    class BaseCollector:
        """Fallback BaseCollector for development purposes"""

        def __init__(self, **kwargs):
            pass

        def collector_data(self, **kwargs):
            """Fallback collector_data method"""
            pass

    QLIB_AVAILABLE = False

from .exceptions import (
    DataCollectionError,
    DataSourceError,
    DataValidationError,
    CollectorConfigurationError,
)


class DataInterval(Enum):
    """
    Enumeration of supported data intervals.

    Educational Notes:
    - Only includes the two most commonly used intervals in stock trading
    - DAILY: For daily OHLCV data , most common for backtesting
    - MINUTE_1: For high-frequency trading and detailed analysis
    - Maps directly to Qlib's interval format
    """

    DAILY = "1d"
    MINUTE_1 = "1min"


class BaseDataCollector(BaseCollector):
    """
    Abstract base class for all data collectors in the system.

    This class inherits from Qlib's BaseCollector and provides a standardized
    interface for data collection operations. All specific data collectors
    (Tushare, EOD Historical Data, etc.) should inherit from this class.

    Educational Notes:
    - Follows Qlib's BaseCollector interface requirements
    - Implements common error handling and validation
    - Provides standardized logging and monitoring
    - Ensures consistent data format across all collectors
    - Supports Qlib's binary format for optimal performance
    - Includes field metadata system for frontend integration

    Key Qlib Integration Points:
    - get_instrument_list(): Returns list of available instruments
    - normalize_symbol(): Standardizes symbol format for Qlib
    - get_data(): Fetches data for a specific instrument and time range (returns DataFrame)
    - collector_data(): Main collection workflow (inherited from BaseCollector)
    """

    def __init__(self, **kwargs):
        """
        Initialize BaseDataCollector.

        Args:
            **kwargs: Configuration parameters for the collector

        Educational Notes:
        - Configuration should include data source settings
        - Common parameters: region, market, data_dir, etc.
        - Each collector can define its own specific parameters
        - Qlib will handle binary format conversion automatically
        """
        super().__init__(**kwargs)
        self.config = kwargs
        self._field_metadata = {}
        self._initialize_field_metadata()

    def _initialize_field_metadata(self) -> None:
        """
        Initialize field metadata for this collector.

        Educational Notes:
        - Called during initialization to set up field information
        - Subclasses should override to define their specific fields
        - Used by frontend to display available fields dynamically
        """
        # Default OHLCV fields - subclasses should extend this
        self._field_metadata = {
            "open": {
                "type": "float64",
                "required": True,
                "description": "Opening price",
            },
            "high": {
                "type": "float64",
                "required": True,
                "description": "Highest price",
            },
            "low": {"type": "float64", "required": True, "description": "Lowest price"},
            "close": {
                "type": "float64",
                "required": True,
                "description": "Closing price (effectively forward adjusted)",
            },
            "volume": {
                "type": "int64",
                "required": True,
                "description": "Trading volume",
            },
        }

    # Abstract methods that must be implemented by subclasses
    @abc.abstractmethod
    def get_instrument_list(self) -> List[str]:
        """
        Get list of available instruments for this data source.

        Returns:
            List[str]: List of instrument symbols/codes

        Educational Notes:
        - This is a Qlib BaseCollector required method
        - Should return standardized instrument codes
        - Used by Qlib to determine available data scope
        - Implementation varies by data source (Tushare: ts_codes, EOD: ticker symbols)
        """
        pass

    @abc.abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize instrument symbol to standard format.

        Args:
            symbol: Raw symbol from data source

        Returns:
            str: Normalized symbol for Qlib

        Educational Notes:
        - This is a Qlib BaseCollector required method
        - Converts data source specific symbols to Qlib format
        - Example: "000001.SZ" (Tushare) -> "SZ000001" (Qlib)
        - Critical for data consistency across the system
        """
        pass

    @abc.abstractmethod
    def get_data(
        self,
        symbol: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        interval: DataInterval = DataInterval.DAILY,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data for a specific instrument and time range.

        Args:
            symbol: Instrument symbol (normalized)
            start_time: Start date (YYYY-MM-DD format)
            end_time: End date (YYYY-MM-DD format)
            interval: Data interval (daily or minute)
            **kwargs: Additional parameters specific to data source

        Returns:
            pd.DataFrame: OHLCV data with datetime index

        Educational Notes:
        - This is a Qlib BaseCollector required method
        - MUST return DataFrame - this is the Qlib standard interface
        - DataFrame should have datetime index and OHLCV columns
        - Qlib will handle binary conversion automatically
        - This method is called by collector_data() for each instrument
        """
        pass

    # Helper methods and properties for enhanced functionality
    def get_supported_fields(self) -> Dict[str, str]:
        """
        Get field metadata for frontend integration.

        Returns:
            Dict[str, str]: Field name to description mapping

        Educational Notes:
        - Used by API to populate DataSourceStatus.features
        - Frontend displays this information to users
        - Subclasses can override _initialize_field_metadata() to customize
        - Directly supports existing API contract
        """
        return self._field_metadata.copy()

    def validate_config(self) -> bool:
        """
        Validate collector configuration.

        Returns:
            bool: True if configuration is valid

        Educational Notes:
        - Called during initialization to ensure proper setup
        - Subclasses should override to add specific validation
        - Helps catch configuration errors early
        - Supports robust error handling
        """
        if not isinstance(self.config, dict):
            return False

        return True

    def _handle_error(self, error: Exception, context: str) -> None:
        """
        Standardized error handling for data collection operations.

        Args:
            error: The exception that occurred
            context: Description of the operation context

        Educational Notes:
        - Provides consistent error handling across all collectors
        - Logs errors with proper context for debugging
        - Can be extended for error reporting/monitoring
        - Helps maintain system stability
        """
        error_msg = f"Error in {context}: {str(error)}"
        # In a real implementation, this would use proper logging
        print(f"[ERROR] {error_msg}")

        # Re-raise as appropriate collector exception
        if "network" in str(error).lower() or "connection" in str(error).lower():
            raise DataSourceError(error_msg) from error
        else:
            raise DataCollectionError(error_msg) from error
