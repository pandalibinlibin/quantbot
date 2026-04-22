"""
Verify backtest results after running Run Backtest from Dashboard.
Checks: result file exists, metrics are valid, confidence history was generated.

Usage: docker compose exec backend python /app/../temp_scripts/verify_backtest.py
"""
import json
import os
import glob
import sys


def check_backtest_results():
    """Check if backtest result files exist and are valid."""
    print("=" * 60)
    print("BACKTEST VERIFICATION")
    print("=" * 60)

    errors = []
    warnings = []

    # 1. Check latest backtest result
    print("\n[1] Checking backtest result file...")
    result_dir = "/app/data"
    result_pattern = os.path.join(result_dir, "backtest_result*.json")
    result_files = sorted(glob.glob(result_pattern))

    if not result_files:
        # Also check alternative locations
        alt_patterns = [
            "/app/data/target_portfolio/backtest_*.json",
            "/app/data/backtest_*.json",
        ]
        for pat in alt_patterns:
            result_files.extend(sorted(glob.glob(pat)))

    if not result_files:
        errors.append("No backtest result files found")
        print("   FAIL: No backtest result files found")
    else:
        latest = result_files[-1]
        print("   Found:", latest)
        with open(latest, "r") as f:
            data = json.load(f)

        status = data.get("status", "unknown")
        if status == "success":
            print("   Status: SUCCESS")
        else:
            errors.append("Backtest status: " + status)
            print("   FAIL: Status =", status)
            if "error" in data:
                print("   Error:", data["error"])

        # Check key metrics
        metrics_to_check = [
            ("trading_days", lambda v: v > 0),
            ("total_return", lambda v: isinstance(v, (int, float))),
            ("rebalance_period", lambda v: v == 1),
        ]
        for key, validator in metrics_to_check:
            val = data.get(key)
            if val is None:
                warnings.append("Missing key: " + key)
                print("   WARN: Missing", key)
            elif not validator(val):
                warnings.append(key + " = " + str(val) + " (unexpected)")
                print("   WARN:", key, "=", val)
            else:
                print("   ", key, "=", val)

        # Check risk metrics
        risk = data.get("risk_metrics", {})
        if risk:
            print("   Risk metrics:")
            for k in ["annualized_return", "max_drawdown", "sharpe_ratio", "volatility"]:
                v = risk.get(k)
                if v is not None:
                    print("     ", k, "=", round(v, 4))
                else:
                    warnings.append("Missing risk metric: " + k)

        # Check strategy
        strategy = data.get("strategy", "")
        print("   Strategy:", strategy)
        if "topk" not in strategy.lower():
            warnings.append("Strategy does not contain 'topk': " + strategy)

    # 2. Check confidence history
    print("\n[2] Checking confidence history...")
    conf_dir = "/app/data/target_portfolio"
    conf_path = os.path.join(conf_dir, "confidence_history.json")

    if not os.path.exists(conf_path):
        warnings.append("confidence_history.json not found (expected after backtest)")
        print("   WARN: confidence_history.json not found at", conf_path)
    else:
        with open(conf_path, "r") as f:
            history = json.load(f)

        total = len(history)
        backtest_entries = [h for h in history if h.get("source") == "backtest"]
        live_entries = [h for h in history if h.get("source") == "live"]

        print("   Total entries:", total)
        print("   Backtest entries:", len(backtest_entries))
        print("   Live entries:", len(live_entries))

        if total == 0:
            warnings.append("Confidence history is empty")
        else:
            # Show confidence stats
            values = [h["confidence"] for h in history if "confidence" in h]
            if values:
                print("   Confidence range: [%.4f, %.4f]" % (min(values), max(values)))
                print("   Confidence mean: %.4f" % (sum(values) / len(values)))

            # Show first and last dates
            dates = [h.get("date", "") for h in history]
            if dates:
                print("   Date range:", dates[0], "to", dates[-1])

    # 3. Check portfolio output directory
    print("\n[3] Checking portfolio output directory...")
    portfolio_files = sorted(glob.glob(os.path.join(conf_dir, "topk_portfolio_*.json")))
    print("   Portfolio files:", len(portfolio_files))
    if portfolio_files:
        print("   Latest:", os.path.basename(portfolio_files[-1]))

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print("RESULT: FAIL (%d errors, %d warnings)" % (len(errors), len(warnings)))
        for e in errors:
            print("  ERROR:", e)
    elif warnings:
        print("RESULT: PASS with %d warnings" % len(warnings))
    else:
        print("RESULT: ALL CHECKS PASSED")

    for w in warnings:
        print("  WARN:", w)

    print("=" * 60)
    return len(errors) == 0


if __name__ == "__main__":
    success = check_backtest_results()
    sys.exit(0 if success else 1)
