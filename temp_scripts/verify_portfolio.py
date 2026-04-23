#!/usr/bin/env python3
"""
Verify Update Portfolio execution results.

Run inside Docker:
  docker exec quantbot-backend-1 python /app/temp_scripts/verify_portfolio.py

Checks:
  1. Portfolio JSON file exists and has valid structure
  2. TopK positions match config (topk count, score-weighted weights)
  3. Weights sum to ~1.0
  4. Confidence is calculated and percentile uses backtest history
  5. Live confidence entry was appended to confidence_history.json
  6. Scores are sorted descending (top K are truly the highest)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
errors = []
warnings = []


def check(condition, msg_pass, msg_fail):
    if condition:
        print(f"  {PASS} {msg_pass}")
    else:
        print(f"  {FAIL} {msg_fail}")
        errors.append(msg_fail)


def warn(condition, msg_pass, msg_warn):
    if condition:
        print(f"  {PASS} {msg_pass}")
    else:
        print(f"  {WARN} {msg_warn}")
        warnings.append(msg_warn)


# ============================================================
# 1. Find the latest portfolio file
# ============================================================
print("\n" + "=" * 60)
print("1. PORTFOLIO FILE CHECK")
print("=" * 60)

portfolio_dir = Path("/app/data/target_portfolio")
check(portfolio_dir.exists(), f"Portfolio dir exists: {portfolio_dir}", f"Portfolio dir NOT found: {portfolio_dir}")

if not portfolio_dir.exists():
    print(f"\n{FAIL} Cannot continue without portfolio directory")
    sys.exit(1)

# Find topk_portfolio_*.json files
portfolio_files = sorted(portfolio_dir.glob("topk_portfolio_*.json"))
check(len(portfolio_files) > 0, f"Found {len(portfolio_files)} portfolio file(s)", "No topk_portfolio_*.json files found")

if not portfolio_files:
    print(f"\n{FAIL} Cannot continue without portfolio file")
    sys.exit(1)

latest_file = portfolio_files[-1]
print(f"  📄 Latest file: {latest_file.name}")

with open(latest_file, "r", encoding="utf-8") as f:
    portfolio = json.load(f)

# ============================================================
# 2. Structure validation
# ============================================================
print("\n" + "=" * 60)
print("2. STRUCTURE VALIDATION")
print("=" * 60)

required_keys = ["strategy", "generated_at", "trade_date", "signal_for_date",
                 "topk", "weight_method", "confidence", "positions"]
for key in required_keys:
    check(key in portfolio, f"Key '{key}' present", f"Key '{key}' MISSING")

check(portfolio.get("strategy") == "topk", f"Strategy: {portfolio.get('strategy')}", f"Unexpected strategy: {portfolio.get('strategy')}")

print(f"\n  📋 Summary:")
print(f"     Trade date:        {portfolio.get('trade_date')}")
print(f"     Signal for date:   {portfolio.get('signal_for_date')}")
print(f"     Generated at:      {portfolio.get('generated_at')}")
print(f"     TopK:              {portfolio.get('topk')}")
print(f"     Weight method:     {portfolio.get('weight_method')}")
print(f"     Confidence:        {portfolio.get('confidence')}")
print(f"     Score spread:      {portfolio.get('score_spread')}")
print(f"     Conf percentile:   {portfolio.get('confidence_percentile')}")
print(f"     Conf label:        {portfolio.get('confidence_label')}")
print(f"     Conf interpretation: {portfolio.get('confidence_interpretation', '')[:60]}...")

# ============================================================
# 3. Positions validation
# ============================================================
print("\n" + "=" * 60)
print("3. POSITIONS VALIDATION")
print("=" * 60)

positions = portfolio.get("positions", [])
topk = portfolio.get("topk", 10)

check(len(positions) == topk, f"Position count = {len(positions)} (matches topk={topk})", f"Position count = {len(positions)}, expected topk={topk}")

# Print positions
print(f"\n  {'Rank':<6} {'Symbol':<12} {'Name':<16} {'Score':<12} {'Weight':<10}")
print(f"  {'-'*56}")
for pos in positions:
    print(f"  {pos.get('rank', '?'):<6} {pos.get('symbol', '?'):<12} {pos.get('name', '?'):<16} {pos.get('score', 0):.6f}   {pos.get('weight', 0):.4%}")

# Check weights sum to ~1.0
total_weight = sum(p.get("weight", 0) for p in positions)
check(abs(total_weight - 1.0) < 0.01, f"Weights sum = {total_weight:.6f} (≈1.0)", f"Weights sum = {total_weight:.6f} (should be ≈1.0)")

# Check scores are sorted descending
scores = [p.get("score", 0) for p in positions]
is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
check(is_sorted, "Scores sorted descending (top K selection correct)", "Scores NOT sorted descending!")

# Check all weights > 0
all_positive = all(p.get("weight", 0) > 0 for p in positions)
check(all_positive, "All weights > 0", "Some weights are <= 0!")

# Check rank sequence
ranks = [p.get("rank", 0) for p in positions]
check(ranks == list(range(1, len(positions) + 1)), "Ranks are 1..N sequential", f"Ranks not sequential: {ranks}")

# If score_weighted, verify weights proportional to scores
if portfolio.get("weight_method") == "score_weighted":
    print(f"\n  Verifying score-weighted allocation:")
    total_score = sum(p.get("score", 0) for p in positions)
    if total_score > 0:
        max_deviation = 0
        for pos in positions:
            expected_weight = pos.get("score", 0) / total_score
            actual_weight = pos.get("weight", 0)
            deviation = abs(expected_weight - actual_weight)
            max_deviation = max(max_deviation, deviation)
        check(max_deviation < 0.001, f"Weight allocation matches scores (max deviation: {max_deviation:.6f})", f"Weight allocation mismatch (max deviation: {max_deviation:.6f})")

# ============================================================
# 4. Confidence validation
# ============================================================
print("\n" + "=" * 60)
print("4. CONFIDENCE VALIDATION")
print("=" * 60)

confidence = portfolio.get("confidence", -1)
check(0 <= confidence <= 1, f"Confidence = {confidence:.4f} (in [0,1])", f"Confidence = {confidence} (out of range!)")

percentile = portfolio.get("confidence_percentile")
check(percentile is not None, f"Percentile = {percentile}", "Percentile is None (no history?)")

label = portfolio.get("confidence_label", "")
valid_labels = ["极强", "较强", "正常", "较弱", "极弱", "历史数据不足"]
check(label in valid_labels, f"Label = '{label}' (valid)", f"Label = '{label}' (unexpected)")

# ============================================================
# 5. Confidence history check
# ============================================================
print("\n" + "=" * 60)
print("5. CONFIDENCE HISTORY CHECK")
print("=" * 60)

history_path = Path("/app/data/target_portfolio/confidence_history.json")
check(history_path.exists(), f"History file exists", "History file NOT found")

if history_path.exists():
    with open(history_path, "r", encoding="utf-8") as f:
        history_data = json.load(f)
    
    history = history_data.get("history", [])
    print(f"  📊 Total entries: {len(history)}")
    
    backtest_entries = [h for h in history if h.get("source") == "backtest"]
    live_entries = [h for h in history if h.get("source") == "live"]
    print(f"     Backtest entries: {len(backtest_entries)}")
    print(f"     Live entries:     {len(live_entries)}")
    
    check(len(backtest_entries) > 0, "Has backtest history (from Run Backtest)", "No backtest history! Run Backtest first.")
    check(len(live_entries) > 0, "Has live entry (from Update Portfolio)", "No live entry found!")
    
    # Check that today's date has a live entry
    trade_date = portfolio.get("trade_date", "")
    live_for_today = [h for h in live_entries if h.get("date") == trade_date]
    check(len(live_for_today) > 0, f"Live entry exists for trade_date={trade_date}", f"No live entry for trade_date={trade_date}")
    
    if live_for_today:
        live_conf = live_for_today[0].get("confidence", -1)
        print(f"     Live confidence for {trade_date}: {live_conf:.4f}")
    
    # Verify percentile calculation manually
    if percentile is not None and len(history) > 5:
        # The percentile is calculated BEFORE appending live entry
        # So use all entries except the current live one
        historical_values = [h["confidence"] for h in history if not (h.get("date") == trade_date and h.get("source") == "live")]
        if historical_values:
            rank = sum(1 for v in historical_values if v <= confidence)
            expected_pct = round(rank / len(historical_values) * 100, 1)
            pct_diff = abs(expected_pct - percentile)
            # Allow small tolerance due to the live entry being appended after percentile calc
            warn(pct_diff < 5.0, f"Percentile verification: expected≈{expected_pct}%, got {percentile}% (diff={pct_diff}%)", f"Percentile mismatch: expected≈{expected_pct}%, got {percentile}% (diff={pct_diff}%)")
    
    # Show last 5 entries
    print(f"\n  Last 5 history entries:")
    for entry in history[-5:]:
        src = entry.get("source", "?")
        date = entry.get("date", "?")
        conf = entry.get("confidence", 0)
        raw = entry.get("raw_confidence", "N/A")
        print(f"     [{src:8s}] {date}: confidence={conf:.4f}, raw={raw}")

# ============================================================
# 6. Signal export check
# ============================================================
print("\n" + "=" * 60)
print("6. SIGNAL EXPORT CHECK")
print("=" * 60)

signals_dir = Path("/app/data/signals")
if signals_dir.exists():
    signal_files = sorted(signals_dir.glob("*.json"))
    print(f"  📄 Signal files: {len(signal_files)}")
    if signal_files:
        latest_signal = signal_files[-1]
        print(f"     Latest: {latest_signal.name}")
else:
    print(f"  {WARN} Signals directory not found")

# ============================================================
# FINAL RESULT
# ============================================================
print("\n" + "=" * 60)
if errors:
    print(f"RESULT: {FAIL} {len(errors)} ERROR(S)")
    for e in errors:
        print(f"  - {e}")
else:
    print(f"RESULT: {PASS} ALL CHECKS PASSED")

if warnings:
    print(f"\n{WARN} {len(warnings)} WARNING(S):")
    for w in warnings:
        print(f"  - {w}")

print("=" * 60)
sys.exit(1 if errors else 0)
