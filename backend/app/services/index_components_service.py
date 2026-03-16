"""
Index Components Service - Multi-source stock components fetching.

This service provides a unified interface to fetch index constituent stocks
from multiple data sources:
- tushare: Tushare Pro API for A-share market (CSI300, CSI500, CSI800, CSI1000, Dividend)
- eod: EOD Historical Data API for US market (SP500, NASDAQ100, DJIA)
- file: Local text file (backup/custom indices)

Educational Notes:
- Reads configuration from index_config.yaml
- Returns stock codes in Qlib standard format (SH600519, SZ000858 for A-shares, AAPL for US)
- Supports caching to avoid frequent API calls
- Provides clear error messages for debugging
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import yaml

from app.core.config import settings

logger = logging.getLogger(__name__)


class IndexComponentsService:
    """
    Service for fetching index constituent stocks from multiple sources.

    Supported data sources:
    - tushare: Tushare Pro API for A-share market
    - eod: EOD Historical Data API for US market
    - file: Local file fallback
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
        return self.config.get("active_index", "csi300")

    def get_index_config(self, index_name: str) -> dict:
        """
        Get configuration for a specific index.

        Args:
            index_name: Index identifier (e.g., 'csi300', 'dividend')

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

        # Fetch from appropriate source
        if source == "tushare":
            index_code = index_config.get("components_index_code")
            components = self._get_from_tushare(index_code)
        elif source == "eod":
            index_code = index_config.get("components_index_code")
            components = self._get_from_eod(index_code)
        elif source == "file":
            file_path = index_config.get("components_file")
            components = self._get_from_file(file_path)
        else:
            raise ValueError(
                f"Unsupported components source: {source}. Supported: tushare, eod, file"
            )

        # Cache results
        self.cache[index_name] = components
        logger.info(f"Fetched {len(components)} components for {index_name}")

        return components

    def _get_from_tushare(self, index_code: str) -> List[str]:
        """
        Fetch components from Tushare Pro API.

        Args:
            index_code: Tushare index code (e.g., '000300.SH' for CSI300)

        Returns:
            List of stock codes in Qlib format (e.g., ['SH600519', 'SZ000858'])

        Educational Notes:
        - Tushare is the primary data source for A-share market
        - Requires TUSHARE_TOKEN environment variable
        - Returns codes in Qlib format for consistency
        """
        try:
            from app.services.data_collectors.tushare_collector import (
                TushareDataCollector,
            )

            logger.info(f"Fetching components for index {index_code} from Tushare")

            # Use static method from TushareDataCollector
            components = TushareDataCollector.get_index_components(index_code)

            logger.info(f"Tushare returned {len(components)} components")
            if components:
                logger.info(f"Sample: {components[:5]}")

            return components

        except Exception as e:
            logger.error(f"Error fetching from Tushare: {e}")
            raise

    def _get_from_eod(self, index_code: str) -> List[str]:
        """
        Fetch components from EOD Historical Data API.

        Args:
            index_code: EOD index code (e.g., 'GSPC.INDX' for S&P 500)

        Returns:
            List of stock codes in Qlib format (e.g., ['AAPL', 'MSFT'])

        Educational Notes:
        - EOD Historical Data is the primary source for US stocks
        - Requires EOD_API_KEY environment variable
        - Returns codes in Qlib format for consistency
        """
        try:
            from app.services.data_collectors.eod_collector import EODDataCollector

            logger.info(f"Fetching components for index {index_code} from EOD")

            # Use static method from EODDataCollector
            components = EODDataCollector.get_index_components(index_code)

            logger.info(f"EOD returned {len(components)} components")
            if components:
                logger.info(f"Sample: {components[:5]}")

            return components

        except Exception as e:
            logger.error(f"Error fetching from EOD: {e}")
            raise

    def _get_from_file(self, file_path: str) -> List[str]:
        """
        Read components from local text file.

        Args:
            file_path: Path to text file with one stock code per line

        Returns:
            List of stock codes

        Educational Notes:
        - Useful for custom indices or offline testing
        - File should contain one stock code per line
        - Codes should already be in Qlib format
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Components file not found: {file_path}")

            with open(path, "r", encoding="utf-8") as f:
                codes = [line.strip() for line in f if line.strip()]

            logger.info(f"Read {len(codes)} components from file: {file_path}")
            return codes

        except Exception as e:
            logger.error(f"Error reading components from file: {e}")
            raise


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
