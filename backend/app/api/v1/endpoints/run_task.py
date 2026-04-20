"""
Run Task API - 实时投资组合状态查看
"""

from datetime import datetime
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.services.portfolio_service import get_portfolio_service
from app.services.email_service import get_email_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class RunTaskResponse:
    """Run Task响应模型"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.sell_changes: Dict[str, Dict[str, float]] = {}
        self.buy_changes: Dict[str, Dict[str, float]] = {}
        self.latest_portfolio: Dict[str, float] = {}
        self.success = False
        self.message = ""


@router.post("/run", response_model=dict)
async def run_task(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    执行Run Task - 获取最新投资组合状态
    
    功能:
    1. 获取最新市场数据
    2. 计算最新投资组合权重
    3. 对比当前持仓，生成买卖信号
    4. 发送邮件通知
    5. 返回权重变化信息
    """
    try:
        logger.info("开始执行Run Task")
        response = RunTaskResponse()
        
        # 1. 获取服务
        portfolio_service = get_portfolio_service()
        email_service = get_email_service()
        
        # 2. 计算最新投资组合权重
        logger.info("计算最新投资组合权重...")
        latest_portfolio_result = await portfolio_service.calculate_latest_portfolio()
        
        if not latest_portfolio_result.success:
            raise HTTPException(
                status_code=500, 
                detail=f"计算投资组合失败: {latest_portfolio_result.error}"
            )
        
        response.latest_portfolio = latest_portfolio_result.portfolio_weights
        
        # 3. 获取当前持仓权重
        logger.info("获取当前持仓权重...")
        current_weights = await portfolio_service.get_current_weights()
        
        # 4. 计算权重变化
        logger.info("计算权重变化...")
        changes = calculate_weight_changes(current_weights, response.latest_portfolio)
        response.sell_changes = changes["sell"]
        response.buy_changes = changes["buy"]
        
        # 5. 发送邮件通知
        logger.info("发送邮件通知...")
        email_data = {
            "timestamp": response.timestamp,
            "sell_changes": response.sell_changes,
            "buy_changes": response.buy_changes,
            "latest_portfolio": response.latest_portfolio,
            "user_email": current_user.email
        }
        
        email_result = await email_service.send_run_task_notification(email_data)
        
        if not email_result.success:
            logger.warning(f"邮件发送失败: {email_result.error}")
        
        # 6. 构建响应
        response.success = True
        response.message = "Run Task执行成功"
        
        logger.info(f"Run Task执行完成，权重变化: 买入{len(response.buy_changes)}只，卖出{len(response.sell_changes)}只")
        
        return {
            "success": response.success,
            "message": response.message,
            "timestamp": response.timestamp.isoformat(),
            "data": {
                "sell_changes": response.sell_changes,
                "buy_changes": response.buy_changes,
                "latest_portfolio": dict(sorted(
                    response.latest_portfolio.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )),
                "summary": {
                    "total_positions": len(response.latest_portfolio),
                    "sell_count": len(response.sell_changes),
                    "buy_count": len(response.buy_changes),
                    "cash_ratio": response.latest_portfolio.get("CASH", 0.0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Run Task执行失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Run Task执行失败: {str(e)}"
        )


def calculate_weight_changes(
    current_weights: Dict[str, float], 
    new_weights: Dict[str, float],
    threshold: float = 0.001
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
                "change": round(change, 3)
            }
            
            if change < 0:  # 减持/卖出
                sell_changes[etf] = change_info
            else:  # 增持/买入
                buy_changes[etf] = change_info
    
    return {
        "sell": sell_changes,
        "buy": buy_changes
    }
