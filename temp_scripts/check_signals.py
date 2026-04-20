"""
Check signals data to understand why only 132 stocks have signals.
"""

import sys

sys.path.insert(0, "/app")

import pandas as pd
from pathlib import Path

# Check Qlib data directly
print("=" * 60)
print("CHECKING QLIB DATA")
print("=" * 60)

# Initialize Qlib
import qlib
from qlib.config import REG_CN

qlib.init(provider_uri="/app/qlib_data", region=REG_CN)

from qlib.data import D

# Get instruments for csi300
print("\n1. Checking CSI300 instruments in Qlib:")
try:
    instruments = D.instruments(market="csi300")
    inst_list = D.list_instruments(instruments=instruments, as_list=True)
    print(f"   CSI300 instruments count: {len(inst_list)}")
    if inst_list:
        print(f"   Sample instruments: {inst_list[:5]}")
except Exception as e:
    print(f"   Error: {e}")

# Check what data we have
print("\n2. Checking available data:")
try:
    # Get all instruments
    all_instruments = D.instruments(market="all")
    all_list = D.list_instruments(instruments=all_instruments, as_list=True)
    print(f"   Total instruments in data: {len(all_list)}")
    if all_list:
        print(f"   Sample: {all_list[:5]}")
except Exception as e:
    print(f"   Error: {e}")

# Check data for a specific date
print("\n3. Checking data for latest date:")
try:
    # Get close prices for all instruments
    df = D.features(
        instruments=all_list,  # Use list directly
        fields=["$close"],
        start_time="2026-02-01",
        end_time="2026-02-28",
    )
    print(f"   Data shape: {df.shape}")
    print(f"   Index names: {df.index.names}")

    if hasattr(df.index, "nlevels") and df.index.nlevels > 1:
        dates = df.index.get_level_values("datetime").unique()
        instruments = df.index.get_level_values("instrument").unique()
        print(f"   Date range: {dates.min()} to {dates.max()}")
        print(f"   Total unique instruments: {len(instruments)}")

        # Check stocks per date
        print("\n   Stocks per date (last 5 dates):")
        for date in sorted(dates)[-5:]:
            count = len(df.loc[date])
            print(f"     {date}: {count} stocks")
except Exception as e:
    import traceback

    print(f"   Error: {e}")
    traceback.print_exc()

# Check instruments file
print("\n4. Checking instruments files:")
import os

inst_dir = "/app/qlib_data/instruments"
if os.path.exists(inst_dir):
    files = os.listdir(inst_dir)
    print(f"   Files in {inst_dir}: {files}")

    # Read all.txt to see content
    all_txt = os.path.join(inst_dir, "all.txt")
    if os.path.exists(all_txt):
        with open(all_txt, "r") as f:
            lines = f.readlines()
        print(f"   all.txt has {len(lines)} instruments")
else:
    print(f"   Directory {inst_dir} does not exist")

# Create csi300.txt as a copy of all.txt (since we have 300 stocks)
print("\n5. Creating csi300.txt from all.txt:")
csi300_txt = os.path.join(inst_dir, "csi300.txt")
if not os.path.exists(csi300_txt):
    import shutil

    shutil.copy(all_txt, csi300_txt)
    print(f"   Created {csi300_txt}")
else:
    print(f"   {csi300_txt} already exists")

print("\n" + "=" * 60)
