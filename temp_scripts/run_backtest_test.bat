@echo off
echo ========================================
echo Enhanced Indexing Strategy 回测功能测试
echo ========================================

echo.
echo 1. 检查Online Serving状态...
docker compose exec backend python -c "import requests; resp = requests.get('http://localhost:8000/api/v1/online/status'); print('Online状态:', resp.json().get('is_initialized', False) if resp.status_code == 200 else 'API调用失败'); print('信号数量:', resp.json().get('signal_count', 0) if resp.status_code == 200 else 'N/A')"

echo.
echo 2. 获取回测配置...
docker compose exec backend python -c "import requests; resp = requests.get('http://localhost:8000/api/v1/backtest/config'); config = resp.json() if resp.status_code == 200 else {}; print('配置状态:', config.get('status', 'failed')); strategy = config.get('config', {}).get('strategy', {}); print('策略类型:', strategy.get('class', 'N/A')); backtest = config.get('config', {}).get('backtest', {}); print('基准指数:', backtest.get('benchmark', 'N/A')); print('初始资金:', backtest.get('account', 'N/A'))"

echo.
echo 3. 检查回测准备状态...
docker compose exec backend python -c "import requests; resp = requests.get('http://localhost:8000/api/v1/backtest/status'); status = resp.json() if resp.status_code == 200 else {}; print('准备状态:', status.get('ready', False)); print('状态消息:', status.get('message', 'N/A')); print('信号数量:', status.get('signal_count', 'N/A'))"

echo.
echo 4. 执行Enhanced Indexing Strategy回测...
echo    注意: 这将使用我们自定义的指数增强策略
echo    预计耗时: 30-60秒
docker compose exec backend python -c "import requests; import time; print('开始执行回测...'); start = time.time(); resp = requests.post('http://localhost:8000/api/v1/backtest/run', json={}, timeout=300); end = time.time(); print(f'回测完成，耗时: {end-start:.2f}s'); result = resp.json() if resp.status_code == 200 else {}; print('回测状态:', result.get('status', 'failed')); print('策略类型:', result.get('strategy', 'N/A')); print('基准指数:', result.get('benchmark', 'N/A')); print('时间范围:', result.get('start_time', 'N/A'), '~', result.get('end_time', 'N/A')); print('交易天数:', result.get('trading_days', 'N/A')); print('总收益:', f\"{result.get('total_return', 0):.4f}\" if result.get('total_return') is not None else 'N/A'); print('净收益:', f\"{result.get('net_return', 0):.4f}\" if result.get('net_return') is not None else 'N/A'); print('最大偏离:', result.get('max_deviation', 'N/A')); risk = result.get('risk_metrics', {}); print('风险指标:'); print('  年化收益:', risk.get('annualized_return', 'N/A')); print('  最大回撤:', risk.get('max_drawdown', 'N/A')); print('  夏普比率:', risk.get('sharpe_ratio', 'N/A')); charts = result.get('charts', {}); print('图表数据:', len(charts), '个图表' if charts else '无图表数据')"

echo.
echo 5. 验证结果持久化...
timeout /t 3 /nobreak >nul
docker compose exec backend python -c "import requests; resp = requests.get('http://localhost:8000/api/v1/backtest/latest-result'); result = resp.json() if resp.status_code == 200 else {}; print('持久化状态:', result.get('status', 'failed')); latest = result.get('result', {}); print('最新结果存在:', 'Yes' if latest else 'No'); print('策略类型:', latest.get('strategy', 'N/A')); print('净收益:', f\"{latest.get('net_return', 0):.4f}\" if latest.get('net_return') is not None else 'N/A')"

echo.
echo ========================================
echo Enhanced Indexing Strategy 回测测试完成
echo ========================================
pause
