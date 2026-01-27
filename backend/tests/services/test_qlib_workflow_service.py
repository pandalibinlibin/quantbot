"""
Test script for Qlib workflow service.
This script tests the execute_training_workflow method with a minimal configuration.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.qlib_workflow_service import qlib_workflow_service


def test_execute_training_workflow():
    """Test the training workflow with a minimal configuration."""

    # Minimal training configuration
    config = {
        "task": {
            "dataset": {
                "class": "DatasetH",
                "module_path": "qlib.data.dataset",
                "kwargs": {
                    "handler": {
                        "class": "Alpha158",
                        "module_path": "qlib.contrib.data.handler",
                        "kwargs": {
                            "start_time": "2020-01-01",
                            "end_time": "2020-12-31",
                            "fit_start_time": "2020-01-01",
                            "fit_end_time": "2020-06-30",
                            "instruments": "csi300",
                        },
                    },
                    "segments": {
                        "train": ("2020-01-01", "2020-06-30"),
                        "valid": ("2020-07-01", "2020-09-30"),
                        "test": ("2020-10-01", "2020-12-31"),
                    },
                },
            },
            "model": {
                "class": "LGBModel",
                "module_path": "qlib.contrib.model.gbdt",
                "kwargs": {
                    "loss": "mse",
                    "num_leaves": 31,
                    "learning_rate": 0.05,
                    "num_boost_round": 100,
                    "verbose": -1,
                },
            },
        }
    }

    print("=" * 60)
    print("Testing execute_training_workflow...")
    print("=" * 60)

    try:
        # Execute training workflow
        result = qlib_workflow_service.execute_training_workflow(
            config=config, experiment_name="test_workflow"
        )

        print("\n" + "=" * 60)
        print("✅ Test PASSED!")
        print("=" * 60)
        print(f"\nResult:")
        print(f" Status: {result.get('status')}")
        print(f" Predictions count: {result.get('predictions_count')}")
        print(f" Model saved: {result.get('model_saved')}")
        print(f"\nTimings:")
        for step, duration in result.get("timings", {}).items():
            print(f" {step}: {duration:.2f}s")

        return True
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ Test FAILED!")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_execute_training_workflow()
    sys.exit(0 if success else 1)
