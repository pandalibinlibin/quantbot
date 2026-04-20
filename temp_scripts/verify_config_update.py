#!/usr/bin/env python3
"""
Verify that backtest_config.yaml has been updated correctly
"""

import requests

def test_config_update():
    """Test that backtest config now shows TopkDropoutStrategy"""
    print("🔍 Verifying Configuration Update")
    print("=" * 35)
    
    try:
        response = requests.get("http://localhost:8000/api/v1/backtest/config")
        if response.status_code == 200:
            config_data = response.json()
            strategy_class = config_data.get('config', {}).get('strategy', {}).get('class')
            
            if strategy_class == 'TopkDropoutStrategy':
                print("✅ Configuration updated successfully!")
                print(f"   - Strategy class: {strategy_class}")
                
                # Check module path
                module_path = config_data.get('config', {}).get('strategy', {}).get('module_path')
                print(f"   - Module path: {module_path}")
                
                return True
            else:
                print(f"❌ Strategy class still shows: {strategy_class}")
                print("   Expected: TopkDropoutStrategy")
                return False
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing config: {e}")
        return False

if __name__ == "__main__":
    if test_config_update():
        print("\n🎉 Ready for end-to-end testing!")
        print("\n🚀 Next Steps:")
        print("1. Open frontend Dashboard")
        print("2. Click 'Clear Data' to reset")
        print("3. Click 'Run Task' to execute TopkDropoutStrategy")
        print("4. Check Backtest page for results")
    else:
        print("\n❌ Configuration issue detected. Please check the setup.")
