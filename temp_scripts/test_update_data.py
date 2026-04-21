"""
Test script to verify the 'Update Data' flow is correct and complete.

This script checks:
1. Qlib data directory structure
2. Calendar file validity
3. Instruments file
4. Binary data files per symbol
5. Factor data (return_1d)
6. Label expression validity (the CSRankNorm fix)
7. Qlib initialization
8. D.features() works correctly
9. CustomFactorHandler can load data

Run inside Docker:
    docker exec -it quantbot-backend-1 python /app/temp_scripts/test_update_data.py
"""

import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, "/app")

QLIB_DATA_PATH = "/app/qlib_data"
PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
WARN = "\033[93m⚠️  WARN\033[0m"

results = []


def check(name, condition, detail=""):
    """Record a check result."""
    status = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))
    return condition


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ==============================================================
# Test 1: Qlib data directory structure
# ==============================================================
section("1. Qlib Data Directory Structure")

qlib_path = Path(QLIB_DATA_PATH)
check("qlib_data directory exists", qlib_path.exists())

calendars_dir = qlib_path / "calendars"
instruments_dir = qlib_path / "instruments"
features_dir = qlib_path / "features"

check("calendars/ directory exists", calendars_dir.exists())
check("instruments/ directory exists", instruments_dir.exists())
check("features/ directory exists", features_dir.exists())

# ==============================================================
# Test 2: Calendar file
# ==============================================================
section("2. Calendar File (day.txt)")

calendar_file = calendars_dir / "day.txt"
check("calendars/day.txt exists", calendar_file.exists())

if calendar_file.exists():
    with open(calendar_file, "r") as f:
        dates = [line.strip() for line in f if line.strip()]
    check("Calendar has dates", len(dates) > 0, f"{len(dates)} dates")

    if dates:
        first_date = dates[0].split()[0]
        last_date = dates[-1].split()[0]
        check("First date format OK", len(first_date) == 10, f"first={first_date}")
        check("Last date format OK", len(last_date) == 10, f"last={last_date}")
        print(f"  📅 Calendar range: {first_date} to {last_date}")

    # Check no minute-level calendar
    min_calendar = calendars_dir / "1min.txt"
    check("No 1min.txt calendar (cleaned)", not min_calendar.exists())

# ==============================================================
# Test 3: Instruments file
# ==============================================================
section("3. Instruments File")

instruments_file = instruments_dir / "all.txt"
check("instruments/all.txt exists", instruments_file.exists())

