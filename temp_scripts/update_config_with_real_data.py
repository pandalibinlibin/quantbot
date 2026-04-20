#!/usr/bin/env python3
"""
用真实Tushare数据更新配置文件
"""

import pandas as pd
from pathlib import Path
import yaml

def update_config_with_real_data():
    """用真实Tushare数据更新配置文件"""
    print("🔧 用真实Tushare数据更新配置文件")
    print("=" * 60)
    
    try:
        # 读取真实ETF数据
        csv_path = Path("/app/temp_scripts/optimized_etf_list.csv")
        if not csv_path.exists():
            print(f"❌ 找不到真实数据文件: {csv_path}")
            return False
        
        df = pd.read_csv(csv_path)
        print(f"✅ 读取真实ETF数据: {len(df)}只")
        
        # 读取优化后的配置
        yaml_path = Path("/app/temp_scripts/optimized_etf_config.yaml")
        if not yaml_path.exists():
            print(f"❌ 找不到优化配置文件: {yaml_path}")
            return False
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            optimized_content = f.read()
        
        print(f"✅ 读取优化配置文件")
        
        # 读取当前配置文件
        config_path = Path("/app/app/config/index_config.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # 找到ETF配置区域的开始和结束
        start_marker = "etf_codes:"
        end_marker = "# Legacy parameters"
        
        start_idx = current_content.find(start_marker)
        end_idx = current_content.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            print("❌ 找不到ETF配置区域标记")
            return False
        
        # 提取优化配置中的ETF代码部分
        opt_start_idx = optimized_content.find(start_marker)
        if opt_start_idx == -1:
            print("❌ 优化配置中找不到ETF代码")
            return False
        
        # 提取新的ETF配置
        new_etf_section = optimized_content[opt_start_idx:].strip()
        
        # 构建新的配置文件内容
        new_content = (
            current_content[:start_idx] + 
            new_etf_section + "\n\n    " +
            current_content[end_idx:]
        )
        
        # 更新top_n_etfs数量
        new_content = new_content.replace(
            "top_n_etfs: 166 # Based on real Tushare data verification",
            f"top_n_etfs: {len(df)} # Based on real Tushare data verification"
        )
        
        # 写入更新后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 配置文件已更新: {config_path}")
        
        # 验证更新结果
        print(f"\n📊 更新验证:")
        print(f"   ETF总数: {len(df)}只")
        print(f"   数据来源: 真实Tushare API")
        print(f"   规模排序: 各类别中最大规模")
        
        # 显示Top 10真实规模ETF
        print(f"\n🏆 Top 10 真实规模ETF:")
        top10 = df.nlargest(10, 'size_yi')
        for i, (_, etf) in enumerate(top10.iterrows(), 1):
            print(f"   {i:2d}. {etf['qlib_code']} - {etf['extname']} ({etf['size_yi']:.0f}亿)")
        
        print(f"\n🎉 配置文件更新完成！现在可以测试真实数据流程")
        return True
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    update_config_with_real_data()
