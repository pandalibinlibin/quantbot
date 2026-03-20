"""
Signal Export Service - Export trading signals for VeighNa

This service generates trading signal files in JSON format for VeighNa to consume.
It combines ETF holdings with top-ranked alpha stocks based on model predictions.

Educational Notes:
- Reads target portfolio from EnhancedIndexingService
- Reads index configuration from IndexComponentsService
- Generates hybrid strategy signals (ETF + Alpha stocks)
- Outputs JSON files to shared directory for VeighNa
"""

import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from app.core.config import settings
from app.services.index_components_service import get_index_components_service

logger = logging.getLogger(__name__)


class SignalExportService:
    """
    Service for exporting trading signals to VeighNa.

    Strategy:
    - ETF: Fixed weight allocation (e.g., 70%)
    - Alpha stocks: Top-N stocks from model predictions (e.g., 30%)
    - Weight normalization: Ensure total weight = 100%
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        etf_weight: float = 0.7,
        alpha_weight: float = 0.3,
        max_stocks: int = 10,
    ):
        """
        Initialize the service.

        Args:
            output_dir: Directory for signal files, defaults to settings.SIGNAL_OUTPUT_DIR
            etf_weight: Weight allocation for ETF (default: 0.7 = 70%)
            alpha_weight: Weight allocation for alpha stocks (default: 0.3 = 30%)
            max_stocks: Maximum number of alpha stocks to hold (default: 10)

        Educational Notes:
        - etf_weight + alpha_weight should equal 1.0
        - max_stocks controls portfolio concentration
        - Smaller max_stocks = higher concentration, higher risk
        """
        self.output_dir = output_dir or settings.SIGNAL_OUTPUT_DIR
        self.etf_weight = etf_weight
        self.alpha_weight = alpha_weight
        self.max_stocks = max_stocks

        # Validate weights
        if abs(etf_weight + alpha_weight - 1.0) > 0.001:
            raise ValueError(
                f"etf_weight ({etf_weight}) + alpha_weight ({alpha_weight}) "
                f"must equal 1.0"
            )

        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        logger.info(
            f"SignalExportService initialized: "
            f"ETF={etf_weight:.1%}, Alpha={alpha_weight:.1%}, "
            f"MaxStocks={max_stocks}, OutputDir={self.output_dir}"
        )

    def export_signals(
        self,
        portfolio_data: Dict[str, Any],
        index_name: Optional[str] = None,
        trade_date: Optional[str] = None,
    ) -> str:
        """
        Export trading signals to JSON file.

        Args:
            portfolio_data: Target portfolio from EnhancedIndexingService
            index_name: Index identifier (defaults to active index)
            trade_date: Trading date (defaults to today)

        Returns:
            Path to exported signal file

        Educational Notes:
        - Reads target_portfolio and summary from portfolio_data
        - Selects Top-N stocks by score
        - Scales stock weights to alpha_weight range
        - Adds ETF position with etf_weight
        - Validates total weight = 100%
        """
        # Get index configuration
        index_service = get_index_components_service()
        if index_name is None:
            index_name = index_service.get_active_index()

        index_config = index_service.get_index_config(index_name)

        # Determine trade date
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        # Extract portfolio data
        # Note: EnhancedIndexingService saves data under 'portfolio' key
        target_portfolio = portfolio_data.get("portfolio", [])
        summary = portfolio_data.get("summary", {})

        if not target_portfolio:
            logger.warning("Empty target portfolio, generating ETF-only signal")
            return self._export_etf_only_signal(index_config, index_name, trade_date)

        # Generate signal positions
        positions = self._generate_positions(
            target_portfolio=target_portfolio,
            etf_code=index_config.get("etf_code"),
        )

        # Build signal data
        signal_data = {
            "generated_at": datetime.now().isoformat(),
            "trade_date": trade_date,
            "index": index_name,
            "index_config": {
                "name": index_config.get("name"),
                "name_en": index_config.get("name_en"),
                "benchmark_code": index_config.get("benchmark_code"),
                "etf_code": index_config.get("etf_code"),
            },
            "strategy": {
                "etf_weight": self.etf_weight,
                "alpha_weight": self.alpha_weight,
                "max_stocks": self.max_stocks,
            },
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "etf_positions": sum(1 for p in positions if p["type"] == "etf"),
                "stock_positions": sum(1 for p in positions if p["type"] == "stock"),
                "total_weight": sum(p["weight"] for p in positions),
                "portfolio_summary": summary,
            },
        }

        # Validate total weight
        total_weight = signal_data["summary"]["total_weight"]
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                f"Total weight {total_weight:.4f} deviates from 1.0, "
                f"this may indicate a calculation error"
            )

        # Save to file
        output_file = Path(self.output_dir) / f"{trade_date}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(signal_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Exported signal to {output_file}: "
            f"{len(positions)} positions, total_weight={total_weight:.4f}"
        )

        return str(output_file)

    def _generate_positions(
        self,
        target_portfolio: List[Dict[str, Any]],
        etf_code: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate position list for signal file.

        Args:
            target_portfolio: List of portfolio items from EnhancedIndexingService
            etf_code: ETF symbol code

        Returns:
            List of position dictionaries

        Educational Notes:
        - Method A: Proportional scaling of original weights
        - Selects Top-N stocks by score (descending)
        - Scales their weights to fit alpha_weight allocation
        - Adds ETF position with etf_weight
        """
        positions = []

        # Add ETF position
        positions.append(
            {
                "symbol": etf_code,
                "type": "etf",
                "weight": round(self.etf_weight, 6),
                "action": "buy",
            }
        )

        # Select Top-N stocks by score
        # Sort by score descending
        sorted_portfolio = sorted(
            target_portfolio,
            key=lambda x: x.get("score", 0),
            reverse=True,
        )

        top_stocks = sorted_portfolio[: self.max_stocks]

        if not top_stocks:
            logger.warning("No stocks selected for alpha pool")
            return positions

        # Calculate scaling factor for weights
        # Original weights sum
        original_weight_sum = sum(item.get("target_weight", 0) for item in top_stocks)

        if original_weight_sum <= 0:
            logger.warning("Original weight sum is zero, using equal weights")
            # Fallback to equal weights
            stock_weight = self.alpha_weight / len(top_stocks)
            for item in top_stocks:
                # Support both "instrument" (Enhanced Indexing) and "symbol" (ETF Enhanced Indexing)
                symbol = item.get("symbol") or item.get("instrument")
                positions.append(
                    {
                        "symbol": symbol,
                        "type": "stock",
                        "weight": round(stock_weight, 6),
                        "score": round(item.get("score", 0), 6),
                        "rank": item.get("rank", 0),
                        "action": "buy",
                    }
                )
        else:
            # Scale weights proportionally
            scaling_factor = self.alpha_weight / original_weight_sum

            for item in top_stocks:
                original_weight = item.get("target_weight", 0)
                scaled_weight = original_weight * scaling_factor
                # Support both "instrument" (Enhanced Indexing) and "symbol" (ETF Enhanced Indexing)
                symbol = item.get("symbol") or item.get("instrument")

                positions.append(
                    {
                        "symbol": symbol,
                        "type": "stock",
                        "weight": round(scaled_weight, 6),
                        "score": round(item.get("score", 0), 6),
                        "rank": item.get("rank", 0),
                        "original_weight": round(original_weight, 6),
                        "action": "buy",
                    }
                )

            logger.info(
                f"Selected {len(top_stocks)} stocks, "
                f"original_weight_sum={original_weight_sum:.4f}, "
                f"scaling_factor={scaling_factor:.4f}"
            )

        return positions

    def _export_etf_only_signal(
        self,
        index_config: Dict[str, Any],
        index_name: str,
        trade_date: str,
    ) -> str:
        """
        Export ETF-only signal when no stocks are available.

        Args:
            index_config: Index configuration
            index_name: Index identifier
            trade_date: Trading date

        Returns:
            Path to exported signal file
        """
        signal_data = {
            "generated_at": datetime.now().isoformat(),
            "trade_date": trade_date,
            "index": index_name,
            "index_config": {
                "name": index_config.get("name"),
                "name_en": index_config.get("name_en"),
                "benchmark_code": index_config.get("benchmark_code"),
                "etf_code": index_config.get("etf_code"),
            },
            "strategy": {
                "etf_weight": 1.0,
                "alpha_weight": 0.0,
                "max_stocks": 0,
            },
            "positions": [
                {
                    "symbol": index_config.get("etf_code"),
                    "type": "etf",
                    "weight": 1.0,
                    "action": "buy",
                }
            ],
            "summary": {
                "total_positions": 1,
                "etf_positions": 1,
                "stock_positions": 0,
                "total_weight": 1.0,
                "note": "ETF-only signal due to empty target portfolio",
            },
        }

        output_file = Path(self.output_dir) / f"{trade_date}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(signal_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported ETF-only signal to {output_file}")
        return str(output_file)


# Singleton instance
_service_instance: Optional[SignalExportService] = None


def get_signal_export_service(
    etf_weight: float = 0.7,
    alpha_weight: float = 0.3,
    max_stocks: int = 10,
) -> SignalExportService:
    """
    Get singleton instance of SignalExportService.

    Args:
        etf_weight: Weight allocation for ETF (default: 0.7)
        alpha_weight: Weight allocation for alpha stocks (default: 0.3)
        max_stocks: Maximum number of alpha stocks (default: 10)

    Returns:
        SignalExportService instance

    Educational Notes:
    - Singleton pattern ensures consistent configuration
    - Parameters only apply on first initialization
    - Subsequent calls return the same instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SignalExportService(
            etf_weight=etf_weight,
            alpha_weight=alpha_weight,
            max_stocks=max_stocks,
        )
    return _service_instance
