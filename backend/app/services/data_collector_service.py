"""
Data Collector Service.
This module provides service layer components for managing data collectors.

Components:
- CollectorRegistry: Manages registration and retrieval of data collectors
- DataCollectorService: Provides high-level business logic for data collection

Educational Notes:
- Service Layer Pattern: Separate business logic from data access layer
- Registry Pattern: Centralized management of collector instances
- Dependency Injection: Service can be injected into API routes
- Qlib Integration: Collectors fetch data and convert to Qlib format

Architecture:
    API Layer (FastAPI routes)
        ↓
    Service Layer (this module)
        ↓
    Data Layer (collectors in data_sources/)
        ↓
    External APIs (yfinance, tushare, etc.)
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from app.services.data_sources.base_collector import BaseCollector
from app.services.data_sources.yahoo_collector import YahooCollector

logger = logging.getLogger(__name__)


class CollectorRegistry:
    """
    Registry for managing multiple data collectors.

    This class maintains a registry of all available collectors and
    provides methods to select the appropriate collector for a task.

    Usage Example:
    ```python
    registry = CollectorRegistry()

    # Register collectors
    registry.register(YahooCollector())
    registry.register(TushareCollector(config={'token', 'xxx'}))

    # Get a collector
    yahoo = registry.get_collector('yahoo')

    # Get all collectors
    all_collectors = registry.get_all_collectors()
    ```

    Educational Notes:
    - Centralized management of all data sources
    - Easy to add/remove collectors
    - Validates field compatibility during registration
    """

    def __init__(self):
        """Initialize the collector registry."""
        self._collectors: Dict[str, BaseCollector] = {}
        self.logger = logging.getLogger(f"{__name__}.CollectorRegistry")

    def register(self, collector: BaseCollector) -> None:
        """
        Register a collector.

        Args:
            collector: Instance of a BaseCollector subclass

        Raises:
            ValueError: If collector with same name already registered

        Educational Notes:
        - Validate field compatibility during registration
        - Logs warnings if collector doesn't support all fields
        """
        name = collector.get_collector_name()

        if name in self._collectors:
            raise ValueError(f"Collector '{name}' is already registered")

        # Validate field coverage
        coverage = collector.validate_field_coverage()

        if not coverage["is_fully_compatible"]:
            self.logger.warning(coverage["warning"])
        else:
            self.logger.info(
                f"Collector '{name}' registered successfully "
                f"({coverage['supported_count']} / {coverage['total_required']} fields)"
            )

        self._collectors[name] = collector

    def get_collector(self, name: str) -> Optional[BaseCollector]:
        """
        Get a collector by name.

        Args:
            name: Collector name

        Returns:
            Collector instance or None if not found
        """

        return self._collectors.get(name)

    def get_all_collectors(self) -> Dict[str, BaseCollector]:
        """
        Get all registered collectors.

        Returns:
            Dictionary mapping collector names to instance
        """

        return self._collectors.copy()

    def list_collector_names(self) -> List[str]:
        """
        Get names of all registered collectors.

        Returns:
            List of collector names
        """
        return list(self._collectors.keys())

    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get information about all registered collectors.

        Returns:
            Info dictionary with keys:
            - total_collectors: int
            - collectors: Dict[str, Dict] (name -> collector info)
        """
        return {
            "total_collectors": len(self._collectors),
            "collectors": {
                name: collector.get_collector_info()
                for name, collector in self._collectors.items()
            },
        }


