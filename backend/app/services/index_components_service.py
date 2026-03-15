"""
Index Components Service - Multi-source stock components fetching

This service provides a unified interface to fetch index constituent stocks
from multiple data sources:
- yfiua_api: yfiua.github.io JSON API (CSI300, CSI500, SP500, NASDAQ100)
- akshare: AKShare library (Dividend Index, CSI1000, etc.)
- file: Local text file (backup/custom indices)

Educational Notes:
- Reads configuration from index_config.yaml
- Returns stock codes in Qlib standard format (SH600519, SZ000858)
- Supports caching to avoid frequent API calls
- Provides clear error messages for debugging
"""

import logging
import json
import requests
from typing import List, Dict, Optional
from pathlib import Path
import yaml

from app.core.config import settings

logger = logging.getLogger(__name__)

# Request headers for API calls
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Connection": "keep-alive",
}

# yfiua API configuration
YFIUA_API_CONFIG = {
    "base_url": "https://yfiua.github.io/index-constituents",
    "endpoints": {
        "CSI300": "/constituents-csi300.json",
        "CSI500": "/constituents-csi500.json",
        "SP500": "/constituents-sp500.json",
        "NASDAQ100": "/constituents-nasdaq100.json",
    },
}


class IndexComponentsService:
    """
    Service for fetching index constituent stocks from multiple sources.

    Supports:
    - yfiua_api: Fast, reliable API for major indices
    - akshare: Python library for Chinese market data
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
        if source == "yfiua_api":
            api_key = index_config.get("components_api_key")
            components = self._get_from_yfiua(api_key)
        elif source == "akshare":
            index_code = index_config.get("components_index_code")
            components = self._get_from_akshare(index_code)
        elif source == "file":
            file_path = index_config.get("components_file")
            components = self._get_from_file(file_path)
        else:
            raise ValueError(f"Unsupported components source: {source}")

        # Cache results
        self.cache[index_name] = components
        logger.info(f"Fetched {len(components)} components for {index_name}")

        return components

    def _get_from_yfiua(self, api_key: str) -> List[str]:
        """
        Fetch components from yfiua.github.io API.

        Args:
            api_key: API endpoint key (e.g., 'CSI300', 'CSI500')

        Returns:
            List of stock codes in Qlib format

        Educational Notes:
        - API returns symbols in Yahoo Finance format (e.g., '000001.SZ')
        - Need to convert to Qlib format (e.g., 'SZ000001')
        - API is fast and reliable for major indices
        """
        try:
            # Build API URL
            endpoint = YFIUA_API_CONFIG["endpoints"].get(api_key)
            if not endpoint:
                raise ValueError(f"Unknown yfiua API key: {api_key}")

            api_url = YFIUA_API_CONFIG["base_url"] + endpoint
            logger.info(f"Fetching from yfiua API: {api_url}")

            # Make API request
            response = requests.get(api_url, headers=REQUEST_HEADERS, timeout=30)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()
            logger.info(f"yfiua API returned {len(data)} items")

            # Extract and convert symbols
            symbols = []
            for item in data:
                if isinstance(item, dict) and "Symbol" in item:
                    yahoo_symbol = item["Symbol"].strip()
                    if yahoo_symbol:
                        # Convert Yahoo format to Qlib format
                        qlib_symbol = self._convert_yahoo_to_qlib(yahoo_symbol)
                        symbols.append(qlib_symbol)

            logger.info(f"Converted {len(symbols)} symbols to Qlib format")
            logger.info(f"Sample: {symbols[:5]}")
            return symbols

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching from yfiua API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching from yfiua API: {e}")
            raise

    def _get_from_akshare(self, index_code: str) -> List[str]:
        """
        Fetch components from AKShare library.

        Args:
            index_code: Index code for AKShare (e.g., '000015' for dividend index)

        Returns:
            List of stock codes in Qlib format

        Educational Notes:
        - AKShare provides comprehensive Chinese market data
        - Requires akshare package to be installed
        - Need to add exchange prefix to match Qlib format
        """
        try:
            import akshare as ak

            logger.info(f"Fetching components for index {index_code} from AKShare")

            # Fetch index components
            # AKShare function: index_stock_cons(symbol="000300")
            df = ak.index_stock_cons(symbol=index_code)

            # Extract stock codes
            # Column name might be '品种代码' or 'code' depending on AKShare version
            if "品种代码" in df.columns:
                raw_codes = df["品种代码"].tolist()
            elif "code" in df.columns:
                raw_codes = df["code"].tolist()
            else:
                raise ValueError(
                    f"Unknown column format in AKShare response: {df.columns}"
                )

            # Convert to Qlib format by adding exchange prefix
            codes = []
            for code in raw_codes:
                code = str(code).strip()
                if not code:
                    continue
                # Add exchange prefix based on code pattern
                # Shanghai: 60xxxx, 688xxx (科创板)
                # Shenzhen: 00xxxx, 30xxxx (创业板), 002xxx (中小板)
                if code.startswith(("60", "688")):
                    qlib_code = f"SH{code}"
                elif code.startswith(("00", "30", "002")):
                    qlib_code = f"SZ{code}"
                else:
                    # Unknown pattern, log warning and skip
                    logger.warning(f"Unknown stock code pattern: {code}, skipping")
                    continue
                codes.append(qlib_code)

            logger.info(f"AKShare returned {len(codes)} components")
            logger.info(f"Sample: {codes[:5]}")
            return codes

        except ImportError:
            logger.error("AKShare not installed. Install with: pip install akshare")
            raise
        except Exception as e:
            logger.error(f"Error fetching from AKShare: {e}")
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

    def _convert_yahoo_to_qlib(self, yahoo_symbol: str) -> str:
        """
        Convert Yahoo Finance symbol to Qlib format.

        Args:
            yahoo_symbol: Symbol in Yahoo format (e.g., '000001.SZ', '600519.SS')

        Returns:
            Symbol in Qlib format (e.g., 'SZ000001', 'SH600519')

        Educational Notes:
        - Yahoo uses suffix: .SZ for Shenzhen, .SS for Shanghai
        - Qlib uses prefix: SZ for Shenzhen, SH for Shanghai
        - US stocks remain unchanged (e.g., 'AAPL')
        """
        if "." in yahoo_symbol:
            code, exchange = yahoo_symbol.split(".")
            if exchange == "SZ":
                return f"SZ{code}"
            elif exchange == "SS":
                return f"SH{code}"
            else:
                # Unknown exchange, return as-is
                return yahoo_symbol
        else:
            # No exchange suffix (US stocks), return as-is
            return yahoo_symbol


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
