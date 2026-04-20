"""
Data Update Service - 数据更新和预处理服务

负责完整的数据准备workflow:
1. 数据检查和增量下载
2. 数据预处理
3. 因子计算
4. 模型训练和预测
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

from app.services.index_components_service import get_index_components_service
from app.services.online_serving_service import get_online_serving_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DataUpdateResult:
    """数据更新结果"""
    success: bool
    completed_steps: List[str] = None
    data_start_date: str = None
    data_end_date: str = None
    etf_count: int = 0
    records_processed: int = 0
    factors_count: int = 0
    model_trained: bool = False
    predictions_count: int = 0
    total_duration_seconds: float = 0.0
    download_duration_seconds: float = 0.0
    preprocessing_duration_seconds: float = 0.0
    factor_duration_seconds: float = 0.0
    training_duration_seconds: float = 0.0
    prediction_duration_seconds: float = 0.0
    error: str = None


@dataclass
class DataStatus:
    """数据状态"""
    is_ready: bool
    last_update_time: Optional[datetime] = None
    data_freshness_hours: float = 0.0
    model_ready: bool = False
    predictions_available: bool = False
    data_start_date: str = None
    data_end_date: str = None
    etf_count: int = 0
    next_update_recommended: Optional[datetime] = None


class DataUpdateService:
    """数据更新服务"""
    
    def __init__(self):
        self.index_service = get_index_components_service()
        self.online_service = get_online_serving_service()
        
    async def run_full_update_workflow(self) -> DataUpdateResult:
        """
        执行完整的数据更新workflow
        
        Returns:
            数据更新结果
        """
        start_time = time.time()
        result = DataUpdateResult(success=False)
        completed_steps = []
        
        try:
            logger.info("开始执行完整数据更新workflow...")
            
            # 步骤1: 检查数据新鲜度
            logger.info("步骤1: 检查数据新鲜度...")
            data_status = await self.get_data_status()
            completed_steps.append("数据状态检查")
            
            # 步骤2: 获取ETF列表
            logger.info("步骤2: 获取ETF列表...")
            etf_list = self.index_service.get_components("etf_universe")
            result.etf_count = len(etf_list)
            completed_steps.append(f"ETF列表获取 ({result.etf_count}只)")
            
            # 步骤3: 数据下载和更新 (模拟)
            download_start = time.time()
            logger.info("步骤3: 数据下载和更新...")
            await self._simulate_data_download(etf_list)
            result.download_duration_seconds = time.time() - download_start
            completed_steps.append("数据下载完成")
            
            # 步骤4: 数据预处理
            preprocessing_start = time.time()
            logger.info("步骤4: 数据预处理 (EMA去噪、Surprise、ZScore)...")
            await self._simulate_data_preprocessing()
            result.preprocessing_duration_seconds = time.time() - preprocessing_start
            completed_steps.append("数据预处理完成")
            
            # 步骤5: 因子计算
            factor_start = time.time()
            logger.info("步骤5: 因子计算 (Alpha158)...")
            result.factors_count = await self._simulate_factor_calculation()
            result.factor_duration_seconds = time.time() - factor_start
            completed_steps.append(f"因子计算完成 ({result.factors_count}个因子)")
            
            # 步骤6: 模型训练 (如需要)
            training_start = time.time()
            logger.info("步骤6: 检查模型状态...")
            model_needs_training = await self._check_model_needs_training()
            if model_needs_training:
                logger.info("执行模型训练...")
                await self._simulate_model_training()
                result.model_trained = True
                completed_steps.append("模型训练完成")
            else:
                logger.info("模型无需重新训练")
                completed_steps.append("模型状态检查 (无需训练)")
            result.training_duration_seconds = time.time() - training_start
            
            # 步骤7: 模型预测
            prediction_start = time.time()
            logger.info("步骤7: 生成模型预测...")
            result.predictions_count = await self._simulate_model_prediction()
            result.prediction_duration_seconds = time.time() - prediction_start
            completed_steps.append(f"模型预测完成 ({result.predictions_count}条预测)")
            
            # 完成
            result.total_duration_seconds = time.time() - start_time
            result.completed_steps = completed_steps
            result.data_start_date = "2024-01-01"  # 模拟数据范围
            result.data_end_date = datetime.now().strftime("%Y-%m-%d")
            result.records_processed = result.etf_count * 252  # 模拟一年的交易日数据
            result.success = True
            
            logger.info(f"数据更新workflow完成，总耗时: {result.total_duration_seconds:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"数据更新workflow失败: {str(e)}")
            result.error = str(e)
            result.completed_steps = completed_steps
            result.total_duration_seconds = time.time() - start_time
            return result
    
    async def get_data_status(self) -> DataStatus:
        """
        获取数据状态
        
        Returns:
            数据状态信息
        """
        try:
            # 模拟数据状态检查
            now = datetime.now()
            last_update = now - timedelta(hours=2)  # 模拟2小时前更新
            
            status = DataStatus(
                is_ready=True,
                last_update_time=last_update,
                data_freshness_hours=2.0,
                model_ready=True,
                predictions_available=True,
                data_start_date="2024-01-01",
                data_end_date=now.strftime("%Y-%m-%d"),
                etf_count=166,
                next_update_recommended=now + timedelta(hours=22)  # 建议22小时后更新
            )
            
            return status
            
        except Exception as e:
            logger.error(f"获取数据状态失败: {str(e)}")
            return DataStatus(
                is_ready=False,
                etf_count=0
            )
    
    async def _simulate_data_download(self, etf_list: List[str]):
        """模拟数据下载过程"""
        # 模拟下载延迟
        await self._async_sleep(1.0)
        logger.info(f"模拟下载{len(etf_list)}只ETF的最新数据")
    
    async def _simulate_data_preprocessing(self):
        """模拟数据预处理过程"""
        await self._async_sleep(0.5)
        logger.info("模拟数据预处理: EMA去噪、Surprise计算、ZScore标准化")
    
    async def _simulate_factor_calculation(self) -> int:
        """模拟因子计算过程"""
        await self._async_sleep(1.5)
        logger.info("模拟Alpha158因子计算")
        return 158  # Alpha158因子数量
    
    async def _check_model_needs_training(self) -> bool:
        """检查模型是否需要重新训练"""
        # 模拟检查逻辑：如果数据更新时间超过7天，则需要重新训练
        return False  # 模拟不需要训练
    
    async def _simulate_model_training(self):
        """模拟模型训练过程"""
        await self._async_sleep(2.0)
        logger.info("模拟模型训练过程")
    
    async def _simulate_model_prediction(self) -> int:
        """模拟模型预测过程"""
        await self._async_sleep(0.8)
        logger.info("模拟生成模型预测结果")
        return 166 * 20  # 模拟166只ETF，每只20天的预测
    
    async def _async_sleep(self, seconds: float):
        """异步睡眠 (模拟处理时间)"""
        import asyncio
        await asyncio.sleep(seconds)


# 全局服务实例
_data_update_service = None


def get_data_update_service() -> DataUpdateService:
    """获取数据更新服务实例"""
    global _data_update_service
    if _data_update_service is None:
        _data_update_service = DataUpdateService()
    return _data_update_service
