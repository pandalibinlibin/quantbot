@echo off
echo ========================================
echo Qlib缓存优化测试脚本
echo ========================================

echo.
echo 1. 检查缓存目录状态...
docker compose exec backend find /app/qlib_data -name "*cache*" -type d -exec ls -la {} \;

echo.
echo 2. 等待30秒让缓存完全生效...
timeout /t 30 /nobreak

echo.
echo 3. 执行第三次routine测试 (缓存预热后)...
docker compose exec backend python -c "import time; import requests; print('开始第三次测试...'); start = time.time(); resp = requests.post('http://localhost:8000/api/v1/online/routine', json={}, timeout=300); end = time.time(); result = resp.json() if resp.status_code == 200 else {}; print(f'第三次完成: {end-start:.2f}s (后端: {result.get(\"total_duration_seconds\", 0):.2f}s)') if resp.status_code == 200 else print(f'失败: {resp.status_code}'); [print(f'  • {step.get(\"step\", \"Unknown\")}: {step.get(\"duration_seconds\", 0):.2f}s') for step in result.get('steps', [])] if resp.status_code == 200 else None"

echo.
echo 4. 验证因子计算缓存效果...
docker compose exec backend python /app/temp_scripts/test_qlib_cache_optimization.py

echo.
echo 5. 检查缓存文件数量...
docker compose exec backend bash -c "echo '缓存文件统计:'; find /app/qlib_data -name '*cache*' -type d | while read dir; do echo \"$dir: $(find \"$dir\" -type f | wc -l) 文件\"; done"

echo.
echo ========================================
echo 测试完成！
echo ========================================
pause
