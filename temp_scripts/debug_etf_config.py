#!/usr/bin/env python3
"""
调试ETF配置读取

检查配置文件是否正确读取平衡选择参数
"""

def debug_etf_config():
    """调试ETF配置"""
    print("🔍 调试ETF配置读取")
    print("=" * 50)
    
    try:
        from app.services.index_components_service import get_index_components_service
        
        service = get_index_components_service()
        
        # 获取配置
        config = service.get_index_config('etf_universe')
        
        print("📋 ETF Universe 配置内容:")
        for key, value in config.items():
            print(f"   {key}: {value}")
        
        # 检查关键参数
        selection_strategy = config.get("selection_strategy", "simple")
        min_requirements = config.get("min_requirements", {})
        top_n = config.get("top_n_etfs", 100)
        
        print(f"\n🎯 关键参数:")
        print(f"   selection_strategy: {selection_strategy}")
        print(f"   top_n_etfs: {top_n}")
        print(f"   min_requirements: {min_requirements}")
        
        # 判断条件
        balanced_enabled = selection_strategy == "balanced" and min_requirements
        print(f"\n✅ 平衡选择启用条件:")
        print(f"   selection_strategy == 'balanced': {selection_strategy == 'balanced'}")
        print(f"   min_requirements 非空: {bool(min_requirements)}")
        print(f"   平衡选择启用: {balanced_enabled}")
        
        if balanced_enabled:
            print(f"\n📊 最小要求详情:")
            for category, count in min_requirements.items():
                print(f"   {category}: {count}只")
        else:
            print(f"\n⚠️ 平衡选择未启用，将使用简单规模排序")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_etf_config()
