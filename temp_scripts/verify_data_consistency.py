#!/usr/bin/env python3
"""
Data Consistency Verification Script

This script verifies that data downloaded from Yahoo Finance API
matches the data stored in Qlib bin format after conversion.

Verification Steps:
1. Fetch fresh data from Yahoo Finance API
2. Compare with existing CSV datatemp_scripts/verify_data_consistency.py
3. Compare with Qlib bin data
4. Generate detailed comparison report

Educational Notes:
- Ensures data integrity throughout the pipeline
- Validates that no data is lost or corrupted during conversion
- Provides confidence in the data processing workflow
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

# Add app directory to Python path
sys.path.append("/app")

from yahooquery import Ticker
import qlib
from qlib.data import D

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataConsistencyVerifier:
    """
    Comprehensive data consistency verification between Yahoo Finance API,
    CSV files, and Qlib bin data.
    """

    def __init__(self):
        self.csv_data_path = Path("/app/csv_data")
        self.qlib_data_path = Path("/app/qlib_data")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_samples": [],
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "warnings": 0,
            },
            "detailed_results": [],
        }

        # Initialize Qlib
        try:
            qlib.init(provider_uri=str(self.qlib_data_path), region="cn")
            logger.info("Qlib initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Qlib: {e}")
            raise

    def select_test_samples(self):
        """
        Select representative test samples for verification.

        Returns samples covering:
        - Different stocks
        - Different time periods
        - Both daily and minute data (if available)
        """
        samples = []

        # Check available data
        cn_data_dir = self.csv_data_path / "cn_data"
        if not cn_data_dir.exists():
            logger.error("No CN data directory found")
            return samples

        # Get available stocks from Qlib data directory
        qlib_features_dir = self.qlib_data_path / "features"
        if not qlib_features_dir.exists():
            logger.error("No Qlib features directory found")
            return samples

        # Get available stock directories from Qlib data
        stock_dirs = [d.name for d in qlib_features_dir.iterdir() if d.is_dir()]
        if not stock_dirs:
            logger.error("No stock directories found in Qlib features")
            return samples

        # Filter to only include stocks that we know exist (deep market stocks)
        # Prefer 000xxx.sz stocks as they are more likely to have complete data
        sz_stocks = [
            stock
            for stock in stock_dirs
            if stock.startswith("000") and stock.endswith(".sz")
        ]

        if len(sz_stocks) >= 3:
            selected_stocks = sz_stocks[:3]
        else:
            # Fallback to any available stocks
            selected_stocks = stock_dirs[:3]

        logger.info(f"Available stock directories: {len(stock_dirs)}")
        logger.info(f"Available SZ stocks: {sz_stocks[:5]}")  # Show first 5 SZ stocks
        logger.info(f"Selected stocks for testing: {selected_stocks}")

        # Get date range from calendar - check for different frequency files
        calendar_files = ["1min.txt", "day.txt"]
        dates = []
        for calendar_filename in calendar_files:
            calendar_file = self.qlib_data_path / "calendars" / calendar_filename
            if calendar_file.exists():
                with open(calendar_file, "r") as f:
                    raw_dates = [line.strip() for line in f if line.strip()]

                # For minute data, extract just the date part
                if calendar_filename == "1min.txt":
                    dates = list(
                        set([d.split()[0] for d in raw_dates])
                    )  # Extract unique dates
                    dates.sort()  # Sort dates
                else:
                    dates = raw_dates
                break

        if dates:
            start_date = dates[0]
            end_date = dates[-1]

            # Select test dates: first, middle, last
            test_dates = [
                start_date,
                dates[len(dates) // 2] if len(dates) > 2 else start_date,
                end_date,
            ]

            for stock in selected_stocks:
                for date in test_dates:
                    samples.append({"stock": stock, "date": date, "interval": "1d"})

                    # Add minute data sample for first stock and first date
                    if stock == selected_stocks[0] and date == test_dates[0]:
                        samples.append({"stock": stock, "date": date, "interval": "1m"})

        self.results["test_samples"] = samples
        logger.info(f"Selected {len(samples)} test samples")
        return samples

    def fetch_yahoo_data(self, stock, date, interval="1d"):
        """
        Fetch fresh data from Yahoo Finance API for comparison.
        """
        try:
            ticker = Ticker(stock)

            if interval == "1d":
                data = ticker.history(start=date, end=date, interval="1d")
            else:  # 1m
                # For minute data, get the whole day
                next_day = (
                    datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
                ).strftime("%Y-%m-%d")
                data = ticker.history(start=date, end=next_day, interval="1m")

            if data is None or data.empty:
                logger.warning(f"No Yahoo data for {stock} on {date}")
                return None

            # Reset index to get date as column
            if isinstance(data.index, pd.MultiIndex):
                data = data.reset_index()
                data = data.set_index("date")

            # Convert column names to lowercase
            data.columns = [col.lower() for col in data.columns]

            # Select OHLCV columns
            required_columns = ["open", "high", "low", "close", "volume"]
            available_columns = [col for col in required_columns if col in data.columns]

            if available_columns:
                data = data[available_columns]

                # Remove timezone info
                if hasattr(data.index, "tz") and data.index.tz is not None:
                    data.index = data.index.tz_localize(None)

                logger.info(
                    f"Fetched Yahoo data for {stock} on {date}: {len(data)} records"
                )
                return data
            else:
                logger.warning(f"No required columns found in Yahoo data for {stock}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch Yahoo data for {stock} on {date}: {e}")
            return None

    def load_csv_data(self, stock, date, interval="1d"):
        """
        Load data from CSV file for comparison.
        """
        try:
            # Try different CSV file naming patterns
            csv_patterns = [
                f"{stock}.csv",  # Direct match: 000001.sz.csv
                f"{stock.upper()}.csv",  # Uppercase: 000001.SZ.csv
                f"{stock.replace('.sz', '.SS')}.csv",  # Convert to Yahoo format: 000001.SS.csv
            ]

            csv_file = None
            for pattern in csv_patterns:
                potential_file = self.csv_data_path / "cn_data" / pattern
                if potential_file.exists():
                    csv_file = potential_file
                    break

            if csv_file is None:
                logger.warning(
                    f"No CSV file found for stock {stock} with any naming pattern"
                )
                return None

            data = pd.read_csv(csv_file, index_col=0, parse_dates=True)

            # Filter by date
            target_date = pd.to_datetime(date).date()

            if interval == "1d":
                # For daily data, exact date match
                filtered_data = data[data.index.date == target_date]
            else:  # 1m
                # For minute data, all records on that date
                filtered_data = data[data.index.date == target_date]

            if filtered_data.empty:
                logger.warning(f"No CSV data for {stock} on {date}")
                return None

            logger.info(
                f"Loaded CSV data for {stock} on {date}: {len(filtered_data)} records"
            )
            return filtered_data

        except Exception as e:
            logger.error(f"Failed to load CSV data for {stock} on {date}: {e}")
            return None

    def load_qlib_data(self, stock, date, interval="1d"):
        """
        Load data from Qlib bin format for comparison.
        """
        try:
            # Convert stock symbol to Qlib format if needed
            qlib_symbol = stock

            # We only have minute data, so always use 1min frequency
            # Add time to make it a full datetime for minute data
            if interval == "1m":
                # For minute data, query the full day
                start_datetime = f"{date} 09:30:00"
                end_datetime = f"{date} 15:00:00"
            else:
                # For daily data, use date only
                start_datetime = date
                end_datetime = date

            data = D.features(
                [qlib_symbol],
                ["$open", "$high", "$low", "$close", "$volume"],
                start_time=start_datetime,
                end_time=end_datetime,
                freq="1min",
            )

            # If interval is 1d, we'll aggregate minute data to daily
            if interval == "1d" and data is not None and not data.empty:
                # Convert MultiIndex to regular DataFrame first
                if isinstance(data.index, pd.MultiIndex):
                    data = data.reset_index()
                    data = data[data["instrument"] == qlib_symbol]
                    data = data.set_index("datetime")

                # Aggregate minute data to daily
                daily_data = (
                    data.resample("D")
                    .agg(
                        {
                            "$open": "first",
                            "$high": "max",
                            "$low": "min",
                            "$close": "last",
                            "$volume": "sum",
                        }
                    )
                    .dropna()
                )

                data = daily_data

            if data is None or data.empty:
                logger.warning(f"No Qlib data for {stock} on {date}")
                return None

            # Convert MultiIndex to regular DataFrame
            if isinstance(data.index, pd.MultiIndex):
                # Reset index and filter by instrument
                data = data.reset_index()
                data = data[data["instrument"] == qlib_symbol]
                data = data.set_index("datetime")

            # Rename columns to match CSV format
            column_mapping = {
                "$open": "open",
                "$high": "high",
                "$low": "low",
                "$close": "close",
                "$volume": "volume",
            }
            data = data.rename(columns=column_mapping)

            # Select only OHLCV columns
            required_columns = ["open", "high", "low", "close", "volume"]
            available_columns = [col for col in required_columns if col in data.columns]
            data = data[available_columns]

            logger.info(f"Loaded Qlib data for {stock} on {date}: {len(data)} records")
            return data

        except Exception as e:
            logger.error(f"Failed to load Qlib data for {stock} on {date}: {e}")
            return None

    def compare_dataframes(self, df1, df2, name1, name2, tolerance=1e-6):
        """
        Compare two DataFrames and return detailed comparison results.
        """
        result = {
            "comparison": f"{name1} vs {name2}",
            "status": "PASS",
            "issues": [],
            "statistics": {},
        }

        if df1 is None and df2 is None:
            result["status"] = "SKIP"
            result["issues"].append("Both datasets are None")
            return result

        if df1 is None or df2 is None:
            result["status"] = "FAIL"
            result["issues"].append(
                f"One dataset is None: {name1}={df1 is not None}, {name2}={df2 is not None}"
            )
            return result

        # Check shape
        if df1.shape != df2.shape:
            result["status"] = "FAIL"
            result["issues"].append(
                f"Shape mismatch: {name1}={df1.shape}, {name2}={df2.shape}"
            )

        # Check columns
        df1_cols = set(df1.columns)
        df2_cols = set(df2.columns)
        if df1_cols != df2_cols:
            result["status"] = "FAIL"
            result["issues"].append(
                f"Column mismatch: {name1}={df1_cols}, {name2}={df2_cols}"
            )

        # Check index alignment
        common_indices = df1.index.intersection(df2.index)
        if len(common_indices) == 0:
            result["status"] = "FAIL"
            result["issues"].append("No common time indices found")
            return result

        # Align DataFrames to common indices and columns
        common_columns = list(df1_cols.intersection(df2_cols))
        df1_aligned = df1.loc[common_indices, common_columns]
        df2_aligned = df2.loc[common_indices, common_columns]

        # Compare values
        for col in common_columns:
            try:
                # Handle NaN values
                df1_col = df1_aligned[col].fillna(0)
                df2_col = df2_aligned[col].fillna(0)

                # Calculate differences
                diff = np.abs(df1_col - df2_col)
                max_diff = diff.max()
                mean_diff = diff.mean()

                result["statistics"][col] = {
                    "max_difference": float(max_diff),
                    "mean_difference": float(mean_diff),
                    "records_compared": len(df1_col),
                }

                if max_diff > tolerance:
                    result["status"] = "FAIL"
                    result["issues"].append(
                        f"Column {col}: max difference {max_diff} > tolerance {tolerance}"
                    )

            except Exception as e:
                result["status"] = "FAIL"
                result["issues"].append(f"Error comparing column {col}: {e}")

        return result

    def run_verification(self):
        """
        Run complete data consistency verification.
        """
        logger.info("Starting data consistency verification")

        # Select test samples
        samples = self.select_test_samples()
        if not samples:
            logger.error("No test samples selected")
            return self.results

        # Run verification for each sample
        for i, sample in enumerate(samples):
            logger.info(f"Testing sample {i+1}/{len(samples)}: {sample}")

            stock = sample["stock"]
            date = sample["date"]
            interval = sample["interval"]

            # Fetch data from all sources
            yahoo_data = self.fetch_yahoo_data(stock, date, interval)
            csv_data = self.load_csv_data(stock, date, interval)
            qlib_data = self.load_qlib_data(stock, date, interval)

            # Compare Yahoo vs CSV
            yahoo_csv_result = self.compare_dataframes(
                yahoo_data, csv_data, "Yahoo API", "CSV", tolerance=1e-6
            )

            # Compare CSV vs Qlib
            csv_qlib_result = self.compare_dataframes(
                csv_data, qlib_data, "CSV", "Qlib", tolerance=1e-6
            )

            # Compare Yahoo vs Qlib (end-to-end)
            yahoo_qlib_result = self.compare_dataframes(
                yahoo_data, qlib_data, "Yahoo API", "Qlib", tolerance=1e-6
            )

            # Record results
            sample_result = {
                "sample": sample,
                "yahoo_csv": yahoo_csv_result,
                "csv_qlib": csv_qlib_result,
                "yahoo_qlib": yahoo_qlib_result,
            }

            self.results["detailed_results"].append(sample_result)

            # Update summary
            self.results["summary"]["total_tests"] += 3
            for comparison in [yahoo_csv_result, csv_qlib_result, yahoo_qlib_result]:
                if comparison["status"] == "PASS":
                    self.results["summary"]["passed_tests"] += 1
                elif comparison["status"] == "FAIL":
                    self.results["summary"]["failed_tests"] += 1
                else:  # SKIP
                    self.results["summary"]["warnings"] += 1

        logger.info("Data consistency verification completed")
        return self.results

    def generate_report(self):
        """
        Generate a comprehensive verification report.
        """
        report = []
        report.append("=" * 80)
        report.append("DATA CONSISTENCY VERIFICATION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {self.results['timestamp']}")
        report.append("")

        # Summary
        summary = self.results["summary"]
        report.append("SUMMARY:")
        report.append(f"  Total Tests: {summary['total_tests']}")
        report.append(f"  Passed: {summary['passed_tests']}")
        report.append(f"  Failed: {summary['failed_tests']}")
        report.append(f"  Warnings: {summary['warnings']}")
        report.append(
            f"  Success Rate: {summary['passed_tests']/summary['total_tests']*100:.1f}%"
        )
        report.append("")

        # Detailed results
        report.append("DETAILED RESULTS:")
        report.append("-" * 40)

        for i, result in enumerate(self.results["detailed_results"]):
            sample = result["sample"]
            report.append(
                f"\nSample {i+1}: {sample['stock']} on {sample['date']} ({sample['interval']})"
            )

            for comparison_name in ["yahoo_csv", "csv_qlib", "yahoo_qlib"]:
                comp = result[comparison_name]
                status_icon = (
                    "✅"
                    if comp["status"] == "PASS"
                    else "❌" if comp["status"] == "FAIL" else "⚠️"
                )
                report.append(f"  {status_icon} {comp['comparison']}: {comp['status']}")

                if comp["issues"]:
                    for issue in comp["issues"]:
                        report.append(f"    - {issue}")

                if comp["statistics"]:
                    report.append("    Statistics:")
                    for col, stats in comp["statistics"].items():
                        report.append(
                            f"      {col}: max_diff={stats['max_difference']:.6f}, mean_diff={stats['mean_difference']:.6f}"
                        )

        return "\n".join(report)


def main():
    """
    Main execution function.
    """
    try:
        verifier = DataConsistencyVerifier()
        results = verifier.run_verification()

        # Generate and save report
        report = verifier.generate_report()

        # Save results to JSON
        results_file = "/app/temp_scripts/verification_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        # Save report to text file
        report_file = "/app/temp_scripts/verification_report.txt"
        with open(report_file, "w") as f:
            f.write(report)

        # Print summary
        print(report)
        print(f"\nDetailed results saved to: {results_file}")
        print(f"Report saved to: {report_file}")

        # Return exit code based on results
        if results["summary"]["failed_tests"] > 0:
            print("\n❌ VERIFICATION FAILED - Data inconsistencies detected!")
            sys.exit(1)
        else:
            print("\n✅ VERIFICATION PASSED - All data is consistent!")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Verification failed with error: {e}")
        print(f"\n💥 VERIFICATION ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
