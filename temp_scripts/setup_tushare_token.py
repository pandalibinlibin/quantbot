#!/usr/bin/env python3
"""
配置Tushare token并验证ETF数据获取
"""

import os
from pathlib import Path

def setup_tushare_token():
    """设置Tushare token"""
    print("🔧 Tushare Token配置")
    print("=" * 25)
    
    # 提示用户输入token
    print("请输入您的Tushare token:")
    print("(可在 https://tushare.pro/user/token 获取)")
    
    # 在实际使用中，token应该通过环境变量或安全方式提供
    # 这里提供配置指导
    
    token_file = Path.home() / ".tushare_token"
    
    print(f"\n📝 请手动创建token文件:")
    print(f"   文件路径: {token_file}")
    print(f"   文件内容: 您的tushare_token")
    print(f"   示例: echo 'your_token_here' > {token_file}")
    
    # 检查是否已存在
    if token_file.exists():
        print("✅ Token文件已存在")
        with open(token_file, 'r') as f:
            token = f.read().strip()
        if len(token) > 20:  # 基本验证token长度
            print("✅ Token格式看起来正确")
            return True, token
        else:
            print("⚠️ Token格式可能不正确")
            return False, None
    else:
        print("❌ 请先创建token文件")
        return False, None

def test_etf_data_with_token(token):
    """使用token测试ETF数据获取"""
    print("\n🧪 测试ETF数据获取")
    print("=" * 20)
    
    try:
        import tushare as ts
        
        # 初始化API
        pro = ts.pro_api(token)
        print("✅ Tushare API初始化成功")
        
        # 测试ETF基本信息
        print("\n📋 获取ETF基本信息...")
        etf_basic = pro.fund_basic(market='E', fields='ts_code,name,fund_type,list_date')
        print(f"✅ 获取到 {len(etf_basic)} 只ETF")
        
        # 显示前10只ETF
        print("\n📊 前10只ETF:")
        for i, row in etf_basic.head(10).iterrows():
            print(f"   {row['ts_code']} - {row['name'][:15]:15s} - {row.get('fund_type', 'N/A')}")
        
        # 测试行情数据
        print(f"\n📈 测试行情数据获取...")
        sample_code = etf_basic.iloc[0]['ts_code']
        
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        daily_data = pro.fund_daily(ts_code=sample_code, start_date=start_date, end_date=end_date)
        print(f"✅ 获取到 {sample_code} 的 {len(daily_data)} 条行情数据")
        
        if len(daily_data) > 0:
            # 计算成交额
            if 'amount' in daily_data.columns:
                avg_amount = daily_data['amount'].mean() * 1000  # 转换为元
                print(f"   平均日成交额: {avg_amount:,.0f} 元 ({avg_amount/100000000:.1f}亿元)")
            
        return True, etf_basic, daily_data
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False, None, None

def analyze_etf_universe(etf_basic, daily_data):
    """分析ETF股票池"""
    print(f"\n🔍 ETF股票池分析")
    print("=" * 20)
    
    if etf_basic is None:
        print("❌ 缺少ETF基础数据")
        return
    
    # ETF类型分析
    print("📊 ETF类型分布:")
    if 'fund_type' in etf_basic.columns:
        type_counts = etf_basic['fund_type'].value_counts()
        for fund_type, count in type_counts.head(10).items():
            print(f"   - {fund_type}: {count}只")
    
    # 上市时间分析
    print(f"\n📅 上市时间分析:")
    if 'list_date' in etf_basic.columns:
        etf_basic['list_year'] = etf_basic['list_date'].astype(str).str[:4]
        year_counts = etf_basic['list_year'].value_counts().sort_index()
        recent_years = year_counts.tail(5)
        for year, count in recent_years.items():
            print(f"   - {year}年: {count}只")
    
    # 预估符合条件的ETF数量
    total_etfs = len(etf_basic)
    estimated_qualified = int(total_etfs * 0.05)  # 估算5%符合5亿成交额条件
    
    print(f"\n🎯 股票池预估:")
    print(f"   - 总ETF数量: {total_etfs}只")
    print(f"   - 预估符合条件: {estimated_qualified}只 (成交额≥5亿)")
    print(f"   - 筛选比例: 5%")

def main():
    """主函数"""
    print("🚀 Tushare ETF数据源配置")
    print("=" * 30)
    
    # 配置token
    success, token = setup_tushare_token()
    
    if success:
        # 测试数据获取
        success, etf_basic, daily_data = test_etf_data_with_token(token)
        
        if success:
            # 分析ETF股票池
            analyze_etf_universe(etf_basic, daily_data)
            
            print(f"\n🎉 配置完成！")
            print("=" * 15)
            print("✅ Tushare连接正常")
            print("✅ ETF数据获取成功") 
            print("✅ 可以开始实施ETF股票池方案")
            
            print(f"\n🚀 下一步:")
            print("1. 开发ETF数据收集器")
            print("2. 实现股票池筛选逻辑")
            print("3. 集成到TopkDropoutStrategy")
            print("4. 进行回测验证")
            
        else:
            print(f"\n❌ 数据获取测试失败")
            print("请检查token是否正确，或网络连接是否正常")
    else:
        print(f"\n❌ Token配置失败")
        print("请按照提示创建token文件")

if __name__ == "__main__":
    main()
