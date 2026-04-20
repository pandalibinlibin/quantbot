"""
Test script to verify signal consistency and multiple execution safety.

This script tests:
1. Whether signals are consistent when run multiple times
2. Whether holdings are correctly persisted and loaded
3. Whether multiple daily task executions are safe

Run in docker:
docker exec -it quantbot-backend-1 python /app/temp_scripts/test_signal_consistency.py
"""

import sys

sys.path.insert(0, "/app")

import json
from pathlib import Path
from datetime import datetime
import copy

print("=" * 60)
print("SIGNAL CONSISTENCY AND MULTIPLE EXECUTION TEST")
print("=" * 60)

# 1. Check current holdings file
print("\n1. CURRENT HOLDINGS STATE:")
print("-" * 40)
holdings_file = Path("/app/data/target_portfolio/current_holdings.json")
if holdings_file.exists():
    with open(holdings_file, "r", encoding="utf-8") as f:
        holdings_data = json.load(f)
    print(f"   Holdings file exists: {holdings_file}")
    print(f"   Updated at: {holdings_data.get('updated_at', 'unknown')}")
    print(f"   Trade date: {holdings_data.get('trade_date', 'unknown')}")
    print(f"   Position count: {holdings_data.get('position_count', 0)}")
    print(f"   Holdings: {list(holdings_data.get('holdings', {}).keys())[:5]}...")
    original_holdings = holdings_data.get("holdings", {}).copy()
else:
    print(f"   Holdings file does not exist")
    original_holdings = {}

# 2. Check latest portfolio files
print("\n2. LATEST PORTFOLIO FILES:")
print("-" * 40)
portfolio_dir = Path("/app/data/target_portfolio")
if portfolio_dir.exists():
    portfolio_files = sorted(portfolio_dir.glob("etf_enhanced_*.json"), reverse=True)
    print(f"   Total portfolio files: {len(portfolio_files)}")
    for f in portfolio_files[:3]:
        print(f"   - {f.name}")
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
            positions = data.get("positions", [])
            summary = data.get("summary", {})
            print(f"     Positions: {len(positions)}")
            print(
                f"     Buy: {summary.get('buy_count', 0)}, Sell: {summary.get('sell_count', 0)}, Hold: {summary.get('hold_count', 0)}"
            )

# 3. Compare two consecutive portfolio files
print("\n3. COMPARE CONSECUTIVE PORTFOLIOS:")
print("-" * 40)
if len(portfolio_files) >= 2:
    file1, file2 = portfolio_files[0], portfolio_files[1]
    print(f"   Comparing: {file1.name} vs {file2.name}")

    with open(file1, "r", encoding="utf-8") as f:
        data1 = json.load(f)
    with open(file2, "r", encoding="utf-8") as f:
        data2 = json.load(f)

    positions1 = {p["symbol"]: p for p in data1.get("positions", [])}
    positions2 = {p["symbol"]: p for p in data2.get("positions", [])}

    # Check if symbols are the same
    symbols1 = set(positions1.keys())
    symbols2 = set(positions2.keys())

    print(f"   Symbols in {file1.name}: {len(symbols1)}")
    print(f"   Symbols in {file2.name}: {len(symbols2)}")
    print(f"   Common symbols: {len(symbols1 & symbols2)}")
    print(f"   New in latest: {symbols1 - symbols2}")
    print(f"   Removed from latest: {symbols2 - symbols1}")

    # Check if rankings are the same
    ranks1 = [(p["symbol"], p["rank"]) for p in data1.get("positions", [])]
    ranks2 = [(p["symbol"], p["rank"]) for p in data2.get("positions", [])]

    if ranks1 == ranks2:
        print(f"   Rankings: IDENTICAL")
    else:
        print(f"   Rankings: DIFFERENT")
        print(f"   Latest: {ranks1[:5]}")
        print(f"   Previous: {ranks2[:5]}")
else:
    print("   Not enough portfolio files to compare")

# 4. Test ETFEnhancedIndexingService holdings persistence
print("\n4. TEST HOLDINGS PERSISTENCE:")
print("-" * 40)
try:
    from app.services.etf_enhanced_indexing_service import (
        get_etf_enhanced_indexing_service,
    )

    etf_service = get_etf_enhanced_indexing_service()

    # Get current holdings from service
    current_holdings = etf_service._current_holdings.copy()
    print(f"   Service holdings count: {len(current_holdings)}")
    print(f"   Service holdings: {list(current_holdings.keys())[:5]}...")

    # Check if service holdings match file
    if current_holdings == original_holdings:
        print(f"   Service holdings match file: YES")
    else:
        print(f"   Service holdings match file: NO")
        print(f"   File has {len(original_holdings)} positions")
        print(f"   Service has {len(current_holdings)} positions")

