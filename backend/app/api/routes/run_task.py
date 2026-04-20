"""
Run Signal API Routes - 实时信号生成和投资组合更新

功能边界:
- 只影响实盘投资组合状态和所有非backtest页面
- 独立的完整workflow，可触发数据下载、预处理、因子计算
- 与Run Backtest完全独立，互不依赖
"""

from datetime import datetime
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.services.portfolio_service import get_portfolio_service
from app.services.email_service import get_email_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/run")
async def run_task(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    """
    执行Run Signal - 实时信号生成和投资组合更新

    功能边界: 只影响实盘投资组合状态，不影响backtest页面

    完整workflow:
    1. 检查数据新鲜度，必要时触发增量下载
    2. 数据预处理 (EMA去噪、Surprise、ZScore)
    3. 因子计算 (Alpha158等)
    4. 模型预测和信号生成
    5. 投资组合权重计算
    6. 对比当前持仓，生成买卖信号
    7. 更新全局投资组合状态
    8. 发送邮件通知
    9. 影响所有非backtest页面的显示
    """
    try:
        logger.info(f"用户 {current_user.email} 开始执行Run Task")

        # 1. 获取服务
        portfolio_service = get_portfolio_service()
        email_service = get_email_service()

        # 2. 计算最新投资组合权重
        logger.info("计算最新投资组合权重...")
        latest_portfolio_result = await portfolio_service.calculate_latest_portfolio()

        if not latest_portfolio_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"计算投资组合失败: {latest_portfolio_result.error}",
            )

        latest_portfolio = latest_portfolio_result.portfolio_weights

        # 3. 获取当前持仓权重
        logger.info("获取当前持仓权重...")
        current_weights = await portfolio_service.get_current_weights()

        # 4. 计算权重变化
        logger.info("计算权重变化...")
        changes = calculate_weight_changes(current_weights, latest_portfolio)
        sell_changes = changes["sell"]
        buy_changes = changes["buy"]

        # 5. 发送邮件通知
        logger.info("发送邮件通知...")
        email_data = {
            "timestamp": datetime.now(),
            "sell_changes": sell_changes,
            "buy_changes": buy_changes,
            "latest_portfolio": latest_portfolio,
            "user_email": current_user.email,
        }

        email_result = await email_service.send_run_task_notification(email_data)

        if not email_result.success:
            logger.warning(f"邮件发送失败: {email_result.error}")

        # 6. 构建响应
        logger.info(
            f"Run Task执行完成，权重变化: 买入{len(buy_changes)}只，卖出{len(sell_changes)}只"
        )

        return {
            "success": True,
            "message": "Run Task执行成功",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "sell_changes": sell_changes,
                "buy_changes": buy_changes,
                "latest_portfolio": dict(
                    sorted(latest_portfolio.items(), key=lambda x: x[1], reverse=True)
                ),
                "summary": {
                    "total_positions": len(latest_portfolio),
                    "sell_count": len(sell_changes),
                    "buy_count": len(buy_changes),
                    "cash_ratio": latest_portfolio.get("CASH", 0.0),
                },
            },
            "email_sent": email_result.success,
            "email_message": (
                email_result.message if email_result.success else email_result.error
            ),
        }

    except Exception as e:
        logger.error(f"Run Task执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Run Task执行失败: {str(e)}")


def calculate_weight_changes(
    current_weights: Dict[str, float],
    new_weights: Dict[str, float],
    threshold: float = 0.001,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    计算权重变化

    Args:
        current_weights: 当前持仓权重
        new_weights: 新的目标权重
        threshold: 变化阈值

    Returns:
        包含买入和卖出变化的字典
    """
    sell_changes = {}
    buy_changes = {}

    # 获取所有涉及的ETF
    all_etfs = set(current_weights.keys()) | set(new_weights.keys())

    for etf in all_etfs:
        current_weight = current_weights.get(etf, 0.0)
        new_weight = new_weights.get(etf, 0.0)
        change = new_weight - current_weight

        if abs(change) > threshold:
            change_info = {
                "from": round(current_weight, 3),
                "to": round(new_weight, 3),
                "change": round(change, 3),
            }

            if change < 0:  # 减持/卖出
                sell_changes[etf] = change_info
            else:  # 增持/买入
                buy_changes[etf] = change_info

    return {"sell": sell_changes, "buy": buy_changes}
