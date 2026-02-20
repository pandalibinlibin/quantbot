"""
Verify backtest results by checking:
1. Benchmark (CSI300) return for comparison
2. Prediction score distribution
3. Model information
"""

import sys

sys.path.insert(0, "/app")

import qlib

qlib.init(provider_uri="/app/qlib_data")

import pickle
from pathlib import Path
from qlib.data import D
import pandas as pd

print("=" * 60)
print("BACKTEST VERIFICATION REPORT")
print("=" * 60)

# 1. Check model
print("\n[1] MODEL INFORMATION")
print("-" * 40)
model_files = list(Path("/app/models").glob("*.pkl"))
if model_files:
    model_path = model_files[0]
    print(f"Model path: {model_path}")
    print(f"Model size: {model_path.stat().st_size / 1024:.1f} KB")
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    print(f"Model type: {type(model).__name__}")
else:
    print("No model found!")
    sys.exit(1)

# 2. Check data range
print("\n[2] DATA RANGE")
print("-" * 40)
try:
    # Read calendar to get date range
    calendar_path = Path("/app/qlib_data/calendars/day.txt")
    if calendar_path.exists():
        with open(calendar_path, "r") as f:
            dates = [line.strip() for line in f if line.strip()]
        print(f"Calendar dates: {dates[0]} to {dates[-1]}")
        print(f"Total trading days: {len(dates)}")
except Exception as e:
    print(f"Error reading calendar: {e}")

# 3. Check instruments
print("\n[3] INSTRUMENTS")
print("-" * 40)
try:
    instruments_path = Path("/app/qlib_data/instruments/all.txt")
    if instruments_path.exists():
        with open(instruments_path, "r") as f:
            instruments = [line.strip().split("\t")[0] for line in f if line.strip()]
        print(f"Total instruments: {len(instruments)}")
        print(f"Sample: {instruments[:5]}")
except Exception as e:
    print(f"Error reading instruments: {e}")

# 4. Generate predictions and check distribution
print("\n[4] PREDICTION DISTRIBUTION")
print("-" * 40)
try:
    from app.services.custom_factor_handler import CustomFactorHandler
    from qlib.data.dataset import DatasetH

    handler = CustomFactorHandler(
        instruments="all",
        start_time="2025-02-10",
        end_time="2026-02-10",
        freq="day",
        infer_processors=[],
    )
    dataset = DatasetH(
        handler=handler, segments={"backtest": ["2025-02-10", "2026-02-10"]}
    )

    pred = model.predict(dataset, segment="backtest")
    print(f"Total predictions: {len(pred)}")
    print(f"Unique dates: {pred.index.get_level_values(0).nunique()}")
    print(f"Unique stocks: {pred.index.get_level_values(1).nunique()}")
    # pred is a Series with MultiIndex, not a DataFrame with 'score' column
    print(f"\nPrediction score statistics:")
    print(f"  Mean: {pred.mean():.6f}")
    print(f"  Std:  {pred.std():.6f}")
    print(f"  Min:  {pred.min():.6f}")
    print(f"  Max:  {pred.max():.6f}")
except Exception as e:
    print(f"Error generating predictions: {e}")
    import traceback

    traceback.print_exc()

# 5. Simple return calculation (if we can get price data)
print("\n[5] SIMPLE RETURN CHECK")
print("-" * 40)
try:
    # Get a sample stock's return
    sample_stock = instruments[0] if instruments else None
    if sample_stock:
        df = D.features(
            [sample_stock], ["$close"], start_time="2025-02-10", end_time="2026-02-10"
        )
        if not df.empty:
            start_price = df.iloc[0]["$close"]
            end_price = df.iloc[-1]["$close"]
            simple_return = (end_price - start_price) / start_price
            print(f"Sample stock ({sample_stock}) return: {simple_return*100:.2f}%")
except Exception as e:
    print(f"Error calculating simple return: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
