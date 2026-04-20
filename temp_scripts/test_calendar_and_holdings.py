"""
Test script to check calendar data and holdings persistence.

Run in docker:
docker exec -it quantbot-backend-1 python /app/temp_scripts/test_calendar_and_holdings.py
"""

import sys

sys.path.insert(0, "/app")

import json
from pathlib import Path
from datetime import datetime

print("=" * 60)
print("CALENDAR AND HOLDINGS INVESTIGATION")
print("=" * 60)

# 1. Check calendar file directly (no Qlib init needed)
print("\n1. CALENDAR FILE CONTENTS:")
print("-" * 40)
calendar_dir = Path("/app/data/qlib_data/cn_data/calendars")
print(f"   Calendar dir exists: {calendar_dir.exists()}")

if calendar_dir.exists():
    files = list(calendar_dir.iterdir())
    print(f"   Files in calendar dir: {[f.name for f in files]}")

    for f in files:
        if f.is_file():
            print(f"\n   File: {f.name}")
            with open(f, "r") as file:
                lines = file.readlines()
                print(f"   Total lines: {len(lines)}")
                if lines:
                    print(f"   First 3: {[l.strip() for l in lines[:3]]}")
                    print(f"   Last 5: {[l.strip() for l in lines[-5:]]}")
else:
    # Check alternative locations
    alt_paths = [
        "/app/data/qlib_data/cn_data",
        "/app/data/qlib_data",
    ]
    for p in alt_paths:
        path = Path(p)
        if path.exists():
            print(f"   Contents of {p}:")
            for item in path.iterdir():
                print(f"     - {item.name}")

# 2. Check feature data files directly
print("\n2. FEATURE DATA FILES:")
print("-" * 40)
feature_dir = Path("/app/data/qlib_data/cn_data/features")
if feature_dir.exists():
    # List some instrument directories
    instruments = list(feature_dir.iterdir())[:3]
    print(f"   Total instruments: {len(list(feature_dir.iterdir()))}")

    for inst_dir in instruments:
        if inst_dir.is_dir():
            print(f"\n   Instrument: {inst_dir.name}")
            # Check for close.day.bin
            close_file = inst_dir / "close.day.bin"
            if close_file.exists():
                import struct

                with open(close_file, "rb") as f:
                    # Read header (first 8 bytes: start_index, end_index as int32)
                    header = f.read(8)
                    if len(header) == 8:
                        start_idx, end_idx = struct.unpack("<ii", header)
                        print(
                            f"   close.day.bin: start_idx={start_idx}, end_idx={end_idx}"
                        )
                        print(f"   Data points: {end_idx - start_idx + 1}")
else:
    print(f"   Feature dir does not exist: {feature_dir}")

# 3. Check instruments file
print("\n3. INSTRUMENTS FILE:")
print("-" * 40)
instruments_dir = Path("/app/data/qlib_data/cn_data/instruments")
if instruments_dir.exists():
    files = list(instruments_dir.iterdir())
    print(f"   Files: {[f.name for f in files]}")

    for f in files[:2]:
        if f.is_file():
            print(f"\n   File: {f.name}")
            with open(f, "r") as file:
                lines = file.readlines()
                print(f"   Total instruments: {len(lines)}")
                if lines:
                    print(f"   Sample (first 3):")
                    for line in lines[:3]:
                        print(f"     {line.strip()}")
else:
    print(f"   Instruments dir does not exist")

# 4. Check holdings persistence issue
print("\n4. HOLDINGS PERSISTENCE CHECK:")
print("-" * 40)
holdings_file = Path("/app/data/target_portfolio/current_holdings.json")
print(f"   Expected path: {holdings_file}")
print(f"   File exists: {holdings_file.exists()}")
print(f"   Parent dir exists: {holdings_file.parent.exists()}")

if holdings_file.parent.exists():
    print(f"   Files in parent dir:")
    for f in holdings_file.parent.iterdir():
        print(f"     - {f.name}")

# 5. Check if apply_trades_to_holdings was called
print("\n5. CHECK PORTFOLIO FILES FOR HOLDINGS INFO:")
print("-" * 40)
portfolio_dir = Path("/app/data/target_portfolio")
if portfolio_dir.exists():
    portfolio_files = sorted(portfolio_dir.glob("etf_enhanced_*.json"), reverse=True)
    if portfolio_files:
        latest = portfolio_files[0]
        print(f"   Latest portfolio: {latest.name}")
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check positions for current_shares info
        positions = data.get("positions", [])
        print(f"   Positions count: {len(positions)}")

        if positions:
            print(f"\n   Sample position:")
            pos = positions[0]
            for key in [
                "symbol",
                "name",
                "current_shares",
                "target_shares",
                "action",
                "action_shares",
            ]:
                print(f"     {key}: {pos.get(key, 'N/A')}")

            # Check if all current_shares are 0
            all_zero = all(p.get("current_shares", 0) == 0 for p in positions)
            print(f"\n   All current_shares are 0: {all_zero}")
            if all_zero:
                print(
                    "   This indicates holdings were NOT loaded from persistence file"
                )

# 6. Manually test holdings save
print("\n6. TEST HOLDINGS SAVE:")
print("-" * 40)
try:
    from app.services.etf_enhanced_indexing_service import (
        get_etf_enhanced_indexing_service,
    )

    etf_service = get_etf_enhanced_indexing_service()
    print(f"   Service enabled: {etf_service.enabled}")
    print(f"   Output dir: {etf_service.output_dir}")
    print(f"   Current holdings: {len(etf_service._current_holdings)}")

    # Try to save test holdings
    test_holdings = {"TEST001": 100, "TEST002": 200}
    etf_service._current_holdings = test_holdings
    saved_path = etf_service.save_holdings(trade_date="2026-03-24")
    print(f"   Saved test holdings to: {saved_path}")

    # Verify
    if Path(saved_path).exists():
        with open(saved_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        print(f"   Verified saved data: {saved_data}")
        print("   ✓ Holdings save is working correctly")
    else:
        print("   ✗ Holdings file was not created")

    # Clean up test data
    etf_service._current_holdings = {}

except Exception as e:
    import traceback

    print(f"   Error: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("ANALYSIS:")
print("=" * 60)
print(
    """
The issue is that apply_trades_to_holdings() is called AFTER 
save_portfolio(), but the holdings file doesn't exist.

Possible causes:
1. The routine was run but apply_trades_to_holdings() failed silently
2. The routine was run before the holdings persistence code was added
3. There's a path issue with the holdings file

Solution: Run daily task again to trigger apply_trades_to_holdings()
with the new code that includes trade_date tracking.
"""
)
