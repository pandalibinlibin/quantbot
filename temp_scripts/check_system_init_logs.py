"""
Check System Initialization logs to understand why it took 859.88 seconds.

Run in Docker:
    docker compose exec backend python /app/temp_scripts/check_system_init_logs.py
"""

import sys
import os

sys.path.append("/app")

from datetime import datetime, timedelta
from pathlib import Path

print("=" * 60)
print("SYSTEM INITIALIZATION PERFORMANCE ANALYSIS")
print("=" * 60)

# Check recent backend logs for system initialization
print("\n1. Checking recent backend logs for system initialization...")

# Look for log files
log_paths = ["/app/logs", "/var/log", "/tmp"]

for log_path in log_paths:
    log_dir = Path(log_path)
    if log_dir.exists():
        print(f"\nFound log directory: {log_dir}")
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            print(f"Log files: {[f.name for f in log_files]}")
        else:
            print("No .log files found")

# Check if we can access Docker logs programmatically
print("\n2. System Initialization Components Analysis:")

# The main components that could cause delays:
components = {
    "Qlib Initialization": "Loading Qlib data provider and configuration",
    "Model Loading": "Loading trained models from MongoDB/MLflow",
    "OnlineManager Setup": "Initializing OnlineManager with rolling models",
    "Data Validation": "Validating existing data integrity",
    "Factor Computation": "Computing or validating factors",
    "Memory Allocation": "Large dataset loading into memory",
}

for component, description in components.items():
    print(f"  • {component}: {description}")

print("\n3. Potential Performance Issues:")

issues = [
    "Large dataset loading (3+ years of data for 300 stocks)",
    "Model ensemble loading (multiple rolling-trained models)",
    "Factor computation or validation",
    "Network I/O for MongoDB/MLflow connections",
    "Memory allocation for large DataFrames",
    "Qlib data provider initialization with large calendar",
]

for i, issue in enumerate(issues, 1):
    print(f"  {i}. {issue}")

print("\n4. Recommended Optimizations:")

optimizations = [
    "Lazy loading: Only load models when needed",
    "Parallel model loading: Load multiple models concurrently",
    "Data caching: Cache frequently accessed data in memory",
    "Incremental initialization: Initialize components progressively",
    "Connection pooling: Reuse database connections",
    "Memory optimization: Use more efficient data structures",
]

for i, opt in enumerate(optimizations, 1):
    print(f"  {i}. {opt}")

print("\n5. Checking current system state...")

try:
    from app.services.online_serving_service import OnlineServingService

    service = OnlineServingService()

    # Check if OnlineManager is initialized
    if hasattr(service, "online_manager") and service.online_manager is not None:
        print("✓ OnlineManager is initialized")

        # Try to get some basic info
        try:
            signals = service.get_signals(limit=5)
            if signals.get("success"):
                print(
                    f"✓ Signals available: {signals.get('signal_count', 'unknown')} signals"
                )
            else:
                print(f"⚠ Signal retrieval issue: {signals.get('error', 'unknown')}")
        except Exception as e:
            print(f"⚠ Signal check failed: {e}")
    else:
        print("✗ OnlineManager not initialized")

except Exception as e:
    print(f"✗ Service check failed: {e}")

print("\n6. Memory and Performance Check:")

try:
    import psutil
    import os

    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    print(f"Current process memory: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"System memory usage: {psutil.virtual_memory().percent:.1f}%")
    print(f"CPU usage: {psutil.cpu_percent(interval=1):.1f}%")

except ImportError:
    print("psutil not available for memory check")
except Exception as e:
    print(f"Memory check failed: {e}")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)

print("\nNext steps:")
print("1. Check Docker logs: docker compose logs backend --tail 100")
print("2. Monitor next routine execution time")
print("3. Consider implementing lazy loading optimizations")
