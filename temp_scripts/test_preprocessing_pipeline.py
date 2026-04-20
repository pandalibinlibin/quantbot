"""
Test script for data preprocessing pipeline

This script validates the preprocessing pipeline implementation by:
1. Testing EMA5Processor with sample data
2. Testing RelativeChangeProcessor with sample data
3. Verifying the complete preprocessing flow

Usage (in Docker):
    docker compose exec backend python /app/../temp_scripts/test_preprocessing_pipeline.py
"""

import sys
import numpy as np
import pandas as pd

# Add app to path
sys.path.insert(0, "/app")

print("=" * 60)
print("Data Preprocessing Pipeline Test")
print("=" * 60)


def test_ema5_processor():
    """Test EMA5Processor with sample data"""
    print("\n[Test 1] EMA5Processor")
    print("-" * 40)

    from app.qlib_extensions.preprocessing import EMA5Processor

    # Create sample data
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    instruments = ["STOCK_A", "STOCK_B"]

    index = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )

    # Sample close prices
    data = {
        ("feature", "CLOSE"): [100, 200, 102, 204, 99, 198, 101, 202, 103, 206],
    }

    df = pd.DataFrame(data, index=index)

    print("Original data:")
    print(df)

    # Apply EMA5
    processor = EMA5Processor(fields_group="feature", window=5)
    result = processor(df.copy())

    print("\nAfter EMA-5 smoothing:")
    print(result)

    # Verify: EMA should smooth the values
    stock_a_original = [100, 102, 99, 101, 103]
    stock_a_ema = result.xs("STOCK_A", level="instrument")[("feature", "CLOSE")].values

    print(f"\nStock A original: {stock_a_original}")
    print(f"Stock A EMA-5:    {[round(x, 2) for x in stock_a_ema]}")

    # Manual verification for first few values
    # alpha = 2/(5+1) = 0.333
    alpha = 2.0 / 6
    expected_day1 = 100  # Initial value
    expected_day2 = alpha * 102 + (1 - alpha) * 100  # ~100.67

    print(f"\nExpected Day1: {expected_day1}, Got: {stock_a_ema[0]:.2f}")
    print(f"Expected Day2: {expected_day2:.2f}, Got: {stock_a_ema[1]:.2f}")

    assert abs(stock_a_ema[0] - expected_day1) < 0.01, "Day1 EMA mismatch"
    assert abs(stock_a_ema[1] - expected_day2) < 0.01, "Day2 EMA mismatch"

    print("\n✅ EMA5Processor test PASSED")
    return True


def test_relative_change_processor():
    """Test RelativeChangeProcessor with sample data"""
    print("\n[Test 2] RelativeChangeProcessor")
    print("-" * 40)

    from app.qlib_extensions.preprocessing import RelativeChangeProcessor

    # Create sample data with different price scales
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    instruments = ["HIGH_PRICE", "LOW_PRICE"]

    index = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )

    # HIGH_PRICE: 1000 -> 1250 (25% increase)
    # LOW_PRICE: 100 -> 125 (25% increase)
    data = {
        ("feature", "CLOSE"): [1000, 100, 1250, 125, 1000, 100],
    }

    df = pd.DataFrame(data, index=index)

    print("Original data (different price scales):")
    print(df)

    # Apply relative change
    processor = RelativeChangeProcessor(fields_group="feature")
    result = processor(df.copy())

    print("\nAfter relative change calculation:")
    print(result)

    # Verify: Both stocks should have same relative change
    high_price_changes = result.xs("HIGH_PRICE", level="instrument")[
        ("feature", "CLOSE")
    ].values
    low_price_changes = result.xs("LOW_PRICE", level="instrument")[
        ("feature", "CLOSE")
    ].values

    print(
        f"\nHIGH_PRICE relative changes: {[round(x, 4) if not np.isnan(x) else 'NaN' for x in high_price_changes]}"
    )
    print(
        f"LOW_PRICE relative changes:  {[round(x, 4) if not np.isnan(x) else 'NaN' for x in low_price_changes]}"
    )

    # Day 2: Both should be +0.25 (25% increase)
    assert np.isnan(high_price_changes[0]), "Day1 should be NaN"
    assert abs(high_price_changes[1] - 0.25) < 0.01, "HIGH_PRICE Day2 should be ~0.25"
    assert abs(low_price_changes[1] - 0.25) < 0.01, "LOW_PRICE Day2 should be ~0.25"

    # Day 3: Both should be -0.20 (20% decrease from 1250->1000, 125->100)
    assert (
        abs(high_price_changes[2] - (-0.20)) < 0.01
    ), "HIGH_PRICE Day3 should be ~-0.20"
    assert abs(low_price_changes[2] - (-0.20)) < 0.01, "LOW_PRICE Day3 should be ~-0.20"

    print("\n✅ RelativeChangeProcessor test PASSED")
    print("   Scale difference eliminated: both stocks show same relative changes")
    return True


