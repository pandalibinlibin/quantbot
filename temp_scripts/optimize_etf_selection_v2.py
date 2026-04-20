#!/usr/bin/env python3
"""
优化ETF选择 v2.0

基于真实Tushare数据重新筛选ETF，特别优化：
1. 增加货币ETF到10只
2. 增加REIT ETF到8只
3. 确保所有ETF代码真实存在
4. 按真实规模排序选择
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import yaml


def get_real_etf_data():
    """获取真实的ETF数据"""
    print("📊 获取真实ETF数据...")
    
    try:
        import tushare as ts
        
        # 读取token
        token_file = Path.home() / ".tushare_token"
        with open(token_file, 'r') as f:
            token = f.read().strip()
        
        pro = ts.pro_api(token)
        
        # 获取ETF基本信息
        etf_basic = pro.etf_basic(
            list_status='L',
            fields='ts_code,name,extname,fund_type,index_code,index_name,exchange,mgr_name,list_date'
        )
        
        # 获取ETF规模信息
        etf_sizes = None
        for days_ago in range(1, 15):
            try:
                trade_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
                etf_sizes = pro.etf_share_size(
                    trade_date=trade_date,
                    fields='ts_code,etf_name,total_share,total_size'
                )
                if etf_sizes is not None and not etf_sizes.empty:
                    print(f"   获取规模数据 (日期: {trade_date}): {len(etf_sizes)}条")
                    break
            except:
                continue
        
        if etf_sizes is None or etf_sizes.empty:
            print("❌ 无法获取规模数据")
            return None
        
        # 合并数据
        etf_info = etf_basic.merge(etf_sizes, on='ts_code', how='inner')
        etf_info['size_yi'] = etf_info['total_size'] / 10000
        etf_info = etf_info.sort_values('total_size', ascending=False)
        
        print(f"✅ 获取到 {len(etf_info)} 只ETF数据")
        return etf_info
        
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None


def classify_etf_enhanced(etf_df):
    """增强版ETF分类"""
    
    def classify_etf_type(row):
        name = str(row.get('name', '')).upper()
        extname = str(row.get('extname', '')).upper()
        index_name = str(row.get('index_name', '')).upper()
        
        full_name = f"{name} {extname} {index_name}"
        
        # 货币ETF - 更精确的识别
        if any(keyword in full_name for keyword in [
            '货币', '现金', '理财', 'MONEY', '保证金', '日利', '添益', 
            '快线', '现金流', '短融', '银华日利', '华宝添益'
        ]):
            return '货币ETF'
        
        # REIT ETF - 更精确的识别
        elif any(keyword in full_name for keyword in [
            'REIT', 'REITS', '房地产信托', '不动产', '房地产投资信托',
            '基础设施', '产业园', '仓储物流', '数据中心'
        ]):
            return 'REIT_ETF'
        
        # 宽基指数ETF
        elif any(keyword in full_name for keyword in [
            '沪深300', 'CSI300', '中证500', 'CSI500', '创业板', '科创50', 
            '上证50', '中证1000', '深证100', '全指', '综指', 'A股', '上证综指'
        ]):
            return '宽基指数ETF'
        
        # 红利/价值ETF
        elif any(keyword in full_name for keyword in ['红利', '价值', '股息', 'DIVIDEND']):
            return '红利价值ETF'
        
        # 行业ETF - 细分
        elif any(keyword in full_name for keyword in ['医药', '医疗', '生物', '健康']):
            return '医药医疗ETF'
        elif any(keyword in full_name for keyword in ['科技', '芯片', '半导体', '计算机', '电子']):
            return '科技电子ETF'
        elif any(keyword in full_name for keyword in ['新能源', '光伏', '风电', '储能', '电池']):
            return '新能源ETF'
        elif any(keyword in full_name for keyword in ['消费', '白酒', '食品', '零售']):
            return '消费ETF'
        elif any(keyword in full_name for keyword in ['银行', '证券', '保险', '金融']):
            return '金融ETF'
        elif any(keyword in full_name for keyword in [
            '军工', '汽车', '钢铁', '煤炭', '有色', '化工', '电力', 
            '通信', '传媒', '机械', '建筑', '交通', '环保', '农业'
        ]):
            return '其他行业ETF'
        
        # 债券ETF - 细分
        elif any(keyword in full_name for keyword in ['国债', '利率债']):
            return '国债ETF'
        elif any(keyword in full_name for keyword in ['可转债', '转债']):
            return '可转债ETF'
        elif any(keyword in full_name for keyword in ['信用债', '公司债', '企债']):
            return '信用债ETF'
        elif any(keyword in full_name for keyword in ['城投债']):
            return '城投债ETF'
        elif any(keyword in full_name for keyword in ['债', 'BOND']) and '可转债' not in full_name:
            return '其他债券ETF'
        
        # 商品ETF - 细分
        elif any(keyword in full_name for keyword in ['黄金', 'GOLD']):
            return '黄金ETF'
        elif any(keyword in full_name for keyword in ['白银', 'SILVER']):
            return '白银ETF'
        elif any(keyword in full_name for keyword in ['原油', 'OIL', '石油']):
            return '原油ETF'
        elif any(keyword in full_name for keyword in ['商品', '大宗', 'COMMODITY']):
            return '其他商品ETF'
        
        # 海外ETF - 细分
        elif any(keyword in full_name for keyword in ['美股', 'NASDAQ', 'S&P', '标普']):
            return '美股ETF'
        elif any(keyword in full_name for keyword in ['港股', 'H股', '恒生']):
            return '港股ETF'
        elif any(keyword in full_name for keyword in ['日本', '德国', '欧洲', '印度', '越南']):
            return '其他海外ETF'
        elif any(keyword in full_name for keyword in ['MSCI', '全球', '国际']):
            return '全球ETF'
        
        # 策略ETF
        elif any(keyword in full_name for keyword in [
            '量化', '策略', '多因子', '低波', '质量', '动量', 'SMART', 
            '基本面', '成长', '均衡'
        ]):
            return '策略ETF'
        
        else:
            return '其他ETF'
    
    etf_df['etf_type'] = etf_df.apply(classify_etf_type, axis=1)
    return etf_df


def select_optimized_etf_portfolio(etf_df):
    """选择优化的ETF组合"""
    print("\n🎯 选择优化ETF组合")
    print("=" * 50)
    
    # 优化后的目标分布
    target_distribution = {
        '货币ETF': 10,          # 从5增加到10
        'REIT_ETF': 8,          # 从2增加到8
        '宽基指数ETF': 25,      # 略减
        '医药医疗ETF': 12,      # 保持
        '科技电子ETF': 12,      # 保持
        '新能源ETF': 12,        # 保持
        '消费ETF': 8,           # 保持
        '金融ETF': 8,           # 保持
        '红利价值ETF': 8,       # 保持
        '其他行业ETF': 20,      # 保持
        '国债ETF': 5,           # 债券细分
        '可转债ETF': 8,         # 债券细分
        '信用债ETF': 6,         # 债券细分
        '城投债ETF': 3,         # 债券细分
        '其他债券ETF': 3,       # 债券细分
        '黄金ETF': 6,           # 商品细分
        '白银ETF': 2,           # 商品细分
        '原油ETF': 3,           # 商品细分
        '其他商品ETF': 4,       # 商品细分
        '美股ETF': 6,           # 海外细分
        '港股ETF': 8,           # 海外细分
        '其他海外ETF': 4,       # 海外细分
        '全球ETF': 2,           # 海外细分
        '策略ETF': 5,           # 策略ETF
        '其他ETF': 2            # 其他
    }
    
    total_target = sum(target_distribution.values())
    print(f"目标总数: {total_target}只ETF")
    
    selected_etfs = []
    selection_summary = {}
    
    # 按类别选择
    for etf_type, target_count in target_distribution.items():
        type_etfs = etf_df[etf_df['etf_type'] == etf_type]
        
        if len(type_etfs) > 0:
            # 按规模排序，选择前N只
            selected = type_etfs.head(min(target_count, len(type_etfs)))
            selected_etfs.append(selected)
            actual_count = len(selected)
            selection_summary[etf_type] = {
                'target': target_count,
                'available': len(type_etfs),
                'selected': actual_count
            }
            print(f"   {etf_type}: 目标{target_count}只, 可选{len(type_etfs)}只, 实选{actual_count}只")
        else:
            selection_summary[etf_type] = {
                'target': target_count,
                'available': 0,
                'selected': 0
            }
            print(f"   {etf_type}: 目标{target_count}只, 可选0只, 实选0只 ❌")
    
    # 合并结果
    if selected_etfs:
        final_etfs = pd.concat(selected_etfs).sort_values('total_size', ascending=False)
        final_etfs = final_etfs.drop_duplicates(subset=['ts_code'])  # 去重
    else:
        final_etfs = pd.DataFrame()
    
    print(f"\n✅ 最终选择: {len(final_etfs)}只ETF")
    
    return final_etfs, selection_summary


def generate_optimized_config(final_etfs):
    """生成优化后的配置"""
    print("\n⚙️ 生成优化配置")
    print("=" * 50)
    
    # 按类别分组
    etf_by_category = {}
    for _, etf in final_etfs.iterrows():
        category = etf['etf_type']
        if category not in etf_by_category:
            etf_by_category[category] = []
        
        # 转换为Qlib格式
        ts_code = etf['ts_code']
        if ts_code.endswith('.SH'):
            qlib_code = 'SH' + ts_code[:6]
        elif ts_code.endswith('.SZ'):
            qlib_code = 'SZ' + ts_code[:6]
        else:
            continue
        
        etf_by_category[category].append({
            'qlib_code': qlib_code,
            'name': etf['extname'],
            'size_yi': etf['size_yi']
        })
    
    # 生成YAML配置
    config_lines = []
    config_lines.append("    etf_codes:")
    
    # 按重要性排序类别
    category_order = [
        '宽基指数ETF', '红利价值ETF', '医药医疗ETF', '科技电子ETF', '新能源ETF',
        '消费ETF', '金融ETF', '其他行业ETF', '策略ETF',
        '国债ETF', '可转债ETF', '信用债ETF', '城投债ETF', '其他债券ETF',
        '黄金ETF', '白银ETF', '原油ETF', '其他商品ETF',
        '美股ETF', '港股ETF', '其他海外ETF', '全球ETF',
        '货币ETF', 'REIT_ETF', '其他ETF'
    ]
    
    total_count = 0
    for category in category_order:
        if category in etf_by_category:
            etfs = etf_by_category[category]
            if etfs:
                config_lines.append(f"      # === {category} ({len(etfs)}只) ===")
                for etf in etfs:
                    config_lines.append(f"      - {etf['qlib_code']}  # {etf['name']} ({etf['size_yi']:.0f}亿)")
                config_lines.append("")
                total_count += len(etfs)
    
    print(f"✅ 生成配置: {total_count}只ETF")
    
    return config_lines, total_count


def main():
    """主函数"""
    print("🔧 ETF选择优化 v2.0")
    print("=" * 60)
    print("优化目标:")
    print("  1. 增加货币ETF: 5只 → 10只")
    print("  2. 增加REIT ETF: 2只 → 8只")
    print("  3. 确保所有ETF真实存在")
    print("  4. 按真实规模排序选择")
    print("=" * 60)
    
    # 步骤1: 获取真实ETF数据
    etf_df = get_real_etf_data()
    if etf_df is None:
        return False
    
    # 步骤2: 增强分类
    etf_df = classify_etf_enhanced(etf_df)
    
    # 步骤3: 分析当前分布
    print(f"\n📊 当前ETF类型分布:")
    type_counts = etf_df['etf_type'].value_counts()
    for etf_type, count in type_counts.items():
        print(f"   {etf_type}: {count}只")
    
    # 步骤4: 选择优化组合
    final_etfs, selection_summary = select_optimized_etf_portfolio(etf_df)
    
    # 步骤5: 生成配置
    config_lines, total_count = generate_optimized_config(final_etfs)
    
    # 步骤6: 保存配置
    output_file = Path("temp_scripts/optimized_etf_config.yaml")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 优化后的ETF配置\n")
        f.write("# 货币ETF: 10只, REIT ETF: 8只\n")
        f.write("# 基于真实Tushare数据按规模排序选择\n\n")
        f.write("  etf_universe:\n")
        f.write("    name: Optimized ETF Universe v2\n")
        f.write("    components_source: static_list\n")
        f.write(f"    top_n_etfs: {total_count}\n")
        for line in config_lines:
            f.write(line + "\n")
    
    print(f"\n📁 配置已保存到: {output_file}")
    
    # 步骤7: 优化效果分析
    print(f"\n📊 优化效果分析:")
    
    key_categories = ['货币ETF', 'REIT_ETF']
    for category in key_categories:
        if category in selection_summary:
            stats = selection_summary[category]
            print(f"   {category}: {stats['selected']}只 (目标: {stats['target']}只)")
        else:
            print(f"   {category}: 0只 (目标: 未设置)")
    
    # 导出详细清单
    export_file = Path("temp_scripts/optimized_etf_list.csv")
    export_df = final_etfs[[
        'ts_code', 'extname', 'etf_type', 'size_yi', 'exchange'
    ]].copy()
    
    # 添加Qlib代码
    qlib_codes = []
    for _, row in export_df.iterrows():
        ts_code = row['ts_code']
        if ts_code.endswith('.SH'):
            qlib_codes.append('SH' + ts_code[:6])
        elif ts_code.endswith('.SZ'):
            qlib_codes.append('SZ' + ts_code[:6])
        else:
            qlib_codes.append('')
    
    export_df['qlib_code'] = qlib_codes
    export_df.to_csv(export_file, index=False, encoding='utf-8-sig')
    
    print(f"📁 详细清单已保存到: {export_file}")
    
    print(f"\n🎉 优化完成!")
    print(f"   总ETF数量: {total_count}只")
    print(f"   货币ETF: {selection_summary.get('货币ETF', {}).get('selected', 0)}只")
    print(f"   REIT ETF: {selection_summary.get('REIT_ETF', {}).get('selected', 0)}只")
    
    return True


if __name__ == "__main__":
    success = main()
