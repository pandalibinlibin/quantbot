"""
Index Components Service - ETF Universe components fetching.

This service provides an interface to fetch ETF universe components
from index_config.yaml (static_list source).

Educational Notes:
- Reads configuration from index_config.yaml
- Returns ETF codes in Qlib standard format (e.g., SH510300, SZ159919)
- Supports caching to avoid repeated reads
- Provides clear error messages for debugging
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import yaml
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


class IndexComponentsService:
    """
    Service for fetching ETF universe components from index_config.yaml.

    Supported data source:
    - static_list: Pre-defined ETF codes from index_config.yaml
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the service.

        Args:
            config_path: Path to index_config.yaml, defaults to settings.INDEX_CONFIG_PATH
        """
        self.config_path = config_path or settings.INDEX_CONFIG_PATH
        self.config = self._load_config()
        self.cache: Dict[str, List[str]] = {}
        logger.info(
            f"IndexComponentsService initialized with config: {self.config_path}"
        )

    def _load_config(self) -> dict:
        """Load index configuration from YAML file."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(
                f"Loaded index config with {len(config.get('indexes', {}))} indices"
            )
            return config
        except Exception as e:
            logger.error(f"Failed to load index config from {self.config_path}: {e}")
            raise

    def get_active_index(self) -> str:
        """Get the currently active index name."""
        return self.config.get("active_index", "etf_universe")

    def get_index_config(self, index_name: str) -> dict:
        """
        Get configuration for a specific index.

        Args:
            index_name: Index identifier (e.g., 'etf_universe')

        Returns:
            Index configuration dictionary

        Raises:
            ValueError: If index not found in configuration
        """
        indexes = self.config.get("indexes", {})
        if index_name not in indexes:
            available = list(indexes.keys())
            raise ValueError(
                f"Index '{index_name}' not found in configuration. "
                f"Available indices: {available}"
            )
        return indexes[index_name]

    def get_components(
        self, index_name: Optional[str] = None, use_cache: bool = True
    ) -> List[str]:
        """
        Get constituent stocks for specified index.

        Args:
            index_name: Index identifier, defaults to active_index
            use_cache: Whether to use cached results

        Returns:
            List of stock codes in Qlib format (e.g., ['SH600519', 'SZ000858'])

        Educational Notes:
        - Automatically selects data source based on index configuration
        - Returns codes in Qlib standard format for consistency
        - Caches results to avoid repeated API calls
        """
        if index_name is None:
            index_name = self.get_active_index()

        # Check cache first
        if use_cache and index_name in self.cache:
            logger.info(f"Using cached components for {index_name}")
            return self.cache[index_name]

        # Get index configuration
        index_config = self.get_index_config(index_name)
        source = index_config.get("components_source")

        logger.info(f"Fetching components for {index_name} from source: {source}")

        # Only static_list source is supported
        if source == "static_list":
            components = self._get_from_static_list(index_config)
        else:
            raise ValueError(
                f"Unsupported components source: {source}. Only 'static_list' is supported."
            )

        # Cache results
        self.cache[index_name] = components
        logger.info(f"Fetched {len(components)} components for {index_name}")

        return components

    def _get_from_static_list(self, index_config: dict) -> List[str]:
        """
        Get components from static list defined in configuration.

        Args:
            index_config: Index configuration containing etf_codes list

        Returns:
            List of ETF codes in Qlib format
        """
        try:
            etf_codes = index_config.get("etf_codes", [])

            if not etf_codes:
                raise ValueError("No etf_codes found in static_list configuration")

            logger.info(f"Using static ETF list with {len(etf_codes)} ETFs")

            # Validate format
            valid_codes = []
            for code in etf_codes:
                if isinstance(code, str) and (
                    code.startswith("SH") or code.startswith("SZ")
                ):
                    valid_codes.append(code)
                else:
                    logger.warning(f"Invalid ETF code format: {code}")

            logger.info(f"Validated {len(valid_codes)} ETF codes from static list")

            if valid_codes:
                logger.info(f"Sample ETF codes: {valid_codes[:5]}")

            return valid_codes

        except Exception as e:
            logger.error(f"Error reading static ETF list: {e}")
            # Fallback to a minimal list
            fallback_codes = [
                "SH510300",
                "SH510310",
                "SZ159919",
                "SH510330",
                "SH510500",
            ]
            logger.info(f"Using fallback ETF list: {fallback_codes}")
            return fallback_codes


# Singleton instance
_service_instance: Optional[IndexComponentsService] = None


def get_index_components_service() -> IndexComponentsService:
    """
    Get singleton instance of IndexComponentsService.

    Returns:
        IndexComponentsService instance

    Educational Notes:
    - Singleton pattern ensures only one instance exists
    - Shares cache across the application
    - Lazy initialization on first call
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = IndexComponentsService()
    return _service_instance
