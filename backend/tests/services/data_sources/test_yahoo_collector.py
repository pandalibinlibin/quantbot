"""
Unit tests for YahooCollector.

Educational Notes:
- pytest automatically discovers files starting with 'test_'
- Test functions must start with 'test_'
- Use fixtures for reusable test data
- Use assert for validation
"""

import pytest
from pathlib import Path
from app.services.data_sources.yahoo_collector import YahooCollector


class TestYahooCollectorBasics:
    """Test basic YahooCollector functionality."""

    def test_collector_name(self):
        """Test get_collector_name returns 'yahoo'."""
        collector = YahooCollector()

        assert collector.get_collector_name() == "yahoo"

    def test_supported_fields(self):
        """Test get_supported_fields returns correct fields."""
        collector = YahooCollector()

        fields = collector.get_supported_fields()
        # Should return 7 fields
        assert len(fields) == 7

        # Should contain these fields
        expected_fields = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "factor",
        ]
        assert fields == expected_fields

    def test_field_coverage(self):
        """Test validate_field_coverage returns correct coverage info."""
        collector = YahooCollector()

        coverage = collector.validate_field_coverage()

        # Check coverage structure
        assert "collector" in coverage
        assert coverage["collector"] == "yahoo"

        assert "is_fully_compatible" in coverage
        assert coverage["is_fully_compatible"] is False  # Missing 3 fields

        assert "supported_count" in coverage
        assert coverage["supported_count"] == 7

        assert "total_required" in coverage
        assert coverage["total_required"] == 10

        assert "missing_fields" in coverage
        assert set(coverage["missing_fields"]) == {"vwap", "amount", "turnover"}

        assert "coverage_percentage" in coverage
        assert coverage["coverage_percentage"] == 70.0


class TestYahooCollectorDataFetching:
    """Test YahooCollector data fetching functionality (integration tests)."""

    @pytest.mark.integration
    def test_fetch_instrument_data_success(self):
        """Test fetching data for a valid instrument."""
        collector = YahooCollector()

        # Fetch recent data for Apple
        df = collector._fetch_instrument_data(
            instrument="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            interval="1d",
            auto_adjust=False,
        )

        # Should return a DataFrame
        assert df is not None
        assert not df.empty

        # Should have expected columns from yfinance
        expected_columns = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]
        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"

        # Should have data for January 2024
        assert len(df) > 0

    @pytest.mark.integration
    def test_convert_to_standard_format(self):
        """Test converting yfinance data to standard format."""
        collector = YahooCollector()

        # First fetch some real data
        df = collector._fetch_instrument_data(
            instrument="AAPL",
            start_date="2024-01-01",
            end_date="2024-01-31",
            interval="1d",
            auto_adjust=False,
        )

        # Convert to standard format
        df_standard = collector._convert_to_standard_format(df)

        # Check index name
        assert df_standard.index.name == "date"

        # Check standard columns exist
        expected_fields = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "factor",
        ]
        for field in expected_fields:
            assert field in df_standard.columns, f"Missing field: {field}"

        # Check factor calculation
        assert "factor" in df_standard.columns
        # Factor should be close / adj_close, typically around 1.0
        assert (df_standard["factor"] > 0).all()

    @pytest.mark.integration
    def test_collect_data_single_instrument(self, tmp_path):
        """Test collecting data for a single instrument."""
        collector = YahooCollector()

        # Use pytest's tmp_path fixture for temporary directory
        output_dir = tmp_path / "test_output"

        # Collect data for Apple
        result = collector.collect_data(
            instruments=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-31",
            output_dir=output_dir,
            interval="1d",
        )

        # Check result structure
        assert "success" in result
        assert "instruments_count" in result
        assert "successful_instruments" in result
        assert "failed_instruments" in result

        # Should succeed
        assert result["instruments_count"] == 1
        assert "AAPL" in result["successful_instruments"]
        assert len(result["failed_instruments"]) == 0

        # Check CSV file was created
        csv_file = output_dir / "csv" / "AAPL.csv"
        assert csv_file.exists()

        # Check CSV content
        import pandas as pd

        df = pd.read_csv(csv_file, index_col=0)
        assert len(df) > 0
        assert "open" in df.columns
        assert "close" in df.columns
