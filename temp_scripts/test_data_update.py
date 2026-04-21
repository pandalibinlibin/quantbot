"""
Test script for data update validation.

Verifies:
1. Qlib data availability and integrity
2. Feature loading via CustomFactorHandler
3. Preprocessing pipeline (EMA-5, RelativeChange, CSZScoreNorm)
4. Cross-sectional normalization properties
5. Label calculation correctness

Usage:
    docker exec quantbot-backend-1 python /app/temp_scripts/test_data_update.py
"""

import sys

sys.path.insert(0, "/app")

import traceback
import numpy as np


def section(title):
    print("\n" + "=" * 70)
    print("  " + title)
    print("=" * 70)


def check(condition, msg_pass, msg_fail):
    if condition:
        print("  [PASS] " + msg_pass)
        return True
    else:
        print("  [FAIL] " + msg_fail)
        return False


def main():
    results = {"pass": 0, "fail": 0}

    def record(ok):
        if ok:
            results["pass"] += 1
        else:
            results["fail"] += 1

    # ====================================================================
    # STEP 1: Check Qlib data exists
    # ====================================================================
    section("Step 1: Check Qlib Data Availability")
    try:
        from pathlib import Path

        qlib_data_dir = Path("/app/qlib_data")

        record(
            check(
                qlib_data_dir.exists(),
                "Qlib data directory exists: " + str(qlib_data_dir),
                "Qlib data directory NOT found: " + str(qlib_data_dir),
            )
        )

        features_dir = qlib_data_dir / "features"
        if features_dir.exists():
            instrument_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
            count = len(instrument_dirs)
            record(
                check(
                    count > 0,
                    "Found " + str(count) + " instrument directories",
                    "No instrument directories found",
                )
            )
            if instrument_dirs:
                sample_dir = instrument_dirs[0]
                bin_files = list(sample_dir.glob("*.day.bin"))
                print("  Sample instrument: " + str(sample_dir.name))
                print("  Bin files: " + str([f.name for f in bin_files[:10]]))
                record(
                    check(
                        len(bin_files) > 0,
                        "Found "
                        + str(len(bin_files))
                        + " bin files in sample instrument",
                        "No bin files found in sample instrument",
                    )
                )
        else:
            print("  Features directory not found at: " + str(features_dir))
            record(False)

        # Check calendars
        calendars_dir = qlib_data_dir / "calendars"
        if calendars_dir.exists():
            cal_files = list(calendars_dir.glob("*"))
            print("  Calendar files: " + str([f.name for f in cal_files]))
            record(
                check(
                    len(cal_files) > 0,
                    "Calendar files exist",
                    "No calendar files found",
                )
            )
        else:
            print("  Calendars directory not found")

        # Check instruments
        instruments_dir = qlib_data_dir / "instruments"
        if instruments_dir.exists():
            inst_files = list(instruments_dir.glob("*"))
            print("  Instrument files: " + str([f.name for f in inst_files]))
            record(
                check(
                    len(inst_files) > 0,
                    "Instrument files exist",
                    "No instrument files found",
                )
            )
    except Exception as e:
        print("  ERROR: " + str(e))
        traceback.print_exc()
        record(False)

    # ====================================================================
    # STEP 2: Initialize Qlib
    # ====================================================================
    section("Step 2: Initialize Qlib")
    try:
        import qlib
        from qlib.config import REG_CN

        qlib.init(
            provider_uri="/app/qlib_data",
            region=REG_CN,
        )
        print("  Qlib initialized successfully")
        record(True)

        # Test calendar
        from qlib.data import D

        calendar = D.calendar(freq="day")
        cal_len = len(calendar)
        print("  Calendar length: " + str(cal_len))
        print("  Date range: " + str(calendar[0]) + " ~ " + str(calendar[-1]))
        record(
            check(
                cal_len > 100,
                "Calendar has " + str(cal_len) + " trading days",
                "Calendar too short: " + str(cal_len),
            )
        )

        # Test instruments
        instruments = D.instruments("all")
        inst_list = D.list_instruments(instruments=instruments, as_list=True)
        inst_count = len(inst_list)
        print("  Total instruments: " + str(inst_count))
        if inst_list:
            print("  Sample instruments: " + str(inst_list[:5]))
        record(
            check(
                inst_count > 0,
                "Found " + str(inst_count) + " instruments",
                "No instruments found",
            )
        )

    except Exception as e:
        print("  ERROR: " + str(e))
        traceback.print_exc()
        record(False)

    # ====================================================================
    # STEP 3: Test raw data loading
    # ====================================================================
    section("Step 3: Test Raw Data Loading")
    try:
        from qlib.data import D

        # Load raw close price for a few instruments
        recent_dates = D.calendar(freq="day")[-30:]
        start = str(recent_dates[0])[:10]
        end = str(recent_dates[-1])[:10]
        print("  Loading raw data for last 30 trading days: " + start + " ~ " + end)

        raw_df = D.features(
            instruments=D.instruments("all"),
            fields=["$close", "$open", "$high", "$low", "$volume"],
            start_time=start,
            end_time=end,
            freq="day",
        )
        print("  Raw data shape: " + str(raw_df.shape))
        print("  Columns: " + str(list(raw_df.columns)))
        print("  Index levels: " + str(raw_df.index.names))

        record(
            check(
                raw_df.shape[0] > 0,
                "Raw data loaded: " + str(raw_df.shape[0]) + " rows",
                "No raw data loaded",
            )
        )

        # Check for NaN ratio
        nan_ratio = float(raw_df.isnull().sum().sum()) / (
            raw_df.shape[0] * raw_df.shape[1]
        )
        print("  NaN ratio: " + str(round(nan_ratio * 100, 2)) + "%")
        record(
            check(
                nan_ratio < 0.5,
                "NaN ratio acceptable: " + str(round(nan_ratio * 100, 2)) + "%",
                "NaN ratio too high: " + str(round(nan_ratio * 100, 2)) + "%",
            )
        )

        # Check close price range
        close_vals = raw_df["$close"].dropna()
        if len(close_vals) > 0:
            print("  Close price stats:")
            print("    min: " + str(round(float(close_vals.min()), 4)))
            print("    max: " + str(round(float(close_vals.max()), 4)))
            print("    mean: " + str(round(float(close_vals.mean()), 4)))
            record(
                check(
                    float(close_vals.min()) > 0,
                    "Close prices are positive",
                    "Found non-positive close prices",
                )
            )

    except Exception as e:
        print("  ERROR: " + str(e))
        traceback.print_exc()
        record(False)

    # ====================================================================
    # STEP 4: Test preprocessing pipeline
    # ====================================================================
    section("Step 4: Test Preprocessing Pipeline (via DataHandlerLP)")
    try:
        import pandas as pd
        from qlib.data import D
        from qlib.data.dataset.handler import DataHandlerLP

        # Use DataHandlerLP to test the full preprocessing pipeline,
        # which is how CustomFactorHandler actually processes data.
        # The processors use fields_group="feature" which requires
        # DataHandlerLP's internal MultiIndex column structure.

        recent_dates = D.calendar(freq="day")
        start_60 = str(recent_dates[-60])[:10]
        end_date = str(recent_dates[-1])[:10]
        print("  Test period: " + start_60 + " ~ " + end_date)

        from app.qlib_extensions.preprocessing import (
            EMA5Processor,
            RelativeChangeProcessor,
        )

        # Build a handler with the same preprocessing pipeline as CustomFactorHandler
        data_loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (
                        ["$close", "$open", "$high", "$low", "$volume"],
                        ["CLOSE", "OPEN", "HIGH", "LOW", "VOLUME"],
                    ),
                },
            },
        }

        infer_processors = [
            {"class": "Fillna", "kwargs": {"fields_group": "feature", "fill_value": 0}},
            EMA5Processor(fields_group="feature", window=5),
            RelativeChangeProcessor(fields_group="feature"),
            {"class": "CSZScoreNorm", "kwargs": {"fields_group": "feature"}},
        ]

        handler = DataHandlerLP(
            instruments="all",
            start_time=start_60,
            end_time=end_date,
            data_loader=data_loader,
            infer_processors=infer_processors,
        )

        # Fetch infer data (preprocessed features)
        infer_df = handler.fetch(data_key=DataHandlerLP.DK_I)
        print("  Preprocessed data shape: " + str(infer_df.shape))
        print("  Columns: " + str(list(infer_df.columns)))

        record(
            check(
                infer_df.shape[0] > 0,
                "DataHandlerLP produced " + str(infer_df.shape[0]) + " rows",
                "DataHandlerLP produced no data",
            )
        )

        # Check NaN ratio after full pipeline
        nan_ratio = float(infer_df.isnull().sum().sum()) / max(
            infer_df.shape[0] * infer_df.shape[1], 1
        )
        print("  NaN ratio after pipeline: " + str(round(nan_ratio * 100, 2)) + "%")

        # Check cross-sectional properties on the CLOSE column
        close_col = ("feature", "CLOSE")
        if close_col in infer_df.columns:
            col_data = infer_df[close_col]
        else:
            # Flat column name fallback
            close_col = "CLOSE"
            col_data = infer_df[close_col] if close_col in infer_df.columns else None

        if col_data is not None:
            vals = col_data.dropna()
            print("\n  Preprocessed CLOSE stats (after full pipeline):")
            print("    count: " + str(len(vals)))
            print("    mean: " + str(round(float(vals.mean()), 4)))
            print("    std: " + str(round(float(vals.std()), 4)))
            print("    min: " + str(round(float(vals.min()), 4)))
            print("    max: " + str(round(float(vals.max()), 4)))

            # Cross-sectional stats per date
            date_level = infer_df.index.get_level_values("datetime")
            unique_dates = date_level.unique()
            sample_dates = unique_dates[-5:]

            print("\n  Cross-sectional stats for last 5 dates:")
            cs_means = []
            cs_stds = []
            for dt in sample_dates:
                date_slice = col_data.loc[
                    infer_df.index.get_level_values("datetime") == dt
                ].dropna()
                if len(date_slice) > 1:
                    cs_mean = float(date_slice.mean())
                    cs_std = float(date_slice.std())
                    cs_means.append(cs_mean)
                    cs_stds.append(cs_std)
                    dt_str = str(dt)[:10]
                    print(
                        "    "
                        + dt_str
                        + ": mean="
                        + str(round(cs_mean, 4))
                        + ", std="
                        + str(round(cs_std, 4))
                        + ", n="
                        + str(len(date_slice))
                    )

            if cs_means:
                avg_mean = np.mean(cs_means)
                avg_std = np.mean(cs_stds)
                print("  Average cross-sectional mean: " + str(round(avg_mean, 4)))
                print("  Average cross-sectional std: " + str(round(avg_std, 4)))

                record(
                    check(
                        abs(avg_mean) < 0.5,
                        "Cross-sectional mean near 0: " + str(round(avg_mean, 4)),
                        "Cross-sectional mean NOT near 0: " + str(round(avg_mean, 4)),
                    )
                )
                record(
                    check(
                        0.3 < avg_std < 3.0,
                        "Cross-sectional std reasonable: " + str(round(avg_std, 4)),
                        "Cross-sectional std out of range: " + str(round(avg_std, 4)),
                    )
                )
            else:
                print("  WARNING: Could not compute cross-sectional stats")
                record(False)
        else:
            print("  WARNING: CLOSE column not found in preprocessed data")
            record(False)

    except Exception as e:
        print("  ERROR: " + str(e))
        traceback.print_exc()
        record(False)

    # ====================================================================
    # STEP 5: Test Label Calculation
    # ====================================================================
    section("Step 5: Test Label Calculation")
    try:
        import yaml
        from qlib.data import D

        # Load label config
        config_path = "/app/app/config/qlib/system_config.yaml"
        with open(config_path, "r") as f:
            sys_config = yaml.safe_load(f)

        region = sys_config.get("data", {}).get("region", "cn")
        label_cfg = sys_config.get("label_config", {}).get(region, {})
        label_expr = label_cfg.get("expression", "")
        label_desc = label_cfg.get("description", "")
        print("  Region: " + region)
        print("  Label expression: " + label_expr)
        print("  Label description: " + label_desc)

        record(
            check(
                len(label_expr) > 0,
                "Label expression configured",
                "Label expression is empty",
            )
        )

        # Calculate label values
        recent_dates = D.calendar(freq="day")[-30:]
        start = str(recent_dates[0])[:10]
        end = str(recent_dates[-1])[:10]

        label_df = D.features(
            instruments=D.instruments("all"),
            fields=[label_expr],
            start_time=start,
            end_time=end,
            freq="day",
        )
        print("  Label data shape: " + str(label_df.shape))

        label_vals = label_df.iloc[:, 0].dropna()
        if len(label_vals) > 0:
            print("  Label value stats:")
            print("    count: " + str(len(label_vals)))
            print("    min: " + str(round(float(label_vals.min()), 6)))
            print("    max: " + str(round(float(label_vals.max()), 6)))
            print("    mean: " + str(round(float(label_vals.mean()), 6)))
            print("    std: " + str(round(float(label_vals.std()), 6)))

            # Label should be return values (typically small, centered near 0)
            record(
                check(
                    abs(float(label_vals.mean())) < 0.5,
                    "Label values look like returns (mean near 0)",
                    "Label values may not be returns (mean="
                    + str(round(float(label_vals.mean()), 6))
                    + ")",
                )
            )

            # Check for no extreme outliers (returns > 100% or < -100%)
            extreme_count = int(((label_vals.abs() > 1.0).sum()))
            total_count = len(label_vals)
            extreme_pct = extreme_count / total_count * 100
            print(
                "  Extreme values (|return| > 100%): "
                + str(extreme_count)
                + " ("
                + str(round(extreme_pct, 2))
                + "%)"
            )
            record(
                check(
                    extreme_pct < 5.0,
                    "Extreme values within acceptable range",
                    "Too many extreme values: " + str(round(extreme_pct, 2)) + "%",
                )
            )
        else:
            print("  WARNING: No valid label values")
            record(False)

    except Exception as e:
        print("  ERROR: " + str(e))
        traceback.print_exc()
        record(False)

    # ====================================================================
    # STEP 6: Test CustomFactorHandler integration
    # ====================================================================
    section("Step 6: Test CustomFactorHandler Integration")
    try:
        from app.services.custom_factor_handler import CustomFactorHandler

        handler = CustomFactorHandler.__new__(CustomFactorHandler)
        handler.enable_alpha158 = True
        handler.freq = "day"
        handler._system_config = None
        handler.region = None

        # Test feature config
        feature_config = handler.get_feature_config()
        feat_exprs, feat_names = feature_config
        print("  Feature expressions count: " + str(len(feat_exprs)))
        print("  Feature names count: " + str(len(feat_names)))
        if feat_names:
            print("  First 10 features: " + str(feat_names[:10]))
        record(
            check(
                len(feat_exprs) > 0,
                "Feature config has " + str(len(feat_exprs)) + " features",
                "Feature config is empty",
            )
        )

        # Test label config
        label_config = handler.get_label_config()
        label_exprs, label_names = label_config
        print("  Label expressions: " + str(label_exprs))
        print("  Label names: " + str(label_names))
        record(
            check(
                len(label_exprs) > 0,
                "Label config has " + str(len(label_exprs)) + " labels",
                "Label config is empty",
            )
        )

    except Exception as e:
        print("  ERROR: " + str(e))
        traceback.print_exc()
        record(False)

    # ====================================================================
    # STEP 7: Test DataHandlerLP with learn_processors (CSZScoreNorm on labels)
    # ====================================================================
    section("Step 7: Test DataHandlerLP Label Normalization")
    try:
        from qlib.data import D
        from qlib.data.dataset.handler import DataHandlerLP
        from qlib.data.dataset.processor import CSZScoreNorm
        import yaml

        # Load config
        with open("/app/app/config/qlib/system_config.yaml", "r") as f:
            sys_config = yaml.safe_load(f)
        region = sys_config.get("data", {}).get("region", "cn")
        label_cfg = sys_config.get("label_config", {}).get(region, {})
        label_expr = label_cfg.get("expression", "Ref($close, -2) / $close - 1")

        recent_dates = D.calendar(freq="day")
        start = str(recent_dates[0])[:10]
        end = str(recent_dates[-1])[:10]

        # Build a simple handler to test learn_processors
        data_loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (["$close", "$volume"], ["CLOSE", "VOLUME"]),
                    "label": ([label_expr], ["LABEL0"]),
                },
            },
        }

        learn_processors = [
            {"class": "DropnaLabel"},
            {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}},
        ]
        infer_processors = [
            {"class": "Fillna", "kwargs": {"fields_group": "feature", "fill_value": 0}},
        ]

        handler = DataHandlerLP(
            instruments="all",
            start_time=start,
            end_time=end,
            data_loader=data_loader,
            learn_processors=learn_processors,
            infer_processors=infer_processors,
        )

        # Get learn data (with label normalization applied)
        learn_data = handler.fetch(data_key=DataHandlerLP.DK_L, col_set=["label"])
        print("  Learn label data shape: " + str(learn_data.shape))

        if learn_data.shape[0] > 0:
            label_col = learn_data.columns[0]
            label_vals = learn_data[label_col].dropna()
            print("  Normalized label stats:")
            print("    count: " + str(len(label_vals)))
            print("    mean: " + str(round(float(label_vals.mean()), 4)))
            print("    std: " + str(round(float(label_vals.std()), 4)))

            # After CSZScoreNorm on labels, cross-sectional mean should be ~0
            date_level = learn_data.index.get_level_values("datetime")
            unique_dates = date_level.unique()
            sample_dates = unique_dates[-5:]

            print("  Cross-sectional label stats (last 5 dates):")
            cs_label_means = []
            for dt in sample_dates:
                date_slice = learn_data.loc[
                    learn_data.index.get_level_values("datetime") == dt, label_col
                ].dropna()
                if len(date_slice) > 1:
                    cs_mean = float(date_slice.mean())
                    cs_label_means.append(cs_mean)
                    dt_str = str(dt)[:10]
                    print(
                        "    "
                        + dt_str
                        + ": mean="
                        + str(round(cs_mean, 4))
                        + ", std="
                        + str(round(float(date_slice.std()), 4))
                        + ", n="
                        + str(len(date_slice))
                    )

            if cs_label_means:
                avg_label_mean = np.mean(cs_label_means)
                record(
                    check(
                        abs(avg_label_mean) < 0.1,
                        "Label cross-sectional mean near 0: "
                        + str(round(avg_label_mean, 4)),
                        "Label cross-sectional mean NOT near 0: "
                        + str(round(avg_label_mean, 4)),
                    )
                )
            else:
                record(False)
        else:
            print("  WARNING: No learn data")
            record(False)

    except Exception as e:
        print("  ERROR: " + str(e))
        traceback.print_exc()
        record(False)

    # ====================================================================
    # Summary
    # ====================================================================
    section("TEST SUMMARY")
    total = results["pass"] + results["fail"]
    print("  Total checks: " + str(total))
    print("  Passed: " + str(results["pass"]))
    print("  Failed: " + str(results["fail"]))
    if results["fail"] == 0:
        print("\n  ALL TESTS PASSED!")
    else:
        print("\n  SOME TESTS FAILED - review output above")
    print("")


if __name__ == "__main__":
    main()
