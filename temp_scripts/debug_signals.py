#!/usr/bin/env python3
"""
Debug script to check why signal_count is 0 on Dashboard.

This script creates a FRESH instance (not the running singleton),
so it tests the underlying data/model availability, not in-memory state.
"""

import sys

sys.path.append("/app")

print("=" * 60)
print("Signal Count Debug")
print("=" * 60)

# 1. Check if Qlib data exists
from pathlib import Path

print("\n1. Qlib Data Check:")
qlib_data = Path("/app/qlib_data")
cal_file = qlib_data / "calendars" / "day.txt"
features_dir = qlib_data / "features"
print(f"   qlib_data exists: {qlib_data.exists()}")
print(f"   calendar exists: {cal_file.exists()}")
print(f"   features dir exists: {features_dir.exists()}")
if features_dir.exists():
    dirs = [d for d in features_dir.iterdir() if d.is_dir()]
    print(f"   instrument dirs: {len(dirs)}")

# 2. Check MLflow/experiment recorders
print("\n2. MLflow Experiments:")
try:
    mlruns_path = Path("/app/mlruns")
    if mlruns_path.exists():
        for exp_dir in sorted(mlruns_path.iterdir()):
            if exp_dir.is_dir() and exp_dir.name != ".trash":
                runs = [
                    r for r in exp_dir.iterdir() if r.is_dir() and r.name != "meta.yaml"
                ]
                print(f"   Experiment {exp_dir.name}: {len(runs)} runs")
    else:
        print("   mlruns dir not found!")
except Exception as e:
    print(f"   ERROR: {e}")

# 3. Check if we can initialize Qlib and get signals
print("\n3. Qlib Init + Signal Test:")
try:
    import qlib
    from qlib.config import C

    qlib.init(provider_uri=str(qlib_data), region="cn")
    print(f"   Qlib initialized OK")

    from qlib.data import D

    cal = D.calendar(freq="day")
    print(f"   Calendar: {cal[0]} to {cal[-1]}, {len(cal)} days")
except Exception as e:
    print(f"   ERROR: {e}")

# 4. Check MongoDB for tasks
print("\n4. MongoDB Task Check:")
try:
    from pymongo import MongoClient

    client = MongoClient("mongodb://mongo:27017/")
    db = client["quantbot"]
    collections = db.list_collection_names()
    print(f"   Collections: {collections}")
    for col_name in collections:
        col = db[col_name]
        count = col.count_documents({})
        print(f"   {col_name}: {count} documents")
except Exception as e:
    print(f"   ERROR: {e}")

# 5. Try to get signals via OnlineServingService (fresh instance)
print("\n5. OnlineServingService Status (fresh instance):")
try:
    from app.services.online_serving_service import OnlineServingService

    svc = OnlineServingService()
    print(f"   is_initialized: {svc.is_initialized}")
    print(f"   _online_manager is None: {svc._online_manager is None}")
    status = svc.get_status()
    print(f"   status.is_initialized: {status.get('is_initialized')}")
    print(f"   status.signal_count: {status.get('signal_count', 'NOT_SET')}")
    print(f"   status.last_routine_time: {status.get('last_routine_time')}")
except Exception as e:
    print(f"   ERROR: {e}")

# 6. Check what happens when we call the dashboard API endpoint internally
print("\n6. Dashboard API signal_count source:")
try:
    # The dashboard uses get_online_serving_service() which is a singleton
    # In a fresh script, this creates a new instance
    from app.services.online_serving_service import get_online_serving_service

    online_svc = get_online_serving_service()
    status = online_svc.get_status()
    print(f"   is_initialized: {status.get('is_initialized')}")
    print(f"   signal_count: {status.get('signal_count', 'NOT_SET')}")

    # KEY INSIGHT: In a fresh script, the singleton is NEW (not the running server's).
    # The running server's singleton may have signals loaded in memory.
    # This script proves whether signals PERSIST or are only in-memory.
    print("\n   NOTE: This is a fresh process, NOT the running server.")
    print("   If signal_count=0 here but the server had signals,")
    print("   it means signals are only in-memory (not persisted).")
    print("   The dashboard gets signals from the SAME process as update_data.")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 60)
print("Debug complete")
print("=" * 60)
