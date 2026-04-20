"""
Debug script to verify Qlib price fetching fix.
Run this script inside the backend container:
    docker compose exec backend python /app/temp_scripts/debug_qlib_price.py
"""

import qlib
from qlib.data import D

print("=" * 60)
print("Qlib Price Fetch Verification")
print("=" * 60)

# Initialize Qlib
print("\n1. Initializing Qlib...")
qlib.init(provider_uri="/app/qlib_data", region="cn")
print("   Qlib initialized successfully")

# Test symbols from the JSON output
test_symbols = ["SZ300782", "SH510300", "SH600570", "SZ300866"]

print("\n2. Testing CORRECT price extraction method...")
print("   Index order is ['instrument', 'datetime'], so use df.loc[symbol]")

for symbol in test_symbols:
    print(f"\n   {symbol}:")
    try:
        df = D.features(
            instruments=[symbol],
            fields=["$close"],
            start_time="2023-01-01",
            end_time="2023-12-31",
            freq="day",
        )

        if df.empty:
            print(f"   ERROR: No data returned")
            continue

        # CORRECT way: index level 0 is instrument, so use df.loc[symbol]
        if symbol in df.index.get_level_values("instrument"):
            symbol_data = df.loc[symbol, "$close"]
            latest_price = float(symbol_data.dropna().iloc[-1])
            print(f"   Latest price: {latest_price:.2f}")
        else:
            print(f"   ERROR: Symbol not in index")

    except Exception as e:
        print(f"   ERROR: {e}")

print("\n" + "=" * 60)
print("Verification complete")
print("=" * 60)
