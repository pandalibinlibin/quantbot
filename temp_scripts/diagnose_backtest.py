"""
Diagnose backtest issues:
1. Check backtest_daily return format
2. Test end_time boundary fix
3. Verify QlibConfig attributes
"""

import sys

sys.path.insert(0, "/app")

print("=" * 60)
print("Step 1: Check QlibConfig attributes")
print("=" * 60)
try:
    from app.config.qlib import qlib_config

    print(f"type(qlib_config): {type(qlib_config)}")
    print(f"has '_config': {hasattr(qlib_config, '_config')}")
    print(f"has 'system_config': {hasattr(qlib_config, 'system_config')}")
    print(f"has 'backtest_config': {hasattr(qlib_config, 'backtest_config')}")

    # Show topk_dropout_strategy config
    topk_config = qlib_config._config.get("topk_dropout_strategy", {})
    print(f"topk_dropout_strategy config: {topk_config}")

    # Show backtest config
    bt_config = qlib_config.backtest_config
    print(f"backtest_config: {bt_config}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()

print()
print("=" * 60)
print("Step 2: Check backtest_daily return format")
print("=" * 60)
try:
    from qlib.contrib.evaluate import backtest_daily
    import inspect

    sig = inspect.signature(backtest_daily)
    print(f"backtest_daily signature: {sig}")

    # Get source code of the return statement
    source = inspect.getsource(backtest_daily)
    # Find return statements
    lines = source.split("\n")
    for i, line in enumerate(lines):
        if "return" in line and not line.strip().startswith("#"):
            print(f"  Line {i}: {line.strip()}")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 60)
print("Step 3: Get signals and test minimal backtest")
print("=" * 60)
try:
    from app.services.online_serving_service import get_online_serving_service
    import pandas as pd

    service = get_online_serving_service()

    print(f"is_initialized: {service.is_initialized}")
    if not service.is_initialized:
        print("Auto-initializing...")
        service._auto_init()
        print(f"is_initialized after _auto_init: {service.is_initialized}")

    signals = service._online_manager.get_signals()
    if signals is None or (hasattr(signals, "empty") and signals.empty):
        print("ERROR: No signals available")
        sys.exit(1)

    print(f"Total signals: {len(signals)}")
    print(f"Signal columns: {signals.columns.tolist()}")
    print(f"Signal index names: {signals.index.names}")

    signal_dates = signals.index.get_level_values(0).unique().sort_values()
    print(f"Signal date range: {signal_dates[0]} to {signal_dates[-1]}")
    print(f"Total unique dates: {len(signal_dates)}")
    print(f"Last 5 dates: {[str(d.date()) for d in signal_dates[-5:]]}")

    # Test with end_time = second-to-last date (to avoid boundary issue)
    start_time = str(signal_dates[0].date())
    end_time_safe = str(signal_dates[-2].date())  # second-to-last
    end_time_last = str(signal_dates[-1].date())  # last date (causes error)

    print(f"\nstart_time: {start_time}")
    print(f"end_time (safe, -2): {end_time_safe}")
    print(f"end_time (last, -1): {end_time_last}")

    # Run a SHORT backtest with safe end_time to check return format
    from qlib.contrib.strategy import TopkDropoutStrategy

    # Use only last 30 days of signals for quick test
    test_start = str(signal_dates[-30].date())
    print(f"\nRunning quick test backtest: {test_start} to {end_time_safe}")

    strategy = TopkDropoutStrategy(topk=10, n_drop=10, signal=signals)

    result = backtest_daily(
        start_time=test_start,
        end_time=end_time_safe,
        strategy=strategy,
        account=1000000,
        benchmark="SH510300",
        exchange_kwargs={
            "limit_threshold": 0.095,
            "deal_price": "close",
            "open_cost": 0.0003,
            "close_cost": 0.0013,
            "min_cost": 5,
        },
    )

    print(f"\nResult type: {type(result)}")

    if isinstance(result, tuple):
        print(f"Tuple length: {len(result)}")
        for i, item in enumerate(result):
            print(f"  result[{i}] type: {type(item)}")
            if isinstance(item, dict):
                print(f"  result[{i}] keys: {list(item.keys())}")
                for k, v in item.items():
                    print(f"    key={k}, value type={type(v)}")
                    if isinstance(v, tuple):
                        print(f"      tuple length: {len(v)}")
                        for j, sub in enumerate(v):
                            print(f"      [{j}] type={type(sub)}")
                            if hasattr(sub, "shape"):
                                print(f"      [{j}] shape={sub.shape}")
                            if hasattr(sub, "columns"):
                                print(f"      [{j}] columns={sub.columns.tolist()}")
                            if hasattr(sub, "head"):
                                print(f"      [{j}] head=\n{sub.head(3)}")
    elif isinstance(result, dict):
        print(f"Dict keys: {list(result.keys())}")
        for k, v in result.items():
            print(f"  key={k}, value type={type(v)}")
    else:
        print(f"Unexpected result: {result}")

    print("\n✅ Quick backtest succeeded!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()

print()
print("=" * 60)
print("Diagnosis complete")
print("=" * 60)
