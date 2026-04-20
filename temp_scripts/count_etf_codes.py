#!/usr/bin/env python3
"""
统计配置文件中的ETF数量和分布
"""

import yaml
from pathlib import Path

def count_etf_codes():
    """统计ETF代码数量"""
    print("📊 统计配置文件中的ETF数量")
    print("=" * 50)
    
    try:
        config_path = Path("/app/backend/app/config/index_config.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        etf_universe = config.get('indexes', {}).get('etf_universe', {})
        etf_codes = etf_universe.get('etf_codes', [])
        top_n_etfs = etf_universe.get('top_n_etfs', 0)
        
        print(f"📋 配置信息:")
        print(f"   top_n_etfs: {top_n_etfs}")
        print(f"   实际ETF数量: {len(etf_codes)}")
        print(f"   数量差异: {top_n_etfs - len(etf_codes)}")
        
        # 按类别统计
        categories = {}
        current_category = "未分类"
        
        for code in etf_codes:
            if isinstance(code, str):
                if code.startswith('#'):
                    # 这是分类标题
                    if '===' in code:
                        current_category = code.split('===')[1].split('===')[0].strip()
                        categories[current_category] = 0
                elif code.startswith('SH') or code.startswith('SZ'):
                    # 这是ETF代码
                    if current_category not in categories:
                        categories[current_category] = 0
                    categories[current_category] += 1
        
        print(f"\n📊 各类别ETF分布:")
        total_counted = 0
        for category, count in categories.items():
            print(f"   {category}: {count}只")
            total_counted += count
        
        print(f"\n✅ 统计完成:")
        print(f"   配置中的top_n_etfs: {top_n_etfs}")
        print(f"   实际ETF代码数量: {total_counted}")
        print(f"   需要调整: {top_n_etfs - total_counted}")
        
        return total_counted, top_n_etfs
        
    except Exception as e:
        print(f"❌ 统计失败: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

if __name__ == "__main__":
    count_etf_codes()
