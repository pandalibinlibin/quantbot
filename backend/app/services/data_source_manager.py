"""
Data source management service for handling data source configuration and automatic cleanup.
"""

import json
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DataSourceManager:
    """Manages data source configuration and automatic cleanup when source changes."""

    def __init__(self):
        self.config_file = Path(settings.QLIB_DATA_PATH) / "data_source_config.json"
        self.current_source = settings.DATA_SOURCE

    def get_current_source(self) -> str:
        """Get the currently configured data source."""
        return self.current_source

    def check_and_handle_source_change(self) -> bool:
        """
        Check if data source has changed and handle cleanup if needed.

        Returns:
            bool: True if source changed and cleanup was performed, False otherwise
        """
        try:
            # Check if config file exists
            if not self.config_file.exists():
                logger.info(
                    f"No existing data source config found, initializing with {self.current_source}"
                )
                self._save_source_config()
                return False

            # Read existing config
            with open(self.config_file, "r") as f:
                config = json.load(f)

            previous_source = config.get("data_source")

            # Check if source has changed
            if previous_source != self.current_source:
                logger.warning(
                    f"Data source changed from '{previous_source}' to '{self.current_source}'. "
                    f"Cleaning up existing data to prevent inconsistency."
                )

                # Perform cleanup
                self._cleanup_existing_data()

                # Update config
                self._save_source_config()

                return True

            return False

        except Exception as e:
            logger.error(f"Error checking data source change: {e}")
            # If we can't determine, assume no change to be safe
            return False

    def _cleanup_existing_data(self):
        """Clean up existing Qlib data and CSV data."""
        try:
            # Clean up Qlib data directory
            qlib_data_path = Path(settings.QLIB_DATA_PATH)
            if qlib_data_path.exists():
                # Remove all contents except the config file we're about to update
                for item in qlib_data_path.iterdir():
                    if item.name != "data_source_config.json":
                        if item.is_dir():
                            shutil.rmtree(item)
                            logger.info(f"Removed directory: {item}")
                        else:
                            item.unlink()
                            logger.info(f"Removed file: {item}")

            # Clean up CSV data directory
            csv_data_path = Path(settings.CSV_DATA_PATH)
            if csv_data_path.exists():
                shutil.rmtree(csv_data_path)
                logger.info(f"Removed CSV data directory: {csv_data_path}")

            logger.info("Data cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
            raise

    def _save_source_config(self):
        """Save current data source configuration."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            config = {
                "data_source": self.current_source,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }

            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)

            logger.info(f"Saved data source config: {self.current_source}")

        except Exception as e:
            logger.error(f"Error saving data source config: {e}")
            raise

    def get_source_info(self) -> dict:
        """Get information about the current data source configuration."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                return {
                    "current_source": self.current_source,
                    "config_exists": True,
                    "last_updated": config.get("last_updated"),
                    "version": config.get("version", "unknown"),
                }
            else:
                return {
                    "current_source": self.current_source,
                    "config_exists": False,
                    "last_updated": None,
                    "version": None,
                }
        except Exception as e:
            logger.error(f"Error getting source info: {e}")
            return {
                "current_source": self.current_source,
                "config_exists": False,
                "error": str(e),
            }


# Global instance
data_source_manager = DataSourceManager()
