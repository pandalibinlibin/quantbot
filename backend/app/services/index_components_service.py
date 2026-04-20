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
import time

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
        elif source == "tushare_etf":
            # ETF universe screening
            components = self._get_etf_universe(index_config)
        elif source == "eod":
            index_code = index_config.get("components_index_code")
            components = self._get_from_eod(index_code)
        elif source == "file":
            file_path = index_config.get("components_file")
            components = self._get_from_file(file_path)
        else:
            raise ValueError(
                f"Unsupported components source: {source}. Supported: tushare, tushare_etf, eod, file"
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
            logger.error(f"Error reading file {file_path}: {e}")
            raise

    def _get_etf_universe(self, index_config: dict) -> List[str]:
        """
        Get ETF universe by selecting top ETFs by fund size.

        Uses Tushare etf_basic and etf_share_size interfaces.

        Args:
            index_config: ETF universe configuration

        Returns:
            List of ETF codes in Qlib format (e.g., ['SH510300', 'SZ159919'])
        """
        try:
            import tushare as ts
            import pandas as pd
            from datetime import datetime, timedelta
            from pathlib import Path

            logger.info("Fetching ETF universe from Tushare")

            # Read Tushare token
            token_file = Path.home() / ".tushare_token"
            if not token_file.exists():
                raise ValueError("Tushare token not found")

            with open(token_file, "r") as f:
                token = f.read().strip()

            pro = ts.pro_api(token)

            # Get screening parameters
            top_n = index_config.get("top_n_etfs", 100)
            logger.info(f"Selecting top {top_n} ETFs by fund size")

            # Get ETF basic information using etf_basic interface
            logger.info("Getting ETF basic information...")
            etf_basic = pro.etf_basic(
                list_status="L",
                fields="ts_code,extname,index_code,index_name,exchange,mgr_name",
            )
            logger.info(f"Retrieved {len(etf_basic)} listed ETFs")

            # Get ETF fund size using etf_share_size interface
            logger.info("Getting ETF fund sizes...")
            etf_sizes = None

            for days_ago in range(1, 15):
                try:
                    trade_date = (datetime.now() - timedelta(days=days_ago)).strftime(
                        "%Y%m%d"
                    )
                    etf_sizes = pro.etf_share_size(
                        trade_date=trade_date,
                        fields="ts_code,etf_name,total_share,total_size",
                    )
                    if etf_sizes is not None and not etf_sizes.empty:
                        logger.info(
                            f"Got size data for {trade_date}: {len(etf_sizes)} records"
                        )
                        break
                except Exception as e:
                    logger.debug(f"No data for {trade_date}: {e}")
                    continue

            if etf_sizes is None or etf_sizes.empty:
                raise ValueError("No ETF size data available")

            # Merge and sort by size
            etf_with_size = etf_basic.merge(
                etf_sizes[["ts_code", "total_size", "etf_name"]],
                on="ts_code",
                how="inner",
            )
            etf_with_size = etf_with_size.sort_values("total_size", ascending=False)
            logger.info(f"Found {len(etf_with_size)} ETFs with size data")

            # Select top N ETFs
            top_etfs = etf_with_size.head(top_n)

            # Convert to Qlib format
            qualified_etfs = []
            for _, etf in top_etfs.iterrows():
                ts_code = etf["ts_code"]

                if ts_code.endswith(".SH"):
                    qlib_code = "SH" + ts_code[:6]
                elif ts_code.endswith(".SZ"):
                    qlib_code = "SZ" + ts_code[:6]
                else:
                    continue

                qualified_etfs.append(qlib_code)

                if len(qualified_etfs) <= 10:
                    size_yi = etf["total_size"] / 10000  # 万元转亿元
                    name = etf.get("etf_name", etf.get("extname", ""))[:15]
                    logger.info(
                        f"Top ETF: {qlib_code} ({name}) - 规模: {size_yi:.1f}亿元"
                    )

            logger.info(f"Selected {len(qualified_etfs)} ETFs by fund size")

            if len(qualified_etfs) == 0:
                raise ValueError("No qualified ETFs found")

            return qualified_etfs

        except Exception as e:
            logger.error(f"Error fetching ETF universe: {e}")
            fallback_etfs = [
                "SH510300",
                "SH510500",
                "SZ159919",
                "SZ159915",
                "SH512100",
                "SH510050",
                "SZ159949",
                "SH588000",
                "SZ159901",
                "SH512690",
            ]
            logger.info(f"Using fallback ETF list: {fallback_etfs}")
            return fallback_etfs


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