class DataCollectorService:
    """
    Service for orchestrating data collection operations.

    This service provides high-level business logic for data collection,
    including collector management, task execution, and result formatting.

    Educational Notes:
    - Facade Pattern: Provides simplified interface to complex subsystem
    - Singleton Pattern: Single instance manages all operations
    - Business Logic Layer: Handles validation, orchestration, error handling

    Responsibilities:
    - Initialize and manage CollectorRegistry
    - Execute data collection tasks
    - Format results for API response
    - Handle errors and logging
    """

    def __init__(self):
        """Initialize the service with default collectors."""
        self.logger = logging.getLogger(__name__)
        self.registry = CollectorRegistry()

        # Register default collectors
        self._register_default_collectors()

    def _register_default_collectors(self):
        """
        Register default data collectors.

        Educational Notes:
        - Currently only Yahoo Finance is implemented
        - Future: Add TushareCollector, AkshareCollector, etc.
        - Collectors are registered on service initialization
        """
        try:
            yahoo_collector = YahooCollector()
            self.registry.register(yahoo_collector)
            self.logger.info("Default collectors registered successfully")
        except Exception as e:
            self.logger.error(f"Failed to register default collector: {e}")
            raise

    def collect_data(
        self,
        collector_name: str,
        instruments: List[str],
        start_date: str,
        end_date: str,
        output_dir: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute data collection task.

        Args:
            collector_name: Name of the collector to use (e.g., 'yahoo')
            instruments: List of instrument codes (e.g., ['AAPL', 'MSFT'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_dir: Optional output directory (default: ~/.qlib/stock_data)
            **kwargs: Additional collector-specific parameters

        Returns:
            Result dictionary with keys:
            - success: bool
            - collector: str
            - instruments_requested: int
            - instruments_collected: int
            - csv_dir: str
            - qlib_dir: str
            - errors: List[str]

        Raises:
            ValueError: If collector not found or invalid parameters

        Educational Notes:
        - Validates inputs before execution
        - Delegates to appropriate collector
        - Formats result for API response
        - Handles errors gracefully
        """

        # Validate collector exists
        collector = self.registry.get_collector(collector_name)
        if collector is None:
            available = self.registry.list_collector_names()
            raise ValueError(
                f"Collector '{collector_name}' not found. "
                f"Available collectors: {available}"
            )

        # Log task start
        self.logger.info(
            f"Starting data collection: collector={collector_name}, "
            f"instruments={len(instruments)}, "
            f"date_range={start_date} to {end_date}"
        )

        try:
            # Execute collection
            result = collector.collect_data(
                instruments=instruments,
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir,
                **kwargs,
            )

            # Add success flag
            result["success"] = True

            # Log completion
            self.logger.info(
                f"Data collection completed: "
                f"{result['successful_count']}/{result['total_instruments']} instruments"
            )

            return result
        except Exception as e:
            self.logger.error(f"Data collection failed: {e}", exc_info=True)
            return {
                "success": False,
                "collector": collector_name,
                "error": str(e),
                "instruments_requested": len(instruments),
                "instruments_collected": 0,
            }

    def get_collectors_info(self) -> Dict[str, Any]:
        """
        Get information about all available collectors.

        Returns:
            Registry information dictionary

        Educational Notes:
        - Delegates to CollectorRegistry
        - Provides API-friendly format
        - Includes field coverage for each collector
        """
        return self.registry.get_registry_info()

    def get_collector_info(self, collector_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific collector.

        Args:
            collector_name: Name of the collector

        Returns:
            Collector info dictionary or None if not found
        """
        collector = self.registry.get_collector(collector_name)
        if collector is None:
            return None
        return collector.get_collector_info()


# Global service instance (Singleton pattern)
_data_collector_service: Optional[DataCollectorService] = None


def get_data_collector_service() -> DataCollectorService:
    """
    Get the global DataCollectorService instance.

    Returns:
        DataCollectorService instance

    Educational Notes:
    - Singleton Pattern: Ensures only one service instance exists
    - Lazy Initialization: Service is created on first access
    - Thread-safe: Python's module-level initialization is thread-safe
    - Dependency Injection: Can be used in FastAPI with Depends()

    Usage in FastAPI:
    ```python
    from fastapi import Depends

    @router.post("/collect")
    def collect_data(
        service: DataCollectorService = Depends(get_data_collector_service)
    ):
        return service.collect_data(...)
    ```
    """
    global _data_collector_service

    if _data_collector_service is None:
        _data_collector_service = DataCollectorService()

    return _data_collector_service
