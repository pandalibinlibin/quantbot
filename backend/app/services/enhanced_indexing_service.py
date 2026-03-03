"""
Enhanced Indexing Strategy Service

This service implements a simplified enhanced indexing strategy that:
1. Tracks a benchmark index (CSI300, CSI500, SP500, NASDAQ100)
2. Adjusts weights based on model prediction scores
3. Controls tracking error via max_deviation parameter
4. Outputs target portfolio weights for execution layer (VeighNa/LEAN)

The strategy does NOT handle execution timing - that is delegated to external systems.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.config.qlib import qlib_config

logger = logging.getLogger(__name__)


class EnhancedIndexingService:
    """
    Enhanced Indexing Strategy Service

    Implements a simplified enhanced indexing algorithm that:
    - Takes model prediction scores as input
    - Adjusts benchmark weights based on scores
    - Controls deviation from benchmark
    - Outputs target portfolio weights
    """

    _instance: Optional["EnhancedIndexingService"] = None

    def __new__(cls) -> "EnhancedIndexingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config = self._load_config()
        self._initialized = True
        logger.info("EnhancedIndexingService initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load enhanced indexing configuration from system_config.yaml."""
        qlib_config.reload()
        config = qlib_config._config.get("enhanced_indexing", {})

        return {
            "enabled": config.get("enabled", True),
            "max_deviation": config.get("max_deviation", 0.02),
            "min_weight": config.get("min_weight", 0.001),
            "benchmark": config.get("benchmark", "auto"),
            "output_dir": config.get("output_dir", "/app/data/target_portfolio"),
        }

    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._config = self._load_config()
        logger.info(f"EnhancedIndexingService config reloaded: {self._config}")

    @property
    def enabled(self) -> bool:
        """Check if enhanced indexing is enabled."""
        return self._config.get("enabled", True)

    @property
    def max_deviation(self) -> float:
        """Get maximum deviation from benchmark weight."""
        return self._config.get("max_deviation", 0.02)

    @property
    def min_weight(self) -> float:
        """Get minimum weight threshold."""
        return self._config.get("min_weight", 0.001)

    @property
    def benchmark(self) -> str:
        """Get benchmark index setting."""
        return self._config.get("benchmark", "auto")

    @property
    def output_dir(self) -> str:
        """Get output directory for target portfolio files."""
        return self._config.get("output_dir", "/app/data/target_portfolio")

    def detect_benchmark(self) -> str:
        """
        Auto-detect benchmark index from data configuration.

        Returns:
            str: Detected benchmark index (csi300, csi500, sp500, nasdaq100)
        """
        stock_pool = qlib_config.stock_pool
        region = qlib_config.region

        # Map stock_pool to benchmark
        benchmark_map = {
            "csi300": "csi300",
            "csi500": "csi500",
            "csi800": "csi500",  # Use CSI500 as proxy for CSI800
            "sp500": "sp500",
            "nasdaq100": "nasdaq100",
        }

        detected = benchmark_map.get(stock_pool)

        if detected:
            logger.info(
                f"Auto-detected benchmark: {detected} (from stock_pool={stock_pool})"
            )
            return detected

        # Fallback based on region
        if region == "us":
            logger.info("Auto-detected benchmark: sp500 (from region=us)")
            return "sp500"
        else:
            logger.info("Auto-detected benchmark: csi300 (default for region=cn)")
            return "csi300"

    def get_benchmark_weights(
        self,
        benchmark: str,
        date: Optional[str] = None,
        instrument_list: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Get benchmark index constituent weights.

        For now, this returns equal weights for all stocks in the universe.
        In production, this should fetch actual index weights from:
        - Qlib data ($csi300_weight, $csi500_weight fields)
        - External data sources (Wind, Bloomberg, etc.)

        Args:
            benchmark: Benchmark index name
            date: Date for weights (optional, defaults to latest)
            instrument_list: Optional list of instruments (if provided, use this instead of querying Qlib)

        Returns:
            Dict mapping instrument to weight
        """
        # If instrument_list is provided, use it directly
        if instrument_list:
            n_stocks = len(instrument_list)
            if n_stocks == 0:
                logger.warning("Empty instrument list provided")
                return {}

            equal_weight = 1.0 / n_stocks
            weights = {inst: equal_weight for inst in instrument_list}
            logger.info(
                f"Using {n_stocks} stocks from signals with equal weights for benchmark {benchmark}"
            )
            return weights

        # Try to get instruments from Qlib
        try:
            from qlib.data import D

            # Always use "all" market since instruments are stored in all.txt
            # The actual benchmark (csi300, csi500, etc.) is just for display purposes
            instruments = D.instruments(market="all")
            qlib_instrument_list = D.list_instruments(
                instruments=instruments, as_list=True
            )

            if not qlib_instrument_list:
                logger.warning(
                    f"No instruments found for benchmark {benchmark} in Qlib"
                )
                return {}

            # For now, use equal weights
            # TODO: Fetch actual index weights from Qlib data or external source
            n_stocks = len(qlib_instrument_list)
            equal_weight = 1.0 / n_stocks

            weights = {inst: equal_weight for inst in qlib_instrument_list}

            logger.info(
                f"Got {n_stocks} stocks for benchmark {benchmark} with equal weights from Qlib"
            )
            return weights

        except Exception as e:
            logger.warning(f"Failed to get benchmark weights from Qlib: {e}")
            return {}

    def calculate_target_portfolio(
        self,
        signals: pd.DataFrame,
        benchmark: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate target portfolio weights using enhanced indexing strategy.

        Args:
            signals: DataFrame with 'instrument' and 'score' columns,
                     or MultiIndex DataFrame with (datetime, instrument) index
            benchmark: Benchmark index (None = use config)
            date: Target date (None = use latest)

        Returns:
            Dict containing:
            - target_portfolio: List of portfolio items
            - summary: Portfolio summary statistics
        """
        if not self.enabled:
            logger.warning("Enhanced indexing is disabled")
            return {"target_portfolio": [], "summary": {"enabled": False}}

        # Determine benchmark
        if benchmark is None:
            benchmark = self.benchmark
        if benchmark == "auto":
            benchmark = self.detect_benchmark()

        # Extract signals as dict first (we need this for fallback)
        signal_dict = self._extract_signals(signals)

        if not signal_dict:
            logger.error("No signals provided")
            return {"target_portfolio": [], "summary": {"error": "No signals"}}

        # Get benchmark weights - try Qlib first, fallback to signals
        benchmark_weights = self.get_benchmark_weights(benchmark, date)
        if not benchmark_weights:
            # Fallback: use signals' instruments with equal weights
            logger.info("Using signals instruments as benchmark fallback")
            benchmark_weights = self.get_benchmark_weights(
                benchmark, date, instrument_list=list(signal_dict.keys())
            )

        if not benchmark_weights:
            logger.error("Failed to get benchmark weights")
            return {
                "target_portfolio": [],
                "summary": {"error": "No benchmark weights"},
            }

        # Calculate target weights
        target_portfolio = self._calculate_weights(
            signals=signal_dict,
            benchmark_weights=benchmark_weights,
            max_deviation=self.max_deviation,
            min_weight=self.min_weight,
        )

        # Build summary
        summary = self._build_summary(
            target_portfolio=target_portfolio,
            benchmark=benchmark,
            date=date,
        )

        return {
            "target_portfolio": target_portfolio,
            "summary": summary,
        }

    def _extract_signals(self, signals: pd.DataFrame) -> Dict[str, float]:
        """
        Extract signals from DataFrame to dict format.

        Args:
            signals: DataFrame with signals (various formats supported)

        Returns:
            Dict mapping instrument to score
        """
        if signals is None or signals.empty:
            return {}

        signal_dict = {}

        try:
            # Handle MultiIndex (datetime, instrument)
            if isinstance(signals.index, pd.MultiIndex):
                # Get the latest date's signals
                latest_date = signals.index.get_level_values(0).max()
                signals = signals.loc[latest_date]

            # Handle DataFrame with 'score' column
            if isinstance(signals, pd.DataFrame):
                if "score" in signals.columns:
                    for idx, row in signals.iterrows():
                        inst = idx if isinstance(idx, str) else str(idx)
                        signal_dict[inst] = float(row["score"])
                elif len(signals.columns) == 1:
                    # Single column, use it as score
                    col = signals.columns[0]
                    for idx, val in signals[col].items():
                        inst = idx if isinstance(idx, str) else str(idx)
                        signal_dict[inst] = float(val)
            elif isinstance(signals, pd.Series):
                for idx, val in signals.items():
                    inst = idx if isinstance(idx, str) else str(idx)
                    signal_dict[inst] = float(val)

        except Exception as e:
            logger.error(f"Failed to extract signals: {e}")

        logger.info(f"Extracted {len(signal_dict)} signals")
        return signal_dict

    def _calculate_weights(
        self,
        signals: Dict[str, float],
        benchmark_weights: Dict[str, float],
        max_deviation: float,
        min_weight: float,
    ) -> List[Dict[str, Any]]:
        """
        Calculate target weights using simplified enhanced indexing algorithm.

        Algorithm:
        1. Normalize prediction scores to [-1, 1]
        2. Calculate deviation = normalized_score * max_deviation
        3. Calculate target_weight = benchmark_weight + deviation
        4. Ensure weight >= 0
        5. Normalize to ensure total weight = 100%

        Args:
            signals: Dict mapping instrument to prediction score
            benchmark_weights: Dict mapping instrument to benchmark weight
            max_deviation: Maximum deviation from benchmark weight
            min_weight: Minimum weight threshold

        Returns:
            List of portfolio items with weights and metadata
        """
        universe = set(benchmark_weights.keys())

        if not universe:
            return []

        # Get scores for universe (default to 0 for missing)
        scores = {inst: signals.get(inst, 0.0) for inst in universe}

        # Normalize scores to [-1, 1]
        score_values = list(scores.values())
        score_mean = np.mean(score_values)
        score_std = np.std(score_values)

        if score_std > 0:
            normalized_scores = {
                inst: np.clip((score - score_mean) / score_std, -1, 1)
                for inst, score in scores.items()
            }
        else:
            normalized_scores = {inst: 0.0 for inst in scores}

        # Calculate target weights
        raw_weights = {}
        for inst in universe:
            bench_weight = benchmark_weights[inst]
            norm_score = normalized_scores[inst]
            deviation = norm_score * max_deviation
            target_weight = max(0, bench_weight + deviation)
            raw_weights[inst] = target_weight

        # Normalize to sum = 1
        total = sum(raw_weights.values())
        if total > 0:
            target_weights = {inst: w / total for inst, w in raw_weights.items()}
        else:
            target_weights = {inst: 0.0 for inst in universe}

        # Apply min_weight threshold
        for inst in target_weights:
            if target_weights[inst] < min_weight:
                target_weights[inst] = 0.0

        # Re-normalize after threshold
        total = sum(target_weights.values())
        if total > 0:
            target_weights = {inst: w / total for inst, w in target_weights.items()}

        # Build portfolio items
        portfolio = []
        rank = 0

        # Sort by target weight descending
        sorted_items = sorted(target_weights.items(), key=lambda x: x[1], reverse=True)

        for inst, target_weight in sorted_items:
            # Include all stocks, even those with 0 weight
            rank += 1
            bench_weight = benchmark_weights[inst]
            deviation = target_weight - bench_weight
            score = signals.get(inst, 0.0)

            # Determine action
            if deviation > 0.0001:
                action = "超配"
            elif deviation < -0.0001:
                action = "低配"
            else:
                action = "持平"

            portfolio.append(
                {
                    "rank": rank,
                    "instrument": inst,
                    "benchmark_weight": round(bench_weight, 6),
                    "score": round(score, 6),
                    "target_weight": round(target_weight, 6),
                    "deviation": round(deviation, 6),
                    "deviation_pct": f"{deviation * 100:+.2f}%",
                    "action": action,
                }
            )

        logger.info(f"Calculated target portfolio with {len(portfolio)} positions")
        return portfolio

    def _build_summary(
        self,
        target_portfolio: List[Dict[str, Any]],
        benchmark: str,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build portfolio summary statistics."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        total_weight = sum(item["target_weight"] for item in target_portfolio)
        overweight_count = sum(
            1 for item in target_portfolio if item["action"] == "超配"
        )
        underweight_count = sum(
            1 for item in target_portfolio if item["action"] == "低配"
        )
        neutral_count = sum(1 for item in target_portfolio if item["action"] == "持平")

        benchmark_names = {
            "csi300": "沪深300",
            "csi500": "中证500",
            "sp500": "标普500",
            "nasdaq100": "纳斯达克100",
        }

        return {
            "benchmark": benchmark,
            "benchmark_name": benchmark_names.get(benchmark, benchmark),
            "total_stocks": len(target_portfolio),
            "total_weight": round(total_weight, 6),
            "overweight_count": overweight_count,
            "underweight_count": underweight_count,
            "neutral_count": neutral_count,
            "max_deviation": self.max_deviation,
            "generated_at": datetime.now().isoformat(),
            "target_date": date,
        }

    def save_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        date: Optional[str] = None,
    ) -> str:
        """
        Save target portfolio to JSON file.

        Args:
            portfolio_data: Portfolio data from calculate_target_portfolio()
            date: Date string for filename (defaults to today)

        Returns:
            Path to saved file
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Ensure output directory exists
        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build output data
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "config": {
                "max_deviation": self.max_deviation,
                "min_weight": self.min_weight,
                "benchmark": portfolio_data.get("summary", {}).get(
                    "benchmark", "unknown"
                ),
            },
            "portfolio": portfolio_data.get("target_portfolio", []),
            "summary": portfolio_data.get("summary", {}),
        }

        # Save to file
        output_file = output_dir / f"{date}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved target portfolio to {output_file}")
        return str(output_file)

    def load_portfolio(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Load target portfolio from JSON file.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Portfolio data or None if not found
        """
        output_dir = Path(self.output_dir)
        output_file = output_dir / f"{date}.json"

        if not output_file.exists():
            logger.warning(f"Portfolio file not found: {output_file}")
            return None

        try:
            with open(output_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
            return None

    def get_latest_portfolio(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest saved portfolio.

        Returns:
            Latest portfolio data or None if no portfolios exist
        """
        output_dir = Path(self.output_dir)

        if not output_dir.exists():
            return None

        # Find latest file
        files = sorted(output_dir.glob("*.json"), reverse=True)

        if not files:
            return None

        try:
            with open(files[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load latest portfolio: {e}")
            return None


def get_enhanced_indexing_service() -> EnhancedIndexingService:
    """Get the singleton EnhancedIndexingService instance."""
    return EnhancedIndexingService()


def create_enhanced_indexing_strategy(
    signal: pd.DataFrame,
    max_deviation: float = 0.02,
    min_weight: float = 0,
):
    """
    Create an Enhanced Indexing Strategy for Qlib Backtest.

    This function creates a strategy that uses the EnhancedIndexingService
    to calculate target weights based on model predictions and benchmark weights.

    Args:
        signal: DataFrame with prediction scores (MultiIndex: datetime, instrument)
        max_deviation: Maximum deviation from benchmark weight
        min_weight: Minimum weight threshold

    Returns:
        A Qlib-compatible strategy object
    """
    from qlib.contrib.strategy import WeightStrategyBase

    class _EnhancedIndexingStrategy(WeightStrategyBase):
        """Internal enhanced indexing strategy class."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._ei_service = get_enhanced_indexing_service()
            self._max_deviation = max_deviation
            self._min_weight = min_weight

        def generate_target_weight_position(
            self, score, current, trade_start_time, trade_end_time
        ):
            """
            Generate target weight position based on enhanced indexing.

            Args:
                score: Prediction scores for current trading period
                current: Current position
                trade_start_time: Start time of trading period
                trade_end_time: End time of trading period

            Returns:
                Dict mapping instrument to target weight
            """
            if score is None or len(score) == 0:
                return {}

            # Convert score to dict
            signal_dict = {}
            if isinstance(score, pd.Series):
                for inst in score.index:
                    val = score.loc[inst]
                    if isinstance(val, pd.Series):
                        val = val.iloc[0]
                    signal_dict[inst] = float(val)
            elif isinstance(score, pd.DataFrame):
                for inst in score.index:
                    val = score.loc[inst]
                    if isinstance(val, pd.Series):
                        val = val.iloc[0]
                    signal_dict[inst] = float(val)

            if not signal_dict:
                return {}

            # Get benchmark weights
            benchmark_weights = self._ei_service.get_benchmark_weights(
                benchmark="auto",
                date=str(trade_start_time)[:10] if trade_start_time else None,
                instrument_list=list(signal_dict.keys()),
            )

            if not benchmark_weights:
                # Fallback to equal weights
                n = len(signal_dict)
                return {inst: 1.0 / n for inst in signal_dict}

            # Calculate target weights using enhanced indexing logic
            universe = set(benchmark_weights.keys())
            scores = {inst: signal_dict.get(inst, 0.0) for inst in universe}

            # Normalize scores to [-1, 1]
            score_values = list(scores.values())
            score_mean = np.mean(score_values)
            score_std = np.std(score_values)

            if score_std > 0:
                normalized_scores = {
                    inst: np.clip((s - score_mean) / score_std, -1, 1)
                    for inst, s in scores.items()
                }
            else:
                normalized_scores = {inst: 0.0 for inst in scores}

            # Calculate target weights
            raw_weights = {}
            for inst in universe:
                bench_weight = benchmark_weights[inst]
                norm_score = normalized_scores[inst]
                deviation = norm_score * self._max_deviation
                target_weight = max(0, bench_weight + deviation)
                raw_weights[inst] = target_weight

            # Normalize to sum = 1
            total = sum(raw_weights.values())
            if total > 0:
                target_weights = {inst: w / total for inst, w in raw_weights.items()}
            else:
                target_weights = {inst: 0.0 for inst in universe}

            # Apply min_weight threshold
            for inst in target_weights:
                if target_weights[inst] < self._min_weight:
                    target_weights[inst] = 0.0

            # Re-normalize after threshold
            total = sum(target_weights.values())
            if total > 0:
                target_weights = {inst: w / total for inst, w in target_weights.items()}

            return target_weights

    return _EnhancedIndexingStrategy(signal=signal)
