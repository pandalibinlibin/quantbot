#!/usr/bin/env python3
"""
ETF宇宙分布分析脚本

分析150只ETF的详细分布情况:
1. ETF列表和基本信息
2. 按类型分类统计
3. 按规模分层统计
4. 按交易所分布统计
5. 跨资产配置可行性分析
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def get_etf_universe():
    """获取ETF股票池"""
    print("📊 获取ETF股票池...")
    
    try:
        from app.services.index_components_service import get_index_components_service
        
        service = get_index_components_service()
        service.cache.clear()
        
        etf_list = service.get_components('etf_universe', use_cache=False)
        print(f"✅ 获取到 {len(etf_list)} 只ETF")
        
        return etf_list
        
    except Exception as e:
        print(f"❌ 获取ETF股票池失败: {e}")
        return None


def get_detailed_etf_info(etf_list):
    """获取ETF详细信息"""
    print("\n📋 获取ETF详细信息...")
    
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
        from datetime import datetime, timedelta
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
            print("⚠️ 无法获取规模数据")
            return None
        
        # 合并数据
        etf_info = etf_basic.merge(etf_sizes, on='ts_code', how='inner')
        
        # 筛选我们的150只ETF
        our_etfs = []
        for etf_code in etf_list:
            # 转换格式: SH510300 -> 510300.SH
            if etf_code.startswith('SH'):
                ts_code = etf_code[2:] + '.SH'
            elif etf_code.startswith('SZ'):
                ts_code = etf_code[2:] + '.SZ'
            else:
                continue
            
            etf_row = etf_info[etf_info['ts_code'] == ts_code]
            if not etf_row.empty:
                row = etf_row.iloc[0].copy()
                row['qlib_code'] = etf_code
                our_etfs.append(row)
        
        our_etf_df = pd.DataFrame(our_etfs)
        our_etf_df = our_etf_df.sort_values('total_size', ascending=False).reset_index(drop=True)
        
        print(f"✅ 获取到 {len(our_etf_df)} 只ETF的详细信息")
        return our_etf_df
        
    except Exception as e:
        print(f"❌ 获取详细信息失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_etf_types(etf_df):
    """分析ETF类型分布"""
    print("\n" + "=" * 60)
    print("📊 ETF类型分布分析")
    print("=" * 60)
    
    # 基于ETF名称和代码进行智能分类
    def classify_etf_type(row):
        name = str(row.get('name', '')).upper()
        extname = str(row.get('extname', '')).upper()
        ts_code = str(row.get('ts_code', ''))
        index_name = str(row.get('index_name', '')).upper()
        
        full_name = f"{name} {extname} {index_name}"
        
        # 股票型ETF
        if any(keyword in full_name for keyword in [
            '沪深300', 'CSI300', '中证500', 'CSI500', '创业板', '科创50', 
            '上证50', '中证1000', '深证100', '红利', '价值', '成长',
            '中小板', '全指', '综指', 'A股'
        ]):
            return '宽基指数ETF'
        
        # 行业/主题ETF
        elif any(keyword in full_name for keyword in [
            '医药', '医疗', '生物', '科技', '芯片', '半导体', '新能源', '光伏',
            '军工', '银行', '证券', '保险', '地产', '消费', '白酒', '食品',
            '汽车', '钢铁', '煤炭', '有色', '化工', '电力', '通信', '传媒',
            '计算机', '电子', '机械', '建筑', '交通', '环保', '农业'
        ]):
            return '行业主题ETF'
        
        # 债券ETF
        elif any(keyword in full_name for keyword in [
            '债', '国债', '企债', '公司债', '可转债', '信用债'
        ]):
            return '债券ETF'
        
        # 商品ETF
        elif any(keyword in full_name for keyword in [
            '黄金', '白银', '原油', '商品', '大宗', 'GOLD', 'COMMODITY'
        ]):
            return '商品ETF'
        
        # 货币ETF
        elif any(keyword in full_name for keyword in [
            '货币', '现金', '理财', 'MONEY', '保证金'
        ]):
            return '货币ETF'
        
        # 国际ETF
        elif any(keyword in full_name for keyword in [
            '美股', '港股', '日本', '欧洲', '德国', '印度', '越南',
            'NASDAQ', 'S&P', 'MSCI', '恒生', 'H股'
        ]):
            return '国际ETF'
        
        # 策略ETF
        elif any(keyword in full_name for keyword in [
            '量化', '策略', '多因子', '低波', '质量', '动量', 'SMART'
        ]):
            return '策略ETF'
        
        else:
            return '其他ETF'
    
    # 应用分类
    etf_df['etf_type'] = etf_df.apply(classify_etf_type, axis=1)
    
    # 统计各类型数量
    type_stats = etf_df['etf_type'].value_counts()
    
    print("📋 ETF类型分布:")
    for etf_type, count in type_stats.items():
        percentage = count / len(etf_df) * 100
        print(f"   {etf_type}: {count}只 ({percentage:.1f}%)")
    
    # 显示各类型的代表性ETF
    print("\n📋 各类型代表性ETF:")
    for etf_type in type_stats.index:
        type_etfs = etf_df[etf_df['etf_type'] == etf_type].head(3)
        print(f"\n   【{etf_type}】:")
        for _, etf in type_etfs.iterrows():
            size_yi = etf['total_size'] / 10000
            print(f"     - {etf['qlib_code']}: {etf['extname'][:20]} ({size_yi:.0f}亿元)")
    
    return type_stats


def analyze_etf_scales(etf_df):
    """分析ETF规模分布"""
    print("\n" + "=" * 60)
    print("📊 ETF规模分布分析")
    print("=" * 60)
    
    # 规模分层 (单位: 亿元)
    etf_df['size_yi'] = etf_df['total_size'] / 10000
    
    def classify_scale(size_yi):
        if size_yi >= 1000:
            return '超大规模 (≥1000亿)'
        elif size_yi >= 500:
            return '大规模 (500-1000亿)'
        elif size_yi >= 100:
            return '中等规模 (100-500亿)'
        elif size_yi >= 50:
            return '中小规模 (50-100亿)'
        elif size_yi >= 10:
            return '小规模 (10-50亿)'
        else:
            return '微小规模 (<10亿)'
    
    etf_df['scale_category'] = etf_df['size_yi'].apply(classify_scale)
    
    # 统计各规模层数量
    scale_stats = etf_df['scale_category'].value_counts()
    
    print("📋 ETF规模分布:")
    scale_order = [
        '超大规模 (≥1000亿)', '大规模 (500-1000亿)', '中等规模 (100-500亿)',
        '中小规模 (50-100亿)', '小规模 (10-50亿)', '微小规模 (<10亿)'
    ]
    
    for scale in scale_order:
        if scale in scale_stats:
            count = scale_stats[scale]
            percentage = count / len(etf_df) * 100
            print(f"   {scale}: {count}只 ({percentage:.1f}%)")
    
    # 规模统计
    print(f"\n📊 规模统计:")
    print(f"   总规模: {etf_df['size_yi'].sum():.0f}亿元")
    print(f"   平均规模: {etf_df['size_yi'].mean():.0f}亿元")
    print(f"   中位数规模: {etf_df['size_yi'].median():.0f}亿元")
    print(f"   最大规模: {etf_df['size_yi'].max():.0f}亿元")
    print(f"   最小规模: {etf_df['size_yi'].min():.0f}亿元")
    
    # 显示各规模层的代表ETF
    print(f"\n📋 各规模层代表ETF:")
    for scale in scale_order:
        if scale in scale_stats:
            scale_etfs = etf_df[etf_df['scale_category'] == scale].head(3)
            print(f"\n   【{scale}】:")
            for _, etf in scale_etfs.iterrows():
                print(f"     - {etf['qlib_code']}: {etf['extname'][:20]} ({etf['size_yi']:.0f}亿元)")
    
    return scale_stats


def analyze_exchange_distribution(etf_df):
    """分析交易所分布"""
    print("\n" + "=" * 60)
    print("📊 交易所分布分析")
    print("=" * 60)
    
    exchange_stats = etf_df['exchange'].value_counts()
    
    print("📋 交易所分布:")
    for exchange, count in exchange_stats.items():
        percentage = count / len(etf_df) * 100
        exchange_name = "上海证券交易所" if exchange == "SH" else "深圳证券交易所" if exchange == "SZ" else exchange
        print(f"   {exchange_name} ({exchange}): {count}只 ({percentage:.1f}%)")
    
    return exchange_stats


def analyze_cross_asset_allocation(etf_df):
    """分析跨资产配置可行性"""
    print("\n" + "=" * 60)
    print("🎯 跨资产配置可行性分析")
    print("=" * 60)
    
    # 按资产类别重新分类
    def classify_asset_class(row):
        etf_type = row['etf_type']
        
        if etf_type in ['宽基指数ETF', '行业主题ETF', '策略ETF']:
            return '股票资产'
        elif etf_type == '债券ETF':
            return '债券资产'
        elif etf_type == '商品ETF':
            return '商品资产'
        elif etf_type == '货币ETF':
            return '现金资产'
        elif etf_type == '国际ETF':
            return '海外资产'
        else:
            return '其他资产'
    
    etf_df['asset_class'] = etf_df.apply(classify_asset_class, axis=1)
    
    # 统计各资产类别
    asset_stats = etf_df['asset_class'].value_counts()
    asset_size_stats = etf_df.groupby('asset_class')['size_yi'].agg(['count', 'sum', 'mean']).round(0)
    
    print("📋 资产类别分布:")
    for asset_class, count in asset_stats.items():
        percentage = count / len(etf_df) * 100
        total_size = asset_size_stats.loc[asset_class, 'sum']
        avg_size = asset_size_stats.loc[asset_class, 'mean']
        print(f"   {asset_class}: {count}只 ({percentage:.1f}%) | 总规模: {total_size:.0f}亿 | 平均: {avg_size:.0f}亿")
    
    # 跨资产配置建议
    print(f"\n🎯 跨资产配置建议:")
    
    # 检查各资产类别的可用性
    recommendations = []
    
    if '股票资产' in asset_stats and asset_stats['股票资产'] >= 50:
        recommendations.append("✅ 股票资产充足 - 可进行多元化股票配置")
    
    if '债券资产' in asset_stats and asset_stats['债券资产'] >= 5:
        recommendations.append("✅ 债券资产可用 - 可进行股债平衡配置")
    else:
        recommendations.append("⚠️ 债券资产较少 - 建议增加债券ETF")
    
    if '商品资产' in asset_stats and asset_stats['商品资产'] >= 2:
        recommendations.append("✅ 商品资产可用 - 可进行通胀对冲")
    else:
        recommendations.append("⚠️ 商品资产较少 - 抗通胀能力有限")
    
    if '海外资产' in asset_stats and asset_stats['海外资产'] >= 5:
        recommendations.append("✅ 海外资产可用 - 可进行全球配置")
    else:
        recommendations.append("⚠️ 海外资产较少 - 全球分散化有限")
    
    if '现金资产' in asset_stats:
        recommendations.append("✅ 现金管理工具可用 - 可进行流动性管理")
    
    for rec in recommendations:
        print(f"   {rec}")
    
    # 配置策略建议
    print(f"\n💡 推荐配置策略:")
    
    stock_count = asset_stats.get('股票资产', 0)
    bond_count = asset_stats.get('债券资产', 0)
    commodity_count = asset_stats.get('商品资产', 0)
    overseas_count = asset_stats.get('海外资产', 0)
    
    if stock_count >= 50 and bond_count >= 5:
        print("   1. 核心-卫星策略: 宽基ETF作核心 + 行业ETF作卫星")
        print("   2. 股债平衡策略: 60%股票ETF + 40%债券ETF")
    
    if stock_count >= 30 and bond_count >= 3 and commodity_count >= 2:
        print("   3. 多资产配置: 股票60% + 债券30% + 商品10%")
    
    if overseas_count >= 5:
        print("   4. 全球配置策略: 70%国内 + 30%海外")
    
    if stock_count >= 20:
        print("   5. 行业轮动策略: 基于不同行业ETF的动态配置")
    
    return asset_stats


def export_etf_list(etf_df):
    """导出ETF清单"""
    print("\n" + "=" * 60)
    print("📁 导出ETF清单")
    print("=" * 60)
    
    try:
        # 准备导出数据
        export_df = etf_df[[
            'qlib_code', 'ts_code', 'extname', 'etf_type', 'asset_class',
            'scale_category', 'size_yi', 'exchange', 'mgr_name', 'list_date'
        ]].copy()
        
        export_df = export_df.rename(columns={
            'qlib_code': 'Qlib代码',
            'ts_code': 'Tushare代码',
            'extname': 'ETF名称',
            'etf_type': 'ETF类型',
            'asset_class': '资产类别',
            'scale_category': '规模分层',
            'size_yi': '规模(亿元)',
            'exchange': '交易所',
            'mgr_name': '管理人',
            'list_date': '上市日期'
        })
        
        # 导出到CSV
        output_file = Path("temp_scripts/etf_universe_analysis.csv")
        export_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"✅ ETF清单已导出到: {output_file}")
        print(f"   包含 {len(export_df)} 只ETF的详细信息")
        
        # 显示前10只ETF
        print(f"\n📋 前10只ETF预览:")
        print(export_df.head(10)[['Qlib代码', 'ETF名称', 'ETF类型', '规模(亿元)']].to_string(index=False))
        
        return output_file
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return None


def main():
    """主函数"""
    print("🔍 ETF宇宙分布分析")
    print("=" * 60)
    print("分析内容:")
    print("  1. 获取150只ETF股票池")
    print("  2. ETF类型分布分析")
    print("  3. ETF规模分布分析") 
    print("  4. 交易所分布分析")
    print("  5. 跨资产配置可行性分析")
    print("  6. 导出详细ETF清单")
    print("=" * 60)
    
    # 步骤1: 获取ETF股票池
    etf_list = get_etf_universe()
    if etf_list is None:
        return False
    
    # 步骤2: 获取详细信息
    etf_df = get_detailed_etf_info(etf_list)
    if etf_df is None:
        return False
    
    # 步骤3: 各项分析
    type_stats = analyze_etf_types(etf_df)
    scale_stats = analyze_etf_scales(etf_df)
    exchange_stats = analyze_exchange_distribution(etf_df)
    asset_stats = analyze_cross_asset_allocation(etf_df)
    
    # 步骤4: 导出清单
    export_file = export_etf_list(etf_df)
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 分析总结")
    print("=" * 60)
    
    print(f"✅ ETF总数: {len(etf_df)}只")
    print(f"✅ 总规模: {etf_df['size_yi'].sum():.0f}亿元")
    print(f"✅ 平均规模: {etf_df['size_yi'].mean():.0f}亿元")
    
    print(f"\n📊 分布特征:")
    print(f"   - 类型最多: {type_stats.index[0]} ({type_stats.iloc[0]}只)")
    print(f"   - 规模最多: {scale_stats.index[0]} ({scale_stats.iloc[0]}只)")
    print(f"   - 交易所分布: 上交所 vs 深交所")
    
    print(f"\n🎯 跨资产配置结论:")
    if len(asset_stats) >= 4:
        print("   ✅ 支持多资产配置 - 覆盖股票、债券、商品、海外等资产")
    elif len(asset_stats) >= 3:
        print("   ✅ 支持基础跨资产配置 - 主要覆盖股票和债券资产")
    else:
        print("   ⚠️ 跨资产配置能力有限 - 主要为股票资产")
    
    if export_file:
        print(f"\n📁 详细清单: {export_file}")
    
    print("\n🚀 分析完成!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
