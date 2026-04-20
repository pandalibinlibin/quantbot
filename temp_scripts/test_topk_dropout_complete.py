#!/usr/bin/env python3
"""
Complete test for TopkDropoutStrategy with intelligent rebalancing
Tests configuration, strategy creation, and basic functionality
"""

import sys
import os
import yaml
from pathlib import Path

def test_configuration():
    """Test system configuration for TopkDropoutStrategy"""
    print("🔍 Testing Configuration")
    print("=" * 30)
    
    config_path = Path("/app/app/config/qlib/system_config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check topk_dropout_strategy exists
        if 'topk_dropout_strategy' not in config:
            print("❌ topk_dropout_strategy not found in config")
            return False
        
        strategy_config = config['topk_dropout_strategy']
        
        # Check required fields
        required_fields = ['enabled', 'topk', 'n_drop', 'rebalance_period_days', 'weight_method']
        for field in required_fields:
            if field not in strategy_config:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Check values
        if not strategy_config['enabled']:
            print("❌ TopK Dropout Strategy is not enabled")
            return False
        
        topk = strategy_config['topk']
        n_drop = strategy_config['n_drop']
        
        if topk != 10:
            print(f"❌ Expected topk=10, got {topk}")
            return False
            
        if n_drop != 10:
            print(f"❌ Expected n_drop=10, got {n_drop}")
            return False
        
        print("✅ Configuration is correct")
        print(f"   - topk: {topk}")
        print(f"   - n_drop: {n_drop}")
        print(f"   - weight_method: {strategy_config['weight_method']}")
        print(f"   - rebalance_period_days: {strategy_config['rebalance_period_days']}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def test_strategy_import():
    """Test TopkDropoutStrategy import and creation"""
    print("\n🔍 Testing Strategy Import")
    print("=" * 30)
    
    try:
        from qlib.contrib.strategy import TopkDropoutStrategy
        print("✅ TopkDropoutStrategy imported successfully")
        
        # Check constructor signature
        import inspect
        sig = inspect.signature(TopkDropoutStrategy.__init__)
        print(f"✅ Constructor signature: {sig}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import TopkDropoutStrategy: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_online_serving_service():
    """Test online_serving_service.py integration"""
    print("\n🔍 Testing Online Serving Service Integration")
    print("=" * 45)
    
    service_path = Path("/app/app/services/online_serving_service.py")
    try:
        with open(service_path, 'r') as f:
            content = f.read()
        
        # Check imports
        if 'from qlib.contrib.strategy import TopkDropoutStrategy' not in content:
            print("❌ TopkDropoutStrategy import not found")
            return False
        
        # Check config usage
        if 'topk_dropout_strategy' not in content:
            print("❌ topk_dropout_strategy config not found")
            return False
        
        # Check strategy creation
        if 'TopkDropoutStrategy(topk=topk, n_drop=n_drop, signal=signals)' not in content:
            print("❌ Correct strategy creation not found")
            return False
        
        # Check strategy name
        if 'topk_dropout_intelligent' not in content:
            print("❌ Strategy name not updated")
            return False
        
        print("✅ Online serving service is correctly updated")
        return True
        
    except Exception as e:
        print(f"❌ Error checking service file: {e}")
        return False

def test_label_configuration():
    """Test label configuration"""
    print("\n🔍 Testing Label Configuration")
    print("=" * 30)
    
    config_path = Path("/app/app/config/qlib/system_config.yaml")
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

def test_backtest_api():
    """Test backtest API endpoint"""
    print("\n🔍 Testing Backtest API")
    print("=" * 25)
    
    try:
        import requests
        
        # Test backtest status endpoint
        response = requests.get("http://localhost:8000/api/v1/backtest/status")
        if response.status_code == 200:
            status_data = response.json()
            print("✅ Backtest status API accessible")
            print(f"   - Ready: {status_data.get('ready', 'Unknown')}")
            print(f"   - Message: {status_data.get('message', 'No message')}")
        else:
            print(f"⚠️  Backtest status API returned {response.status_code}")
        
        # Test backtest config endpoint
        response = requests.get("http://localhost:8000/api/v1/backtest/config")
        if response.status_code == 200:
            config_data = response.json()
            print("✅ Backtest config API accessible")
            strategy_class = config_data.get('config', {}).get('strategy', {}).get('class')
            print(f"   - Strategy class: {strategy_class}")
        else:
            print(f"⚠️  Backtest config API returned {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 TopkDropoutStrategy Complete Test Suite")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_strategy_import,
        test_online_serving_service,
        test_label_configuration,
        test_backtest_api,
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
        print("🎉 All tests passed! TopkDropoutStrategy is ready for end-to-end testing.")
        print("\n🚀 Next Steps:")
        print("1. Open frontend Dashboard")
        print("2. Click 'Clear Data' to reset")
        print("3. Click 'Run Task' to execute strategy")
        print("4. Check Backtest page for results")
        return 0
    else:
        print("❌ Some tests failed. Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