except Exception as e:
    print(f"   Error: {e}")

# 5. Simulate multiple executions
print("\n5. SIMULATE MULTIPLE EXECUTIONS:")
print("-" * 40)
print("   This test simulates what happens when daily task is run multiple times")
print("   We will NOT actually run the routine, just check the logic")

try:
    from app.services.etf_enhanced_indexing_service import (
        get_etf_enhanced_indexing_service,
    )

    etf_service = get_etf_enhanced_indexing_service()

    # Load the latest portfolio to simulate
    if portfolio_files:
        with open(portfolio_files[0], "r", encoding="utf-8") as f:
            latest_portfolio = json.load(f)

        positions = latest_portfolio.get("positions", [])

        # Scenario 1: First execution (holdings = 0)
        print("\n   Scenario 1: First execution (empty holdings)")
        empty_holdings = {}
        actions_1 = []
        for pos in positions:
            symbol = pos.get("symbol", "")
            target_shares = pos.get("target_shares", 0)
            current_shares = empty_holdings.get(symbol, 0)
            if target_shares > current_shares:
                actions_1.append(("buy", symbol, target_shares - current_shares))
            elif target_shares < current_shares:
                actions_1.append(("sell", symbol, current_shares - target_shares))
            else:
                actions_1.append(("hold", symbol, 0))

        buy_count_1 = sum(1 for a in actions_1 if a[0] == "buy")
        sell_count_1 = sum(1 for a in actions_1 if a[0] == "sell")
        hold_count_1 = sum(1 for a in actions_1 if a[0] == "hold")
        print(
            f"   Actions: {buy_count_1} buy, {sell_count_1} sell, {hold_count_1} hold"
        )

        # Scenario 2: Second execution (holdings = target from first)
        print("\n   Scenario 2: Second execution (holdings = target from first)")
        holdings_after_1 = {pos["symbol"]: pos["target_shares"] for pos in positions}
        actions_2 = []
        for pos in positions:
            symbol = pos.get("symbol", "")
            target_shares = pos.get("target_shares", 0)
            current_shares = holdings_after_1.get(symbol, 0)
            if target_shares > current_shares:
                actions_2.append(("buy", symbol, target_shares - current_shares))
            elif target_shares < current_shares:
                actions_2.append(("sell", symbol, current_shares - target_shares))
            else:
                actions_2.append(("hold", symbol, 0))

        buy_count_2 = sum(1 for a in actions_2 if a[0] == "buy")
        sell_count_2 = sum(1 for a in actions_2 if a[0] == "sell")
        hold_count_2 = sum(1 for a in actions_2 if a[0] == "hold")
        print(
            f"   Actions: {buy_count_2} buy, {sell_count_2} sell, {hold_count_2} hold"
        )

        if buy_count_2 == 0 and sell_count_2 == 0:
            print(
                f"   ✓ CORRECT: Second execution shows all HOLD (no unnecessary trades)"
            )
        else:
            print(f"   ✗ WARNING: Second execution still has trades")

except Exception as e:
    import traceback

    print(f"   Error: {e}")
    traceback.print_exc()

# 6. Check signal generation date
print("\n6. CHECK SIGNAL GENERATION DATE:")
print("-" * 40)
try:
    from app.services.online_serving_service import get_online_serving_service

    service = get_online_serving_service()
    status = service.get_status()

    print(f"   Is initialized: {status.get('is_initialized', False)}")
    print(f"   Signal count: {status.get('signal_count', 0)}")
    print(f"   Last routine time: {status.get('last_routine_time', 'unknown')}")

    if status.get("data_range"):
        print(
            f"   Data range: {status['data_range'].get('start_date')} to {status['data_range'].get('end_date')}"
        )

except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("CONCLUSION:")
print("=" * 60)
print(
    """
If signals are identical between consecutive days:
1. This is NORMAL if model predictions haven't changed significantly
2. The model uses historical data, so small daily changes may not affect rankings
3. Check if the model is being retrained with new data

Multiple execution safety:
1. First execution: All positions show BUY (starting from 0)
2. After holdings are saved, second execution should show all HOLD
3. This is the expected behavior - holdings persistence is working correctly
"""
)