if instruments_file.exists():
    with open(instruments_file, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    check("Instruments file has entries", len(lines) > 0, f"{len(lines)} instruments")

    if lines:
        # Parse instrument names
        instruments = []
        for line in lines:
            parts = line.split()
            instruments.append(parts[0])
        
        # Check for lowercase (Qlib convention)
        sample = instruments[:5]
        all_lower = all(inst == inst.lower() for inst in instruments)
        check("Instruments are lowercase", all_lower, f"sample: {sample}")
        
        # Check benchmark is excluded
        has_benchmark = any("sh000300" in inst or "000300" in inst.lower() for inst in instruments)
        check("Benchmark (sh000300) excluded from instruments", not has_benchmark)

# ==============================================================
# Test 4: Feature bin files
# ==============================================================
section("4. Feature Binary Files")

if features_dir.exists():
    symbol_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
    check("Feature directories exist", len(symbol_dirs) > 0, f"{len(symbol_dirs)} symbols")

    if symbol_dirs:
        # Check a sample symbol
        sample_dir = symbol_dirs[0]
        bin_files = list(sample_dir.glob("*.bin"))
        day_files = list(sample_dir.glob("*.day.bin"))
        
        check(
            "Sample symbol has bin files",
            len(bin_files) > 0,
            f"{sample_dir.name}: {len(bin_files)} files"
        )

        # List all bin file names for the sample
        bin_names = sorted([f.name for f in bin_files])
        print(f"  📁 Sample ({sample_dir.name}) bin files: {bin_names[:10]}...")

        # Check OHLCV fields exist
        expected_fields = ["open", "high", "low", "close", "volume"]
        for field in expected_fields:
            has_field = any(field in f.name for f in bin_files)
            check(f"  Has '{field}' bin file", has_field)

        # Check return_1d factor exists
        has_return_1d = any("return_1d" in f.name for f in bin_files)
        check("  Has 'return_1d' factor bin file", has_return_1d)

# ==============================================================
# Test 5: System config - label expression fix
# ==============================================================
section("5. System Config - Label Expression")

try:
    import yaml
    config_path = Path("/app/app/config/qlib/system_config.yaml")
    check("system_config.yaml exists", config_path.exists())
    
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        label_config = config.get("label_config", {})
        cn_expr = label_config.get("cn", {}).get("expression", "")
        us_expr = label_config.get("us", {}).get("expression", "")
        
        print(f"  📝 CN label expression: {cn_expr}")
        print(f"  📝 US label expression: {us_expr}")
        
        # CSRankNorm should NOT be in expressions (it's a processor, not an operator)
        check(
            "CN label does NOT contain CSRankNorm",
            "CSRankNorm" not in cn_expr,
            f"expr={cn_expr}"
        )
        check(
            "US label does NOT contain CSRankNorm",
            "CSRankNorm" not in us_expr,
            f"expr={us_expr}"
        )
        
        # Should contain Ref (valid Qlib operator)
        check("CN label contains Ref operator", "Ref(" in cn_expr)
        check("US label contains Ref operator", "Ref(" in us_expr)
except Exception as e:
    check("System config check", False, str(e))

# ==============================================================
# Test 6: Qlib initialization
# ==============================================================
section("6. Qlib Initialization")

try:
    import qlib
    from qlib.constant import REG_CN
    
    qlib.init(
        provider_uri=QLIB_DATA_PATH,
        region=REG_CN,
    )
    check("Qlib init successful", True)
except Exception as e:
    check("Qlib init successful", False, str(e))

# ==============================================================
# Test 7: D.calendar() and D.instruments()
# ==============================================================
section("7. Qlib D.calendar() and D.instruments()")

try:
    from qlib.data import D
    
    calendar = D.calendar(freq="day")
    check("D.calendar(freq='day') works", len(calendar) > 0, f"{len(calendar)} dates")
    if calendar:
        print(f"  📅 Qlib calendar: {calendar[0]} to {calendar[-1]}")
    
    instruments = D.instruments("all")
    check("D.instruments('all') works", instruments is not None)
    
    # Get instrument list
    inst_list = D.list_instruments(instruments=instruments, as_list=True)
    check("Instrument list not empty", len(inst_list) > 0, f"{len(inst_list)} instruments")
    if inst_list:
        print(f"  📋 Sample instruments: {inst_list[:5]}")
except Exception as e:
    check("D.calendar/instruments", False, str(e))

# ==============================================================
# Test 8: D.features() - load OHLCV data
# ==============================================================
section("8. D.features() - Load OHLCV Data")

try:
    from qlib.data import D
    
    # Use first 3 instruments
    test_instruments = inst_list[:3] if inst_list else ["sh510300"]
    
    features = D.features(
        instruments=test_instruments,
        fields=["$close", "$open", "$high", "$low", "$volume"],
        start_time="2026-01-01",
        end_time="2026-04-20",
        freq="day",
    )
    
    check("D.features() returns data", features is not None and not features.empty, 
          f"shape={features.shape}")
    
    if features is not None and not features.empty:
        print(f"  📊 Features head:\n{features.head(3)}")
        
        # Check no NaN in close
        close_col = [c for c in features.columns if 'close' in c.lower()]
        if close_col:
            nan_pct = features[close_col[0]].isna().mean() * 100
            check("Close data NaN% < 5%", nan_pct < 5, f"NaN={nan_pct:.1f}%")
except Exception as e:
    check("D.features()", False, str(e))

# ==============================================================
# Test 9: D.features() - Load return_1d factor
# ==============================================================
section("9. D.features() - Load return_1d Factor")

try:
    from qlib.data import D
    
    test_instruments = inst_list[:3] if inst_list else ["sh510300"]
    
    factor_data = D.features(
        instruments=test_instruments,
        fields=["$return_1d"],
        start_time="2026-01-01",
        end_time="2026-04-20",
        freq="day",
    )
    
    check("return_1d factor loads", factor_data is not None and not factor_data.empty,
          f"shape={factor_data.shape}")
    
    if factor_data is not None and not factor_data.empty:
        nan_pct = factor_data.iloc[:, 0].isna().mean() * 100
        check("return_1d NaN% < 10%", nan_pct < 10, f"NaN={nan_pct:.1f}%")
        print(f"  📊 return_1d sample:\n{factor_data.head(5)}")
except Exception as e:
    check("return_1d factor", False, str(e))

# ==============================================================
# Test 10: Label expression evaluation
# ==============================================================
section("10. Label Expression Evaluation")

try:
    from qlib.data import D
    
    test_instruments = inst_list[:3] if inst_list else ["sh510300"]
    
    # Test CN label expression (the one that was failing with CSRankNorm)
    label_data = D.features(
        instruments=test_instruments,
        fields=["Ref($close, -2) / $close - 1"],
        start_time="2026-01-01",
        end_time="2026-04-20",
        freq="day",
    )
    
    check(
        "CN label expression evaluates",
        label_data is not None and not label_data.empty,
        f"shape={label_data.shape}"
    )
    
    if label_data is not None and not label_data.empty:
        nan_pct = label_data.iloc[:, 0].isna().mean() * 100
        print(f"  📊 Label NaN%: {nan_pct:.1f}% (last 2 days expected NaN)")
        print(f"  📊 Label sample:\n{label_data.head(5)}")
except Exception as e:
    check("Label expression evaluation", False, str(e))
    traceback.print_exc()

# ==============================================================
# Test 11: CustomFactorHandler initialization
# ==============================================================
section("11. CustomFactorHandler Initialization")

try:
    from app.services.custom_factor_handler import CustomFactorHandler
    
    handler = CustomFactorHandler(
        instruments="all",
        start_time="2026-01-01",
        end_time="2026-04-20",
        freq="day",
    )
    
    check("CustomFactorHandler created", handler is not None)
    
    # Check feature config
    feat_config = handler.get_feature_config()
    check("Feature config not empty", len(feat_config) > 0, f"{len(feat_config)} items")
    
    # Check label config
    label_config = handler.get_label_config()
    check("Label config not empty", len(label_config) > 0)
    
    if label_config:
        expressions, names = label_config
        print(f"  🏷️  Label expressions: {expressions}")
        print(f"  🏷️  Label names: {names}")
        check(
            "Label expression does NOT use CSRankNorm",
            all("CSRankNorm" not in expr for expr in expressions)
        )
except Exception as e:
    check("CustomFactorHandler init", False, str(e))
    traceback.print_exc()

# ==============================================================
# Summary
# ==============================================================
section("SUMMARY")

total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)

print(f"\n  Total checks: {total}")
print(f"  {PASS}: {passed}")
print(f"  {FAIL}: {failed}")

if failed > 0:
    print(f"\n  Failed checks:")
    for name, ok, detail in results:
        if not ok:
            print(f"    ❌ {name}: {detail}")

print()
sys.exit(0 if failed == 0 else 1)
