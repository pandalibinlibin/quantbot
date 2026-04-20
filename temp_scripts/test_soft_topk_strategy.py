#!/usr/bin/env python3
"""
Test script for SoftTopkStrategy configuration and functionality.
This script verifies that the Soft TopK Strategy is properly configured.
"""

import sys
import os
import yaml
from pathlib import Path


def test_system_config():
    """Test system_config.yaml for SoftTopkStrategy configuration."""
    print("🔍 Testing system_config.yaml...")

    config_path = Path("/app/app/config/qlib/system_config.yaml")
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Check if soft_topk_strategy exists
        if "soft_topk_strategy" not in config:
            print("❌ soft_topk_strategy not found in config")
            return False

        strategy_config = config["soft_topk_strategy"]

        # Check required fields
        required_fields = ["enabled", "topk", "rebalance_period_days", "weight_method"]
        for field in required_fields:
            if field not in strategy_config:
                print(f"❌ Missing required field: {field}")
                return False

        # Check values
        if not strategy_config["enabled"]:
            print("❌ Soft TopK Strategy is not enabled")
            return False

        if strategy_config["topk"] != 10:
            print(f"❌ Expected topk=10, got {strategy_config['topk']}")
            return False

        print("✅ system_config.yaml configuration is correct")
        print(f"   - topk: {strategy_config['topk']}")
        print(f"   - weight_method: {strategy_config['weight_method']}")
        print(f"   - rebalance_period_days: {strategy_config['rebalance_period_days']}")
        return True

    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False


def test_qlib_strategy_import():
    """Test if SoftTopkStrategy can be imported from Qlib."""
    print("\n🔍 Testing Qlib SoftTopkStrategy import...")

    try:
        from qlib.contrib.strategy import SoftTopkStrategy

        print("✅ SoftTopkStrategy imported successfully")

        # Check if it's a class
        if not isinstance(SoftTopkStrategy, type):
            print("❌ SoftTopkStrategy is not a class")
            return False

        print("✅ SoftTopkStrategy is ready to use")
        return True

    except ImportError as e:
        print(f"❌ Failed to import SoftTopkStrategy: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_label_config():
    """Test label configuration for T+2 return with cross-sectional ranking."""
    print("\n🔍 Testing label configuration...")

    config_path = Path("/app/app/config/qlib/system_config.yaml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if "label_config" not in config:
            print("❌ label_config not found")
            return False

        label_config = config["label_config"]

        # Check CN label
        if "cn" not in label_config:
            print("❌ CN label config not found")
            return False

        cn_expression = label_config["cn"]["expression"]
        expected_cn = "CSRankNorm(Ref($close, -2) / $close - 1)"

        if cn_expression != expected_cn:
            print(f"❌ CN label expression mismatch")
            print(f"   Expected: {expected_cn}")
            print(f"   Got: {cn_expression}")
            return False

        print("✅ Label configuration is correct")
        print(f"   - CN: {cn_expression}")
        return True

    except Exception as e:
        print(f"❌ Error checking label config: {e}")
        return False


def test_online_serving_service():
    """Test if online_serving_service.py uses SoftTopkStrategy."""
    print("\n🔍 Testing online_serving_service.py...")

    service_path = Path("/app/app/services/online_serving_service.py")
    if not service_path.exists():
        print(f"❌ Service file not found: {service_path}")
        return False

    try:
        with open(service_path, "r") as f:
            content = f.read()

        # Check if SoftTopkStrategy is imported
        if "from qlib.contrib.strategy import SoftTopkStrategy" not in content:
            print("❌ SoftTopkStrategy import not found")
            return False

        # Check if soft_topk_strategy config is used
        if "soft_topk_strategy" not in content:
            print("❌ soft_topk_strategy config not found")
            return False

        print("✅ online_serving_service.py is updated correctly")
        return True

    except Exception as e:
        print(f"❌ Error checking service file: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing SoftTopkStrategy Configuration\n")

    tests = [
        test_system_config,
        test_qlib_strategy_import,
        test_label_config,
        test_online_serving_service,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)

    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")

    if all(results):
        print("🎉 All tests passed! SoftTopkStrategy is ready to use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
