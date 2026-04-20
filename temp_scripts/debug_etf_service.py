#!/usr/bin/env python3
"""
Debug script to check ETF Enhanced Indexing service status
"""

import sys
import os

sys.path.append("/app")

from app.services.etf_enhanced_indexing_service import get_etf_enhanced_indexing_service
from app.services.enhanced_indexing_service import get_enhanced_indexing_service

print("=" * 60)
print("ETF Enhanced Indexing Service Debug")
print("=" * 60)

# Check ETF Enhanced Indexing Service
print("\n1. ETF Enhanced Indexing Service:")
try:
    etf_service = get_etf_enhanced_indexing_service()
    print(f"   Service created: {etf_service is not None}")
    print(f"   Enabled: {etf_service.enabled}")
    print(f"   Region: {etf_service.region}")
    print(f"   Lot size: {etf_service.lot_size}")
    print(f"   Max stocks: {etf_service.max_stocks}")
    print(f"   Alpha weight min: {etf_service.alpha_weight_min}")
    print(f"   Alpha weight max: {etf_service.alpha_weight_max}")
    print(f"   Weight mode: {etf_service.weight_mode}")
    print(f"   Output dir: {etf_service.output_dir}")
except Exception as e:
    print(f"   ERROR: {e}")

# Check Legacy Enhanced Indexing Service
print("\n2. Legacy Enhanced Indexing Service:")
try:
    legacy_service = get_enhanced_indexing_service()
    print(f"   Service created: {legacy_service is not None}")
    print(f"   Enabled: {legacy_service.enabled}")
except Exception as e:
    print(f"   ERROR: {e}")

# Check configuration files
print("\n3. Configuration Check:")
config_files = [
    "/app/backend/config/system_config.yaml",
    "/app/config/system_config.yaml",
    "/app/system_config.yaml",
]

for config_file in config_files:
    if os.path.exists(config_file):
        print(f"   Found config: {config_file}")
        try:
            with open(config_file, "r") as f:
                content = f.read()
                if "etf_enhanced_indexing" in content:
                    print(f"   Contains ETF config: Yes")
                    # Extract relevant lines
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "etf_enhanced_indexing" in line.lower():
                            print(f"   Line {i+1}: {line.strip()}")
                            # Print next few lines for context
                            for j in range(1, 5):
                                if i + j < len(lines):
                                    print(f"   Line {i+j+1}: {lines[i+j].strip()}")
                else:
                    print(f"   Contains ETF config: No")
        except Exception as e:
            print(f"   Error reading config: {e}")
    else:
        print(f"   Config not found: {config_file}")

print("\n" + "=" * 60)
print("Debug complete")
print("=" * 60)
