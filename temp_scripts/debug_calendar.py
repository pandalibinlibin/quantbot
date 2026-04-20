"""Debug script to analyze Qlib calendar and rebalance day calculation."""

import qlib
from qlib.data import D
import pandas as pd

# Initialize Qlib
qlib.init(provider_uri="/app/qlib_data", region="cn")

# Get calendar
calendar = D.calendar(freq="day")
calendar_list = list(calendar)

print(f"Calendar length: {len(calendar_list)}")
print(f"First day: {calendar_list[0].date()}")
print(f"Last day: {calendar_list[-1].date()}")
print()

# Check last 15 days
print("Last 15 trading days:")
for i, d in enumerate(calendar_list[-15:]):
    idx = len(calendar_list) - 15 + i
    print(
        f"  idx={idx}, date={d.date()}, weekday={d.dayofweek}, idx%5={idx%5}, is_rebalance={idx%5==0}"
    )

print()

# Find last rebalance day (where idx % 5 == 0)
period = 5
last_idx = len(calendar_list) - 1
last_rebalance_idx = (last_idx // period) * period
last_rebalance_date = calendar_list[last_rebalance_idx]
last_calendar_date = calendar_list[-1]

print(f"Period: {period}")
print(f"Last calendar idx: {last_idx}")
print(
    f"Last calendar date: {last_calendar_date.date()} (weekday={last_calendar_date.dayofweek})"
)
print(f"Last rebalance idx: {last_rebalance_idx}")
print(f"Last rebalance date: {last_rebalance_date.date()}")
print()

# Calculate trading days from last_rebalance to calendar end
trading_days_after_last_rebalance = last_idx - last_rebalance_idx
trading_days_to_next = period - trading_days_after_last_rebalance
print(f"Trading days after last rebalance: {trading_days_after_last_rebalance}")
print(f"Trading days to next rebalance: {trading_days_to_next}")


# Estimate calendar days by counting weekdays
def estimate_calendar_days(trading_days: int, start_date) -> int:
    """Count calendar days for given trading days, skipping weekends."""
    cal_days = 0
    remaining = trading_days
    current = start_date
    while remaining > 0:
        current += pd.Timedelta(days=1)
        cal_days += 1
        # Skip weekends (Saturday=5, Sunday=6)
        if current.dayofweek < 5:
            remaining -= 1
    return cal_days


cal_days_to_next = estimate_calendar_days(trading_days_to_next, last_calendar_date)
next_rebalance_date = last_calendar_date + pd.Timedelta(days=cal_days_to_next)

print(f"Calendar days to next rebalance: {cal_days_to_next}")
print(
    f"Next rebalance date: {next_rebalance_date.date()} (weekday={next_rebalance_date.dayofweek})"
)
print()

# Verify by listing the days
print("Days from calendar end to next rebalance:")
current = last_calendar_date
for i in range(cal_days_to_next):
    current += pd.Timedelta(days=1)
    is_weekday = current.dayofweek < 5
    print(f"  {current.date()} (weekday={current.dayofweek}, is_trading={is_weekday})")