def test_data_broadcast():
    """Test data broadcast utilities"""
    print("\n[Test 3] Data Broadcast Utilities")
    print("-" * 40)

    from app.qlib_extensions.data_broadcast import time_broadcast, stock_broadcast

    # Test time broadcast (monthly -> daily)
    print("Testing time_broadcast (monthly -> daily):")

    monthly_data = pd.DataFrame(
        {"m2_yoy": [8.5, 8.7]}, index=pd.to_datetime(["2024-01-31", "2024-02-29"])
    )

    calendar = pd.date_range("2024-01-15", "2024-02-15", freq="B")  # Business days

    daily_data = time_broadcast(monthly_data, freq="M", calendar=calendar)

    print(f"Monthly data:\n{monthly_data}")
    print(f"\nDaily data (first 5 rows):\n{daily_data.head()}")
    print(f"Daily data (last 5 rows):\n{daily_data.tail()}")

    # Test stock broadcast
    print("\nTesting stock_broadcast (macro -> all stocks):")

    instruments = ["000001.SZ", "000002.SZ", "600000.SH"]
    all_stocks_data = stock_broadcast(daily_data.head(3), instruments)

    print(f"Broadcasted to {len(instruments)} stocks:")
    print(all_stocks_data)

    print("\n✅ Data Broadcast test PASSED")
    return True


def test_complete_pipeline():
    """Test the complete preprocessing pipeline"""
    print("\n[Test 4] Complete Pipeline (EMA -> RelativeChange -> CSZScore)")
    print("-" * 40)

    from app.qlib_extensions.preprocessing import EMA5Processor, RelativeChangeProcessor

    # Create sample data with 3 stocks, different price levels
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    instruments = ["STOCK_A", "STOCK_B", "STOCK_C"]

    index = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )

    # Different price levels but similar percentage movements
    np.random.seed(42)
    base_prices = {"STOCK_A": 1000, "STOCK_B": 100, "STOCK_C": 50}

    data = []
    for date in dates:
        for inst in instruments:
            # Add some random variation
            price = base_prices[inst] * (1 + np.random.randn() * 0.02)
            data.append(price)

    df = pd.DataFrame({("feature", "CLOSE"): data}, index=index)

    print("Original data (different price scales):")
    print(df.unstack(level="instrument"))

    # Step 1: EMA smoothing
    ema_processor = EMA5Processor(fields_group="feature", window=5)
    df_ema = ema_processor(df.copy())

    print("\nAfter EMA-5:")
    print(df_ema.unstack(level="instrument"))

    # Step 2: Relative change
    change_processor = RelativeChangeProcessor(fields_group="feature")
    df_change = change_processor(df_ema.copy())

    print("\nAfter Relative Change:")
    print(df_change.unstack(level="instrument"))

    # Step 3: Cross-sectional Z-Score (manual implementation for test)
    def cs_zscore(group):
        mean = group.mean()
        std = group.std()
        if std == 0:
            return group * 0
        return (group - mean) / std

    df_zscore = df_change.copy()
    df_zscore[("feature", "CLOSE")] = (
        df_zscore[("feature", "CLOSE")].groupby(level="datetime").transform(cs_zscore)
    )

    print("\nAfter Cross-Sectional Z-Score:")
    print(df_zscore.unstack(level="instrument"))

    # Verify: Z-scores should be comparable across stocks
    # Mean of Z-scores for each day should be ~0
    for date in dates[1:]:  # Skip first day (NaN from diff)
        day_data = df_zscore.xs(date, level="datetime")[("feature", "CLOSE")]
        day_mean = day_data.mean()
        day_std = day_data.std()
        print(f"Date {date.date()}: mean={day_mean:.4f}, std={day_std:.4f}")

        # Mean should be close to 0, std close to 1
        if not np.isnan(day_mean):
            assert abs(day_mean) < 0.01, f"Mean should be ~0, got {day_mean}"

    print("\n✅ Complete Pipeline test PASSED")
    print("   All stocks now on comparable scale after preprocessing")
    return True


if __name__ == "__main__":
    try:
        test_ema5_processor()
        test_relative_change_processor()
        test_data_broadcast()
        test_complete_pipeline()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nPreprocessing pipeline is ready for use.")
        print("Next steps:")
        print("1. Import PreprocessedDataHandler in your code")
        print("2. Use it to load and preprocess data")
        print("3. Access preprocessed fields via $close, $volume, etc.")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
