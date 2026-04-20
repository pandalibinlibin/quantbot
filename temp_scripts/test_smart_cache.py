"""
Test script to verify smart cache functionality.

This script tests:
1. Fingerprint calculation (data_end_date, factor_hash)
2. Cache validation logic
3. Multiple execution behavior

Run in docker:
docker exec -it quantbot-backend-1 python /app/temp_scripts/test_smart_cache.py
"""

import sys

sys.path.insert(0, "/app")

import json
from pathlib import Path
from datetime import datetime

print("=" * 60)
print("SMART CACHE FUNCTIONALITY TEST")
print("=" * 60)

# 1. Test fingerprint calculation
print("\n1. FINGERPRINT CALCULATION:")
print("-" * 40)
try:
    from app.services.etf_enhanced_indexing_service import (
        get_etf_enhanced_indexing_service,
    )

    etf_service = get_etf_enhanced_indexing_service()
    fingerprint = etf_service._calculate_fingerprint()

    print(f"   data_end_date: {fingerprint.get('data_end_date', 'N/A')}")
    print(f"   factor_hash: {fingerprint.get('factor_hash', 'N/A')}")

    if fingerprint.get("data_end_date") and fingerprint.get("factor_hash"):
        print("   ✓ Fingerprint calculation successful")
    else:
        print("   ⚠ Fingerprint may be incomplete")

except Exception as e:
    import traceback

    print(f"   Error: {e}")
    traceback.print_exc()

# 2. Check existing portfolio files for fingerprint
print("\n2. CHECK EXISTING PORTFOLIO FILES:")
print("-" * 40)
portfolio_dir = Path("/app/data/target_portfolio")
if portfolio_dir.exists():
    portfolio_files = sorted(portfolio_dir.glob("etf_enhanced_*.json"), reverse=True)
    print(f"   Total portfolio files: {len(portfolio_files)}")

    for f in portfolio_files[:3]:
        print(f"\n   File: {f.name}")
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)

        fp = data.get("fingerprint", {})
        if fp:
            print(
                f"   Fingerprint: data_end_date={fp.get('data_end_date')}, factor_hash={fp.get('factor_hash')}"
            )
        else:
            print(f"   Fingerprint: NOT FOUND (old format, will recalculate)")

# 3. Test cache validation
print("\n3. TEST CACHE VALIDATION:")
print("-" * 40)
try:
    from app.services.etf_enhanced_indexing_service import (
        get_etf_enhanced_indexing_service,
    )

    etf_service = get_etf_enhanced_indexing_service()

    # Test with today's date
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"   Testing cache for date: {today}")

    is_valid, cached_data = etf_service.check_cache_valid(today)

    if is_valid:
        print(f"   ✓ Cache is VALID - will use cached result")
        print(f"   Cached positions: {len(cached_data.get('positions', []))}")
    else:
        print(f"   ✗ Cache is INVALID - will recalculate")
        if cached_data is None:
            print(f"   Reason: No portfolio file for {today}")
        else:
            print(f"   Reason: Fingerprint mismatch (data or factors changed)")

except Exception as e:
    import traceback

    print(f"   Error: {e}")
    traceback.print_exc()

# 4. Test with a date that has existing portfolio
print("\n4. TEST WITH EXISTING PORTFOLIO DATE:")
print("-" * 40)
try:
    if portfolio_files:
        # Get the latest portfolio date
        latest_file = portfolio_files[0]
        latest_date = latest_file.stem.replace("etf_enhanced_", "")
        print(f"   Testing cache for date: {latest_date}")

        is_valid, cached_data = etf_service.check_cache_valid(latest_date)

        if is_valid:
            print(f"   ✓ Cache is VALID")
        else:
            print(f"   ✗ Cache is INVALID")
            # Check why
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_fp = data.get("fingerprint", {})
            current_fp = etf_service._calculate_fingerprint()

            print(f"   Cached fingerprint: {cached_fp}")
            print(f"   Current fingerprint: {current_fp}")

            if not cached_fp:
                print(f"   Reason: Old portfolio format without fingerprint")
            elif cached_fp.get("data_end_date") != current_fp.get("data_end_date"):
                print(f"   Reason: Data source changed")
            elif cached_fp.get("factor_hash") != current_fp.get("factor_hash"):
                print(f"   Reason: Factors changed")

except Exception as e:
    import traceback

    print(f"   Error: {e}")
    traceback.print_exc()

# 5. Check holdings file
print("\n5. CHECK HOLDINGS FILE:")
print("-" * 40)
holdings_file = Path("/app/data/target_portfolio/current_holdings.json")
if holdings_file.exists():
    with open(holdings_file, "r", encoding="utf-8") as f:
        holdings_data = json.load(f)
    print(f"   Holdings file exists")
    print(f"   Updated at: {holdings_data.get('updated_at', 'unknown')}")
    print(f"   Trade date: {holdings_data.get('trade_date', 'unknown')}")
    print(f"   Position count: {holdings_data.get('position_count', 0)}")
else:
    print(f"   Holdings file does not exist")
    print(f"   This is expected if daily task hasn't been run with new code")

print("\n" + "=" * 60)
print("SUMMARY:")
print("=" * 60)
print(
    """
Smart cache behavior:
1. First execution: Calculate and save with fingerprint
2. Same day, same data, same factors: Use cached result
3. Same day, data changed: Recalculate
4. Same day, factors changed: Recalculate
5. Different day: Calculate new portfolio

To test the full flow:
1. Run daily task once (will calculate and save)
2. Run daily task again (should use cache)
3. Check logs for "Using cached portfolio" message
"""
)
