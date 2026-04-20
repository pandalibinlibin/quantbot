#!/usr/bin/env python3
"""
Test script for TopkAmountStrategy configuration and functionality.
This script verifies that the TopK Amount Strategy is properly configured.
"""

import sys
import os
import yaml
from pathlib import Path

def test_system_config():
    """Test system_config.yaml for TopkAmountStrategy configuration."""
    print("🔍 Testing system_config.yaml...")
    
    config_path = Path("/app/config/qlib/system_config.yaml")
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check if topk_amount_strategy exists
        if 'topk_amount_strategy' not in config:
            print("❌ topk_amount_strategy not found in config")
            return False
        
        strategy_config = config['topk_amount_strategy']
        
        # Check required fields
        required_fields = ['enabled', 'topk', 'rebalance_period_days', 'weight_method']
        for field in required_fields:
            if field not in strategy_config:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Check values
        if not strategy_config['enabled']:
            print("❌ TopK Amount Strategy is not enabled")
            return False
        
        if strategy_config['topk'] != 10:
            print(f"❌ Expected topk=10, got {strategy_config['topk']}")
            return False
        
        # Check that old topk_strategy is removed or disabled
        if 'topk_strategy' in config:
            print("⚠️  Old topk_strategy still exists in config")
        
        print("✅ system_config.yaml configuration is correct")
        print(f"   - topk: {strategy_config['topk']}")
        print(f"   - weight_method: {strategy_config['weight_method']}")
        print(f"   - rebalance_period_days: {strategy_config['rebalance_period_days']}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def test_qlib_strategy_import():
    """Test if TopkAmountStrategy can be imported from Qlib."""
    print("\n🔍 Testing Qlib TopkAmountStrategy import...")
    
    try:
        from qlib.contrib.strategy import TopkAmountStrategy
        print("✅ TopkAmountStrategy imported successfully")
        
        # Check if it's a class
        if not isinstance(TopkAmountStrategy, type):
            print("❌ TopkAmountStrategy is not a class")
            return False
        
        print("✅ TopkAmountStrategy is ready to use")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import TopkAmountStrategy: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_label_config():
    """Test label configuration for T+2 return with cross-sectional ranking."""
    print("\n🔍 Testing label configuration...")
    
    config_path = Path("/app/config/qlib/system_config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'label_config' not in config:
            print("❌ label_config not found")
            return False
        
        label_config = config['label_config']
        
        # Check CN label
        if 'cn' not in label_config:
            print("❌ CN label config not found")
            return False
        
        cn_expression = label_config['cn']['expression']
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

def main():
    """Run all tests."""
    print("🚀 Testing TopkAmountStrategy Configuration\n")
    
    tests = [
        test_system_config,
        test_qlib_strategy_import,
        test_label_config,
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
        print("🎉 All tests passed! TopkAmountStrategy is ready to use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
