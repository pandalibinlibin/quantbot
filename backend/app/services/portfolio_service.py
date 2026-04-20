"""
Portfolio Service - 投资组合管理服务
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path

from app.core.config import settings
from app.services.index_components_service import get_index_components_service
from app.services.data_service import get_data_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PortfolioResult:
    """投资组合计算结果"""
    success: bool
    portfolio_weights: Dict[str, float] = None
    error: str = None
    metadata: Dict[str, Any] = None


@dataclass
class CurrentPosition:
    """当前持仓信息"""
    instrument: str
    weight: float
    last_update: datetime


class PortfolioService:
    """投资组合服务"""
    
    def __init__(self):
        self.index_service = get_index_components_service()
        self.data_service = get_data_service()
        self.current_positions_file = Path("data/current_positions.json")
        
    async def calculate_latest_portfolio(self) -> PortfolioResult:
        """
        计算最新投资组合权重
        
        基于最新市场数据计算目标投资组合权重分配
        """
        try:
            logger.info("开始计算最新投资组合...")
            
            # 1. 获取ETF池
            etf_list = self.index_service.get_components("etf_universe")
            if not etf_list:
                return PortfolioResult(
                    success=False,
                    error="无法获取ETF列表"
                )
            
            logger.info(f"获取到{len(etf_list)}只ETF")
            
            # 2. 获取最新数据 (简化版本 - 等权重策略)
            # TODO: 后续集成Qlib的因子计算和模型预测
            portfolio_weights = await self._calculate_equal_weight_portfolio(etf_list)
            
            # 3. 添加现金比例
            portfolio_weights["CASH"] = 0.02  # 2%现金
            
            # 4. 归一化权重
            total_weight = sum(portfolio_weights.values())
            if total_weight > 0:
                portfolio_weights = {
                    k: v / total_weight 
                    for k, v in portfolio_weights.items()
                }
            
            logger.info(f"计算完成，共{len(portfolio_weights)}个持仓")
            
            return PortfolioResult(
                success=True,
                portfolio_weights=portfolio_weights,
                metadata={
                    "calculation_time": datetime.now().isoformat(),
                    "etf_count": len(etf_list),
                    "strategy": "equal_weight",
                    "total_positions": len(portfolio_weights)
                }
            )
            
        except Exception as e:
            logger.error(f"计算投资组合失败: {str(e)}")
            return PortfolioResult(
                success=False,
                error=str(e)
            )
    
    async def _calculate_equal_weight_portfolio(
        self, 
        etf_list: List[str],
        max_positions: int = 50
    ) -> Dict[str, float]:
        """
        计算等权重投资组合 (简化版本)
        
        Args:
            etf_list: ETF代码列表
            max_positions: 最大持仓数量
        
        Returns:
            权重字典
        """
        # 简化策略：选择前50只ETF，等权重分配
        selected_etfs = etf_list[:max_positions]
        weight_per_etf = 1.0 / len(selected_etfs)
        
        portfolio = {
            etf: weight_per_etf 
            for etf in selected_etfs
        }
        
        logger.info(f"等权重策略：选择{len(selected_etfs)}只ETF，每只权重{weight_per_etf:.3f}")
        
        return portfolio
    
    async def get_current_weights(self) -> Dict[str, float]:
        """
        获取当前持仓权重
        
        Returns:
            当前持仓权重字典
        """
        try:
            # TODO: 从数据库或文件读取当前持仓
            # 这里返回模拟的当前持仓
            current_weights = {
                "SH510300": 0.15,
                "SH510310": 0.12,
                "SZ159919": 0.10,
                "SH588000": 0.08,
                "SH510050": 0.07,
                "SH511360": 0.05,
                "CASH": 0.03
            }
            
            # 补充其他权重为0的ETF
            etf_list = self.index_service.get_components("etf_universe")
            for etf in etf_list:
                if etf not in current_weights:
                    current_weights[etf] = 0.0
            
            logger.info(f"获取当前持仓：{len(current_weights)}个位置")
            return current_weights
            
        except Exception as e:
            logger.error(f"获取当前持仓失败: {str(e)}")
            return {}
    
    async def update_current_positions(
        self, 
        new_weights: Dict[str, float]
    ) -> bool:
        """
        更新当前持仓权重
        
        Args:
            new_weights: 新的权重分配
        
        Returns:
            是否更新成功
        """
        try:
            # TODO: 保存到数据库或文件
            logger.info(f"更新持仓权重：{len(new_weights)}个位置")
            return True
            
        except Exception as e:
            logger.error(f"更新持仓失败: {str(e)}")
            return False


# 全局服务实例
_portfolio_service = None


def get_portfolio_service() -> PortfolioService:
    """获取投资组合服务实例"""
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service
