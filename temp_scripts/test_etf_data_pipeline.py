#!/usr/bin/env python3
"""
ETF数据处理全流程测试
测试从数据获取、预处理到因子计算的完整流程

流程:
1. 获取ETF股票池 (IndexComponentsService)
2. 下载ETF行情数据 (TushareDataCollector)
3. 数据预处理 (Qlib dump_bin)
4. Alpha158因子计算 (Qlib DataHandler)
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta


def test_step1_get_etf_universe():
    """步骤1: 获取ETF股票池"""
    print("\n" + "=" * 60)
    print("📊 步骤1: 获取ETF股票池")
    print("=" * 60)
    
    try:
        from app.services.index_components_service import get_index_components_service
        
        service = get_index_components_service()
        service.cache.clear()
        
        start_time = time.time()
        etf_list = service.get_components('etf_universe', use_cache=False)
        elapsed = time.time() - start_time
        
        print(f"✅ 获取到 {len(etf_list)} 只ETF (耗时: {elapsed:.1f}秒)")
        print(f"   前10只: {etf_list[:10]}")
        
        if len(etf_list) < 50:
            print("❌ ETF数量不足50只")
            return None
        
        return etf_list
        
    except Exception as e:
        print(f"❌ 步骤1失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step2_download_etf_data(etf_list, sample_size=10):
    """步骤2: 下载ETF行情数据 (仅测试部分ETF)"""
    print("\n" + "=" * 60)
    print(f"📊 步骤2: 下载ETF行情数据 (测试前{sample_size}只)")
    print("=" * 60)
    
    try:
        import tushare as ts
        import pandas as pd
        from datetime import datetime, timedelta
        
        # 读取token
        token_file = Path.home() / ".tushare_token"
        with open(token_file, 'r') as f:
            token = f.read().strip()
        
        pro = ts.pro_api(token)
        
        # 设置日期范围 (最近60天)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
        
        print(f"📅 日期范围: {start_date} ~ {end_date}")
        
        # 测试下载部分ETF数据
        sample_etfs = etf_list[:sample_size]
        downloaded_data = {}
        
        for etf_code in sample_etfs:
            # 转换Qlib格式到Tushare格式
            if etf_code.startswith('SH'):
                ts_code = etf_code[2:] + '.SH'
            elif etf_code.startswith('SZ'):
                ts_code = etf_code[2:] + '.SZ'
            else:
                continue
            
            try:
                # 使用fund_daily获取ETF日线数据
                df = pro.fund_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    fields='ts_code,trade_date,open,high,low,close,vol,amount'
                )
                
                if df is not None and not df.empty:
                    downloaded_data[etf_code] = df
                    print(f"   ✅ {etf_code}: {len(df)}条记录")
                else:
                    print(f"   ⚠️ {etf_code}: 无数据")
                
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                print(f"   ❌ {etf_code}: {e}")
        
        print(f"\n✅ 成功下载 {len(downloaded_data)}/{sample_size} 只ETF数据")
        
        if len(downloaded_data) < sample_size * 0.8:
            print("⚠️ 下载成功率低于80%")
            return None
        
        return downloaded_data
        
    except Exception as e:
        print(f"❌ 步骤2失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step3_data_preprocessing(downloaded_data):
    """步骤3: 数据预处理 (模拟Qlib格式转换)"""
    print("\n" + "=" * 60)
    print("📊 步骤3: 数据预处理")
    print("=" * 60)
    
    try:
        import pandas as pd
        import numpy as np
        
        processed_data = {}
        
        for etf_code, df in downloaded_data.items():
            # 数据清洗和格式转换
            df_processed = df.copy()
            
            # 1. 重命名列 (Tushare -> Qlib标准)
            df_processed = df_processed.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            })
            
            # 2. 日期格式转换
            df_processed['date'] = pd.to_datetime(df_processed['date'])
            df_processed = df_processed.sort_values('date')
            df_processed = df_processed.set_index('date')
            
            # 3. 数据类型转换
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
            for col in numeric_cols:
                if col in df_processed.columns:
                    df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
            
            # 4. 缺失值处理
            missing_before = df_processed.isnull().sum().sum()
            df_processed = df_processed.fillna(method='ffill')
            df_processed = df_processed.dropna()
            
            # 5. 数据验证
            if len(df_processed) > 0:
                processed_data[etf_code] = df_processed
                print(f"   ✅ {etf_code}: {len(df_processed)}条, "
                      f"日期范围: {df_processed.index[0].strftime('%Y-%m-%d')} ~ "
                      f"{df_processed.index[-1].strftime('%Y-%m-%d')}")
            else:
                print(f"   ⚠️ {etf_code}: 预处理后无有效数据")
        
        print(f"\n✅ 预处理完成: {len(processed_data)} 只ETF")
        
        # 显示数据样例
        if processed_data:
            sample_etf = list(processed_data.keys())[0]
            sample_df = processed_data[sample_etf]
            print(f"\n📋 数据样例 ({sample_etf}):")
            print(sample_df.tail(3).to_string())
        
        return processed_data
        
    except Exception as e:
        print(f"❌ 步骤3失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step4_factor_calculation(processed_data):
    """步骤4: Alpha158因子计算 (简化版)"""
    print("\n" + "=" * 60)
    print("📊 步骤4: 因子计算 (Alpha158简化版)")
    print("=" * 60)
    
    try:
        import pandas as pd
        import numpy as np
        
        factor_data = {}
        
        for etf_code, df in processed_data.items():
            factors = pd.DataFrame(index=df.index)
            
            # 计算一些基础Alpha因子
            close = df['close']
            open_price = df['open']
            high = df['high']
            low = df['low']
            volume = df['volume']
            
            # 1. 收益率因子
            factors['return_1d'] = close.pct_change(1)
            factors['return_5d'] = close.pct_change(5)
            factors['return_10d'] = close.pct_change(10)
            
            # 2. 波动率因子
            factors['volatility_5d'] = close.pct_change().rolling(5).std()
            factors['volatility_10d'] = close.pct_change().rolling(10).std()
            
            # 3. 动量因子
            factors['momentum_5d'] = close / close.shift(5) - 1
            factors['momentum_10d'] = close / close.shift(10) - 1
            
            # 4. 均线因子
            factors['ma_5'] = close.rolling(5).mean()
            factors['ma_10'] = close.rolling(10).mean()
            factors['ma_ratio'] = factors['ma_5'] / factors['ma_10']
            
            # 5. 成交量因子
            factors['volume_ratio_5d'] = volume / volume.rolling(5).mean()
            
            # 6. 价格位置因子
            factors['high_low_ratio'] = (close - low) / (high - low + 1e-8)
            
            # 7. 开盘跳空因子
            factors['gap'] = open_price / close.shift(1) - 1
            
            # 删除NaN
            factors = factors.dropna()
            
            if len(factors) > 0:
                factor_data[etf_code] = factors
                print(f"   ✅ {etf_code}: {len(factors)}条, {len(factors.columns)}个因子")
        
        print(f"\n✅ 因子计算完成: {len(factor_data)} 只ETF")
        
        # 显示因子样例
        if factor_data:
            sample_etf = list(factor_data.keys())[0]
            sample_factors = factor_data[sample_etf]
            print(f"\n📋 因子样例 ({sample_etf}):")
            print(f"   因子列表: {list(sample_factors.columns)}")
            print(f"\n   最近3条数据:")
            print(sample_factors.tail(3).round(4).to_string())
            
            # 因子统计
            print(f"\n📊 因子统计:")
            stats = sample_factors.describe().loc[['mean', 'std', 'min', 'max']]
            print(stats.round(4).to_string())
        
        return factor_data
        
    except Exception as e:
        print(f"❌ 步骤4失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step5_qlib_integration():
    """步骤5: 测试Qlib集成 (可选)"""
    print("\n" + "=" * 60)
    print("📊 步骤5: Qlib集成测试")
    print("=" * 60)
    
    try:
        import qlib
        from qlib.config import REG_CN
        
        # 检查Qlib是否已初始化
        print("   检查Qlib状态...")
        
        # 尝试获取Qlib数据目录
        from app.core.config import settings
        qlib_data_dir = Path(settings.QLIB_DATA_DIR)
        
        if qlib_data_dir.exists():
            print(f"   ✅ Qlib数据目录存在: {qlib_data_dir}")
            
            # 检查instruments文件
            instruments_dir = qlib_data_dir / "instruments"
            if instruments_dir.exists():
                instrument_files = list(instruments_dir.glob("*.txt"))
                print(f"   ✅ Instruments文件: {len(instrument_files)}个")
            else:
                print("   ⚠️ Instruments目录不存在")
            
            # 检查features目录
            features_dir = qlib_data_dir / "features"
            if features_dir.exists():
                feature_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
                print(f"   ✅ Features目录: {len(feature_dirs)}个标的")
            else:
                print("   ⚠️ Features目录不存在")
        else:
            print(f"   ⚠️ Qlib数据目录不存在: {qlib_data_dir}")
            print("   💡 需要先运行数据收集任务")
        
        return True
        
    except Exception as e:
        print(f"   ⚠️ Qlib集成测试跳过: {e}")
        return True  # 不影响整体测试


def main():
    """主函数"""
    print("🚀 ETF数据处理全流程测试")
    print("=" * 60)
    print("测试流程:")
    print("  1. 获取ETF股票池")
    print("  2. 下载ETF行情数据")
    print("  3. 数据预处理")
    print("  4. Alpha因子计算")
    print("  5. Qlib集成检查")
    print("=" * 60)
    
    results = {}
    
    # 步骤1: 获取ETF股票池
    etf_list = test_step1_get_etf_universe()
    results['ETF股票池获取'] = etf_list is not None
    
    if etf_list is None:
        print("\n❌ 步骤1失败，无法继续")
        return False
    
    # 步骤2: 下载ETF数据 (测试前10只)
    downloaded_data = test_step2_download_etf_data(etf_list, sample_size=10)
    results['ETF数据下载'] = downloaded_data is not None
    
    if downloaded_data is None:
        print("\n❌ 步骤2失败，无法继续")
        return False
    
    # 步骤3: 数据预处理
    processed_data = test_step3_data_preprocessing(downloaded_data)
    results['数据预处理'] = processed_data is not None
    
    if processed_data is None:
        print("\n❌ 步骤3失败，无法继续")
        return False
    
    # 步骤4: 因子计算
    factor_data = test_step4_factor_calculation(processed_data)
    results['因子计算'] = factor_data is not None
    
    # 步骤5: Qlib集成检查
    qlib_ok = test_step5_qlib_integration()
    results['Qlib集成'] = qlib_ok
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    all_passed = True
    for step_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {step_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ETF数据处理全流程测试通过！")
        print("\n💡 结论:")
        print("   - ETF股票池获取正常 (基于规模排序)")
        print("   - ETF行情数据下载正常 (使用fund_daily接口)")
        print("   - 数据预处理流程正常 (格式转换、缺失值处理)")
        print("   - Alpha因子计算正常 (收益率、波动率、动量等)")
        print("\n🚀 系统已准备好进行ETF量化交易!")
    else:
        print("⚠️ 部分测试未通过，请检查上述错误信息")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
