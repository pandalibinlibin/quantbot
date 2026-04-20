#!/usr/bin/env python3
"""
测试平衡ETF选择功能

强制清除缓存，测试平衡选择是否生效
"""

def test_balanced_etf_selection():
    """测试平衡ETF选择"""
    print("🎯 测试平衡ETF选择功能")
    print("=" * 60)
    
    try:
        from app.services.index_components_service import get_index_components_service
        
        service = get_index_components_service()
        
        # 强制清除缓存
        print("🧹 清除缓存...")
        service.cache.clear()
        
        # 获取配置确认
        config = service.get_index_config('etf_universe')
        selection_strategy = config.get("selection_strategy", "simple")
        min_requirements = config.get("min_requirements", {})
        
        print(f"📋 配置确认:")
        print(f"   selection_strategy: {selection_strategy}")
        print(f"   min_requirements: {min_requirements}")
        
        # 强制不使用缓存获取ETF
        print(f"\n🚀 获取ETF股票池 (不使用缓存)...")
        import time
        start_time = time.time()
        
        etf_list = service.get_components('etf_universe', use_cache=False)
        
        elapsed = time.time() - start_time
        print(f"✅ 获取完成: {len(etf_list)}只ETF (耗时: {elapsed:.1f}秒)")
        
        # 显示前20只ETF
        print(f"\n📊 前20只ETF:")
        for i, etf_code in enumerate(etf_list[:20], 1):
            print(f"   {i:2d}. {etf_code}")
        
        # 简单分析ETF类型分布
        print(f"\n🔍 ETF类型分析 (基于代码):")
        
        # 统计各交易所数量
        sh_count = sum(1 for code in etf_list if code.startswith('SH'))
        sz_count = sum(1 for code in etf_list if code.startswith('SZ'))
        
        print(f"   上交所 (SH): {sh_count}只")
        print(f"   深交所 (SZ): {sz_count}只")
        
        # 检查是否包含特定类型的ETF
        # 通过代码特征简单判断
        bond_like = [code for code in etf_list if '511' in code]  # 债券ETF通常以511开头
        commodity_like = [code for code in etf_list if '518' in code]  # 商品ETF通常以518开头
        
        print(f"   疑似债券ETF (511xxx): {len(bond_like)}只")
        print(f"   疑似商品ETF (518xxx): {len(commodity_like)}只")
        
        if bond_like:
            print(f"     债券ETF示例: {bond_like[:5]}")
        if commodity_like:
            print(f"     商品ETF示例: {commodity_like[:5]}")
        
        # 判断是否使用了平衡选择
        print(f"\n🎯 平衡选择效果分析:")
        
        # 如果是简单规模排序，前20只应该都是超大规模ETF
        # 如果是平衡选择，应该包含各种类型的ETF
        
        if len(bond_like) >= 10 and len(commodity_like) >= 3:
            print("   ✅ 可能使用了平衡选择 - 包含足够的债券和商品ETF")
        else:
            print("   ⚠️ 可能仍在使用简单规模排序 - 债券/商品ETF较少")
            print(f"      债券ETF: {len(bond_like)}只 (期望: ≥17只)")
            print(f"      商品ETF: {len(commodity_like)}只 (期望: ≥7只)")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_balanced_etf_selection()
