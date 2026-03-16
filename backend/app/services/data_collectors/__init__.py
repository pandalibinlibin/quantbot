"""
Data collectors module for Qlib-compliant data collection.
This module provides standardized data collection interfaces
based on Qlib's BaseCollector architecture.

Educational Notes:
- All collectors inherit from Qlib's BaseCollector
- Follows Qlib's standard data collection workflow
- Provides plugin-based architecture for easy extension
- Full compatibility with Qlib's data processing pipeline

Supported Data Sources:
- Tushare: A-share (China) market data
- EOD Historical Data: US stock market data
"""

# Version information
__version__ = "2.0.0"
__author__ = "QuantBot Team"

# Core exports - using lazy imports to avoid circular dependencies
__all__ = [
    "BaseDataCollector",
    "TushareDataCollector",
    "EODDataCollector",
    "DataCollectionError",
    "CollectorNotFoundError",
]


# Lazy import pattern to handle dependencies
def __getattr__(name: str):
    """Lazy import for module attributes"""
    if name == "BaseDataCollector":
        from .base import BaseDataCollector

        return BaseDataCollector
    elif name == "TushareDataCollector":
        from .tushare_collector import TushareDataCollector

        return TushareDataCollector
    elif name == "EODDataCollector":
        from .eod_collector import EODDataCollector

        return EODDataCollector
    elif name in ("DataCollectionError", "CollectorNotFoundError"):
        from .exceptions import DataCollectionError, CollectorNotFoundError

        return (
            DataCollectionError
            if name == "DataCollectionError"
            else CollectorNotFoundError
        )
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
