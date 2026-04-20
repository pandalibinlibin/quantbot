#!/usr/bin/env python3
"""
真实Tushare数据验证脚本

1. 调用Tushare API获取所有ETF的真实规模数据
2. 验证当前配置文件中的ETF是否真实存在
3. 获取各类别中规模最大的ETF
4. 输出结果供手动更新配置文件
"""

import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import re
from datetime import datetime, timedelta


def get_real_etf_data_from_tushare():
    """从Tushare获取真实ETF数据"""
    print("📊 从Tushare API获取真实ETF数据...")
    print("=" * 60)
    
    try:
        import tushare as ts
        
        # 读取token
        token_file = Path.home() / ".tushare_token"
        with open(token_file, 'r') as f:
            token = f.read().strip()
        
        pro = ts.pro_api(token)
        
        # 获取ETF基本信息
        print("🔍 获取ETF基本信息...")
        etf_basic = pro.etf_basic(
            list_status='L',
            fields='ts_code,name,extname,fund_type,index_code,index_name,exchange,mgr_name,list_date'
        )
        print(f"   获取到 {len(etf_basic)} 只ETF基本信息")
        
        # 获取ETF规模信息 - 尝试最近几天的数据
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
            except Exception as e:
                continue
        
        if etf_sizes is None or etf_sizes.empty:
            print("❌ 无法获取规模数据")
            return None
        
        # 合并数据
        etf_info = etf_basic.merge(etf_sizes, on='ts_code', how='inner')
        etf_info['size_yi'] = etf_info['total_size'] / 10000  # 转换为亿元
        etf_info = etf_info.sort_values('total_size', ascending=False)
        
        print(f"✅ 成功合并数据: {len(etf_info)} 只ETF")
        print(f"   规模范围: {etf_info['size_yi'].min():.1f} - {etf_info['size_yi'].max():.1f} 亿元")
        
        return etf_info
        
    except Exception as e:
        print(f"❌ 获取Tushare数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def classify_etf_enhanced(etf_df):
    """增强版ETF分类"""
    
    def classify_etf_type(row):
        name = str(row.get('name', '')).upper()
        extname = str(row.get('extname', '')).upper()
        index_name = str(row.get('index_name', '')).upper()
        
        full_name = f"{name} {extname} {index_name}"
        
        # 货币ETF
        if any(keyword in full_name for keyword in [
            '货币', '现金', '理财', 'MONEY', '保证金', '日利', '添益', 
            '快线', '现金流', '短融', '银华日利', '华宝添益'
        ]):
            return '货币ETF'
        
        # REIT ETF
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


def verify_current_config_etfs(etf_df):
    """验证当前配置文件中的ETF"""
    print("\n🔍 验证当前配置文件中的ETF...")
    print("=" * 60)
    
    try:
        # 读取当前配置文件
        config_path = Path("/app/app/config/index_config.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取当前配置中的ETF代码
        current_etfs = []
        lines = content.split('\n')
        in_etf_section = False
        
        for line in lines:
            stripped = line.strip()
            
            if 'etf_codes:' in stripped:
                in_etf_section = True
                continue
            
            if in_etf_section and stripped.startswith('#') and 'Legacy parameters' in stripped:
                break
            
            if in_etf_section and stripped.startswith('- '):
                code_match = re.search(r'- ([A-Z]{2}\d{6})', stripped)
                if code_match:
                    current_etfs.append(code_match.group(1))
        
        print(f"📋 当前配置中的ETF数量: {len(current_etfs)}")
        
        # 转换为Tushare格式进行验证
        tushare_codes = []
        for code in current_etfs:
            if code.startswith('SH'):
                tushare_codes.append(code[2:] + '.SH')
            elif code.startswith('SZ'):
                tushare_codes.append(code[2:] + '.SZ')
        
        # 验证哪些ETF在真实数据中存在
        existing_etfs = etf_df[etf_df['ts_code'].isin(tushare_codes)]
        missing_etfs = set(tushare_codes) - set(existing_etfs['ts_code'])
        
        print(f"✅ 验证结果:")
        print(f"   存在的ETF: {len(existing_etfs)}只")
        print(f"   不存在的ETF: {len(missing_etfs)}只")
        
        if missing_etfs:
            print(f"\n❌ 不存在的ETF代码:")
            for code in sorted(missing_etfs):
                qlib_code = 'SH' + code[:6] if code.endswith('.SH') else 'SZ' + code[:6]
                print(f"   {qlib_code} ({code})")
        
        return existing_etfs, missing_etfs
        
    except Exception as e:
        print(f"❌ 验证配置失败: {e}")
        return None, None


def get_top_etfs_by_category(etf_df, target_counts=None):
    """获取各类别中规模最大的ETF"""
    print("\n🏆 获取各类别中规模最大的ETF...")
    print("=" * 60)
    
    if target_counts is None:
        # 默认目标数量
        target_counts = {
            '宽基指数ETF': 25,
            '红利价值ETF': 8,
            '医药医疗ETF': 12,
            '科技电子ETF': 12,
            '新能源ETF': 12,
            '消费ETF': 8,
            '金融ETF': 8,
            '其他行业ETF': 20,
            '策略ETF': 5,
            '国债ETF': 5,
            '可转债ETF': 2,
            '信用债ETF': 6,
            '城投债ETF': 1,
            '其他债券ETF': 3,
            '黄金ETF': 6,
            '白银ETF': 2,
            '原油ETF': 3,
            '其他商品ETF': 1,
            '美股ETF': 4,
            '港股ETF': 8,
            '其他海外ETF': 3,
            '全球ETF': 2,
            '货币ETF': 10,
            'REIT_ETF': 8,
            '其他ETF': 2
        }
    
    selected_etfs = []
    category_summary = {}
    
    # 按类别选择
    for etf_type, target_count in target_counts.items():
        type_etfs = etf_df[etf_df['etf_type'] == etf_type]
        
        if len(type_etfs) > 0:
            # 按规模排序，选择前N只
            selected = type_etfs.nlargest(min(target_count, len(type_etfs)), 'size_yi')
            selected_etfs.append(selected)
            
            category_summary[etf_type] = {
                'target': target_count,
                'available': len(type_etfs),
                'selected': len(selected),
                'avg_size': selected['size_yi'].mean(),
                'total_size': selected['size_yi'].sum(),
                'top_etf': selected.iloc[0] if len(selected) > 0 else None
            }
            
            print(f"📂 {etf_type}:")
            print(f"   目标: {target_count}只, 可选: {len(type_etfs)}只, 实选: {len(selected)}只")
            if len(selected) > 0:
                top_etf = selected.iloc[0]
                print(f"   最大规模: {top_etf['extname']} ({top_etf['size_yi']:.0f}亿)")
        else:
            category_summary[etf_type] = {
                'target': target_count,
                'available': 0,
                'selected': 0,
                'avg_size': 0,
                'total_size': 0,
                'top_etf': None
            }
            print(f"📂 {etf_type}: 目标{target_count}只, 可选0只 ❌")
    
    # 合并结果
    if selected_etfs:
        final_etfs = pd.concat(selected_etfs).sort_values('size_yi', ascending=False)
        final_etfs = final_etfs.drop_duplicates(subset=['ts_code'])
    else:
        final_etfs = pd.DataFrame()
    
    print(f"\n✅ 最终选择: {len(final_etfs)}只ETF")
    print(f"   总规模: {final_etfs['size_yi'].sum():.0f}亿元")
    print(f"   平均规模: {final_etfs['size_yi'].mean():.1f}亿元")
    
    return final_etfs, category_summary


def generate_config_output(final_etfs, category_summary):
    """生成配置文件输出"""
    print("\n📝 生成配置文件格式输出...")
    print("=" * 60)
    
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
    
    # 按重要性排序类别
    category_order = [
        '宽基指数ETF', '红利价值ETF', '医药医疗ETF', '科技电子ETF', '新能源ETF',
        '消费ETF', '金融ETF', '其他行业ETF', '策略ETF',
        '国债ETF', '可转债ETF', '信用债ETF', '城投债ETF', '其他债券ETF',
        '黄金ETF', '白银ETF', '原油ETF', '其他商品ETF',
        '美股ETF', '港股ETF', '其他海外ETF', '全球ETF',
        '货币ETF', 'REIT_ETF', '其他ETF'
    ]
    
    print(f"🎯 配置文件格式输出 (共{len(final_etfs)}只ETF):")
    print("=" * 80)
    print("# Complete ETF list based on real Tushare data")
    print("# All ETF codes verified and selected by actual fund size within each category")
    print(f"# Data source: Tushare etf_basic + etf_share_size ({datetime.now().strftime('%Y-%m-%d')})")
    print("etf_codes:")
    
    total_count = 0
    for category in category_order:
        if category in etf_by_category:
            etfs = etf_by_category[category]
            if etfs:
                avg_size = category_summary[category]['avg_size']
                print(f"  # === {category} ({len(etfs)}只) - 平均规模{avg_size:.0f}亿 ===")
                for etf in etfs:
                    print(f"  - {etf['qlib_code']}  # {etf['name']} ({etf['size_yi']:.0f}亿)")
                print()
                total_count += len(etfs)
    
    print(f"# Legacy parameters (for compatibility)")
    print(f"top_n_etfs: {total_count} # Based on real Tushare data verification")
    print("=" * 80)
    
    return total_count


def main():
    """主函数"""
    print("🔧 真实Tushare数据验证脚本")
    print("=" * 80)
    print("功能:")
    print("1. 调用Tushare API获取所有ETF的真实规模数据")
    print("2. 验证当前配置文件中的ETF是否真实存在")
    print("3. 获取各类别中规模最大的ETF")
    print("4. 输出结果供手动更新配置文件")
    print("=" * 80)
    
    # 步骤1: 获取真实ETF数据
    etf_df = get_real_etf_data_from_tushare()
    if etf_df is None:
        return False
    
    # 步骤2: ETF分类
    etf_df = classify_etf_enhanced(etf_df)
    
    # 步骤3: 验证当前配置
    existing_etfs, missing_etfs = verify_current_config_etfs(etf_df)
    
    # 步骤4: 获取各类别最大规模ETF
    final_etfs, category_summary = get_top_etfs_by_category(etf_df)
    
    # 步骤5: 生成配置输出
    total_count = generate_config_output(final_etfs, category_summary)
    
    # 步骤6: 保存详细数据
    output_file = Path("/app/temp_scripts/verified_etf_data.csv")
    final_etfs.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n📁 详细数据已保存到: {output_file}")
    
    print(f"\n🎉 验证完成!")
    print(f"   验证ETF数量: {len(final_etfs)}只")
    print(f"   全部基于真实Tushare数据")
    print(f"   各类别中规模最大的ETF")
    print(f"\n📋 请将上述配置输出复制到 index_config.yaml 文件中!")
    
    return True


if __name__ == "__main__":
    main()
