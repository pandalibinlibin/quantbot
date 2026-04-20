"""
Force incremental update and debug the issue.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/force_incremental_update.py
"""

import sys
import os

sys.path.append("/app")

from datetime import datetime, timedelta
from app.services.data_collectors.pipeline.service import (
    execute_data_pipeline,
    _get_missing_date_ranges,
)
from app.models import DownloadDataRequest

print("=" * 60)
print("FORCE INCREMENTAL UPDATE DEBUG")
print("=" * 60)

# Test missing date ranges detection
print("\n1. Testing missing date ranges detection:")
start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
end_date = datetime.now().strftime("%Y-%m-%d")

print(f"Requested range: {start_date} to {end_date}")

missing_ranges = _get_missing_date_ranges(start_date, end_date, "1d")
print(f"Missing ranges: {missing_ranges}")

if not missing_ranges:
    print("No missing ranges detected - this is the problem!")

    # Let's check more specifically
    print("\n2. Manual date check:")
    from pathlib import Path

    calendar_file = Path("/app/qlib_data/calendars/day.txt")

    with open(calendar_file, "r") as f:
        calendar_lines = [line.strip() for line in f if line.strip()]

    existing_dates = set()
    for line in calendar_lines:
        date_part = line.split()[0]
        existing_dates.add(date_part)

    # Check last few days
    check_dates = ["2026-03-16", "2026-03-17", "2026-03-18"]
    for d in check_dates:
        exists = d in existing_dates
        weekday = datetime.strptime(d, "%Y-%m-%d").strftime("%A")
        print(f"  {d} ({weekday}): {'EXISTS' if exists else 'MISSING'}")

    # Force add missing trading days to the missing ranges
    print("\n3. Forcing missing ranges:")
    missing_ranges = [("2026-03-17", "2026-03-18")]
    print(f"Forced missing ranges: {missing_ranges}")

print(f"\n4. Executing pipeline with missing ranges: {missing_ranges}")

if missing_ranges:
    # Create request
    request = DownloadDataRequest(
        stock_pool="csi300",
        start_date=start_date,
        end_date=end_date,
        incremental=True,
        interval="1d",
    )

    print(
        f"Request: stock_pool={request.stock_pool}, incremental={request.incremental}"
    )

    # Execute pipeline
    try:
        result = execute_data_pipeline(request)
        print(f"\nPipeline result:")
        print(f"  Status: {result.status}")
        print(f"  Message: {result.message}")
        print(f"  Task ID: {result.task_id}")

        if result.status == "completed":
            print("\n✅ SUCCESS: Data update completed!")
        else:
            print(f"\n❌ FAILED: Status = {result.status}")

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback

        traceback.print_exc()
else:
    print("\n⚠️  No missing ranges to process")

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)
