"""
Yahoo Finance Data Collector.
This module implements a data collector for Yahoo Finance using the yfinance library.

Educational Notes:
- yfinance is a popular Python library for accessing Yahoo Finance data
- It provides OHLCV data, adjusted prices, dividends, and stock splits
- Free to use, no API key required
- Data quality is generally good for US and major international markets
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    raise ImportError(
        "yfinance is required for YahooCollector. "
        "Install it with: pip install yfinance"
    )
from .base_collector import BaseCollector
from .field_config import STANDARD_FIELDS

logger = logging.getLogger(__name__)


class YahooCollector(BaseCollector):
    """
    Data collector for Yahoo Finance.

    This collector uses the yfinance library to fetch stock data from Yahoo Finance.
    """

    def get_collector_name(self) -> str:
        """Get the collector name."""
        return "yahoo"

    def get_supported_fields(self) -> List[str]:
        """
        Get fields supported by Yahoo Finance.

        Returns:
            List of supported field names

        Educational Notes:
        - Yahoo Finance provides: open, high, low, close, volume, adj_close
        - We calculate 'factor' from close / adj_close
        - vwap, amount, turnover are NOT available (will be filled with NaN)
        """
        return [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "factor",  # calculated field: close / adj_close
            # Note: 'vwap', 'amount', 'turnover' not available from Yahoo Finance
        ]

    def collect_data(
        self,
        instruments: List[str],
        start_date: str,
        end_date: str,
        output_dir: Optional[Path] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Collect data from Yahoo Finance.

        Args:
            instruments: List of ticker symbols (e.g., ['AAPL', 'MSFT'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_dir: Directory to store CSV and .bin files
            **kwargs: Additional parameters:
                - interval: Data interval ('1d', '1wk', '1mo'), default '1d'
                - auto_adjust: Whether to use auto-adjusted prices, default False

        Returns:
            Result dictionary with collection status

        Educational Notes:
        - This method orchestrates the entire data collection process
        - Steps: fetch -> convert -> validate -> save CSV -> convert to .bin
        - Errors for individual instruments are logged but don't stop the process
        """
        self.logger.info(
            f"Starting Yahoo Finance data collection for {len(instruments)} instruments "
            f"from {start_date} to {end_date}"
        )

        # Handle output_dir
        if output_dir is None:
            output_dir = Path.home() / ".qlib" / "stock_data"
        else:
            output_dir = Path(output_dir)

        # Create directories
        csv_dir = output_dir / "csv"
        qlib_dir = output_dir / "qlib_data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Get optional parameters
        interval = kwargs.get("interval", "1d")
        auto_adjust = kwargs.get("auto_adjust", False)

        # Track results
        successful_instruments = []
        failed_instruments = []
        errors = []

        # Fetch data for each instrument
        for instrument in instruments:
            try:
                self.logger.info(f"Fetching data for {instrument}...")

                # Fetch data using yfinance
                df = self._fetch_instrument_data(
                    instrument=instrument,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    auto_adjust=auto_adjust,
                )

                if df is None or df.empty:
                    error_msg = f"No data returned for {instrument}"
                    self.logger.warning(error_msg)
                    failed_instruments.append(instrument)
                    errors.append(error_msg)
                    continue

                # Convert to standard format
                df = self._convert_to_standard_format(df)

                # Ensure all standard fields exist
                df = self._ensure_all_fields(df)

                # Save as CSV
                csv_file = csv_dir / f"{instrument}.csv"
                df.to_csv(csv_file, index=True)

                successful_instruments.append(instrument)
                self.logger.info(
                    f"Successfully saved {len(df)} rows for {instrument} to {csv_file}"
                )
            except Exception as e:
                error_msg = f"Error collecting data for {instrument}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                failed_instruments.append(instrument)
                errors.append(error_msg)

        # Check if we have any successful data
        if not successful_instruments:
            return {
                "collector": "yahoo",
                "total_instruments": len(instruments),
                "successful_count": 0,
                "csv_dir": str(csv_dir),
                "qlib_dir": str(qlib_dir),
                "errors": errors,
            }

        # Convert CSV to .bin format
        self.logger.info("Converting CSV files to .bin format...")
        conversion_result = self._convert_csv_to_bin(
            csv_dir=csv_dir,
            qlib_dir=qlib_dir,
            freq="day" if interval == "1d" else interval,
        )

        # Prepare final result
        result = {
            "collector": "yahoo",
            "total_instruments": len(instruments),
            "successful_count": len(successful_instruments),
            "csv_dir": str(csv_dir),
            "qlib_dir": str(qlib_dir),
            "errors": errors,
        }

        self.logger.info(
            f"Data collection completed: {len(successful_instruments)} succeeded, "
            f"{len(failed_instruments)} failed"
        )

        return result

    def _fetch_instrument_data(
        self,
        instrument: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        auto_adjust: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch data for a single instrument from Yahoo Finance.

        Args:
            instrument: Ticker symbol (e.g., 'AAPL', '600000.SS')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval ('1d', '1wk', '1mo')
            auto_adjust: Whether to use auto-adjusted prices

        Returns:
            DataFrame with OHLCV data, or None if fetch failed

        Educational Notes:
        - yf.Ticker() creates a ticker object
        - .history() fetches historical data
        - auto_adjust=False ensures we get both Close and Adj Close
        - This allows us to calculate the adjustment factor
        """
        try:
            ticker = yf.Ticker(instrument)

            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=auto_adjust,
            )

            return df
        except Exception as e:
            self.logger.error(
                f"Error fetching data for {instrument}: {e}", exc_info=True
            )
            return None

    def _convert_to_standard_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert yfinance DataFrame to our standard format.

        Args:
            df: DataFrame from yfinance

        Returns:
            DataFrame with standardized column names and calculated fields

        Educational Notes:
        - yfinance uses capitalized column names (Open, High, Low, Close, Volume)
        - We convert to lowercase for consistency
        - We calculate 'factor' as close / adj_close
        - factor represents the cumulative adjustment ratio (splits, dividends)

        Factor Calculation Example:
        - If a stock has a 2-for-1 split, factor would be ~2.0
        - If adj_close is missing, we set factor to 1.0 (no adjustment)
        """

        # Create a new DataFrame with standard column names
        result = pd.DataFrame(index=df.index)

        # Rename index to 'date' if it's not already
        result.index.name = "date"

        # Map yfinance columns to our standard fields
        column_mapping = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
            "Adj Close": "adj_close",
        }

        for yf_col, std_col in column_mapping.items():
            if yf_col in df.columns:
                result[std_col] = df[yf_col]

        # Calculate factor (adjustment factor)
        if "close" in result.columns and "adj_close" in result.columns:
            # factor = close / adj_close
            # Avoid division by zero
            result["factor"] = result["close"] / result["adj_close"].replace(
                0, float("nan")
            )
        else:
            # If adj_close is not available, set factor to 1.0 (no adjustment)
            result["factor"] = 1.0

        return result
