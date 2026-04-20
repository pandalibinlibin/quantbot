#!/usr/bin/env python3
"""
优化ETF选择策略

目标: 解决150只ETF的结构性不平衡问题
方案: 200只ETF + 平衡配置 + 最小数量保证
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta


def get_all_etf_data():
    """获取所有ETF数据"""
    print("📊 获取全部ETF数据...")
    
    try:
        import tushare as ts
        
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
        
        # 宽基指数ETF
        if any(keyword in full_name for keyword in [
            '沪深300', 'CSI300', '中证500', 'CSI500', '创业板', '科创50', 
            '上证50', '中证1000', '深证100', '全指', '综指', 'A股'
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
        elif any(keyword in full_name for keyword in ['地产', '房地产', 'REIT']):
            return 'REIT地产ETF'
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
        
        # 货币ETF - 细分
        elif any(keyword in full_name for keyword in ['货币', '现金', '理财', 'MONEY']):
            return '货币基金ETF'
        elif any(keyword in full_name for keyword in ['保证金', '现金流']):
            return '现金管理ETF'
        
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
    
    etf_df['detailed_type'] = etf_df.apply(classify_etf_type, axis=1)
    return etf_df


def optimize_etf_selection(etf_df, target_count=200):
    """优化ETF选择策略"""
    print(f"\n🎯 优化ETF选择 (目标: {target_count}只)")
    print("=" * 50)
    
    # 定义最小数量要求
    min_requirements = {
        '货币基金ETF': 3,
        '现金管理ETF': 2,
        '美股ETF': 5,
        '港股ETF': 8,
        '其他海外ETF': 4,
        '全球ETF': 3,
        '国债ETF': 3,
        '可转债ETF': 5,
        '信用债ETF': 4,
        '城投债ETF': 3,
        '黄金ETF': 4,
        '白银ETF': 2,
        '原油ETF': 2,
        'REIT地产ETF': 3,
        '策略ETF': 8
    }
    
    # 按规模排序
    etf_df = etf_df.sort_values('size_yi', ascending=False).reset_index(drop=True)
    
    selected_etfs = []
    type_counts = {}
    
    # 第一轮: 满足最小数量要求
    print("📋 第一轮: 满足最小数量要求")
    for etf_type, min_count in min_requirements.items():
        type_etfs = etf_df[etf_df['detailed_type'] == etf_type]
        if len(type_etfs) >= min_count:
            selected = type_etfs.head(min_count)
            selected_etfs.extend(selected.index.tolist())
            type_counts[etf_type] = min_count
            print(f"   {etf_type}: 选择 {min_count}只")
        else:
            # 如果不足最小数量，全选
            selected_etfs.extend(type_etfs.index.tolist())
            type_counts[etf_type] = len(type_etfs)
            print(f"   {etf_type}: 仅有 {len(type_etfs)}只 (不足{min_count}只)")
    
    # 第二轮: 按重要性填充剩余名额
    remaining_count = target_count - len(selected_etfs)
    print(f"\n📋 第二轮: 填充剩余 {remaining_count}只")
    
    # 重要性排序
    priority_types = [
        '宽基指数ETF',      # 核心资产
        '医药医疗ETF',      # 重要行业
        '科技电子ETF',      # 重要行业
        '新能源ETF',        # 热门赛道
        '消费ETF',          # 重要行业
        '金融ETF',          # 重要行业
        '红利价值ETF',      # 价值投资
        '其他行业ETF',      # 行业多样化
        '其他债券ETF',      # 债券补充
        '其他商品ETF',      # 商品补充
        '其他ETF'           # 其他补充
    ]
    
    for etf_type in priority_types:
        if remaining_count <= 0:
            break
        
        type_etfs = etf_df[etf_df['detailed_type'] == etf_type]
        already_selected = [i for i in type_etfs.index if i in selected_etfs]
        available_etfs = type_etfs[~type_etfs.index.isin(already_selected)]
        
        if len(available_etfs) > 0:
            # 根据剩余名额和ETF重要性决定选择数量
            if etf_type == '宽基指数ETF':
                select_count = min(30, len(available_etfs), remaining_count)
            elif etf_type in ['医药医疗ETF', '科技电子ETF', '新能源ETF']:
                select_count = min(15, len(available_etfs), remaining_count)
            elif etf_type in ['消费ETF', '金融ETF', '红利价值ETF']:
                select_count = min(10, len(available_etfs), remaining_count)
            else:
                select_count = min(8, len(available_etfs), remaining_count)
            
            if select_count > 0:
                selected = available_etfs.head(select_count)
                selected_etfs.extend(selected.index.tolist())
                type_counts[etf_type] = type_counts.get(etf_type, 0) + select_count
                remaining_count -= select_count
                print(f"   {etf_type}: 新增 {select_count}只")
    
    # 生成最终结果
    final_etfs = etf_df.loc[selected_etfs].copy()
    final_etfs = final_etfs.sort_values('size_yi', ascending=False).reset_index(drop=True)
    
    print(f"\n✅ 优化完成: 选择了 {len(final_etfs)}只ETF")
    return final_etfs, type_counts


def analyze_optimized_distribution(etf_df, type_counts):
    """分析优化后的分布"""
    print("\n" + "=" * 60)
    print("📊 优化后ETF分布分析")
    print("=" * 60)
    
    # 按资产大类重新分组
    asset_mapping = {
        '宽基指数ETF': '股票资产',
        '红利价值ETF': '股票资产',
        '医药医疗ETF': '股票资产',
        '科技电子ETF': '股票资产',
        '新能源ETF': '股票资产',
        '消费ETF': '股票资产',
        '金融ETF': '股票资产',
        '其他行业ETF': '股票资产',
        '策略ETF': '股票资产',
        
        '国债ETF': '债券资产',
        '可转债ETF': '债券资产',
        '信用债ETF': '债券资产',
        '城投债ETF': '债券资产',
        '其他债券ETF': '债券资产',
        
        '黄金ETF': '商品资产',
        '白银ETF': '商品资产',
        '原油ETF': '商品资产',
        '其他商品ETF': '商品资产',
        
        '货币基金ETF': '现金资产',
        '现金管理ETF': '现金资产',
        
        '美股ETF': '海外资产',
        '港股ETF': '海外资产',
        '其他海外ETF': '海外资产',
        '全球ETF': '海外资产',
        
        'REIT地产ETF': 'REIT资产',
        '其他ETF': '其他资产'
    }
    
    # 计算资产大类分布
    asset_class_counts = {}
    for etf_type, count in type_counts.items():
        asset_class = asset_mapping.get(etf_type, '其他资产')
        asset_class_counts[asset_class] = asset_class_counts.get(asset_class, 0) + count
    
    total_count = sum(asset_class_counts.values())
    
    print("📋 资产大类分布:")
    for asset_class, count in sorted(asset_class_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / total_count * 100
        print(f"   {asset_class}: {count}只 ({percentage:.1f}%)")
    
    print(f"\n📋 详细类型分布:")
    for etf_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / total_count * 100
        print(f"   {etf_type}: {count}只 ({percentage:.1f}%)")
    
    # 跨资产配置评估
    print(f"\n🎯 跨资产配置能力评估:")
    
    evaluations = []
    if asset_class_counts.get('股票资产', 0) >= 80:
        evaluations.append("✅ 股票资产充足 - 支持多元化股票配置")
    
    if asset_class_counts.get('债券资产', 0) >= 15:
        evaluations.append("✅ 债券资产充足 - 支持股债平衡配置")
    
    if asset_class_counts.get('商品资产', 0) >= 8:
        evaluations.append("✅ 商品资产充足 - 支持通胀对冲配置")
    
    if asset_class_counts.get('海外资产', 0) >= 15:
        evaluations.append("✅ 海外资产充足 - 支持全球配置")
    
    if asset_class_counts.get('现金资产', 0) >= 5:
        evaluations.append("✅ 现金管理充足 - 支持流动性管理")
    
    if asset_class_counts.get('REIT资产', 0) >= 3:
        evaluations.append("✅ REIT资产可用 - 支持房地产配置")
    
    for evaluation in evaluations:
        print(f"   {evaluation}")
    
    return asset_class_counts


def generate_config_recommendation(final_etfs):
    """生成配置建议"""
    print("\n" + "=" * 60)
    print("⚙️ 配置文件建议")
    print("=" * 60)
    
    # 转换为Qlib格式
    qlib_codes = []
    for _, etf in final_etfs.iterrows():
        ts_code = etf['ts_code']
        if ts_code.endswith('.SH'):
            qlib_code = 'SH' + ts_code[:6]
        elif ts_code.endswith('.SZ'):
            qlib_code = 'SZ' + ts_code[:6]
        else:
            continue
        qlib_codes.append(qlib_code)
    
    print("📋 建议的index_config.yaml配置:")
    print(f"""
