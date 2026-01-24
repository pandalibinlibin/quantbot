"""
Base class for all factor handlers
Defines the unified interface for factor calculation
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class BaseFactorHandler(ABC):
    """
    Base class for all factor handlers
    Similar to BaseCollector for data sources

    All factor handlers must implement these methods to provide
    a unified interface for factor calculation and retrieval.
    """

    def __init__(self, name: str, description: str):
        """
        Initialize factor handler

        Args:
            name: Unique identifier for this handler (e.g., "alpha158")
            description: Human-readable description of the handler
        """
        self.name = name
        self.description = description

    @abstractmethod
    def calculate(
        self, instruments: List[str], start_date: str, end_date: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Calculate factors for given instruments and date range

        This method triggers the factor calculation process.
        The actual calculation may be cached by the underlying engine.

        Args:
            instruments: List of instrument codes (e.g., ["AAPL", "MSFT"])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional handler-specific parameters

        Returns:
            Dictionary with calculation status and metadata:
            {
                "success": bool,
                "factor_handler": str,
                "instruments_count": int,
                "features_count": int,
                "calculation_time": float,
                "cached": bool,
                "error": Optional[str]
            }
        """
        pass

    @abstractmethod
    def fetch(
        self,
        instruments: List[str],
        start_date: str,
        end_date: str,
        features: Optional[List[str]] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch calculated factor data

        Retrieves previously calculated factor data.
        If data is not cached, may trigger calculation.

        Args:
            instruments: List of instrument codes
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            features: Optional list of specific features to fetch.
                    If None, fetch all features.
            **kwargs: Additional handler-specific parameters

        Returns:
            DataFrame with columns: datetime, instrument, feature1, feature2, ...
            Index: MultiIndex (datetime, instrument)
        """
        pass

    @abstractmethod
    def get_feature_names(self) -> List[str]:
        """
        Get list of all feature names this handler provides

        Returns:
            List of feature names (e.g., ["KLEN", "KMID", "KLOW", ...])
        """
        pass

    @abstractmethod
    def get_feature_info(self) -> List[Dict[str, str]]:
        """
        Get detailed information about features

        Returns:
            List of feature metadata dictionaries:
            [
                {
                    "name": "KLEN",
                    "description": "K线长度",
                    "category": "价格形态"
                },
                ...
            ]
        """
        pass

    def __repr__(self) -> str:
        """String representation of the handler"""
        return f"{self.__class__.__name__} (name='{self.name}')"
