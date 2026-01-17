"""
Qlib utility functions for initialization and common operations.
This module provides helper functions to work with Qlib, including:
- Qlib initialization
- Path management
- Data validation
"""

from pathlib import Path
import qlib
from qlib.config import REG_CN, REG_US


def init_qlib(provider_uri: str | None = None, region: str = "cn") -> None:
    """
    Initialize Qlib with specified configuration.

    Qlib needs to be initialized before using its data and models.
    This function handles the initialization process.

    Args:
        provider_uri: Path to Qlib data directory. If None, uses default.
                    Default: ~/.qlib/qlib_data/cn_data or us_data

        region: Market region, either 'cn' or 'us'
                'cn' = China A-share market
                'us' = US stock market

    Example:
        >>> # Initialize with default path
        >>> init_qlib(region="cn")

        >>> # Initialize with custom path
        >>> init_qlib(provider_uri="/data/qlib_data/cn_data", region="cn")

    Note:
        This function is idempotent - calling it multiple times is safe.
        If Qlib is already initialized, it will skip re-initialization.
    """
    if provider_uri is None:
        # Use default path: ~/.qlib/qlib_data/cn_data
        home = Path.home()
        provider_uri = str(home / ".qlib" / "qlib_data" / f"{region}_data")

    # Check if already initialized
    try:
        # Try to get Qlib's logger - if it works, Qlib is initialized
        qlib.get_module_logger("qlib")
        return  # Already initialized, skip
    except Exception:
        pass  # Not initialized yet, continue

    # Initialize Qlib
    region_config = REG_CN if region == "cn" else REG_US
    qlib.init(
        provider_uri=provider_uri,
        region=region_config,
        auto_mount=True,  # Automatically mount data provider
    )


def get_qlib_data_path(region: str = "cn") -> Path:
    """
    Get the default Qlib data path for specified region.

    Args:
        region: Market region, either 'cn' or 'us'

    Returns:
        Path object pointing to Qlib data directory

    Example:
        >>> path = get_qlib_data_path("cn")
        >>> print(path)
        /home/user/.qlib/qlib_data/cn_data
    """
    home = Path.home()

    return home / ".qlib" / "qlib_data" / f"{region}_data"


def ensure_qlib_data_exists(region: str = "cn") -> bool:
    """
    Check if Qlib data exists for the specified region.

    This function checks for the presence of essential Qlib data files:
    - calendars/ directory (trading calendar)
    - instruments/ directory (stock list)
    - features/ directory (market data)

    Args:
        region: Market region, either 'cn' or 'us'

    Returns:
        True if data exists and is valid, False otherwise

    Example:
        >>> if ensure_qlib_data_exists("cn"):
        ...     print("Data is ready")
        ... else:
        ...     print("Please download data first")
    """
    data_path = get_qlib_data_path(region)

    # Check if data directory exists
    if not data_path.exists():
        return False

    # Check for essential subdirectories
    calendars_dir = data_path / "calendars"
    instruments_dir = data_path / "instruments"
    features_dir = data_path / "features"

    return calendars_dir.exists() and instruments_dir.exists() and features_dir.exists()
