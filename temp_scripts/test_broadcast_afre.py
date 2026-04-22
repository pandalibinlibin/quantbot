"""
Test script for afre_monthly_flow broadcast field.
Validates: Tushare API call, frequency detection, resample to daily,
broadcast to instrument CSVs, and .bin file generation.
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Ensure app modules are importable
sys.path.insert(0, "/app")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = []


class SkipSection(Exception):
    """Raised to skip the rest of a test section."""

    pass


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, condition))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return condition


print("=" * 70)
print("TEST: afre_monthly_flow Broadcast Field")
print("=" * 70)

# ------------------------------------------------------------------
# 1. Tushare API call
# ------------------------------------------------------------------
print("\n--- 1. Tushare sf_month API ---")
df = None
try:
    import tushare as ts
    from app.core.config import settings

    ts.set_token(settings.TUSHARE_TOKEN)
    pro = ts.pro_api()

    df = pro.sf_month(start_m="202301", end_m="202412")
    check(
        "sf_month API returns data",
        df is not None and not df.empty,
        f"{len(df)} rows" if df is not None else "None",
    )

    if df is not None and not df.empty:
        check("'month' column exists", "month" in df.columns, str(df.columns.tolist()))
        check("'inc_month' column exists", "inc_month" in df.columns)
        print(f"\n  Sample data (first 5 rows):")
        print(df.head().to_string(index=False))
except Exception as e:
    check("sf_month API call", False, str(e))

# ------------------------------------------------------------------
# 2. Frequency detection
# ------------------------------------------------------------------
print("\n--- 2. Frequency Detection ---")
test_df = None
try:
    if df is None:
        check("Skipped (no API data from step 1)", False)
        raise SkipSection()
    from app.services.data_collectors.broadcast_field_collector import (
        detect_frequency,
        resample_to_daily,
        get_trading_calendar_for_broadcast,
        BROADCAST_FIELD_NAMES,
    )

    check(
        "afre_monthly_flow in BROADCAST_FIELD_NAMES",
        "afre_monthly_flow" in BROADCAST_FIELD_NAMES,
        str(BROADCAST_FIELD_NAMES),
    )

    # Simulate the date conversion done in _download_and_broadcast_sf_month
    test_df = df.copy()
    test_df["month"] = pd.to_datetime(
        test_df["month"], format="%Y%m"
    ) + pd.offsets.MonthEnd(0)

    freq = detect_frequency(test_df, "month")
    check("Detected frequency is 'monthly'", freq == "monthly", f"got: {freq}")

except SkipSection:
    pass
except Exception as e:
    check("Frequency detection", False, str(e))

# ------------------------------------------------------------------
# 3. Resample to daily
# ------------------------------------------------------------------
print("\n--- 3. Resample to Daily ---")
try:
    if test_df is None:
        check("Skipped (no data from step 2)", False)
        raise SkipSection()
    series = test_df.set_index("month")["inc_month"].sort_index()
    series = series[~series.index.duplicated(keep="last")]
    series = series.astype(np.float64)
    print(
        f"  Monthly series: {len(series)} points, "
        f"{series.index.min().date()} to {series.index.max().date()}"
    )

    trading_cal = get_trading_calendar_for_broadcast()
    check(
        "Trading calendar loaded",
        trading_cal is not None and len(trading_cal) > 0,
        f"{len(trading_cal)} dates" if trading_cal else "None",
    )

    daily_series = resample_to_daily(series, trading_cal)
    check(
        "Resampled to daily",
        len(daily_series) > len(series),
        f"{len(series)} monthly -> {len(daily_series)} daily",
    )

    # Check ffill worked (no NaN in the middle)
    nan_count = daily_series.isna().sum()
    check(
        "No NaN after ffill (within range)", nan_count == 0, f"{nan_count} NaN values"
    )

    print(f"\n  Daily series sample (first 10):")
    print(daily_series.head(10).to_string())

except SkipSection:
    pass
except Exception as e:
    check("Resample to daily", False, str(e))

# ------------------------------------------------------------------
# 4. CSV injection check
# ------------------------------------------------------------------
print("\n--- 4. CSV Injection ---")
try:
    csv_dir = Path("/app/csv_data/cn_data")
    csv_files = list(csv_dir.glob("*.csv"))
    check("CSV directory exists", csv_dir.exists())
    check("CSV files present", len(csv_files) > 0, f"{len(csv_files)} files")

    if csv_files:
        sample_csv = csv_files[0]
        sample_df = pd.read_csv(sample_csv, index_col=0, parse_dates=True)
        has_col = "afre_monthly_flow" in sample_df.columns
        check(
            f"afre_monthly_flow column in {sample_csv.name}",
            has_col,
            f"columns: {sample_df.columns.tolist()[:8]}...",
        )
        if has_col:
            non_null = sample_df["afre_monthly_flow"].notna().sum()
            total = len(sample_df)
            check(
                "afre_monthly_flow has data",
                non_null > 0,
                f"{non_null}/{total} non-null values",
            )
            print(f"\n  Sample values from {sample_csv.name}:")
            print(sample_df[["afre_monthly_flow"]].dropna().tail(10).to_string())
except Exception as e:
    check("CSV injection", False, str(e))

# ------------------------------------------------------------------
# 5. .bin file check
# ------------------------------------------------------------------
print("\n--- 5. Qlib .bin Files ---")
try:
    qlib_features_dir = Path("/app/qlib_data/features")
    check("Qlib features dir exists", qlib_features_dir.exists())

    if qlib_features_dir.exists():
        instrument_dirs = [d for d in qlib_features_dir.iterdir() if d.is_dir()]
        check(
            "Instrument dirs present",
            len(instrument_dirs) > 0,
            f"{len(instrument_dirs)} dirs",
        )

        if instrument_dirs:
            bin_count = 0
            missing_count = 0
            sample_dir = instrument_dirs[0]
            for d in instrument_dirs[:50]:  # Check first 50
                bin_file = d / "afre_monthly_flow.day.bin"
                if bin_file.exists():
                    bin_count += 1
                else:
                    missing_count += 1

            checked = min(50, len(instrument_dirs))
            check(
                f"afre_monthly_flow.day.bin exists ({bin_count}/{checked})",
                bin_count > 0,
                f"{bin_count} found, {missing_count} missing",
            )

            # Read a sample .bin to verify data
            sample_bin = sample_dir / "afre_monthly_flow.day.bin"
            if sample_bin.exists():
                data = np.fromfile(str(sample_bin), dtype="<f")
                non_nan = np.count_nonzero(~np.isnan(data))
                check(
                    f".bin data in {sample_dir.name}",
                    non_nan > 0,
                    f"{non_nan}/{len(data)} non-NaN values",
                )
except Exception as e:
    check(".bin file check", False, str(e))

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print("\n" + "=" * 70)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"Results: {passed}/{total} passed")
if passed == total:
    print(f"[{PASS}] All checks passed!")
else:
    failed = [(name, ok) for name, ok in results if not ok]
    for name, _ in failed:
        print(f"  [{FAIL}] {name}")
print("=" * 70)
