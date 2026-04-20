#!/usr/bin/env python3
"""Debug script to investigate rebalance day calculation issues."""

import os
import sys

# Initialize Qlib
import qlib
from qlib.data import D
import pandas as pd

qlib_data_dir = os.environ.get("QLIB_DATA_DIR", "/app/qlib_data")
qlib.init(provider_uri=qlib_data_dir, region="cn")

# Get calendar
calendar = D.calendar(freq="day")
calendar_list = list(calendar)

print(f"Calendar length: {len(calendar_list)}")
print(f"Calendar start: {calendar_list[0]}")
print(f"Calendar end: {calendar_list[-1]}")
print(f"Last 10 dates: {calendar_list[-10:]}")

# Test with today's date
from_date = "2026-03-30"
from_dt = pd.Timestamp(from_date)
period = 5

print(f"\nTesting with from_date={from_date}, period={period}")

# Find index
try:
    start_idx = calendar_list.index(from_dt)
    print(f"Found exact match at index {start_idx}")
except ValueError:
    print(f"{from_date} not in calendar, searching for next trading day...")
    start_idx = None
    for i, cal_date in enumerate(calendar_list):
        if cal_date > from_dt:
            start_idx = i
            print(f"Found next trading day at index {i}: {cal_date}")
            break
    if start_idx is None:
        print(f"No trading day found after {from_date}")
        print(f"This is the root cause - calendar ends at {calendar_list[-1]}")

# Check rebalance calculation
if start_idx is not None:
    is_rebalance = (start_idx % period) == 0
    print(
        f"Index {start_idx} % {period} = {start_idx % period}, is_rebalance={is_rebalance}"
    )

    next_rebalance_idx = ((start_idx // period) + 1) * period
    print(f"Next rebalance index: {next_rebalance_idx}")
    print(f"Calendar length: {len(calendar_list)}")

    if next_rebalance_idx < len(calendar_list):
        print(f"Next rebalance date: {calendar_list[next_rebalance_idx]}")
    else:
        print(
            f"Next rebalance index {next_rebalance_idx} >= calendar length {len(calendar_list)}"
        )
        print("This is why get_next_rebalance_day returns None!")
