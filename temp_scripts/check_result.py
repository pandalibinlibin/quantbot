"""Check latest backtest result for updated risk metrics."""
import json

path = "/app/mlruns/backtest_results/latest_result.json"
with open(path, "r") as f:
    d = json.load(f)

print("=== Risk Metrics ===")
rm = d.get("risk_metrics", {})
for k, v in rm.items():
    print(f"  {k}: {v}")

print(f"\ntotal_cost: {d.get('total_cost')}")
print(f"net_return: {d.get('net_return')}")
print(f"total_return: {d.get('total_return')}")
print(f"final_account: {d.get('final_account')}")
