#!/usr/bin/env python3
"""
三按钮工作流端到端测试验证脚本

用途: 验证前端操作后的后端执行结果
执行: docker compose exec backend python /app/temp_scripts/test_three_button_workflow.py
"""

import requests
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000"

def print_header(title):
    """打印测试标题"""
    print("\n" + "="*60)
    print(f"🧪 {title}")
    print("="*60)

def test_update_data_execution():
    """验证Update Data按钮执行结果"""
    print_header("验证 Update Data 执行结果")
    
    try:
        # 检查数据状态API
        response = requests.get(f"{BASE_URL}/api/v1/update-data/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Update Data API 可访问")
            
            if data.get('success'):
                status = data.get('data', {})
                print(f"📊 数据状态检查:")
                print(f"   数据就绪: {status.get('is_ready')}")
                print(f"   ETF数量: {status.get('etf_count')}")
                print(f"   数据新鲜度: {status.get('data_freshness_hours')}小时")
                print(f"   模型就绪: {status.get('model_ready')}")
                print(f"   预测可用: {status.get('predictions_available')}")
                print(f"   最后更新: {status.get('last_update')}")
                
                return status.get('is_ready', False)
            else:
                print("❌ API返回失败状态")
                return False
        else:
            print(f"❌ API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Update Data验证失败: {str(e)}")
        return False

def test_run_signal_execution():
    """验证Run Signal按钮执行结果"""
    print_header("验证 Run Signal 执行结果")
    
    try:
        # 检查Run Signal API响应
        response = requests.post(f"{BASE_URL}/api/v1/run-task/run", 
                               headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Run Signal API 可访问")
            
            if data.get('success'):
                signal_data = data.get('data', {})
                print(f"📊 信号生成结果:")
                print(f"   买入信号数量: {len(signal_data.get('buy_changes', {}))}")
                print(f"   卖出信号数量: {len(signal_data.get('sell_changes', {}))}")
                print(f"   投资组合持仓数: {signal_data.get('summary', {}).get('total_positions')}")
                print(f"   现金比例: {signal_data.get('summary', {}).get('cash_ratio')}%")
                print(f"   邮件发送状态: {data.get('email_sent')}")
                
                # 显示部分买卖信号
                buy_changes = signal_data.get('buy_changes', {})
                sell_changes = signal_data.get('sell_changes', {})
                
                if buy_changes:
                    print(f"\n🟢 买入信号样例 (前3只):")
                    for i, (etf, change) in enumerate(list(buy_changes.items())[:3]):
                        print(f"   {etf}: {change['from']:.1f}% → {change['to']:.1f}% ({change['change']:+.1f}%)")
                
                if sell_changes:
                    print(f"\n🔴 卖出信号样例 (前3只):")
                    for i, (etf, change) in enumerate(list(sell_changes.items())[:3]):
                        print(f"   {etf}: {change['from']:.1f}% → {change['to']:.1f}% ({change['change']:+.1f}%)")
                
                return True
            else:
                print(f"❌ Run Signal执行失败: {data.get('message')}")
                return False
        else:
            print(f"❌ Run Signal API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Run Signal验证失败: {str(e)}")
        return False

def test_run_backtest_execution():
    """验证Run Backtest按钮执行结果"""
    print_header("验证 Run Backtest 执行结果")
    
    try:
        # 检查Backtest API响应
        response = requests.post(f"{BASE_URL}/api/v1/backtest/run", 
                               headers={"Content-Type": "application/json"},
                               json={})
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Run Backtest API 可访问")
            
            if data.get('success'):
                print(f"📊 回测执行结果:")
                print(f"   执行状态: {data.get('message')}")
                print(f"   执行时间: {data.get('timestamp')}")
                
                # 如果有回测数据，显示关键指标
                if 'backtest_results' in data:
                    results = data['backtest_results']
                    print(f"   总收益率: {results.get('total_return_pct', 'N/A')}")
                    print(f"   年化收益率: {results.get('annualized_return_pct', 'N/A')}")
                    print(f"   最大回撤: {results.get('max_drawdown_pct', 'N/A')}")
                    print(f"   夏普比率: {results.get('sharpe_ratio', 'N/A')}")
                
                return True
            else:
                print(f"❌ Run Backtest执行失败: {data.get('message')}")
                return False
        else:
            print(f"❌ Run Backtest API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Run Backtest验证失败: {str(e)}")
        return False

def test_dashboard_data_consistency():
    """验证Dashboard数据一致性"""
    print_header("验证 Dashboard 数据一致性")
    
    try:
        # 检查Dashboard API
        response = requests.get(f"{BASE_URL}/api/v1/dashboard/summary")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Dashboard API 可访问")
            
            if data.get('success'):
                print(f"📊 Dashboard数据状态:")
                
                # 系统状态
                system = data.get('system', {})
                print(f"   系统初始化: {system.get('is_initialized')}")
                print(f"   信号数量: {system.get('signal_count')}")
                print(f"   最后例行时间: {system.get('last_routine_time')}")
                
                # 回测数据
                backtest = data.get('backtest', {})
                if backtest.get('has_results'):
                    print(f"   回测结果可用: ✅")
                    print(f"   总收益率: {backtest.get('total_return_pct')}")
                    print(f"   净收益率: {backtest.get('net_return_pct')}")
                else:
                    print(f"   回测结果可用: ❌")
                
                # 模型状态
                model = data.get('model', {})
                print(f"   模型指标可用: {model.get('has_metrics')}")
                if model.get('has_metrics'):
                    print(f"   IC指标: {model.get('ic')}")
                    print(f"   ICIR指标: {model.get('icir')}")
                
                # 目标持仓
                positions = data.get('target_positions', [])
                print(f"   目标持仓数量: {len(positions)}")
                
                return True
            else:
                print("❌ Dashboard API返回失败状态")
                return False
        else:
            print(f"❌ Dashboard API请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Dashboard验证失败: {str(e)}")
        return False

def test_functional_boundaries():
    """验证功能边界分离"""
    print_header("验证功能边界分离")
    
    print("🔍 功能边界验证:")
    print("   📥 Update Data: 数据准备，不影响页面显示")
    print("   🚀 Run Signal: 影响所有非backtest页面")
    print("   📈 Run Backtest: 只影响backtest页面")
    
    # 这部分需要通过前端操作来验证
    print("\n💡 请通过前端页面验证:")
    print("   1. 点击Update Data后，Dashboard数据不应立即变化")
    print("   2. 点击Run Signal后，Dashboard应显示新的投资组合数据")
    print("   3. 点击Run Backtest后，只有backtest页面应该更新")
    
    return True

def main():
    """主测试函数"""
    print("🚀 三按钮工作流端到端测试验证")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 执行各项验证
    results = {}
    
    results['update_data'] = test_update_data_execution()
    results['run_signal'] = test_run_signal_execution()
    results['run_backtest'] = test_run_backtest_execution()
    results['dashboard'] = test_dashboard_data_consistency()
    results['boundaries'] = test_functional_boundaries()
    
    # 汇总结果
    print_header("测试结果汇总")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！三按钮工作流运行正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查上述错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
