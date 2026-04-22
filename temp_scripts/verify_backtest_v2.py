"""
Verify backtest results after clicking Run Backtest.
Checks backend logs, result files, and API response.
"""
import sys
sys.path.insert(0, "/app")
import os
import json
import glob

print("=" * 60)
print("Backtest Verification Script v2")
print("=" * 60)

# 1. Check backtest result files
print("\n--- 1. Check result files ---")
result_dirs = [
    "/app/data/target_portfolio",
    "/app/data/backtest_results",
    "/app/mlruns/backtest_results",
]
for d in result_dirs:
    if os.path.exists(d):
        files = glob.glob(os.path.join(d, "**/*"), recursive=True)
        print(f"  {d}: {len(files)} files")
        for f in files[:5]:
            size = os.path.getsize(f) if os.path.isfile(f) else "dir"
            print(f"    {os.path.basename(f)} ({size})")
    else:
        print(f"  {d}: NOT EXISTS")

# 2. Check confidence_history.json
print("\n--- 2. Check confidence_history.json ---")
confidence_path = "/app/data/target_portfolio/confidence_history.json"
if os.path.exists(confidence_path):
    with open(confidence_path) as f:
        data = json.load(f)
    print(f"  EXISTS, entries: {len(data)}")
    if data:
        first = data[0] if isinstance(data, list) else list(data.values())[0]
        print(f"  First entry sample: {str(first)[:200]}")
else:
    print(f"  NOT EXISTS")

# 3. Try calling execute_backtest API directly to see full response
print("\n--- 3. Test execute_backtest directly ---")
try:
    from app.services.online_serving_service import get_online_serving_service
    
    service = get_online_serving_service()
    print(f"  is_initialized: {service.is_initialized}")
    
    if not service.is_initialized:
        print("  Auto-initializing (may take 1-2 min)...")
        service._auto_init()
    
    print("  Running execute_backtest()...")
    result = service.execute_backtest()
    
    print(f"  Result status: {result.get('status')}")
    
    if result.get("status") == "error":
        print(f"  ERROR: {result.get('error')}")
    else:
        print(f"  trading_days: {result.get('trading_days')}")
        print(f"  total_return: {result.get('total_return')}")
        print(f"  net_return: {result.get('net_return')}")
        print(f"  benchmark: {result.get('benchmark')}")
        print(f"  start_time: {result.get('start_time')}")
        print(f"  end_time: {result.get('end_time')}")
        
        risk = result.get("risk_metrics", {})
        print(f"  annualized_return: {risk.get('annualized_return')}")
        print(f"  max_drawdown: {risk.get('max_drawdown')}")
        print(f"  sharpe_ratio: {risk.get('sharpe_ratio')}")
        
        charts = result.get("charts", {})
        print(f"  charts keys: {list(charts.keys()) if charts else 'none'}")
        if charts:
            for k, v in charts.items():
                if isinstance(v, list):
                    print(f"    {k}: {len(v)} data points")
                elif isinstance(v, dict):
                    print(f"    {k}: dict with keys {list(v.keys())[:5]}")

    print("\n  ✅ Backtest verification complete!")

except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Done")
print("=" * 60)
