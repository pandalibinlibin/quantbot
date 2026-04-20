#!/usr/bin/env python3
"""
YahooQuery Field Exploration Test Script

This script explores yahooquery library functionality and data field structure
to help configure BaseCollector metadata and design proper normalize modules.

Purpose:
- Test yahooquery basic functionality in Docker environment
- Explore available data fields for different markets (CN/US)
- Analyze data structure and format for proper BaseCollector integration
- Generate field metadata for YahooDataCollector configuration

Educational Notes:
- yahooquery is the official library used by Qlib's YahooCollector
- Understanding field structure is crucial for BaseCollector metadata configuration
- Different markets may have different available fields
- Field analysis helps design proper normalize and validation logic
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from yahooquery import Ticker

    logger.info("yahooquery imported successfully")
except ImportError as e:
    logger.error(f"Failed to import yahooquery: {e}")
    sys.exit(1)


def test_basic_functionality():
    """
    Test basic yahooquery functionality.

    Based on yahooquery documentation research:
    - Ticker class is the main interface for company data
    - Can accept single symbol or multiple symbols
    - Provides various data properties and methods

    Returns
    -------
    bool
        True if basic functionality works, False otherwise
    """
    logger.info("Testing basic yahooquery functionality")

    try:
        # Test with a simple US stock (based on documentation examples)
        ticker = Ticker("AAPL")
        logger.info("Ticker object created successfully for AAPL")

        # Test basic info access (from documentation: asset_profile is available)
        try:
            info = ticker.asset_profile
            if info and isinstance(info, dict) and len(info) > 0:
                logger.info("Basic ticker info accessible - dict format")
            elif info and hasattr(info, "empty") and not info.empty:
                logger.info("Basic ticker info accessible - DataFrame format")
            else:
                logger.warning("Ticker info is empty or None")
        except Exception as e:
            logger.warning(f"Could not access asset_profile: {e}")

        # If we reach here, basic functionality is working
        return True

    except Exception as e:
        logger.error(f"Basic functionality test failed: {e}")
        return False


def explore_history_fields(symbol, market, period="1mo", interval="1d"):
    """
    Explore historical data fields for a specific symbol.

    Primary purpose: Discover what fields yahooquery returns
    This information is crucial for configuring BaseCollector metadata.

    Parameters
    ----------
    symbol : str
        Stock symbol (e.g., "AAPL", "000001.SZ")
    market : str
        Market identifier for logging
    period : str
        Data period (default: "1mo")
    interval : str
        Data interval (default: "1d")

    Returns
    -------
    list or None
        List of column names returned by yahooquery, None if failed
    """
    logger.info(f"Testing fields for {symbol} ({market}) - {period}, {interval}")

    try:
        ticker = Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)

        if hist is None or hist.empty:
            logger.warning(f"No data returned for {symbol}")
            return None

        # The key information: what fields does yahooquery return?
        fields = list(hist.columns)
        logger.info(f"Fields returned: {fields}")

        # Show data types for each field
        for field in fields:
            dtype = hist[field].dtype
            logger.info(f"  {field}: {dtype}")

        # Show sample values to understand the data
        logger.info("Sample data (first row):")
        first_row = hist.iloc[0]
        for field in fields:
            logger.info(f"  {field}: {first_row[field]}")

        return fields

    except Exception as e:
        logger.error(f"Failed to get fields for {symbol}: {e}")
        return None


def test_adjustment_parameters(symbol, market):
    """
    Test different adjustment parameters in history() method.

    Based on research, yahooquery may use different parameter names
    than expected. Let's test the actual available parameters.

    Parameters
    ----------
    symbol : str
        Stock symbol to test
    market : str
        Market identifier for logging
    """
    logger.info(f"Testing adjustment parameters for {symbol} ({market})")

    try:
        ticker = Ticker(symbol)

        # Test default behavior first
        logger.info("Testing default behavior")
        hist_default = ticker.history(period="1mo", interval="1d")

        if hist_default is not None and not hist_default.empty:
            first_row_default = hist_default.iloc[0]
            logger.info(f"  Default - close: {first_row_default['close']}")
            if "adjclose" in hist_default.columns:
                logger.info(f"  Default - adjclose: {first_row_default['adjclose']}")

                # Compare close and adjclose to see if they're different
                close_val = first_row_default["close"]
                adjclose_val = first_row_default["adjclose"]
                diff = abs(close_val - adjclose_val)
                logger.info(f"  Difference between close and adjclose: {diff}")

                if diff < 0.01:
                    logger.info("  Result: close and adjclose are nearly identical")
                else:
                    logger.info("  Result: close and adjclose are different")
                    logger.info(
                        "  This suggests close may already be adjusted, or adjclose contains the adjustment"
                    )

        return True

    except Exception as e:
        logger.error(f"Failed to test adjustment parameters for {symbol}: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting YahooQuery Field Exploration")
    logger.info(f"Test Time: {datetime.now()}")
    logger.info(f"Python Version: {sys.version}")

    # Test basic functionality first
    if test_basic_functionality():
        logger.info("Basic functionality test passed")
    else:
        logger.error("Basic functionality test failed. Exiting.")
        sys.exit(1)

    # Test history field exploration
    logger.info("=" * 60)
    logger.info("TESTING HISTORY FIELD EXPLORATION")
    logger.info("=" * 60)

    # Test US market symbol
    us_fields = explore_history_fields("AAPL", "US")
    if us_fields:
        logger.info(f"US market fields discoverd: {us_fields}")
    else:
        logger.warning("Failed to get US market fields")

    # Test CN market symbol
    cn_fields = explore_history_fields("000001.SZ", "CN")
    if cn_fields:
        logger.info(f"CN market fields discovered: {cn_fields}")
    else:
        logger.warning("Failed to get CN market fields")

    # Test adjustment parameters
    logger.info("=" * 60)
    logger.info("TESTING ADJUSTMENT PARAMETERS")
    logger.info("=" * 60)

    # Test US stock
    test_adjustment_parameters("AAPL", "US")

    # Test Chinese stock
    test_adjustment_parameters("000001.SZ", "CN")