etf_universe:
  name: Optimized ETF Universe
  benchmark_code: 510300.SH
  etf_code: SH510300
  components_source: tushare_etf
  top_n_etfs: {len(final_etfs)}  # 从150增加到{len(final_etfs)}
  selection_strategy: balanced   # 平衡选择策略
  min_requirements:
    货币ETF: 5
    海外ETF: 20
    债券ETF: 15
    商品ETF: 8
    REIT_ETF: 3
  exclude_types: []
  update_frequency: weekly
""")
    
    return qlib_codes


def main():
    """主函数"""
    print("🔧 ETF选择策略优化")
    print("=" * 60)
    print("目标: 解决150只ETF的结构性不平衡问题")
    print("方案: 200只ETF + 平衡配置 + 最小数量保证")
    print("=" * 60)
    
    # 获取所有ETF数据
    etf_df = get_all_etf_data()
    if etf_df is None:
        return False
    
    # 增强分类
    etf_df = classify_etf_enhanced(etf_df)
    
    # 优化选择
    final_etfs, type_counts = optimize_etf_selection(etf_df, target_count=200)
    
    # 分析优化后分布
    asset_class_counts = analyze_optimized_distribution(final_etfs, type_counts)
    
    # 生成配置建议
    qlib_codes = generate_config_recommendation(final_etfs)
    
    # 导出结果
    output_file = Path("temp_scripts/optimized_etf_universe.csv")
    export_df = final_etfs[[
        'ts_code', 'extname', 'detailed_type', 'size_yi', 'exchange'
    ]].copy()
    export_df['qlib_code'] = qlib_codes
    export_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n📁 优化结果已导出到: {output_file}")
    
    # 对比分析
    print(f"\n📊 优化前后对比:")
    print(f"   ETF总数: 150只 → {len(final_etfs)}只")
    print(f"   货币ETF: 1只 → {type_counts.get('货币基金ETF', 0) + type_counts.get('现金管理ETF', 0)}只")
    print(f"   海外ETF: 7只 → {sum(type_counts.get(t, 0) for t in ['美股ETF', '港股ETF', '其他海外ETF', '全球ETF'])}只")
    print(f"   债券ETF: 18只 → {sum(type_counts.get(t, 0) for t in ['国债ETF', '可转债ETF', '信用债ETF', '城投债ETF', '其他债券ETF'])}只")
    print(f"   商品ETF: 9只 → {sum(type_counts.get(t, 0) for t in ['黄金ETF', '白银ETF', '原油ETF', '其他商品ETF'])}只")
    
    print("\n🎉 优化完成!")
    return True


if __name__ == "__main__":
    success = main()
