#!/usr/bin/env python3
"""
Debug script to check OnlineServingService methods and initialization
"""

import sys
import os

sys.path.append("/app")

from app.services.online_serving_service import get_online_serving_service

print("=" * 60)
print("OnlineServingService Methods Debug")
print("=" * 60)

# Get online service
online_service = get_online_serving_service()

print("\n1. OnlineServingService Methods:")
methods = [method for method in dir(online_service) if not method.startswith("__")]
print(f"   Available methods ({len(methods)}):")
for method in sorted(methods):
    print(f"     {method}")

print("\n2. Checking initialization-related methods:")
init_methods = [method for method in methods if "init" in method.lower()]
print(f"   Initialization methods: {init_methods}")

print("\n3. Checking OnlineManager-related attributes:")
online_attrs = [attr for attr in dir(online_service) if "online" in attr.lower()]
print(f"   Online-related attributes: {online_attrs}")

print("\n4. Checking _online_manager attribute:")
print(f"   Has _online_manager: {hasattr(online_service, '_online_manager')}")
print(
    f"   _online_manager value: {getattr(online_service, '_online_manager', 'NOT_FOUND')}"
)

print("\n5. Checking execute_routine method source:")
try:
    import inspect

    routine_method = getattr(online_service, "execute_routine", None)
    if routine_method:
        print("   execute_routine method exists")
        # Get the source code to see how it handles OnlineManager
        try:
            source_lines = inspect.getsourcelines(routine_method)
            print(f"   Method starts at line {source_lines[1]}")
            # Look for OnlineManager initialization in the first 20 lines
            for i, line in enumerate(source_lines[0][:20]):
                if "online_manager" in line.lower() or "initialize" in line.lower():
                    print(f"   Line {i+1}: {line.strip()}")
        except Exception as e:
            print(f"   Cannot get source: {e}")
    else:
        print("   execute_routine method NOT found")
except Exception as e:
    print(f"   Error inspecting method: {e}")

print("\n6. Checking if OnlineManager is initialized during routine:")
try:
    # Look at the actual execute_routine implementation
    print("   Checking routine execution logic...")

    # Check if there's an initialization step
    if hasattr(online_service, "is_initialized"):
        print(f"   is_initialized property: {online_service.is_initialized}")

    # Check what happens when we call execute_routine
    print("   Attempting to call execute_routine with debug=True...")

    # We won't actually call it, but check what it would do
    print("   (Skipping actual execution to avoid side effects)")

except Exception as e:
    print(f"   Error checking routine: {e}")

print("\n7. Looking for the actual initialization logic:")
try:
    # Check the source file directly
    import app.services.online_serving_service as oss_module

    # Get all functions and classes in the module
    module_items = dir(oss_module)
    print(
        f"   Module items with 'init': {[item for item in module_items if 'init' in item.lower()]}"
    )
    print(
        f"   Module items with 'online': {[item for item in module_items if 'online' in item.lower()]}"
    )

except Exception as e:
    print(f"   Error checking module: {e}")

print("\n" + "=" * 60)
print("Debug complete")
print("=" * 60)
