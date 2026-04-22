"""
Diagnostic script: Verify backtest report_df data correctness.
Run inside Docker: docker exec quantbot-backend-1 python /app/temp_scripts/verify_backtest_data.py
"""

import sys
import os
import json

sys.path.insert(0, "/app")
os.chdir("/app")

# 1. Load and check saved result JSON
print("=" * 60)
print("STEP 1: Check saved backtest result JSON")
print("=" * 60)
result_path = "/app/mlruns/backtest_results/latest_result.json"
try:
    with open(result_path) as f:
        result = json.load(f)
    print(f"  status: {result.get('status')}")
    print(f"  start_time: {result.get('start_time')}")
    print(f"  end_time: {result.get('end_time')}")
    print(f"  trading_days: {result.get('trading_days')}")
    print(f"  total_return: {result.get('total_return')}")
    print(f"  total_cost: {result.get('total_cost')}")
    print(f"  net_return: {result.get('net_return')}")
    print(f"  final_account: {result.get('final_account')}")
    print(f"  benchmark: {result.get('benchmark')}")
    rm = result.get("risk_metrics", {})
    print(f"  risk_metrics:")
    for k, v in rm.items():
        print(f"    {k}: {v}")
    charts = result.get("charts", {})
    cr = charts.get("cumulative_returns", [])
    print(f"  charts.cumulative_returns: {len(cr)} points")
    if cr:
        print(f"    first: {cr[0]}")
        print(f"    last:  {cr[-1]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. Re-run a quick backtest and inspect report_df columns
print()
print("=" * 60)
print("STEP 2: Run backtest and inspect report_df structure")
print("=" * 60)
try:
    from app.services.online_serving_service import get_online_serving_service
    from qlib.contrib.evaluate import backtest_daily, risk_analysis
    from qlib.contrib.strategy import TopkDropoutStrategy
    import pandas as pd

    service = get_online_serving_service()
    if not service.is_initialized:
        service._auto_init()

    signals = service._online_manager.get_signals()
    print(f"  Signals shape: {signals.shape}")
    print(f"  Signals type: {type(signals)}")
    if hasattr(signals, "columns"):
        print(f"  Signal columns: {signals.columns.tolist()}")
    else:
        print(f"  Signal name: {signals.name}")
        print(f"  Signal index names: {signals.index.names}")

    signal_dates = signals.index.get_level_values(0).unique().sort_values()
    # Use only last 30 days for quick test
    start_time = str(signal_dates[-30].date())
    end_time = str(signal_dates[-2].date())
    print(f"  Quick test period: {start_time} to {end_time}")

    strategy = TopkDropoutStrategy(topk=10, n_drop=10, signal=signals)
    report_df, positions = backtest_daily(
        start_time=start_time,
        end_time=end_time,
        strategy=strategy,
        account=1000000,
        benchmark="SH510300",
        exchange_kwargs={
            "limit_threshold": 0.095,
            "deal_price": "close",
            "open_cost": 0.0001,
            "close_cost": 0.0001,
            "min_cost": 0,
        },
    )

    print(f"\n  report_df type: {type(report_df)}")
    print(f"  report_df shape: {report_df.shape}")
    print(f"  report_df columns: {report_df.columns.tolist()}")
    print(f"  report_df dtypes:\n{report_df.dtypes}")
    print(f"\n  report_df.head(5):\n{report_df.head(5)}")
    print(f"\n  report_df.tail(5):\n{report_df.tail(5)}")
    print(f"\n  report_df.describe():\n{report_df.describe()}")

    # Check specific columns
    if "return" in report_df.columns:
        returns = report_df["return"]
        print(f"\n  Daily returns stats:")
        print(f"    mean:  {returns.mean():.6f}")
        print(f"    std:   {returns.std():.6f}")
        print(f"    min:   {returns.min():.6f}")
        print(f"    max:   {returns.max():.6f}")
        print(f"    >0 count: {(returns > 0).sum()} / {len(returns)}")
        print(f"    cum_return: {((1 + returns).cumprod().iloc[-1] - 1):.6f}")

    if "cost" in report_df.columns:
        costs = report_df["cost"]
        print(f"\n  Daily cost stats:")
        print(f"    mean:  {costs.mean():.6f}")
        print(f"    std:   {costs.std():.6f}")
        print(f"    sum:   {costs.sum():.6f}")
        print(f"    min:   {costs.min():.6f}")
        print(f"    max:   {costs.max():.6f}")
    else:
        print(f"\n  WARNING: 'cost' column NOT in report_df!")

    if "bench" in report_df.columns:
        bench = report_df["bench"]
        print(f"\n  Benchmark return stats:")
        print(f"    mean:  {bench.mean():.6f}")
        print(f"    cum:   {((1 + bench).cumprod().iloc[-1] - 1):.6f}")
    else:
        print(f"\n  WARNING: 'bench' column NOT in report_df!")

    if "turnover" in report_df.columns:
        to = report_df["turnover"]
        print(f"\n  Turnover stats:")
        print(f"    mean:  {to.mean():.6f}")
        print(f"    sum:   {to.sum():.6f}")
    else:
        print(f"\n  WARNING: 'turnover' column NOT in report_df!")

    # Check positions structure
    print(f"\n  positions type: {type(positions)}")
    if isinstance(positions, dict):
        print(f"  positions keys (first 5): {list(positions.keys())[:5]}")
        first_key = list(positions.keys())[0]
        first_pos = positions[first_key]
        print(f"  first position type: {type(first_pos)}")
        if isinstance(first_pos, dict):
            print(f"  first position keys: {list(first_pos.keys())[:10]}")
            for k, v in list(first_pos.items())[:3]:
                print(f"    {k}: {v}")

    # Calculate metrics that should be returned
    print("\n" + "=" * 60)
    print("STEP 3: Calculate expected metrics")
    print("=" * 60)
    returns = report_df["return"]
    analysis = risk_analysis(returns, freq="day")
    print(f"  risk_analysis output:\n{analysis}")

    annual_ret = float(analysis.loc["annualized_return", "risk"])
    max_dd = float(analysis.loc["max_drawdown", "risk"])
    sharpe = float(analysis.loc["information_ratio", "risk"])
    vol = float(analysis.loc["std", "risk"])

    # Calmar ratio
    calmar = annual_ret / abs(max_dd) if max_dd != 0 else 0
    print(f"\n  Calculated metrics:")
    print(f"    annualized_return: {annual_ret:.6f}")
    print(f"    max_drawdown: {max_dd:.6f}")
    print(f"    sharpe_ratio: {sharpe:.6f}")
    print(f"    volatility: {vol:.6f}")
    print(f"    calmar_ratio: {calmar:.4f}")

    # Win rate
    win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
    print(f"    win_rate: {win_rate:.4f}")

    # P/L ratio
    pos_returns = returns[returns > 0]
    neg_returns = returns[returns < 0]
    pl_ratio = (
        (pos_returns.mean() / abs(neg_returns.mean()))
        if len(neg_returns) > 0 and neg_returns.mean() != 0
        else 0
    )
    print(f"    profit_loss_ratio: {pl_ratio:.4f}")

    # Cost metrics
    if "cost" in report_df.columns:
        total_cost_pct = report_df["cost"].sum()
        total_cost_money = total_cost_pct * 1000000  # account
        total_profit = ((1 + returns).cumprod().iloc[-1] - 1) * 1000000
        cost_to_profit = total_cost_money / total_profit if total_profit > 0 else 0
        cost_ratio = total_cost_pct
        print(f"    total_cost (% of account): {total_cost_pct:.6f}")
        print(f"    total_cost (money): {total_cost_money:.2f}")
        print(f"    total_profit (money): {total_profit:.2f}")
        print(f"    cost_to_profit_ratio: {cost_to_profit:.4f}")
        print(f"    cost_ratio: {cost_ratio:.6f}")

    # Turnover
    if "turnover" in report_df.columns:
        total_turnover = report_df["turnover"].sum()
        print(f"    total_turnover: {total_turnover:.4f}")

    print("\n✅ Diagnostic complete")

except Exception as e:
    print(f"  ERROR: {e}")
    import traceback

    traceback.print_exc()
