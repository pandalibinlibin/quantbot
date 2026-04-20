"""
Check Qlib calendar file to diagnose missing date issue.

Run in Docker:
    docker compose exec backend python /app/../temp_scripts/check_calendar.py
"""

from pathlib import Path
from datetime import datetime, timedelta

# Check calendar file
qlib_data_path = Path("/app/qlib_data")
calendar_file = qlib_data_path / "calendars" / "day.txt"

print("=" * 60)
print("CALENDAR FILE ANALYSIS")
print("=" * 60)

if not calendar_file.exists():
    print(f"Calendar file not found: {calendar_file}")
else:
    with open(calendar_file, "r") as f:
        calendar_lines = [line.strip() for line in f if line.strip()]

    print(f"Total lines in calendar: {len(calendar_lines)}")

    # Get unique dates
    existing_dates = set()
    for line in calendar_lines:
        date_part = line.split()[0]
        existing_dates.add(date_part)

    print(f"Unique dates: {len(existing_dates)}")

    # Sort dates
    sorted_dates = sorted(existing_dates)

    print(f"\nFirst 5 dates: {sorted_dates[:5]}")
    print(f"Last 5 dates: {sorted_dates[-5:]}")

    # Check specific dates
    today = datetime.now()
    print(f"\nToday: {today.strftime('%Y-%m-%d')}")

    check_dates = [
        "2026-03-13",  # Friday
        "2026-03-14",  # Saturday
        "2026-03-15",  # Sunday
        "2026-03-16",  # Monday
        "2026-03-17",  # Tuesday
        "2026-03-18",  # Wednesday (today)
    ]

    print("\nDate existence check:")
    for d in check_dates:
        exists = d in existing_dates
        weekday = datetime.strptime(d, "%Y-%m-%d").strftime("%A")
        print(f"  {d} ({weekday}): {'EXISTS' if exists else 'MISSING'}")

print("\n" + "=" * 60)
print("CHECKING TUSHARE DATA AVAILABILITY")
print("=" * 60)

# Check if Tushare has data for 2026-03-17
try:
    import tushare as ts
    import os

    token = os.environ.get("TUSHARE_TOKEN")
    if token:
        ts.set_token(token)
        pro = ts.pro_api()

        # Check trade calendar
        print("\nTushare trade calendar for recent days:")
        cal = pro.trade_cal(exchange="SSE", start_date="20260313", end_date="20260318")
        print(cal.to_string())

        # Check if 2026-03-17 is a trading day
        trading_days = cal[cal["is_open"] == 1]["cal_date"].tolist()
        print(f"\nTrading days: {trading_days}")
    else:
        print("TUSHARE_TOKEN not set")
except Exception as e:
    print(f"Tushare check failed: {e}")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
