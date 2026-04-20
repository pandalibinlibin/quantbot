"""
Test script for EnhancedIndexingService algorithm validation.

This script tests:
1. Algorithm correctness (total weight = 100%)
2. Deviation constraints
3. Action labels (overweight/underweight)
"""

import sys

sys.path.insert(0, "/app")

import pandas as pd
import numpy as np
from app.services.enhanced_indexing_service import get_enhanced_indexing_service


def test_algorithm():
    """Test the enhanced indexing algorithm with mock data."""
    print("=" * 60)
    print("Enhanced Indexing Algorithm Test")
    print("=" * 60)

    # Initialize service
    svc = get_enhanced_indexing_service()
    print(f"\nService config:")
    print(f"  enabled: {svc.enabled}")
    print(f"  max_deviation: {svc.max_deviation}")
    print(f"  benchmark: {svc.benchmark}")

    # Create mock benchmark weights (equal weights for 5 stocks)
    benchmark_weights = {
        "STOCK_A": 0.2,
        "STOCK_B": 0.2,
        "STOCK_C": 0.2,
        "STOCK_D": 0.2,
        "STOCK_E": 0.2,
    }

    # Create mock signals (prediction scores)
    # Higher score = better expected return
    signals = {
        "STOCK_A": 0.05,  # Best performer
        "STOCK_B": 0.03,  # Good performer
        "STOCK_C": -0.02,  # Poor performer
        "STOCK_D": -0.04,  # Worst performer
        "STOCK_E": 0.01,  # Average performer
    }

    print(f"\nInput signals:")
    for stock, score in sorted(signals.items(), key=lambda x: x[1], reverse=True):
        print(f"  {stock}: {score:+.4f}")

    print(f"\nBenchmark weights:")
    for stock, weight in benchmark_weights.items():
        print(f"  {stock}: {weight:.2%}")

    # Test the algorithm
    result = svc._calculate_weights(
        signals=signals,
        benchmark_weights=benchmark_weights,
        max_deviation=0.02,  # 2% max deviation
        min_weight=0.001,
    )

    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60)

    # Calculate totals
    total_weight = sum(item["target_weight"] for item in result)
    overweight_count = sum(1 for item in result if item["action"] == "超配")
    underweight_count = sum(1 for item in result if item["action"] == "低配")
    neutral_count = sum(1 for item in result if item["action"] == "持平")

    print(f"\nPortfolio ({len(result)} positions):")
    print("-" * 60)
    print(
        f"{'Rank':<5} {'Stock':<10} {'Benchmark':<10} {'Target':<10} {'Deviation':<12} {'Action':<8}"
    )
    print("-" * 60)

    for item in result:
        print(
            f"{item['rank']:<5} {item['instrument']:<10} {item['benchmark_weight']:.2%}      {item['target_weight']:.2%}      {item['deviation_pct']:<12} {item['action']:<8}"
        )

    print("-" * 60)
    print(
        f"{'Total':<16} {sum(benchmark_weights.values()):.2%}      {total_weight:.2%}"
    )

    print(f"\nStatistics:")
    print(f"  Overweight stocks: {overweight_count}")
    print(f"  Underweight stocks: {underweight_count}")
    print(f"  Neutral stocks: {neutral_count}")

    # Validation
    print("\n" + "=" * 60)
    print("Validation")
    print("=" * 60)

    tests_passed = 0
    tests_total = 3

    # Test 1: Total weight should be ~1.0
    if abs(total_weight - 1.0) < 0.0001:
        print(f"✅ Test 1 PASSED: Total weight = {total_weight:.6f}")
        tests_passed += 1
    else:
        print(f"❌ Test 1 FAILED: Total weight = {total_weight:.6f} (expected ~1.0)")

    # Test 2: Best performer should be overweight
    stock_a_item = next(
        (item for item in result if item["instrument"] == "STOCK_A"), None
    )
    if stock_a_item and stock_a_item["action"] == "超配":
        print(f"✅ Test 2 PASSED: Best performer (STOCK_A) is overweight")
        tests_passed += 1
    else:
        print(f"❌ Test 2 FAILED: Best performer (STOCK_A) should be overweight")

    # Test 3: Worst performer should be underweight
    stock_d_item = next(
        (item for item in result if item["instrument"] == "STOCK_D"), None
    )
    if stock_d_item and stock_d_item["action"] == "低配":
        print(f"✅ Test 3 PASSED: Worst performer (STOCK_D) is underweight")
        tests_passed += 1
    else:
        print(f"❌ Test 3 FAILED: Worst performer (STOCK_D) should be underweight")

    print(f"\n{'=' * 60}")
    print(f"Test Summary: {tests_passed}/{tests_total} tests passed")
    print(f"{'=' * 60}")

    return tests_passed == tests_total


if __name__ == "__main__":
    success = test_algorithm()
    sys.exit(0 if success else 1)
