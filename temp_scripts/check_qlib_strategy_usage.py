#!/usr/bin/env python3
"""
Check how to properly use Qlib strategies in backtest
"""

def check_qlib_backtest_usage():
    """Check proper way to use strategies in Qlib backtest"""
    
    print("🔍 Checking Qlib backtest usage patterns")
    print("=" * 50)
    
    try:
        from qlib.contrib.evaluate import backtest_daily
        from qlib.contrib.strategy import TopkDropoutStrategy, SoftTopkStrategy
        import inspect
        
        print("\n📋 backtest_daily signature:")
        sig = inspect.signature(backtest_daily)
        print(f"backtest_daily{sig}")
        
        print("\n📄 backtest_daily docstring:")
        print(backtest_daily.__doc__ or "No documentation")
        
        # Check if we can use strategy directly or need to pass it differently
        print("\n🔍 Checking strategy parameter types...")
        
        # Let's see what TopkDropoutStrategy needs (our previous working version)
        print("\n📋 TopkDropoutStrategy signature:")
        sig_topk = inspect.signature(TopkDropoutStrategy.__init__)
        print(f"TopkDropoutStrategy.__init__{sig_topk}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def check_alternative_approaches():
    """Check alternative ways to implement soft topk behavior"""
    
    print("\n🔍 Alternative Approaches")
    print("=" * 30)
    
    try:
        # Check if we can use TopkDropoutStrategy with n_drop=topk for similar effect
        from qlib.contrib.strategy import TopkDropoutStrategy
        
        print("💡 Idea: Use TopkDropoutStrategy with n_drop=topk")
        print("   This would effectively reselect all positions each time")
        print("   Similar to 'amount' strategy behavior")
        
        # Check other available strategies
        import qlib.contrib.strategy as strategies
        all_strategies = [x for x in dir(strategies) if 'Strategy' in x and not x.startswith('_')]
        
        print(f"\n📋 All available strategies:")
        for strategy in all_strategies:
            print(f"  - {strategy}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_qlib_backtest_usage()
    check_alternative_approaches()
