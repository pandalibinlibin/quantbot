"""
Factor calculation service
Provides unified interface for all factor handlers
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import logging


class FactorHandlerRegistry:
    """
    Registry for factor handlers
    Similar to CollectorRegistry for data sources
    """

    def __init__(self):
        self._handlers = {}
        self.logger = logging.getLogger(__name__)

    def register(self, handler):
        """
        Register a factor handler

        Args:
            handler: Factor handler instance to register

        Raises:
            ValueError: If handler with same name already registered
        """
        if handler.name in self._handlers:
            existing_handler = self._handlers[handler.name]
            if existing_handler is handler:
                # Same instance, skip silently
                self.logger.debug(
                    f"Handler '{handler.name}' already registered (same instance)"
                )
                return
            else:
                # Different instance with same name - this is an error
                raise ValueError(
                    f"Factor handler '{handler.name}' is already registered. "
                    f"Cannot register duplicate handler names."
                )

        self._handlers[handler.name] = handler
        self.logger.info(f"Registered factor handler: {handler.name}")

    def get(self, name: str):
        """
        Get a factor handler by name

        Args:
            name: Handler name

        Returns:
            Handler instance or None if not found
        """

        return self._handlers.get(name)

    def list_handler_names(self) -> List[str]:
        """
        List all registered names

        Returns:
            List of handler names
        """
        return list(self._handlers.keys())

    def get_all_handlers(self):
        """
        Get all registered handlers

        Returns:
            List of all handler instances
        """
        return list(self._handlers.values())

    def unregister(self, name: str) -> bool:
        """
        Unregister a factor handler

        Args:
            name: Handler name to unregister

        Returns:
            True if handler was unregistered, False if not found
        """
        if name in self._handlers:
            del self._handlers[name]
            self.logger.info(f"Unregistered factor handler: {name}")
            return True
        return False


class FactorHandlerService:
    """
    Service layer for factor calculation
    Provides unified interface for all factor handlers
    Similar to DataCollectorService
    """

    def __init__(self, region: str = "us"):
        """
        Initialize FactorHandlerService

        Args:
            region: Market region, either 'cn' or 'us'. Default is 'us'.
        """
        self.registry = FactorHandlerRegistry()
        self.region = region
        self.logger = logging.getLogger(__name__)
        self._register_handlers()

    def _register_handlers(self):
        """Register all available factor handlers"""
        from .factors.alpha158_handler import Alpha158Handler

        try:
            # Register Alpha158 with region support
            self.registry.register(Alpha158Handler(region=self.region))
            self.logger.info(f"Registered Alpha158Handler for region: {self.region}")
        except ValueError as e:
            self.logger.warning(f"Failed to register Alpha158Handler: {e}")

        # Future: register other handlers
        # try:
        #     self.registry.register(Alpha191Handler(region=self.region))
        # except ValueError as e:
        #     self.logger.warning(f"Failed to register Alpha191Handler: {e}")

    def calculate_factors(
        self,
        handler_name: str,
        instruments: List[str],
        start_date: str,
        end_date: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate factors using specific handler

        Args:
            handler_name: Name of the factor handler (e.g., "alpha158")
            instruments: List of instrument codes
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional handler-specific parameters

        Returns:
            Calculation result with status and metadata
        """
        handler = self.registry.get(handler_name)
        if not handler:
            return {
                "success": False,
                "error": f"Factor handler '{handler_name}' not found",
                "available_handlers": self.registry.list_handler_names(),
            }

        self.logger.info(
            f"Calculating factors using {handler_name} for "
            f"{len(instruments)} instruments"
        )

        return handler.calculate(instruments, start_date, end_date, **kwargs)

    def fetch_factors(
        self,
        handler_name: str,
        instruments: List[str],
        start_date: str,
        end_date: str,
        features: Optional[List[str]] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch factor data using specified handler

        Args:
            handler_name: Name of the factor handler
            instruments: List of instrument codes
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            features: Optional list of specific features to fetch
            **kwargs: Additional handler-specific parameters

        Returns:
            DataFrame with factor data

        Raises:
            ValueError: If handler not found
        """
        handler = self.registry.get(handler_name)
        if not handler:
            raise ValueError(
                f"Factor handler '{handler_name}' not found. "
                f"Available: {self.registry.list_handler_names()}"
            )

        return handler.fetch(instruments, start_date, end_date, features, **kwargs)

    def get_handlers_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered handlers

        Returns:
            List of handler metadata dictionaries
        """
        return [
            {
                "name": handler.name,
                "description": handler.description,
                "features_count": len(handler.get_feature_names()),
            }
            for handler in self.registry.get_all_handlers()
        ]

    def get_handler_features(self, handler_name: str) -> List[Dict[str, Any]]:
        """
        Get feature information for a specific handler

        Args:
            handler_name: Name of the factor handler

        Returns:
            List of feature information dictionaries

        Raises:
            ValueError: If handler not found
        """
        handler = self.registry.get(handler_name)
        if handler is None:
            raise ValueError(f"Handler '{handler_name}' not found")

        return handler.get_feature_info()

    def fetch_factor_data(
        self,
        handler_name: str,
        instruments: List[str],
        start_date: str,
        end_date: str,
        features: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Fetch actual factor data values as evidence of computation

        Args:
            handler_name: Name of the factor handler
            instruments: List of instrument codes
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            features: Specific features to fetch (if None, fetch first 5)

        Returns:
            Dictionary with actual factor values and metadata
        """
        try:
            handler = self.registry.get(handler_name)
            if handler is None:
                raise ValueError(f"Handler '{handler_name}' not found")

            # Fetch actual data using handler's fetch method
            df = handler.fetch(
                instruments=instruments,
                start_date=start_date,
                end_date=end_date,
                features=features,
            )

            # If no specific features requested, get first 5
            if features is None:
                all_features = df.columns.tolist()
                features = all_features[:5] if len(all_features) >= 5 else all_features
                df = df[features]

            # Extract sample data (first 5 rows)
            sample_data = {}
            for feature in df.columns:
                values = df[feature].head(5).tolist()
                sample_data[feature] = values

            # Get date range
            dates = df.index.get_level_values(0).unique()
            date_range = (
                str(dates.min().date()) if len(dates) > 0 else start_date,
                str(dates.max().date()) if len(dates) > 0 else end_date,
            )

            # Get instruments from index
            actual_instruments = df.index.get_level_values(1).unique().tolist()

            return {
                "success": True,
                "factor_handler": handler_name,
                "instruments": actual_instruments,
                "date_range": date_range,
                "features": df.columns.tolist(),
                "data_shape": df.shape,
                "sample_data": sample_data,
                "error": None,
            }

        except Exception as e:
            self.logger.error(f"Failed to fetch factor data: {e}", exc_info=True)
            return {
                "success": False,
                "factor_handler": handler_name,
                "instruments": instruments,
                "date_range": (start_date, end_date),
                "features": [],
                "data_shape": (0, 0),
                "sample_data": {},
                "error": str(e),
            }


# Singleton instance with region support
# Singleton instance with region support
_factor_handler_service_instances = {}


def get_factor_handler_service(region: str = "us") -> FactorHandlerService:
    """
    Get singleton instance of FactorHandlerService for specified region

    Each region has its own singleton instance to avoid conflicts.

    Args:
        region: Market region, either 'cn' or 'us'. Default is 'us'.

    Returns:
        FactorHandlerService instance for the specified region
    """
    global _factor_handler_service_instances

    if region not in _factor_handler_service_instances:
        _factor_handler_service_instances[region] = FactorHandlerService(region=region)

    return _factor_handler_service_instances[region]
