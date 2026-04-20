"""
Test script to investigate backtest date range issue.

This script checks:
1. Qlib calendar date range
2. Data bin files date range
3. Prediction date range
4. Why backtest ends at 2026-03-20 instead of 2026-03-21

Run in docker:
docker exec -it quantbot-backend-1 python /app/temp_scripts/test_backtest_date_range.py
"""

import sys

sys.path.insert(0, "/app")

import qlib
from qlib.data import D
from pathlib import Path
import pandas as pd
from datetime import datetime

print("=" * 60)
print("BACKTEST DATE RANGE INVESTIGATION")
print("=" * 60)

# Initialize Qlib
qlib.init(provider_uri="/app/data/qlib_data/cn_data")

# 1. Check Qlib calendar
print("\n1. QLIB CALENDAR:")
print("-" * 40)
try:
    calendar = D.calendar(freq="day")
    print(f"   Total trading days: {len(calendar)}")
    print(f"   First date: {calendar[0]}")
    print(f"   Last date: {calendar[-1]}")
    print(f"   Last 5 dates: {[str(d)[:10] for d in calendar[-5:]]}")
except Exception as e:
    print(f"   Error: {e}")

# 2. Check bin files directly
print("\n2. BIN FILES DATE RANGE:")
print("-" * 40)
bin_dir = Path("/app/data/qlib_data/cn_data/calendars")
if bin_dir.exists():
    for f in bin_dir.glob("*.txt"):
        print(f"   Calendar file: {f.name}")
        with open(f, "r") as file:
            lines = file.readlines()
            print(f"   Total lines: {len(lines)}")
            if lines:
                print(f"   First: {lines[0].strip()}")
                print(f"   Last: {lines[-1].strip()}")
                print(f"   Last 5: {[l.strip() for l in lines[-5:]]}")

# 3. Check instruments data
print("\n3. INSTRUMENTS DATA:")
print("-" * 40)
instruments_dir = Path("/app/data/qlib_data/cn_data/instruments")
if instruments_dir.exists():
    for f in list(instruments_dir.glob("*.txt"))[:3]:
        print(f"   {f.name}")
        with open(f, "r") as file:
            lines = file.readlines()
            print(f"   Total instruments: {len(lines)}")
            if lines:
                # Format: instrument\tstart_date\tend_date
                last_line = lines[-1].strip().split("\t")
                print(f"   Sample: {last_line}")

# 4. Check feature data date range
print("\n4. FEATURE DATA DATE RANGE:")
print("-" * 40)
try:
    # Get close price for a sample stock
    df = D.features(
        ["SH510300"],  # ETF
        fields=["$close"],
        start_time="2026-03-01",
        end_time="2026-03-31",
        freq="day",
    )
    if df is not None and len(df) > 0:
        dates = df.index.get_level_values("datetime").unique()
        print(f"   SH510300 data dates in March 2026:")
        print(f"   Total: {len(dates)} days")
        print(f"   Dates: {[str(d)[:10] for d in sorted(dates)]}")
except Exception as e:
    print(f"   Error: {e}")

# 5. Check what happens with T+2 label
print("\n5. T+2 LABEL IMPACT:")
print("-" * 40)
print("   A-shares use T+2 label: Ref($close, -2)/Ref($close, -1) - 1")
print("   This means:")
print("   - To predict for date D, we need close prices for D+1 and D+2")
print("   - If last data is 2026-03-23, last predictable date is 2026-03-21")
print("   - Backtest code subtracts 1 more day for boundary safety")
print("   - So backtest ends at 2026-03-20")

# 6. Verify with actual prediction
print("\n6. VERIFY PREDICTION DATE RANGE:")
print("-" * 40)
try:
    from app.services.custom_factor_handler import CustomFactorHandler
    from qlib.data.dataset import DatasetH

    # Get time range
    calendar = D.calendar(freq="day")
    start_time = str(calendar[0])[:10]
    end_time = str(calendar[-1])[:10]
    print(f"   Calendar range: {start_time} to {end_time}")

    # Create handler with label
    handler = CustomFactorHandler(
        instruments="all",
        start_time="2026-03-01",
        end_time=end_time,
        freq="day",
    )

    # Get label config
    label_config = handler.get_label_config()
    print(f"   Label expression: {label_config[0]}")

    # Create dataset
    dataset = DatasetH(
        handler=handler,
        segments={
            "test": ["2026-03-01", end_time],
        },
    )

    # Get data
    df = dataset.prepare("test", col_set="label")
    if df is not None and len(df) > 0:
        # Check for NaN in labels
        label_col = df.columns[0]
        non_nan = df[~df[label_col].isna()]
        nan_count = df[label_col].isna().sum()

        dates = non_nan.index.get_level_values("datetime").unique()
        print(f"   Total label records: {len(df)}")
        print(f"   Non-NaN label records: {len(non_nan)}")
        print(f"   NaN label records: {nan_count}")
        print(f"   Valid label dates: {[str(d)[:10] for d in sorted(dates)[-10:]]}")
        print(f"   Last valid label date: {str(dates.max())[:10]}")

except Exception as e:
    import traceback

    print(f"   Error: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("CONCLUSION:")
print("=" * 60)
print(
    """
If calendar ends at 2026-03-21 (Friday) and data ends at 2026-03-23:
- 2026-03-22 (Saturday) and 2026-03-23 (Sunday) are NOT trading days
- So calendar correctly ends at 2026-03-21
- T+2 label needs D+1 and D+2 prices, so last valid prediction is 2026-03-19
- Backtest subtracts 1 day for safety, ending at 2026-03-18 or 2026-03-20

If calendar ends at 2026-03-23:
- This would mean 2026-03-23 is a trading day (Monday?)
- Then last valid prediction should be 2026-03-21
- Backtest should end at 2026-03-20

Please check the actual dates above to understand the issue.
"""
)
