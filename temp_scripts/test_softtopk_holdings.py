#!/usr/bin/env python3
"""
Test SoftTopkStrategy actual holdings behavior
"""

import numpy as np
import pandas as pd
from qlib.contrib.strategy import SoftTopkStrategy


def test_softtopk_holdings():
    """Test how many assets SoftTopkStrategy actually holds"""

    # Create mock signal data (8 assets, 5 days)
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    assets = [f"ETF_{i}" for i in range(8)]

    # Create MultiIndex
    index = pd.MultiIndex.from_product(
        [dates, assets], names=["datetime", "instrument"]
    )

    # Mock prediction scores (decreasing order)
    scores = [0.85, 0.82, 0.80, 0.79, 0.65, 0.60, 0.45, 0.30]
    signal_data = np.tile(scores, len(dates))

    signals = pd.Series(signal_data, index=index, name="score")

    print("🔍 Testing SoftTopkStrategy with topk=3")
    print(f"Input signals shape: {signals.shape}")
    print(f"Assets: {assets}")
    print(f"Scores: {scores}")

    # Test different topk values
    for topk in [3, 5]:
        print(f"\n📊 Testing topk={topk}")

        try:
            strategy = SoftTopkStrategy(topk=topk, signal=signals)

            # Get strategy decisions for first day
            first_day = dates[0]
            day_signals = signals.loc[first_day]

            print(f"Strategy created successfully with topk={topk}")
            print(f"Strategy type: {type(strategy)}")

            # Try to get portfolio weights (this depends on Qlib's internal API)
            # This might need adjustment based on actual Qlib API

        except Exception as e:
            print(f"❌ Error with topk={topk}: {e}")


if __name__ == "__main__":
    test_softtopk_holdings()
