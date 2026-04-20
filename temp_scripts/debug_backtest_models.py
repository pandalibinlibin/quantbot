#!/usr/bin/env python3
"""
Debug script to check why backtest fails with "No trained model found".
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, "/app")


def main():
    print()
    print("=" * 60)
    print("Debugging Backtest Model Loading")
    print("=" * 60)
    print()

    # Check MODELS_DIR
    from app.core.config import settings

    MODELS_DIR = Path(settings.QLIB_DATA_PATH).parent / "models"

    print(f"1. QLIB_DATA_PATH: {settings.QLIB_DATA_PATH}")
    print(f"2. MODELS_DIR: {MODELS_DIR}")
    print(f"3. MODELS_DIR exists: {MODELS_DIR.exists()}")
    print()

    if MODELS_DIR.exists():
        pkl_files = list(MODELS_DIR.glob("*.pkl"))
        print(f"4. .pkl files in MODELS_DIR: {len(pkl_files)}")
        for f in pkl_files:
            print(f"   - {f.name} ({f.stat().st_size} bytes)")
    else:
        print("4. MODELS_DIR does not exist!")
    print()

    # Check mlruns directory
    mlruns_dir = Path("/app/mlruns")
    print(f"5. MLruns directory: {mlruns_dir}")
    print(f"6. MLruns exists: {mlruns_dir.exists()}")

    if mlruns_dir.exists():
        subdirs = [d for d in mlruns_dir.iterdir() if d.is_dir()]
        print(f"7. Subdirectories in mlruns: {len(subdirs)}")
        for d in subdirs[:10]:  # Show first 10
            print(f"   - {d.name}")
        if len(subdirs) > 10:
            print(f"   ... and {len(subdirs) - 10} more")
    print()

    # Check if Online Serving has models
    print("8. Checking Online Serving models...")
    try:
        from app.services.online_serving_service import get_online_serving_service

        service = get_online_serving_service()
        status = service.get_status()

        print(f"   - is_initialized: {status.get('is_initialized')}")
        print(f"   - last_routine_time: {status.get('last_routine_time')}")

        if service._online_manager:
            print("   - OnlineManager: exists")
        else:
            print("   - OnlineManager: None")

    except Exception as e:
        print(f"   - Error: {e}")
    print()

    # Check QlibWorkflowService.list_models()
    print("9. Checking QlibWorkflowService.list_models()...")
    try:
        from app.services.qlib_workflow_service import get_qlib_workflow_service

        workflow_service = get_qlib_workflow_service()
        models = workflow_service.list_models()

        print(f"   - Models found: {len(models)}")
        for m in models:
            print(f"   - {m['name']}: {m['path']}")

    except Exception as e:
        print(f"   - Error: {e}")
    print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    print("The backtest requires a .pkl model file in MODELS_DIR.")
    print("However, Online Serving uses MLflow-managed models in mlruns/.")
    print()
    print("Possible solutions:")
    print("1. Export the Online Serving model to MODELS_DIR")
    print("2. Modify backtest to use Online Serving's model directly")
    print("3. Train a model using the Training page first")
    print()


if __name__ == "__main__":
    main()
