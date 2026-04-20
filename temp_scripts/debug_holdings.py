#!/usr/bin/env python3
"""Debug script to check holdings state in ETFEnhancedIndexingService."""

import sys

sys.path.insert(0, "/app")

from app.services.etf_enhanced_indexing_service import get_etf_enhanced_indexing_service


def main():
    print("=" * 60)
    print("DEBUG: ETFEnhancedIndexingService Holdings State")
    print("=" * 60)

    # Get the singleton service
    service = get_etf_enhanced_indexing_service()

    # Check internal holdings
    holdings = service._current_holdings
    print(f"\nInternal _current_holdings: {len(holdings)} positions")
    if holdings:
        for symbol, shares in list(holdings.items())[:5]:
            print(f"  {symbol}: {shares}")
        if len(holdings) > 5:
            print(f"  ... and {len(holdings) - 5} more")
    else:
        print("  (empty)")

    # Check if holdings file exists
    holdings_file = service._get_holdings_file_path()
    print(f"\nHoldings file path: {holdings_file}")
    print(f"Holdings file exists: {holdings_file.exists()}")

    if holdings_file.exists():
        import json

        with open(holdings_file, "r") as f:
            data = json.load(f)
        file_holdings = data.get("holdings", {})
        print(f"Holdings in file: {len(file_holdings)} positions")
        for symbol, shares in list(file_holdings.items())[:5]:
            print(f"  {symbol}: {shares}")

    # Check if they match
    print("\n" + "=" * 60)
    if holdings == file_holdings:
        print("✓ Internal holdings MATCH file holdings")
    else:
        print("✗ Internal holdings DO NOT MATCH file holdings!")
        print(f"  Internal: {len(holdings)} positions")
        print(f"  File: {len(file_holdings)} positions")
    print("=" * 60)


if __name__ == "__main__":
    main()
