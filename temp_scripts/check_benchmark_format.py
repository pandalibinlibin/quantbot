"""
Check what benchmark codes actually exist in Qlib data.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/check_benchmark_format.py
"""

import os
from pathlib import Path


def check_qlib_instruments():
    """Check what instruments exist in Qlib data."""
    print("=" * 60)
    print("CHECKING QLIB DATA FOR BENCHMARK CODES")
    print("=" * 60)

    qlib_path = Path("/app/qlib_data")

    # Check instruments directory
    instruments_dir = qlib_path / "instruments"
    if instruments_dir.exists():
        print(f"\n--- Instruments Directory ---")
        for f in instruments_dir.iterdir():
            print(f"  {f.name}")
            if f.suffix == ".txt":
                with open(f, "r") as file:
                    lines = file.readlines()[:20]  # First 20 lines
                    print(f"    First 20 instruments:")
                    for line in lines:
                        print(f"      {line.strip()}")

    # Check features directory for stock codes
    features_dir = qlib_path / "features"
    if features_dir.exists():
        print(f"\n--- Features Directory (Stock Codes) ---")
        stock_dirs = sorted([d.name for d in features_dir.iterdir() if d.is_dir()])[:30]
        print(f"  Total stock directories: {len(list(features_dir.iterdir()))}")
        print(f"  First 30 stock codes:")
        for code in stock_dirs:
            print(f"    {code}")

        # Look for benchmark-like codes (000300, 000905, etc.)
        print(f"\n--- Looking for Benchmark Codes ---")
        benchmark_patterns = ["000300", "000905", "000016", "399006"]
        for pattern in benchmark_patterns:
            matches = [d.name for d in features_dir.iterdir() if pattern in d.name]
            if matches:
                print(f"  Pattern '{pattern}' matches: {matches}")
            else:
                print(f"  Pattern '{pattern}': No matches found")

    # Check calendars
    calendars_dir = qlib_path / "calendars"
    if calendars_dir.exists():
        print(f"\n--- Calendars Directory ---")
        for f in calendars_dir.iterdir():
            print(f"  {f.name}")


def check_qlib_benchmark_data():
    """Try to load benchmark data using Qlib."""
    print(f"\n" + "=" * 60)
    print("CHECKING BENCHMARK DATA VIA QLIB")
    print("=" * 60)

    try:
        import qlib
        from qlib.data import D

        # Initialize Qlib if not already
        try:
            qlib.init(provider_uri="/app/qlib_data", region="cn")
            print("Qlib initialized successfully")
        except Exception as e:
            print(f"Qlib init note: {e}")

        # Try different benchmark formats
        benchmark_formats = [
            "SH000300",
            "000300.SH",
            "sh000300",
            "000300",
            "SH510300",  # CSI300 ETF
            "510300.SH",
        ]

        print(f"\n--- Testing Benchmark Formats ---")
        for benchmark in benchmark_formats:
            try:
                # Try to get data for this benchmark
                data = D.features(
                    instruments=[benchmark],
                    fields=["$close"],
                    start_time="2024-01-01",
                    end_time="2024-01-31",
                )
                if data is not None and len(data) > 0:
                    print(f"  ✅ '{benchmark}' EXISTS - {len(data)} rows")
                else:
                    print(f"  ❌ '{benchmark}' - No data returned")
            except Exception as e:
                error_msg = str(e)[:80]
                print(f"  ❌ '{benchmark}' - Error: {error_msg}")

        # List all available instruments
        print(f"\n--- All Available Instruments ---")
        try:
            instruments = D.instruments(market="all")
            print(f"  Total instruments: {len(instruments) if instruments else 'None'}")

            # Look for index-like codes
            if instruments:
                index_codes = [
                    i for i in instruments if "000300" in str(i) or "000905" in str(i)
                ]
                if index_codes:
                    print(f"  Index-like codes found: {index_codes[:10]}")
                else:
                    print("  No index-like codes found in instruments")
        except Exception as e:
            print(f"  Error listing instruments: {e}")

    except Exception as e:
        print(f"Error: {e}")


def main():
    check_qlib_instruments()
    check_qlib_benchmark_data()


if __name__ == "__main__":
    main()
