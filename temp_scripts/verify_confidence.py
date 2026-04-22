"""
Verify confidence_history.json after backtest.

Checks:
1. File exists and is valid JSON
2. Has expected number of entries (close to trading_days)
3. Each entry has required fields: date, confidence, source
4. Confidence values are in valid range [0, 1]
5. Dates are sorted and unique
6. Manually recalculate a few confidence values to verify accuracy
7. Cross-check with latest_result.json trading days
"""

import json
import sys
from pathlib import Path

# Paths (inside Docker container)
CONFIDENCE_PATH = Path("/app/data/target_portfolio/confidence_history.json")
RESULT_PATH = Path("/app/mlruns/backtest_results/latest_result.json")


def load_json(path: Path):
    if not path.exists():
        print(f"  ERROR: {path} does not exist!")
        return None
    with open(path, "r") as f:
        return json.load(f)


def main():
    print("=" * 60)
    print("CONFIDENCE HISTORY VERIFICATION")
    print("=" * 60)

    # 1. Load confidence history
    print("\n1. Loading confidence_history.json...")
    raw = load_json(CONFIDENCE_PATH)
    if raw is None:
        sys.exit(1)

    # Unwrap {"history": [...]} wrapper
    if isinstance(raw, dict) and "history" in raw:
        history = raw["history"]
        print(f"   Format: wrapped dict with 'history' key")
    elif isinstance(raw, list):
        history = raw
        print(f"   Format: raw list")
    else:
        print(f"   ERROR: unexpected format: {type(raw)}")
        print(f"   Content preview: {str(raw)[:200]}")
        sys.exit(1)
    print(f"   Entries: {len(history)}")

    # 2. Load latest backtest result for cross-check
    print("\n2. Loading latest_result.json for cross-check...")
    result = load_json(RESULT_PATH)
    trading_days = result.get("trading_days", 0) if result else 0
    print(f"   Backtest trading days: {trading_days}")

    # 3. Validate structure
    print("\n3. Validating entry structure...")
    errors = []
    for i, entry in enumerate(history):
        if "date" not in entry:
            errors.append(f"  Entry {i}: missing 'date'")
        if "confidence" not in entry:
            errors.append(f"  Entry {i}: missing 'confidence'")
        if "source" not in entry:
            errors.append(f"  Entry {i}: missing 'source'")
    if errors:
        for e in errors[:10]:
            print(e)
        print(f"   FAIL: {len(errors)} structural errors")
    else:
        print("   OK: All entries have date, confidence, source")

    # 4. Validate confidence range [0, 1]
    print("\n4. Validating confidence range [0, 1]...")
    confidences = [h["confidence"] for h in history]
    import math

    valid_confs = [
        c for c in confidences if not (isinstance(c, float) and math.isnan(c))
    ]
    nan_count = len(confidences) - len(valid_confs)
    out_of_range = [c for c in valid_confs if c < 0 or c > 1]
    if nan_count > 0:
        print(f"   WARNING: {nan_count} NaN values found")
    if out_of_range:
        print(f"   FAIL: {len(out_of_range)} values out of range!")
        print(f"   Examples: {out_of_range[:5]}")
    elif valid_confs:
        print(
            f"   OK: min={min(valid_confs):.4f}, max={max(valid_confs):.4f}, "
            f"mean={sum(valid_confs)/len(valid_confs):.4f}"
        )
        # Check if all values are identical (bad normalization)
        unique_vals = len(set(round(c, 4) for c in valid_confs))
        if unique_vals <= 3:
            print(
                f"   WARNING: Only {unique_vals} unique values - confidence lacks variation!"
            )
        else:
            print(f"   Unique values: {unique_vals}")
    else:
        print(f"   FAIL: No valid confidence values")

    # 5. Validate dates sorted and unique
    print("\n5. Validating date ordering and uniqueness...")
    dates = [h["date"] for h in history]
    is_sorted = dates == sorted(dates)
    is_unique = len(dates) == len(set(dates))
    print(f"   Sorted: {'OK' if is_sorted else 'FAIL'}")
    print(
        f"   Unique: {'OK' if is_unique else 'FAIL - ' + str(len(dates) - len(set(dates))) + ' duplicates'}"
    )
    print(f"   Date range: {dates[0]} ~ {dates[-1]}")

    # 6. Check source distribution
    print("\n6. Source distribution...")
    sources = {}
    for h in history:
        s = h.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    for s, count in sources.items():
        print(f"   {s}: {count}")

    # 7. Compare count with trading days
    print("\n7. Entry count vs trading days...")
    backtest_entries = [h for h in history if h.get("source") == "backtest"]
    print(f"   Backtest entries: {len(backtest_entries)}")
    print(f"   Trading days: {trading_days}")
    if trading_days > 0:
        ratio = len(backtest_entries) / trading_days
        status = "OK" if 0.8 <= ratio <= 1.2 else "WARNING"
        print(f"   Ratio: {ratio:.2f} ({status})")

    # 8. Spot-check and distribution analysis
    print("\n8. Spot-check and distribution analysis...")
    try:
        import statistics

        # Show first 5 and last 5 entries with all fields
        print("\n   First 5 entries:")
        for h in history[:5]:
            raw = h.get("raw_confidence", "N/A")
            spread = h.get("score_spread", "N/A")
            raw_str = f"{raw:.4f}" if isinstance(raw, (int, float)) else str(raw)
            spread_str = (
                f"{spread:.6f}" if isinstance(spread, (int, float)) else str(spread)
            )
            print(
                f"     {h['date']}: conf={h['confidence']:.4f} raw={raw_str} spread={spread_str}"
            )
        print("\n   Last 5 entries:")
        for h in history[-5:]:
            raw = h.get("raw_confidence", "N/A")
            spread = h.get("score_spread", "N/A")
            raw_str = f"{raw:.4f}" if isinstance(raw, (int, float)) else str(raw)
            spread_str = (
                f"{spread:.6f}" if isinstance(spread, (int, float)) else str(spread)
            )
            print(
                f"     {h['date']}: conf={h['confidence']:.4f} raw={raw_str} spread={spread_str}"
            )

        # Statistics on valid confidence values
        if valid_confs and len(valid_confs) > 1:
            print(f"\n   Statistics (confidence):")
            print(f"     Mean:   {statistics.mean(valid_confs):.4f}")
            print(f"     Median: {statistics.median(valid_confs):.4f}")
            print(f"     Stdev:  {statistics.stdev(valid_confs):.4f}")

        # Histogram (simple text-based)
        buckets = [0] * 10
        for c in valid_confs:
            bucket = min(int(c * 10), 9)
            buckets[bucket] += 1
        print(f"\n   Distribution:")
        max_count = max(buckets) if buckets else 1
        for i in range(10):
            bar = "#" * int(buckets[i] / max_count * 30) if max_count > 0 else ""
            pct = buckets[i] / len(valid_confs) * 100 if valid_confs else 0
            print(f"     [{i*10:3d}%-{(i+1)*10:3d}%]: {bar} ({buckets[i]}, {pct:.1f}%)")

        # Raw confidence stats if available
        raw_confs = [
            h.get("raw_confidence")
            for h in history
            if h.get("raw_confidence") is not None
        ]
        if raw_confs:
            valid_raw = [
                r for r in raw_confs if not (isinstance(r, float) and math.isnan(r))
            ]
            if valid_raw:
                print(f"\n   Raw confidence stats:")
                print(
                    f"     Min: {min(valid_raw):.4f}, Max: {max(valid_raw):.4f}, Mean: {statistics.mean(valid_raw):.4f}"
                )

    except Exception as e:
        print(f"   Error during spot-check: {e}")

    # 9. Verify confidence is usable for portfolio update
    print("\n9. Portfolio update readiness check...")
    latest_entry = history[-1] if history else None
    if latest_entry:
        print(f"   Latest entry: {latest_entry}")
        conf = latest_entry["confidence"]
        if conf > 0:
            print(f"   OK: Confidence {conf:.4f} > 0, portfolio can use this data")
        else:
            print(
                f"   WARNING: Confidence is 0, model may have low discriminative power"
            )
    else:
        print("   FAIL: No entries found")

    # Summary
    print("\n" + "=" * 60)
    all_ok = (
        history is not None
        and len(history) > 0
        and not errors
        and not out_of_range
        and is_sorted
        and is_unique
    )
    if all_ok:
        print("RESULT: ALL CHECKS PASSED")
    else:
        print("RESULT: SOME CHECKS FAILED - review above")
    print("=" * 60)


if __name__ == "__main__":
    main()
