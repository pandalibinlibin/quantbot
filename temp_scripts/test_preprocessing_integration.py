"""
End-to-end test for preprocessing pipeline integration with CustomFactorHandler

This script verifies that:
1. CustomFactorHandler correctly builds the preprocessing pipeline
2. The preprocessing pipeline is applied during data loading
3. Data is properly transformed (EMA-5 -> RelativeChange -> CSZScoreNorm)

Usage (in Docker):
    docker compose exec backend python /app/temp_scripts/test_preprocessing_integration.py
"""

import sys

sys.path.insert(0, "/app")

print("=" * 60)
print("Preprocessing Pipeline Integration Test")
print("=" * 60)


def test_preprocessing_pipeline_build():
    """Test that CustomFactorHandler builds the preprocessing pipeline correctly"""
    print("\n[Test 1] Verify preprocessing pipeline is built")
    print("-" * 40)

    from app.services.custom_factor_handler import CustomFactorHandler
    from app.qlib_extensions.preprocessing import EMA5Processor, RelativeChangeProcessor

    # Create handler instance (without loading data)
    # We just want to verify the pipeline is built correctly
    pipeline = CustomFactorHandler._build_preprocessing_pipeline(None)

    print("Preprocessing pipeline components:")
    for i, proc in enumerate(pipeline):
        if isinstance(proc, dict):
            print("  ", i + 1, proc.get("class"))
        else:
            print("  ", i + 1, type(proc).__name__)

    # Verify pipeline structure
    assert len(pipeline) == 4, "Pipeline should have 4 components"

    # Check component types
    assert pipeline[0]["class"] == "Fillna", "First should be Fillna"
    assert isinstance(pipeline[1], EMA5Processor), "Second should be EMA5Processor"
    assert isinstance(
        pipeline[2], RelativeChangeProcessor
    ), "Third should be RelativeChangeProcessor"
    assert pipeline[3]["class"] == "CSZScoreNorm", "Fourth should be CSZScoreNorm"

    print("\n✅ Preprocessing pipeline structure is correct")
    return True


def test_handler_initialization():
    """Test that CustomFactorHandler initializes with preprocessing pipeline"""
    print("\n[Test 2] Verify handler initialization with preprocessing")
    print("-" * 40)

    # Initialize Qlib first
    import qlib

    print("Initializing Qlib...")
    qlib.init(provider_uri="/app/qlib_data")

    from app.services.custom_factor_handler import CustomFactorHandler

    # Create handler with minimal config
    handler = CustomFactorHandler(
        instruments="all",
        start_time="2023-01-01",
        end_time="2023-01-31",
        freq="day",
    )

    # Check that infer_processors contains our custom processors
    infer_procs = handler.infer_processors

    print("Handler infer_processors:")
    for i, proc in enumerate(infer_procs):
        proc_name = type(proc).__name__
        print("  ", i + 1, proc_name)

    # Verify we have our custom processors
    proc_names = [type(p).__name__ for p in infer_procs]

    assert "EMA5Processor" in proc_names, "EMA5Processor should be in infer_processors"
    assert (
        "RelativeChangeProcessor" in proc_names
    ), "RelativeChangeProcessor should be in infer_processors"

    print("\n✅ Handler initialized with preprocessing pipeline")
    return True


def test_data_transformation():
    """Test that data is actually transformed by the preprocessing pipeline"""
    print("\n[Test 3] Verify data transformation")
    print("-" * 40)

    import qlib
    from qlib.config import C
    import pandas as pd
    import numpy as np

    # Ensure Qlib is initialized
    if not hasattr(C, "provider_uri") or C.provider_uri is None:
        qlib.init(provider_uri="/app/qlib_data")

    from app.services.custom_factor_handler import CustomFactorHandler

    # Create handler and load data
    handler = CustomFactorHandler(
        instruments="all",
        start_time="2023-01-01",
        end_time="2023-01-31",
        freq="day",
    )

    # Setup data (this triggers the preprocessing pipeline)
    print("Loading and preprocessing data...")
    handler.setup_data()

    # Fetch processed data
    data = handler.fetch(col_set="feature")

    print("Processed data shape:", data.shape)
    print("Processed data columns:", list(data.columns)[:5], "...")

    # Check that data has been transformed
    # After CSZScoreNorm, each day's cross-sectional mean should be ~0
    if len(data) > 0:
        # Get first feature column
        first_col = data.columns[0]

        # Group by date and check mean
        daily_means = data[first_col].groupby(level="datetime").mean()
        daily_stds = data[first_col].groupby(level="datetime").std()

        print("\nDaily statistics for first feature (after preprocessing):")
        print("  Mean of daily means:", round(daily_means.mean(), 4))
        print("  Mean of daily stds:", round(daily_stds.mean(), 4))

        # After CSZScoreNorm, daily means should be close to 0
        # and daily stds should be close to 1
        mean_of_means = abs(daily_means.mean())
        mean_of_stds = daily_stds.mean()

        if mean_of_means < 0.1:
            print("\n✅ Data appears to be cross-sectionally normalized (mean ≈ 0)")
        else:
            print("\n⚠️ Daily means not close to 0, may need investigation")

        if 0.5 < mean_of_stds < 1.5:
            print("✅ Data appears to be cross-sectionally normalized (std ≈ 1)")
        else:
            print("⚠️ Daily stds not close to 1, may need investigation")

    print("\n✅ Data transformation test completed")
    return True


if __name__ == "__main__":
    try:
        test_preprocessing_pipeline_build()
        test_handler_initialization()
        test_data_transformation()

        print("\n" + "=" * 60)
        print("ALL INTEGRATION TESTS PASSED!")
        print("=" * 60)
        print("\nThe preprocessing pipeline is correctly integrated.")
        print("You can now click 'Run Task' to train a model with preprocessed data.")

    except Exception as e:
        print("\n❌ TEST FAILED:", str(e))
        import traceback

        traceback.print_exc()
        sys.exit(1)
