"""
Data collector configuration utilities.
This module provides functions to read and parse data collector field configurations
from YAML files. It supports caching for performance and provides proper error handling.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Path to the configuration file
CONFIG_FILE_PATH = Path(__file__).parent / "data_fields.yaml"


@lru_cache(maxsize=1)
def load_data_fields_config() -> Dict:
    """
    Load data fields configuration from YAML file.

    Use LRU cache to avoid repeated file reads for performance.

    Returns:
        Dict: Configuration dictionary with data source field definitions

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    try:
        if not CONFIG_FILE_PATH.exists():
            raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE_PATH}")

        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        if not config or "data_sources" not in config:
            raise ValueError("Invalid configuration: missing 'data_sources' section")

        logger.info(f"Loaded data fields configuration from {CONFIG_FILE_PATH}")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise


def get_required_fields(data_source: str) -> List[str]:
    """
    Get required fields for a specific data source.

    Args:
        data_source: Name of the data source (e.g., 'yahoo_finance')

    Returns:
        List[str]: List of required field names

    Raises:
        KeyError: If data source is not found in configuration
    """
    config = load_data_fields_config()

    if data_source not in config["data_sources"]:
        available_sources = list(config["data_sources"].keys())
        raise KeyError(
            f"Data source '{data_source}' not found. Available sources: {available_sources}"
        )

    return config["data_sources"][data_source].get("fields", [])


def get_field_descriptions(data_source: str) -> Dict[str, str]:
    """
    Get field descriptions for a specific data source.

    Args:
        data_source: Name of the data source (e.g., 'yahoo_finance')

    Returns:
        Dict[str, str]: Mapping of field names to descriptions

    Raises:
        KeyError: If data source is not found in configuration
    """
    config = load_data_fields_config()

    if data_source not in config["data_sources"]:
        available_sources = list(config["data_sources"].keys())
        raise KeyError(
            f"Data source '{data_source}' not found. Available sources: {available_sources}"
        )

    return config["data_sources"][data_source].get("field_descriptions", {})


def get_available_data_sources() -> List[str]:
    """
    Get list of all available data sources.

    Returns:
        List[str]: List of data source names
    """
    config = load_data_fields_config()

    return list(config["data_sources"].keys())
