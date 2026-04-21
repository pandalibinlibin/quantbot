"""
Test script for broadcast field mechanism: Shibor 1Y.

Verifies:
1. Tushare Shibor API returns valid data
2. broadcast_field() correctly injects into instrument CSVs
3. Normalize + dump_bin generates correct .bin files
4. Data values are consistent across pipeline stages

Run inside container:
  docker compose exec backend python /app/temp_scripts/test_broadcast_shibor.py
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Ensure app imports work
sys.path.insert(0, "/app")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, condition))
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    return condition


def main():
    print("=" * 60)
    print("Broadcast Field Test: Shibor 1Y")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Test Tushare API download
    # ------------------------------------------------------------------
    print("\n--- Step 1: Tushare Shibor API ---")
    try:
        import tushare as ts
        from app.core.config import settings

        token = settings.TUSHARE_TOKEN
        check("TUSHARE_TOKEN configured", bool(token))
        if not token:
            print("Cannot continue without TUSHARE_TOKEN")
            return

        ts.set_token(token)
        pro = ts.pro_api()

        # Download a small sample (last 30 days)
        from datetime import datetime, timedelta

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=30)
        ts_start = start_dt.strftime("%Y%m%d")
        ts_end = end_dt.strftime("%Y%m%d")

        df = pro.shibor(start_date=ts_start, end_date=ts_end)
        check("Shibor API returns data", df is not None and not df.empty,
              f"{len(df)} rows" if df is not None else "None")

        if df is not None and not df.empty:
            check("'date' column exists", "date" in df.columns, str(df.columns.tolist()))
            check("'1y' column exists", "1y" in df.columns, str(df.columns.tolist()))
            check("1y values are numeric", pd.api.types.is_numeric_dtype(df["1y"]))
            check("No all-NaN in 1y", not df["1y"].isna().all(),
                  f"NaN count: {df['1y'].isna().sum()}/{len(df)}")
            print(f"\n  Sample data (last 5 rows):")
            print(df[["date", "1y"]].tail().to_string(index=False))
        else:
            print("  Skipping column checks (no data)")
            return

    except Exception as e:
        check("Tushare API call", False, str(e))
        return

    # ------------------------------------------------------------------
    # Step 2: Test broadcast_field() injection into a temp CSV
    # ------------------------------------------------------------------
    print("\n--- Step 2: broadcast_field() injection ---")
    import tempfile
    import shutil

    test_dir = Path(tempfile.mkdtemp(prefix="broadcast_test_"))
    try:
        # Create fake instrument CSVs with OHLCV data
        dates = pd.bdate_range(start=start_dt, end=end_dt)
        for name in ["SH510300", "SZ159919"]:
            fake_df = pd.DataFrame(
                {
                    "open": np.random.uniform(3.0, 4.0, len(dates)),
                    "high": np.random.uniform(3.0, 4.0, len(dates)),
                    "low": np.random.uniform(3.0, 4.0, len(dates)),
                    "close": np.random.uniform(3.0, 4.0, len(dates)),
                    "volume": np.random.randint(1000, 9999, len(dates)),
                },
                index=dates,
            )
            fake_df.to_csv(test_dir / f"{name}.csv")

        check("Created test CSVs", len(list(test_dir.glob("*.csv"))) == 2)

        from app.services.data_collectors.broadcast_field_collector import (
            broadcast_field,
        )

        count = broadcast_field(
            raw_df=df,
            date_col="date",
            value_col="1y",
            field_name="shibor_1y",
            csv_dir=test_dir,
            trading_calendar=None,
        )

        check("broadcast_field() updated CSVs", count == 2, f"count={count}")

        # Verify injected data
        for csv_file in test_dir.glob("*.csv"):
            injected_df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
            has_col = "shibor_1y" in injected_df.columns
            check(f"{csv_file.stem}: shibor_1y column exists", has_col)
            if has_col:
                non_null = injected_df["shibor_1y"].notna().sum()
                total = len(injected_df)
                coverage = non_null / total * 100 if total > 0 else 0
                check(
                    f"{csv_file.stem}: shibor_1y coverage",
                    coverage > 50,
                    f"{non_null}/{total} ({coverage:.1f}%)",
                )
                # Check values are reasonable (Shibor 1Y should be 0.1% - 10%)
                vals = injected_df["shibor_1y"].dropna()
                if len(vals) > 0:
                    check(
                        f"{csv_file.stem}: values in range [0.1, 10]",
                        vals.min() >= 0.1 and vals.max() <= 10.0,
                        f"min={vals.min():.4f}, max={vals.max():.4f}",
                    )

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Step 3: Check actual pipeline results (if data already downloaded)
    # ------------------------------------------------------------------
    print("\n--- Step 3: Production data check ---")
    from app.core.config import settings

    csv_dir = Path("/app/csv_data/cn_data")
    qlib_dir = Path(settings.QLIB_DATA_PATH)
    features_dir = qlib_dir / "features"

    csv_exists = csv_dir.exists() and any(csv_dir.glob("*.csv"))
    check("CSV data directory has files", csv_exists,
          str(csv_dir) if csv_exists else "No CSV files found")

    if csv_exists:
        # Check if shibor_1y is in any CSV
        sample_csv = next(csv_dir.glob("*.csv"))
        sample_df = pd.read_csv(sample_csv, index_col=0, parse_dates=True)
        has_shibor = "shibor_1y" in sample_df.columns
        check(
            f"CSV '{sample_csv.stem}' has shibor_1y column",
            has_shibor,
            f"columns: {sample_df.columns.tolist()}" if not has_shibor else "",
        )

        if has_shibor:
            vals = sample_df["shibor_1y"].dropna()
            check(
                "shibor_1y has data in CSV",
                len(vals) > 0,
                f"{len(vals)} non-null values",
            )
            if len(vals) > 0:
                print(f"\n  CSV date range: {sample_df.index.min().date()} to {sample_df.index.max().date()}")
                print(f"  shibor_1y range: {vals.min():.4f} to {vals.max():.4f}")
                print(f"  shibor_1y last 5 values:")
                print(f"  {vals.tail().to_string()}")

    # Check .bin files
    bin_exists = False
    if features_dir.exists():
        sample_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
        if sample_dirs:
            bin_file = sample_dirs[0] / "shibor_1y.day.bin"
            bin_exists = bin_file.exists()
            check(
                f"shibor_1y.day.bin exists in {sample_dirs[0].name}/",
                bin_exists,
            )

            if bin_exists:
                # Read .bin and verify
                file_size = bin_file.stat().st_size
                n_values = (file_size - 4) // 4  # 4-byte header + 4 bytes per float32
                check(
                    "shibor_1y.day.bin has data",
                    n_values > 0,
                    f"size={file_size} bytes, ~{n_values} values",
                )

                # Read raw values
                with open(bin_file, "rb") as f:
                    import struct
                    header = struct.unpack("<f", f.read(4))[0]
                    raw_vals = np.frombuffer(f.read(), dtype=np.float32)
                    valid = raw_vals[~np.isnan(raw_vals)]
                    check(
                        "shibor_1y .bin values valid",
                        len(valid) > 0,
                        f"{len(valid)}/{len(raw_vals)} non-NaN, range [{valid.min():.4f}, {valid.max():.4f}]"
                        if len(valid) > 0
                        else f"all NaN ({len(raw_vals)} values)",
                    )

                # Count how many instruments have the .bin file
                total_dirs = len(sample_dirs)
                has_bin = sum(
                    1
                    for d in sample_dirs
                    if (d / "shibor_1y.day.bin").exists()
                )
                check(
                    "shibor_1y.day.bin in all instruments",
                    has_bin == total_dirs,
                    f"{has_bin}/{total_dirs} instruments",
                )
    else:
        check("Features directory exists", False, str(features_dir))

    if not bin_exists:
        print(f"\n  {WARN} .bin file not found. Run 'Update Data' first to trigger pipeline.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed > 0:
        print(f"\nFailed checks:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
