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
