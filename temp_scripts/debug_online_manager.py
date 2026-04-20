#!/usr/bin/env python3
"""
Debug script to check OnlineManager initialization
"""

import sys
import os

sys.path.append("/app")

from app.services.online_serving_service import get_online_serving_service

print("=" * 60)
print("OnlineManager Initialization Debug")
print("=" * 60)

# Get online service
online_service = get_online_serving_service()

print("\n1. OnlineServingService Status:")
print(f"   Service exists: {online_service is not None}")
print(f"   OnlineManager: {online_service._online_manager}")

# Check initialization method
print("\n2. Checking initialization:")
try:
    print(f"   Is initialized: {online_service.is_initialized}")

    if not online_service.is_initialized:
        print("   OnlineManager not initialized, attempting initialization...")

        # Try to initialize
        try:
            online_service._initialize_online_manager()
            print(
                f"   After initialization - OnlineManager: {online_service._online_manager}"
            )
            print(f"   Is initialized now: {online_service.is_initialized}")
        except Exception as init_e:
            print(f"   Initialization failed: {init_e}")
            import traceback

            traceback.print_exc()

except Exception as e:
    print(f"   ERROR checking initialization: {e}")
    import traceback

    traceback.print_exc()

# Check what happens during routine execution
print("\n3. Checking routine execution path:")
try:
    # Check if the routine would try to initialize
    print("   Simulating routine execution...")

    # This is what happens in execute_routine
    if not online_service.is_initialized:
        print("   Routine would call _initialize_online_manager()")
        try:
            online_service._initialize_online_manager()
            print(
                f"   OnlineManager after routine init: {online_service._online_manager}"
            )
        except Exception as e:
            print(f"   Routine initialization failed: {e}")
    else:
        print("   OnlineManager already initialized")

    # Try to get signals if manager exists
    if online_service._online_manager is not None:
        print("   Attempting to get signals...")
        signals = online_service._online_manager.get_signals()
        print(
            f"   Signals: {type(signals)}, empty: {signals is None or (hasattr(signals, 'empty') and signals.empty)}"
        )
    else:
        print("   Cannot get signals - OnlineManager is None")

except Exception as e:
    print(f"   ERROR in routine simulation: {e}")
    import traceback

    traceback.print_exc()

# Check configuration
print("\n4. Configuration Check:")
try:
    from app.config.qlib import qlib_config

    print(f"   Qlib config loaded: {qlib_config is not None}")
    if qlib_config:
        print(f"   Region: {qlib_config.region}")
        print(f"   Provider URI: {qlib_config.provider_uri}")

        # Check online serving config
        online_config = qlib_config._config.get("online_serving", {})
        print(f"   Online serving config exists: {bool(online_config)}")
        if online_config:
            print(f"   Online serving enabled: {online_config.get('enabled', False)}")

except Exception as e:
    print(f"   ERROR checking config: {e}")

print("\n" + "=" * 60)
print("Debug complete")
print("=" * 60)
