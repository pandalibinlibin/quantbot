"""
Update Data API Routes - 数据准备和预处理

功能:
- 数据检查和增量下载
- 数据预处理 (EMA去噪、Surprise、ZScore)
- 因子计算 (Alpha158)
- 模型训练和预测
- 为Run Signal和Run Backtest提供就绪的数据
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.services.data_update_service import get_data_update_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/run")
async def update_data(
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    执行数据更新 - 完整的数据准备workflow
    
    完整流程:
    1. 检查数据新鲜度
    2. 增量数据下载 (如需要)
    3. 数据预处理 (EMA去噪、Surprise、ZScore)
    4. 因子计算 (Alpha158)
    5. 模型训练 (如需要)
    6. 模型预测
    7. 标记数据就绪状态
    
    目的: 为Run Signal和Run Backtest提供最新的数据和预测结果
    """
    try:
        logger.info(f"用户 {current_user.email} 开始执行数据更新")
        
        # 获取数据更新服务
        data_update_service = get_data_update_service()
        
        # 执行完整的数据更新workflow
        result = await data_update_service.run_full_update_workflow()
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"数据更新失败: {result.error}"
            )
        
        logger.info("数据更新workflow执行完成")
        
        return {
            "success": True,
            "message": "数据更新完成",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "workflow_steps": result.completed_steps,
                "data_range": {
                    "start_date": result.data_start_date,
                    "end_date": result.data_end_date
                },
                "statistics": {
                    "etf_count": result.etf_count,
                    "records_processed": result.records_processed,
                    "factors_calculated": result.factors_count,
                    "model_trained": result.model_trained,
                    "predictions_generated": result.predictions_count
                },
                "execution_time": {
                    "total_seconds": result.total_duration_seconds,
                    "data_download": result.download_duration_seconds,
                    "preprocessing": result.preprocessing_duration_seconds,
                    "factor_calculation": result.factor_duration_seconds,
                    "model_training": result.training_duration_seconds,
                    "prediction": result.prediction_duration_seconds
                }
            }
        }
        
    except Exception as e:
        logger.error(f"数据更新执行失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"数据更新执行失败: {str(e)}"
        )


@router.get("/status")
async def get_data_status(
    current_user = Depends(deps.get_current_active_user),
):
    """
    获取数据就绪状态
    
    返回:
    - 数据是否最新
    - 最后更新时间
    - 模型预测是否可用
    - 数据覆盖范围
    """
    try:
        data_update_service = get_data_update_service()
        status = await data_update_service.get_data_status()
        
        return {
            "success": True,
            "data": {
                "is_ready": status.is_ready,
                "last_update": status.last_update_time.isoformat() if status.last_update_time else None,
                "data_freshness": status.data_freshness_hours,
                "model_ready": status.model_ready,
                "predictions_available": status.predictions_available,
                "data_range": {
                    "start_date": status.data_start_date,
                    "end_date": status.data_end_date
                },
                "etf_count": status.etf_count,
                "next_update_recommended": status.next_update_recommended.isoformat() if status.next_update_recommended else None
            }
        }
        
    except Exception as e:
        logger.error(f"获取数据状态失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取数据状态失败: {str(e)}"
        )
