"""
Test script for FactorStorage compute and delete functionality
"""

import qlib

qlib.init(provider_uri="/app/qlib_data")

from app.services.factor_storage import FactorStorage

# Initialize storage
s = FactorStorage("day")
print("Storage dir:", s.storage_dir)
print("Features dir:", s.features_dir)

# Test 1: Compute factor from expression
print("\n=== Test 1: Compute factor from expression ===")
# Use $close syntax for Qlib
result = s.compute_and_save_factor("test_ma5", "Mean($close, 5)", overwrite=True)
print("Result:", result)

# Test 2: Delete the factor
print("\n=== Test 2: Delete factor bin files ===")
delete_result = s.delete_factor_bin_files("test_ma5")
print("Delete result:", delete_result)

print("\n=== All tests completed ===")
