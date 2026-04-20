#!/usr/bin/env python3
"""
Debug script to trace the routine execution flow
"""

import sys
import os

sys.path.append("/app")

from app.services.online_serving_service import get_online_serving_service
from app.services.etf_enhanced_indexing_service import get_etf_enhanced_indexing_service
from app.services.enhanced_indexing_service import get_enhanced_indexing_service
import pandas as pd

print("=" * 60)
print("Routine Flow Debug")
print("=" * 60)

# Check services
print("\n1. Service Status:")
online_service = get_online_serving_service()
etf_service = get_etf_enhanced_indexing_service()
legacy_service = get_enhanced_indexing_service()

print(f"   Online service: {online_service is not None}")
print(f"   ETF service enabled: {etf_service.enabled}")
print(f"   Legacy service enabled: {legacy_service.enabled}")

# Test _calculate_enhanced_indexing method directly
print("\n2. Testing _calculate_enhanced_indexing method:")
try:
    # Create dummy signals DataFrame
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

    print(f"   Created test signals: {len(signals)} rows")
    print(f"   Signals preview:")
    for i, (idx, row) in enumerate(signals.head(3).iterrows()):
        print(f"     {idx}: score={row['score']}")

    # Call the method directly
    result = online_service._calculate_enhanced_indexing(signals, "2026-03-20")

    print(f"\n   Result keys: {list(result.keys())}")
    print(f"   Success: {result.get('success')}")
    print(f"   Strategy: {result.get('strategy')}")
    print(f"   Target portfolio length: {len(result.get('target_portfolio', []))}")

    if result.get("target_portfolio"):
        first_position = result["target_portfolio"][0]
        print(f"   First position keys: {list(first_position.keys())}")
        print(f"   First position sample:")
        for key, value in list(first_position.items())[:5]:
            print(f"     {key}: {value}")

    # Check if it has the new format fields
    print(f"\n   New format fields:")
    print(f"     generated_at: {result.get('generated_at')}")
    print(f"     trade_date: {result.get('trade_date')}")
    print(f"     signal_for_date: {result.get('signal_for_date')}")
    print(f"     weights: {result.get('weights')}")

except Exception as e:
    print(f"   ERROR in _calculate_enhanced_indexing: {e}")
    import traceback

    traceback.print_exc()

# Test ETF service directly
print("\n3. Testing ETF service directly:")
try:
    portfolio_data = etf_service.calculate_target_portfolio(
        signals=signals, trade_date="2026-03-20"
    )

    print(f"   ETF service result keys: {list(portfolio_data.keys())}")
    print(f"   Positions count: {len(portfolio_data.get('positions', []))}")

    if portfolio_data.get("positions"):
        first_pos = portfolio_data["positions"][0]
        print(f"   First position from ETF service:")
        for key, value in list(first_pos.items())[:8]:
            print(f"     {key}: {value}")

except Exception as e:
    print(f"   ERROR in ETF service: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Debug complete")
print("=" * 60)
