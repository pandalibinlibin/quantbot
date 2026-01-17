"""
Data collection service for managing market data downloads.
This service orchestrates data collection from various sources
and manages the data lifecycle.
"""

from pathlib import Path
from .data_sources.qlib_yahoo_source import QlibYahooDataSource
from .qlib_utils import ensure_qlib_data_exists, get_qlib_data_path, init_qlib


class DataCollectorService:
    """
    Service for collecting and managing market data.

    This service provides a high-level interface for:
    - Downloading data from various sources
    - Checking data status
    - Managing data updates

    Example:
        >>> service = DataCollectorService(region="cn")
        >>> result = service.download_data(source="qlib_yahoo")
        >>> if result["status"] == "success":
        ...     print("Data downloaded successfully")
    """

    def __init__(self, region: str = "cn"):
        """
        Initialize data collector service.

        Args:
            region: Market region ('cn' or 'us')
        """
        self.region = region.lower()
        self.qlib_data_path = get_qlib_data_path(self.region)

    def check_data_status(self) -> dict:
        """
        Check if Qlib data exists and is ready to use.

        Returns:
            dict with status information

        Example:
            >>> service = DataCollectorService(region="cn")
            >>> status = service.check_data_status()
            >>> print(status["data_exists"])
            True
        """
        data_exists = ensure_qlib_data_exists(self.region)

        return {
            "region": self.region,
            "data_path": str(self.qlib_data_path),
            "data_exists": data_exists,
            "message": (
                "Data is ready"
                if data_exists
                else "Data not found, please download first"
            ),
        }

    def download_data(
        self,
        source: str = "qlib_yahoo",
        method: str = "prebuilt",
    ) -> dict:
        """
        Download market data from specified source.

        Args:
            source: Data source name ('qlib_yahoo')
            method: Download method:
                - 'prebuilt': Download pre-built data (fast, recommended)
                - 'yahoo': Download from Yahoo Finance (slow, latest data)

        Returns:
            dict with download status and message

        Example:
            >>> service = DataCollectorService(region="cn")
            >>> result = service.download_data(source="qlib_yahoo", method="prebuilt")
            >>> print(result["status"])
            'success'
        """
        if source != "qlib_yahoo":
            return {
                "status": "error",
                "message": f"Unsupported data source: {source}. Currently only 'qlib_yahoo' is supported.",
            }

        # Create data source instance
        config = {
            "region": self.region,
            "qlib_data_dir": str(self.qlib_data_path),
        }
        data_source = QlibYahooDataSource(config)

        # Download data based on method
        if method == "prebuilt":
            result = data_source.download_prebuilt_data()
        else:
            return {
                "status": "error",
                "message": f"Unsupported download method: {method}. Currently only 'prebuilt' is supported.",
            }

        # Initialize Qlib after successful download
        if result["status"] == "success":
            try:
                init_qlib(provider_uri=str(self.qlib_data_path), region=self.region)
                result["qlib_initialized"] = True
            except Exception as e:
                result["qlib_initialized"] = False
                result["qlib_init_error"] = str(e)

        return result

    def get_data_info(self) -> dict:
        """
        Get information about downloaded data.

        Returns:
            dict with data information

        Example:
            >>> service = DataCollectorService(region="cn")
            >>> info = service.get_data_info()
            >>> print(info['calendars_exist'])
            True
        """
        data_path = self.qlib_data_path

        if not data_path.exists():
            return {
                "status": "not_found",
                "message": "Data directory does not exist",
                "data_path": str(data_path),
            }

        # Check subdirectories
        calendars_dir = data_path / "calendars"
        instruments_dir = data_path / "instruments"
        features_dir = data_path / "features"

        return {
            "status": "found",
            "data_path": str(data_path),
            "calendars_exist": calendars_dir.exists(),
            "instruments_exist": instruments_dir.exists(),
            "features_exist": features_dir.exists(),
            "message": "Data directory found",
        }
