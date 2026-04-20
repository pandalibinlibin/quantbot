#!/usr/bin/env python3
"""
Test script to verify fallback mechanisms have been removed
"""

import sys
import os

sys.path.append("/app")

from app.services.online_serving_service import get_online_serving_service
from app.services.etf_enhanced_indexing_service import get_etf_enhanced_indexing_service
import pandas as pd

print("=" * 60)
print("No Fallback Test")
print("=" * 60)

# Get services
online_service = get_online_serving_service()
etf_service = get_etf_enhanced_indexing_service()

print("\n1. Service Status:")
print(f"   ETF Enhanced Indexing enabled: {etf_service.enabled}")
print(f"   OnlineManager exists: {online_service._online_manager is not None}")

# Test _calculate_enhanced_indexing with ETF service enabled
print("\n2. Testing _calculate_enhanced_indexing with ETF service enabled:")
try:
    # Create test signals
    signals = pd.DataFrame(
        {"score": [5.9494, 5.8418, 1.3127, 1.2476, 1.2262]},
        index=pd.MultiIndex.from_tuples(
            [
                ("2026-03-20", "SZ300782"),
                ("2026-03-20", "SZ300866"),
                ("2026-03-20", "SH600570"),
                ("2026-03-20", "SH600760"),
                ("2026-03-20", "SH601808"),
            ],
            names=["datetime", "instrument"],
        ),
    )

    result = online_service._calculate_enhanced_indexing(signals, "2026-03-20")

    print(f"   Result success: {result.get('success')}")
    print(f"   Strategy used: {result.get('strategy')}")
    print(f"   Target portfolio length: {len(result.get('target_portfolio', []))}")

    if result.get("target_portfolio"):
        first_pos = result["target_portfolio"][0]
        print(f"   First position format:")
        print(f"     Has 'symbol': {'symbol' in first_pos}")
        print(f"     Has 'name': {'name' in first_pos}")
        print(f"     Has 'weight': {'weight' in first_pos}")
        print(f"     Has 'reference_price': {'reference_price' in first_pos}")
        print(f"     Sample: {dict(list(first_pos.items())[:5])}")

    # Check for new format fields
    print(f"   New format fields present:")
    print(f"     generated_at: {result.get('generated_at') is not None}")
    print(f"     trade_date: {result.get('trade_date') is not None}")
    print(f"     signal_for_date: {result.get('signal_for_date') is not None}")
    print(f"     weights: {result.get('weights') is not None}")

except Exception as e:
    print(f"   ERROR: {e}")
    import traceback

    traceback.print_exc()

# Test what happens if ETF service is disabled (should raise error now)
print("\n3. Testing behavior when ETF service is disabled:")
try:
    # Temporarily disable ETF service
    original_enabled = etf_service._config["enabled"]
    etf_service._config["enabled"] = False

    print(f"   ETF service disabled: {not etf_service.enabled}")

    # This should now raise an error instead of falling back
    result = online_service._calculate_enhanced_indexing(signals, "2026-03-20")

    print(f"   UNEXPECTED: Got result instead of error: {result.get('success')}")
    print(f"   Strategy: {result.get('strategy')}")

except RuntimeError as e:
    print(f"   EXPECTED: RuntimeError raised: {str(e)[:100]}...")
except Exception as e:
    print(f"   UNEXPECTED ERROR: {type(e).__name__}: {e}")
finally:
    # Restore original setting
    etf_service._config["enabled"] = original_enabled

# Test routine execution
print("\n4. Testing routine execution:")
try:
    print("   Calling routine method...")

    # Call the actual routine method (not execute_routine)
    routine_result = online_service.routine()

    print(f"   Routine success: {routine_result.get('success')}")
    print(f"   Strategy used: {routine_result.get('strategy')}")

    if routine_result.get("target_portfolio"):
        first_pos = routine_result["target_portfolio"][0]
        print(f"   First position from routine:")
        print(f"     Format check - has 'symbol': {'symbol' in first_pos}")
        print(f"     Format check - has 'instrument': {'instrument' in first_pos}")

        if "symbol" in first_pos:
            print(f"   SUCCESS: Using NEW format (ETF Enhanced Indexing)")
        elif "instrument" in first_pos:
            print(f"   PROBLEM: Still using OLD format (Legacy Enhanced Indexing)")

    # Check top-level fields
    print(f"   Top-level fields:")
    print(f"     generated_at: {routine_result.get('generated_at')}")
    print(f"     trade_date: {routine_result.get('trade_date')}")
    print(f"     weights: {routine_result.get('weights')}")

except Exception as e:
    print(f"   ERROR in routine: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)
