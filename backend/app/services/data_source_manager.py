"""
Data source management service for handling data source configuration and automatic cleanup.

This service reads configuration from system_config.yaml and detects changes to:
- freq (day/1min)
- source (yahoo/tushare/akshare)
- stock_pool (csi300/csi500/csi800/all/sp500/nasdaq100)
- region (cn/us)

When any of these change, existing data is cleaned up and will be re-downloaded
on the next routine call.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from app.config.qlib import qlib_config
import logging

logger = logging.getLogger(__name__)


class DataSourceManager:
    """Manages data source configuration and automatic cleanup when config changes."""

    def __init__(self):
        # State file to track last known configuration
        self.state_file = Path(qlib_config.qlib_data_path) / ".data_config_state.json"

    def get_current_config(self) -> Dict[str, Any]:
        """Get the current data configuration from system_config.yaml."""
        return {
            "freq": qlib_config.freq,
            "source": qlib_config.source,
            "stock_pool": qlib_config.stock_pool,
            "region": qlib_config.region,
            "config_hash": qlib_config.get_data_config_hash(),
        }

    def get_current_source(self) -> str:
        """Get the current data source from system_config.yaml."""
        return qlib_config.source

    def check_and_handle_config_change(self) -> bool:
        """
        Check if data configuration has changed and handle cleanup if needed.

        Returns:
            bool: True if config changed and cleanup was performed, False otherwise
        """
        try:
            current_config = self.get_current_config()
            current_hash = current_config["config_hash"]

            # Check if state file exists
            if not self.state_file.exists():
                logger.info(
                    f"No existing data config state found, initializing with: {current_hash}"
                )
                self._save_config_state(current_config)
                return False

            # Read existing state
            with open(self.state_file, "r") as f:
                saved_state = json.load(f)

            previous_hash = saved_state.get("config_hash")

            # Check if config has changed
            if previous_hash != current_hash:
                logger.warning(
                    f"Data configuration changed:\n"
                    f"  Previous: {previous_hash}\n"
                    f"  Current:  {current_hash}\n"
                    f"Cleaning up existing data to ensure consistency."
                )

                # Perform cleanup
                self._cleanup_existing_data()

                # Update state
                self._save_config_state(current_config)

                return True

            return False

        except Exception as e:
            logger.error(f"Error checking data config change: {e}")
            return False

    def _cleanup_existing_data(self):
        """Clean up existing Qlib data and CSV data."""
        try:
            # Clean up day-level Qlib data directory
            qlib_data_day = Path(qlib_config.qlib_data_path_day)
            if qlib_data_day.exists():
                for item in qlib_data_day.iterdir():
                    if item.name != ".data_config_state.json":
                        if item.is_dir():
                            shutil.rmtree(item)
                            logger.info(f"Removed directory: {item}")
                        else:
                            item.unlink()
                            logger.info(f"Removed file: {item}")

            # Clean up minute-level Qlib data directory
            qlib_data_1min = Path(qlib_config.qlib_data_path_1min)
            if qlib_data_1min.exists():
                for item in qlib_data_1min.iterdir():
                    if item.name != ".data_config_state.json":
                        if item.is_dir():
                            shutil.rmtree(item)
                            logger.info(f"Removed directory: {item}")
                        else:
                            item.unlink()
                            logger.info(f"Removed file: {item}")

            # Clean up CSV data directory
            csv_data_path = Path(qlib_config.csv_data_path)
            if csv_data_path.exists():
                shutil.rmtree(csv_data_path)
                logger.info(f"Removed CSV data directory: {csv_data_path}")

            logger.info("Data cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
            raise

    def _save_config_state(self, config: Dict[str, Any]):
        """Save current data configuration state."""
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                **config,
                "last_updated": datetime.now().isoformat(),
                "version": "2.0",
            }

            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)

            logger.info(f"Saved data config state: {config['config_hash']}")

        except Exception as e:
            logger.error(f"Error saving data config state: {e}")
            raise

    def has_data(self) -> bool:
        """
        Check if Qlib data exists for current configuration.

        Returns:
            bool: True if data exists, False otherwise
        """
        qlib_data_path = Path(qlib_config.qlib_data_path)

        # Check for essential Qlib data directories
        features_dir = qlib_data_path / "features"
        calendars_dir = qlib_data_path / "calendars"
        instruments_dir = qlib_data_path / "instruments"

        has_features = (
            features_dir.exists() and any(features_dir.iterdir())
            if features_dir.exists()
            else False
        )
        has_calendars = (
            calendars_dir.exists() and any(calendars_dir.iterdir())
            if calendars_dir.exists()
            else False
        )
        has_instruments = (
            instruments_dir.exists() and any(instruments_dir.iterdir())
            if instruments_dir.exists()
            else False
        )

        return has_features and has_calendars and has_instruments

    def get_download_date_range(self) -> tuple:
        """
        Get the date range for data download based on current freq configuration.

        Returns:
            tuple: (start_date, end_date) as strings in YYYY-MM-DD format
        """
        from datetime import datetime, timedelta

        end_date = datetime.now()
        download_days = qlib_config.download_days
        start_date = end_date - timedelta(days=download_days)

        return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    def get_config_info(self) -> Dict[str, Any]:
        """Get information about the current data configuration."""
        current_config = self.get_current_config()

        try:
            saved_state = None
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    saved_state = json.load(f)

            return {
                "current_config": current_config,
                "has_data": self.has_data(),
                "state_exists": saved_state is not None,
                "last_updated": (
                    saved_state.get("last_updated") if saved_state else None
                ),
                "download_range": self.get_download_date_range(),
            }
        except Exception as e:
            logger.error(f"Error getting config info: {e}")
            return {
                "current_config": current_config,
                "has_data": False,
                "error": str(e),
            }


# Global instance
data_source_manager = DataSourceManager()
