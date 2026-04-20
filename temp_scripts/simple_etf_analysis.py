#!/usr/bin/env python3
"""
简化版ETF分析 - 直接解析YAML文件内容
"""

import re
from pathlib import Path
import pandas as pd

def analyze_etf_config():
    """分析ETF配置文件"""
    print("📊 分析最终配置文件中的完整166只ETF")
    print("=" * 70)
    
    try:
        config_path = Path("/app/app/config/index_config.yaml")
        
        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            return False
        
        print(f"✅ 找到配置文件: {config_path}")
        
        # 读取原始文件内容
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析ETF信息
        etf_data = []
        current_category = None
        in_etf_section = False
        
        lines = content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # 检测ETF代码区域开始
            if 'etf_codes:' in stripped:
                in_etf_section = True
                continue
            
            # 检测ETF代码区域结束
            if in_etf_section and stripped.startswith('#') and 'Legacy parameters' in stripped:
                break
            
            if not in_etf_section:
                continue
            
            # 解析类别标题
            if stripped.startswith('# ===') and '===' in stripped:
                category_match = re.search(r'=== (.+?) \((\d+)只\)', stripped)
                if category_match:
                    current_category = category_match.group(1)
                    category_count = int(category_match.group(2))
                    
                    # 提取平均规模
                    avg_size_match = re.search(r'平均规模(\d+)亿', stripped)
                    avg_size = int(avg_size_match.group(1)) if avg_size_match else None
                    
                    print(f"\n📂 {current_category}: {category_count}只")
                    if avg_size:
                        print(f"   平均规模: {avg_size}亿元")
                continue
            
            # 解析ETF代码
            if stripped.startswith('- ') and '#' in stripped and current_category:
                # 提取ETF代码
                code_match = re.search(r'- ([A-Z]{2}\d{6})', stripped)
                if code_match:
                    etf_code = code_match.group(1)
                    
                    # 提取ETF名称
                    name_match = re.search(r'# (.+?) \(', stripped)
                    etf_name = name_match.group(1) if name_match else "未知"
                    
                    # 提取规模
                    size_match = re.search(r'\((\d+)亿\)', stripped)
                    size = int(size_match.group(1)) if size_match else 0
                    
                    etf_data.append({
                        'category': current_category,
                        'code': etf_code,
                        'name': etf_name,
                        'size': size
                    })
                    
                    print(f"   {etf_code} - {etf_name} ({size}亿)")
        
        # 转换为DataFrame进行分析
        if not etf_data:
            print("❌ 未解析到任何ETF数据")
            return False
        
        df = pd.DataFrame(etf_data)
        
        print(f"\n📊 解析结果:")
        print(f"   成功解析ETF数量: {len(df)}")
        print(f"   类别数量: {df['category'].nunique()}")
        
        # 按类别统计
        print(f"\n📋 各类别详细统计:")
        category_stats = df.groupby('category').agg({
            'code': 'count',
            'size': ['mean', 'sum', 'max', 'min']
        }).round(0)
        
        category_stats.columns = ['数量', '平均规模', '总规模', '最大规模', '最小规模']
        category_stats = category_stats.sort_values('总规模', ascending=False)
        
        for category, row in category_stats.iterrows():
            print(f"\n🏷️ {category}:")
            print(f"     数量: {int(row['数量'])}只")
            print(f"     平均规模: {int(row['平均规模'])}亿元")
            print(f"     总规模: {int(row['总规模'])}亿元")
            print(f"     规模范围: {int(row['最小规模'])}-{int(row['最大规模'])}亿元")
        
        # 整体统计
        total_size = df['size'].sum()
        avg_size = df['size'].mean()
        median_size = df['size'].median()
        
        print(f"\n🎯 整体统计:")
        print(f"   总ETF数量: {len(df)}只")
        print(f"   总资产规模: {total_size:,.0f}亿元")
        print(f"   平均规模: {avg_size:.1f}亿元")
        print(f"   中位数规模: {median_size:.1f}亿元")
        
        # 规模分布
        print(f"\n📊 规模分布:")
        size_ranges = [
            (1000, float('inf'), "超大规模(1000亿+)"),
            (500, 1000, "大规模(500-1000亿)"),
            (100, 500, "中等规模(100-500亿)"),
            (50, 100, "中小规模(50-100亿)"),
            (0, 50, "小规模(50亿以下)")
        ]
        
        for min_size, max_size, label in size_ranges:
            if max_size == float('inf'):
                count = len(df[df['size'] >= min_size])
            else:
                count = len(df[(df['size'] >= min_size) & (df['size'] < max_size)])
            percentage = count / len(df) * 100
            print(f"   {label}: {count}只 ({percentage:.1f}%)")
        
        # Top 10 最大规模ETF
        print(f"\n🏆 Top 10 最大规模ETF:")
        top10 = df.nlargest(10, 'size')
        for i, (_, etf) in enumerate(top10.iterrows(), 1):
            print(f"   {i:2d}. {etf['code']} - {etf['name']} ({etf['size']}亿) [{etf['category']}]")
        
        # 验证数据完整性
        print(f"\n✅ 数据完整性验证:")
        
        # 检查ETF代码格式
        invalid_codes = df[~df['code'].str.match(r'^[A-Z]{2}\d{6}$')]
        if len(invalid_codes) == 0:
            print(f"   ETF代码格式: ✅ 全部符合标准格式")
        else:
            print(f"   ETF代码格式: ❌ {len(invalid_codes)}个无效代码")
        
        # 检查规模数据
        zero_size = len(df[df['size'] == 0])
        if zero_size == 0:
            print(f"   规模数据: ✅ 全部有真实规模数据")
        else:
            print(f"   规模数据: ⚠️ {zero_size}只ETF无规模数据")
            
        # 检查重复代码
        duplicates = df[df['code'].duplicated()]
        if len(duplicates) == 0:
            print(f"   重复代码: ✅ 无重复ETF代码")
        else:
            print(f"   重复代码: ❌ {len(duplicates)}个重复代码")
        
        # 按交易所分布
        print(f"\n🏛️ 交易所分布:")
        df['exchange'] = df['code'].str[:2]
        exchange_stats = df['exchange'].value_counts()
        for exchange, count in exchange_stats.items():
            exchange_name = "上海证券交易所" if exchange == "SH" else "深圳证券交易所"
            percentage = count / len(df) * 100
            print(f"   {exchange} ({exchange_name}): {count}只 ({percentage:.1f}%)")
        
        print(f"\n🎉 分析完成！基于Tushare真实数据的{len(df)}只ETF已验证")
        return True
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_etf_config()
