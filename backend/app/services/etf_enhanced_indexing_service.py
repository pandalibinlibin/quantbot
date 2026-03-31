"""
ETF Enhanced Indexing Strategy Service

This service implements a capital-efficient enhanced indexing strategy that:
1. Holds an index-tracking ETF as the base position (50%-80% weight)
2. Holds Top-9 alpha stocks for excess return (20%-50% weight)
3. Dynamically adjusts ETF/Alpha weights based on model prediction score spread
4. Outputs actionable trading signals with share quantities and lot sizes

Key Features:
- Total positions: 1 ETF + 9 stocks = 10 positions
- Capital requirement: ~1 million (vs 100 million for full index replication)
- Trading unit support: A-shares (100 shares/lot), US stocks (1 share)
- Score-weighted allocation for alpha stocks
- Daily rebalancing by default
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.config.qlib import qlib_config

logger = logging.getLogger(__name__)


class ETFEnhancedIndexingService:
    """
    ETF Enhanced Indexing Strategy Service

    A capital-efficient enhanced indexing strategy:
    - Holds index ETF for base return
    - Holds Top-9 alpha stocks for excess return
    - Dynamically adjusts ETF/Alpha weights based on model confidence
    - Outputs actionable trading signals with share quantities
    """

    _instance: Optional["ETFEnhancedIndexingService"] = None

    def __new__(cls) -> "ETFEnhancedIndexingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config = self._load_config()
        self._index_config = self._load_index_config()
        self._current_holdings: Dict[str, int] = {}  # symbol -> shares
        self._stock_name_cache: Dict[str, str] = {}  # symbol -> name cache
        self._initialized = True

        # Load persisted holdings on initialization
        self._load_persisted_holdings()
        logger.info("ETFEnhancedIndexingService initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load ETF enhanced indexing configuration from system_config.yaml."""
        qlib_config.reload()
        config = qlib_config._config.get("etf_enhanced_indexing", {})

        return {
            "enabled": config.get("enabled", True),
            "weight_mode": config.get("weight_mode", "dynamic"),
            "alpha_weight_min": config.get("alpha_weight_min", 0.2),
            "alpha_weight_max": config.get("alpha_weight_max", 0.5),
            "max_stocks": config.get("max_stocks", 9),
            "weight_method": config.get("weight_method", "score_weighted"),
            "rebalance_period_days": config.get("rebalance_period_days", 1),
            "output_dir": config.get("output_dir", "/app/data/target_portfolio"),
        }

    def _load_index_config(self) -> Dict[str, Any]:
        """Load index configuration from index_config.yaml."""
        import yaml

        config_path = Path(__file__).parent.parent / "config" / "index_config.yaml"

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load index_config.yaml: {e}")
            return {"indexes": {}}

    def reload_config(self) -> None:
        """Reload configuration from files."""
        self._config = self._load_config()
        self._index_config = self._load_index_config()
        logger.info(f"ETFEnhancedIndexingService config reloaded")

    # ===== Configuration Properties =====

    @property
    def enabled(self) -> bool:
        """Check if ETF enhanced indexing is enabled."""
        return self._config.get("enabled", True)

    @property
    def max_stocks(self) -> int:
        """Get maximum number of alpha stocks (fixed at 9)."""
        return self._config.get("max_stocks", 9)

    @property
    def alpha_weight_min(self) -> float:
        """Get minimum alpha weight (20%)."""
        return self._config.get("alpha_weight_min", 0.2)

    @property
    def alpha_weight_max(self) -> float:
        """Get maximum alpha weight (50%)."""
        return self._config.get("alpha_weight_max", 0.5)

    @property
    def weight_mode(self) -> str:
        """Get weight mode (dynamic or fixed)."""
        return self._config.get("weight_mode", "dynamic")

    @property
    def output_dir(self) -> str:
        """Get output directory for target portfolio files."""
        return self._config.get("output_dir", "/app/data/target_portfolio")

    @property
    def region(self) -> str:
        """Get market region from qlib config."""
        return qlib_config.region

    @property
    def lot_size(self) -> int:
        """Get trading lot size based on market region."""
        return 100 if self.region == "cn" else 1

    @property
    def rebalance_period_days(self) -> int:
        """Get rebalancing period in trading days (1 = daily, 5 = weekly)."""
        return self._config.get("rebalance_period_days", 1)

    # ===== Rebalancing Methods =====

    def is_rebalance_day(self, trade_date: str) -> bool:
        """
        Check if the given trade_date is a rebalancing day.

        Uses Qlib trading calendar to determine if the date falls on a
        rebalancing day based on the configured rebalance_period_days.

        Args:
            trade_date: Date string in YYYY-MM-DD format

        Returns:
            True if it's a rebalancing day, False otherwise
        """
        import qlib
        from qlib.data import D
        import pandas as pd
        import numpy as np
        import os

        period = self.rebalance_period_days
        if period <= 1:
            return True  # Daily rebalancing

        try:
            # Ensure Qlib is initialized
            if not hasattr(qlib, "_default_config") or qlib._default_config is None:
                qlib_data_dir = os.environ.get("QLIB_DATA_DIR", "/app/qlib_data")
                qlib.init(provider_uri=qlib_data_dir, region="cn")

            # Get trading calendar (returns numpy array)
            calendar = D.calendar(freq="day")
            calendar_list = list(calendar)

            # Convert trade_date to datetime
            trade_dt = pd.Timestamp(trade_date)

            # Find index of trade_date in calendar
            try:
                idx = calendar_list.index(trade_dt)
            except ValueError:
                # If not a trading day, not a rebalance day
                logger.debug(f"{trade_date} is not a trading day")
                return False

            # Check if index is divisible by period
            is_rebalance = (idx % period) == 0

            logger.info(
                f"Rebalance check: {trade_date} (day #{idx}), "
                f"period={period}, is_rebalance_day={is_rebalance}"
            )
            return is_rebalance

        except Exception as e:
            logger.warning(f"Failed to check rebalance day: {e}, defaulting to True")
            return True

    def get_next_rebalance_day(self, from_date: str) -> Optional[str]:
        """
        Get the next rebalancing day from the given date (inclusive).

        If from_date is a rebalance day, returns from_date.
        Otherwise returns the next rebalance day.

        Args:
            from_date: Starting date in YYYY-MM-DD format

        Returns:
            Next rebalancing day in YYYY-MM-DD format, or None if error
        """
        import qlib
        from qlib.data import D
        import pandas as pd
        import os

        period = self.rebalance_period_days
        if period <= 1:
            return from_date  # Daily rebalancing, today is rebalance day

        try:
            # Ensure Qlib is initialized
            if not hasattr(qlib, "_default_config") or qlib._default_config is None:
                qlib_data_dir = os.environ.get("QLIB_DATA_DIR", "/app/qlib_data")
                qlib.init(provider_uri=qlib_data_dir, region="cn")

            calendar = D.calendar(freq="day")
            calendar_list = list(calendar)
            from_dt = pd.Timestamp(from_date)

            # Find index of from_date or nearest trading day
            try:
                start_idx = calendar_list.index(from_dt)
            except ValueError:
                # from_date not in calendar, find nearest trading day
                start_idx = None
                # First try to find next trading day
                for i, cal_date in enumerate(calendar_list):
                    if cal_date > from_dt:
                        start_idx = i
                        break

                # If no future trading day found, from_date is after calendar end
                if start_idx is None:
                    # Find the last rebalance day in calendar
                    last_idx = len(calendar_list) - 1
                    last_rebalance_idx = (last_idx // period) * period
                    last_rebalance_date = calendar_list[last_rebalance_idx]

                    # Calculate how many trading days from last_rebalance to calendar end
                    trading_days_after_last_rebalance = last_idx - last_rebalance_idx
                    # Trading days remaining until next rebalance
                    trading_days_to_next = period - trading_days_after_last_rebalance

                    # Estimate calendar days for remaining trading days
                    # Skip weekends: for each 5 trading days, add 2 weekend days
                    def estimate_calendar_days(trading_days: int, start_date) -> int:
                        """Estimate calendar days for given trading days, accounting for weekends."""
                        cal_days = 0
                        remaining = trading_days
                        current = start_date
                        while remaining > 0:
                            current += pd.Timedelta(days=1)
                            cal_days += 1
                            # Skip weekends (Saturday=5, Sunday=6)
                            if current.dayofweek < 5:
                                remaining -= 1
                        return cal_days

                    # Start from calendar end date
                    last_calendar_date = calendar_list[-1]
                    cal_days_to_next = estimate_calendar_days(
                        trading_days_to_next, last_calendar_date
                    )
                    next_rebalance_date = last_calendar_date + pd.Timedelta(
                        days=cal_days_to_next
                    )

                    # If next_rebalance_date is still before from_date, add another period
                    while next_rebalance_date < from_dt:
                        cal_days_for_period = estimate_calendar_days(
                            period, next_rebalance_date
                        )
                        next_rebalance_date += pd.Timedelta(days=cal_days_for_period)

                    logger.info(
                        f"Estimated next rebalance: last_rebalance={last_rebalance_date.date()}, "
                        f"next={next_rebalance_date.date()}"
                    )
                    return (
                        str(next_rebalance_date.date())
                        if hasattr(next_rebalance_date, "date")
                        else str(next_rebalance_date)[:10]
                    )

            # Check if current day is a rebalance day
            if (start_idx % period) == 0:
                # Today is a rebalance day, return NEXT rebalance day (not today)
                next_rebalance_idx = start_idx + period
            else:
                # Find next rebalance day
                next_rebalance_idx = ((start_idx // period) + 1) * period

            if next_rebalance_idx < len(calendar_list):
                next_date = calendar_list[next_rebalance_idx]
                return (
                    str(next_date.date())
                    if hasattr(next_date, "date")
                    else str(next_date)[:10]
                )

            # Calendar doesn't have future dates, estimate based on period
            # Assume 5 trading days per week, calculate approximate date
            days_since_last_rebalance = start_idx % period
            days_to_next = period - days_since_last_rebalance
            if days_to_next == 0:
                days_to_next = (
                    period  # If today is rebalance day, next is in 'period' days
                )

            # Estimate calendar days (roughly 7/5 ratio for trading to calendar days)
            calendar_days = int(days_to_next * 7 / 5) + 1
            last_date = calendar_list[-1]
            estimated_date = last_date + pd.Timedelta(days=calendar_days)
            return (
                str(estimated_date.date())
                if hasattr(estimated_date, "date")
                else str(estimated_date)[:10]
            )

        except Exception as e:
            logger.warning(f"Failed to get next rebalance day: {e}")
            return None

    def get_days_until_rebalance(self, from_date: str) -> int:
        """
        Get the number of trading days until the next rebalancing day.

        Args:
            from_date: Current date in YYYY-MM-DD format

        Returns:
            Number of trading days until next rebalance (0 if today is rebalance day)
        """
        import qlib
        from qlib.data import D
        import pandas as pd
        import os

        period = self.rebalance_period_days
        if period <= 1:
            return 0  # Daily rebalancing

        try:
            # Ensure Qlib is initialized
            if not hasattr(qlib, "_default_config") or qlib._default_config is None:
                qlib_data_dir = os.environ.get("QLIB_DATA_DIR", "/app/qlib_data")
                qlib.init(provider_uri=qlib_data_dir, region="cn")

            calendar = D.calendar(freq="day")
            calendar_list = list(calendar)
            from_dt = pd.Timestamp(from_date)

            # Find the index - if not a trading day, find the next trading day
            try:
                idx = calendar_list.index(from_dt)
            except ValueError:
                # Not a trading day, find the next trading day
                idx = None
                for i, cal_date in enumerate(calendar_list):
                    if cal_date > from_dt:
                        idx = i
                        break
                if idx is None:
                    return 0  # No future trading days found

            days_since_last = idx % period

            if days_since_last == 0:
                return 0  # Next trading day is rebalance day
            return period - days_since_last

        except Exception as e:
            logger.warning(f"Failed to calculate days until rebalance: {e}")
            return 0

    # ===== Index and ETF Methods =====

    def detect_benchmark(self) -> str:
        """
        Auto-detect benchmark index from data configuration.

        Returns:
            str: Detected benchmark index (csi300, csi500, sp500, nasdaq100)
        """
        stock_pool = qlib_config.stock_pool
        region = qlib_config.region

        benchmark_map = {
            "csi300": "csi300",
            "csi500": "csi500",
            "csi800": "csi500",
            "csi1000": "csi1000",
            "dividend": "dividend",
            "sp500": "sp500",
            "nasdaq100": "nasdaq100",
        }

        detected = benchmark_map.get(stock_pool)
        if detected:
            logger.info(
                f"Auto-detected benchmark: {detected} (from stock_pool={stock_pool})"
            )
            return detected

        if region == "us":
            logger.info("Auto-detected benchmark: sp500 (from region=us)")
            return "sp500"
        else:
            logger.info("Auto-detected benchmark: csi300 (default for region=cn)")
            return "csi300"

    def get_etf_code(self, benchmark: str) -> str:
        """
        Get ETF code for the given benchmark index.

        Args:
            benchmark: Benchmark index name (csi300, sp500, etc.)

        Returns:
            ETF code in Qlib format (e.g., SH510300)
        """
        indexes = self._index_config.get("indexes", {})
        index_info = indexes.get(benchmark, {})
        etf_code = index_info.get("etf_code", "")

        if not etf_code:
            # Fallback defaults
            defaults = {
                "csi300": "SH510300",
                "csi500": "SH510500",
                "sp500": "SPY",
                "nasdaq100": "QQQ",
            }
            etf_code = defaults.get(benchmark, "SH510300")
            logger.warning(
                f"ETF code not found for {benchmark}, using default: {etf_code}"
            )

        return etf_code

    def get_etf_name(self, benchmark: str) -> str:
        """
        Get ETF name for the given benchmark index.

        Args:
            benchmark: Benchmark index name

        Returns:
            ETF name (e.g., "沪深300ETF")
        """
        etf_names = {
            "csi300": "沪深300ETF",
            "csi500": "中证500ETF",
            "csi1000": "中证1000ETF",
            "dividend": "红利ETF",
            "sp500": "SPDR S&P 500 ETF",
            "nasdaq100": "Invesco QQQ Trust",
        }
        return etf_names.get(benchmark, f"{benchmark} ETF")

    # ===== Dynamic Weight Calculation =====

    def calculate_dynamic_weights(
        self, scores: Dict[str, float]
    ) -> Tuple[float, float, float]:
        """
        Calculate ETF and Alpha weights based on score spread.

        High score spread → High alpha weight (model confident)
        Low score spread → Low alpha weight (model uncertain)

        Args:
            scores: Dict mapping instrument to prediction score

        Returns:
            Tuple of (etf_weight, alpha_weight, score_spread)
        """
        if not scores or len(scores) < self.max_stocks * 2:
            # Not enough data, use minimum alpha weight
            alpha_weight = self.alpha_weight_min
            return 1.0 - alpha_weight, alpha_weight, 0.0

        sorted_scores = sorted(scores.values(), reverse=True)

        # Calculate spread between top and bottom stocks
        top_avg = np.mean(sorted_scores[: self.max_stocks])
        bottom_avg = np.mean(sorted_scores[-self.max_stocks :])
        score_spread = top_avg - bottom_avg

        # Normalize spread to [0, 1]
        # Assuming typical spread range is [0, 2]
        normalized_spread = np.clip(score_spread / 2.0, 0, 1)

        # Calculate alpha weight: alpha_weight_min ~ alpha_weight_max
        alpha_weight = self.alpha_weight_min + normalized_spread * (
            self.alpha_weight_max - self.alpha_weight_min
        )
        etf_weight = 1.0 - alpha_weight

        logger.info(
            f"Dynamic weights: ETF={etf_weight:.2%}, Alpha={alpha_weight:.2%}, "
            f"spread={score_spread:.4f}"
        )

        return etf_weight, alpha_weight, score_spread

    # ===== Lot Size Rounding =====

    def round_to_lot(self, shares: float) -> int:
        """Round shares down to trading lot size."""
        return (int(shares) // self.lot_size) * self.lot_size

    def calculate_action(
        self, target_shares: int, current_shares: int
    ) -> Tuple[str, int, int]:
        """
        Calculate trading action with lot size rounding.

        Args:
            target_shares: Target number of shares
            current_shares: Current number of shares

        Returns:
            Tuple of (action, action_shares, action_lots)
        """
        diff = target_shares - current_shares

        if diff > 0:
            action_shares = self.round_to_lot(diff)
            action_lots = action_shares // self.lot_size
            return (
                ("buy", action_shares, action_lots)
                if action_shares > 0
                else ("hold", 0, 0)
            )
        elif diff < 0:
            action_shares = self.round_to_lot(abs(diff))
            action_lots = action_shares // self.lot_size
            return (
                ("sell", action_shares, action_lots)
                if action_shares > 0
                else ("hold", 0, 0)
            )
        else:
            return ("hold", 0, 0)

    # ===== Stock Name Service =====

    def get_stock_name(self, symbol: str) -> str:
        """
        Get stock name by symbol from tushare or cache.

        Args:
            symbol: Stock symbol in Qlib format (e.g., "SH600519")

        Returns:
            Stock name (e.g., "贵州茅台") or symbol if not found
        """
        # Check cache first
        if symbol in self._stock_name_cache:
            return self._stock_name_cache[symbol]

        # Try to get name from tushare
        try:
            name = self._fetch_stock_name_from_tushare(symbol)
            if name and name != symbol:
                self._stock_name_cache[symbol] = name
                return name
        except Exception as e:
            logger.debug(f"Failed to fetch name for {symbol}: {e}")

        # Fallback: return symbol
        self._stock_name_cache[symbol] = symbol
        return symbol

    def _fetch_stock_name_from_tushare(self, symbol: str) -> str:
        """
        Fetch stock name from tushare API.

        Args:
            symbol: Stock symbol in Qlib format (e.g., "SH600519")

        Returns:
            Stock name or symbol if not found
        """
        try:
            import tushare as ts
            from app.core.config import settings

            token = getattr(settings, "TUSHARE_TOKEN", None)
            if not token:
                return symbol

            ts.set_token(token)
            pro = ts.pro_api()

            # Convert Qlib format to tushare format: SH600519 -> 600519.SH
            if symbol.startswith("SH"):
                ts_code = f"{symbol[2:]}.SH"
            elif symbol.startswith("SZ"):
                ts_code = f"{symbol[2:]}.SZ"
            else:
                return symbol

            # Query stock basic info
            df = pro.stock_basic(ts_code=ts_code, fields="ts_code,name")
            if df is not None and not df.empty:
                name = df.iloc[0]["name"]
                logger.debug(f"Fetched name for {symbol}: {name}")
                return name

            # Try fund basic for ETFs
            df = pro.fund_basic(ts_code=ts_code, fields="ts_code,name")
            if df is not None and not df.empty:
                name = df.iloc[0]["name"]
                logger.debug(f"Fetched ETF name for {symbol}: {name}")
                return name

        except Exception as e:
            logger.debug(f"Tushare name lookup failed for {symbol}: {e}")

        return symbol

    def _batch_fetch_stock_names(self, symbols: List[str]) -> Dict[str, str]:
        """
        Batch fetch stock names from tushare to reduce API calls.

        Args:
            symbols: List of stock symbols in Qlib format

        Returns:
            Dict mapping symbol to name
        """
        names = {}
        uncached = [s for s in symbols if s not in self._stock_name_cache]

        if not uncached:
            return {s: self._stock_name_cache.get(s, s) for s in symbols}

        try:
            import tushare as ts
            from app.core.config import settings

            token = getattr(settings, "TUSHARE_TOKEN", None)
            if not token:
                return {s: s for s in symbols}

            ts.set_token(token)
            pro = ts.pro_api()

            # Get all stock basic info at once
            df = pro.stock_basic(fields="ts_code,name")
            if df is not None and not df.empty:
                # Build lookup dict: ts_code -> name
                ts_name_map = dict(zip(df["ts_code"], df["name"]))

                for symbol in uncached:
                    # Convert Qlib format to tushare format
                    if symbol.startswith("SH"):
                        ts_code = f"{symbol[2:]}.SH"
                    elif symbol.startswith("SZ"):
                        ts_code = f"{symbol[2:]}.SZ"
                    else:
                        ts_code = None

                    if ts_code and ts_code in ts_name_map:
                        name = ts_name_map[ts_code]
                        self._stock_name_cache[symbol] = name
                        names[symbol] = name
                    else:
                        self._stock_name_cache[symbol] = symbol
                        names[symbol] = symbol

            # Also try to get ETF names
            df_etf = pro.fund_basic(fields="ts_code,name")
            if df_etf is not None and not df_etf.empty:
                etf_name_map = dict(zip(df_etf["ts_code"], df_etf["name"]))
                for symbol in uncached:
                    if symbol in names:
                        continue
                    if symbol.startswith("SH"):
                        ts_code = f"{symbol[2:]}.SH"
                    elif symbol.startswith("SZ"):
                        ts_code = f"{symbol[2:]}.SZ"
                    else:
                        continue
                    if ts_code in etf_name_map:
                        name = etf_name_map[ts_code]
                        self._stock_name_cache[symbol] = name
                        names[symbol] = name

        except Exception as e:
            logger.warning(f"Batch stock name fetch failed: {e}")

        # Return all names (cached + newly fetched)
        return {s: self._stock_name_cache.get(s, s) for s in symbols}

    # ===== Core Portfolio Calculation =====

    def calculate_target_portfolio(
        self,
        signals: pd.DataFrame,
        trade_date: Optional[str] = None,
        total_value: float = 1000000,
        current_holdings: Optional[Dict[str, int]] = None,
        benchmark: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate target portfolio with actionable trading signals.

        Args:
            signals: DataFrame with prediction scores
            trade_date: Trade date (defaults to today)
            total_value: Total portfolio value
            current_holdings: Current holdings (symbol -> shares)
            benchmark: Benchmark index (None = auto-detect)

        Returns:
            Complete portfolio with positions, weights, and trading actions
        """
        if not self.enabled:
            logger.warning("ETF enhanced indexing is disabled")
            return {"positions": [], "summary": {"enabled": False}}

        # Determine trade date
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        # Determine benchmark
        if benchmark is None:
            benchmark = self.detect_benchmark()

        # Extract signals as dict
        signal_dict = self._extract_signals(signals)
        if not signal_dict:
            logger.error("No signals provided")
            return {"positions": [], "summary": {"error": "No signals"}}

        # Use provided holdings or internal state
        if current_holdings is None:
            current_holdings = self._current_holdings.copy()
            logger.info(
                f"Using internal holdings: {len(current_holdings)} positions, "
                f"symbols: {list(current_holdings.keys())[:5]}..."
            )

        # Calculate dynamic weights
        etf_weight, alpha_weight, score_spread = self.calculate_dynamic_weights(
            signal_dict
        )

        # Get ETF info
        etf_code = self.get_etf_code(benchmark)
        etf_name = self.get_etf_name(benchmark)

        # Select top stocks
        sorted_signals = sorted(signal_dict.items(), key=lambda x: x[1], reverse=True)
        top_stocks = sorted_signals[: self.max_stocks]

        # Calculate alpha stock weights (score-weighted)
        total_score = sum(score for _, score in top_stocks)
        if total_score <= 0:
            # Fallback to equal weights
            stock_weights = [
                (symbol, alpha_weight / self.max_stocks) for symbol, _ in top_stocks
            ]
        else:
            stock_weights = [
                (symbol, (score / total_score) * alpha_weight)
                for symbol, score in top_stocks
            ]

        # Get all symbols for batch operations
        all_stock_symbols = [s for s, _ in top_stocks]
        all_symbols = [etf_code] + all_stock_symbols

        # Batch fetch stock names for efficiency
        self._batch_fetch_stock_names(all_stock_symbols)

        # Get latest prices from Qlib data
        prices = self._get_latest_prices(all_symbols)

        # Build positions list
        positions = []

        # ETF position
        etf_price = prices.get(etf_code, 4.0)  # Placeholder
        etf_target_value = total_value * etf_weight
        etf_target_shares = self.round_to_lot(etf_target_value / etf_price)
        etf_current_shares = current_holdings.get(etf_code, 0)
        etf_action, etf_action_shares, etf_action_lots = self.calculate_action(
            etf_target_shares, etf_current_shares
        )

        positions.append(
            {
                "rank": 0,
                "symbol": etf_code,
                "name": etf_name,
                "type": "etf",
                "weight": round(etf_weight, 4),
                "target_value": round(etf_target_value, 2),
                "reference_price": round(etf_price, 4),
                "target_shares": etf_target_shares,
                "current_shares": etf_current_shares,
                "action": etf_action,
                "action_shares": etf_action_shares,
                "action_lots": etf_action_lots,
            }
        )

        # Alpha stock positions
        for rank, (symbol, weight) in enumerate(stock_weights, start=1):
            score = signal_dict.get(symbol, 0.0)
            price = prices.get(symbol, 100.0)  # Placeholder
            target_value = total_value * weight
            target_shares = self.round_to_lot(target_value / price)
            current_shares = current_holdings.get(symbol, 0)
            action, action_shares, action_lots = self.calculate_action(
                target_shares, current_shares
            )

            positions.append(
                {
                    "rank": rank,
                    "symbol": symbol,
                    "name": self.get_stock_name(symbol),
                    "type": "stock",
                    "weight": round(weight, 4),
                    "score": round(score, 4),
                    "target_value": round(target_value, 2),
                    "reference_price": round(price, 4),
                    "target_shares": target_shares,
                    "current_shares": current_shares,
                    "action": action,
                    "action_shares": action_shares,
                    "action_lots": action_lots,
                }
            )

        # Generate SELL signals for holdings not in target portfolio
        target_symbols = set(all_symbols)  # ETF + top stocks
        for symbol, current_shares in current_holdings.items():
            if symbol not in target_symbols and current_shares > 0:
                # This holding needs to be sold (not in new target portfolio)
                price = prices.get(symbol)
                if price is None:
                    # Fetch price for this symbol
                    extra_prices = self._get_latest_prices([symbol])
                    price = extra_prices.get(symbol, 100.0)

                action_lots = current_shares // self.lot_size
                positions.append(
                    {
                        "rank": -1,  # Negative rank indicates exit position
                        "symbol": symbol,
                        "name": self.get_stock_name(symbol),
                        "type": "stock",
                        "weight": 0.0,
                        "score": 0.0,
                        "target_value": 0.0,
                        "reference_price": round(price, 4),
                        "target_shares": 0,
                        "current_shares": current_shares,
                        "action": "sell",
                        "action_shares": current_shares,
                        "action_lots": action_lots,
                    }
                )
                logger.info(
                    f"Generated SELL signal for {symbol}: {current_shares} shares "
                    f"(not in target portfolio)"
                )

        # Build summary
        buy_count = sum(1 for p in positions if p["action"] == "buy")
        sell_count = sum(1 for p in positions if p["action"] == "sell")
        hold_count = sum(1 for p in positions if p["action"] == "hold")

        summary = {
            "total_positions": len(positions),
            "etf_positions": 1,
            "stock_positions": len(positions) - 1,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
        }

        # Build complete output
        signal_for_date = self._get_next_trading_date(trade_date)

        result = {
            "generated_at": datetime.now().isoformat(),
            "trade_date": trade_date,
            "signal_for_date": signal_for_date,
            "total_value": total_value,
            "region": self.region,
            "lot_size": self.lot_size,
            "weights": {
                "etf_weight": round(etf_weight, 4),
                "alpha_weight": round(alpha_weight, 4),
                "score_spread": round(score_spread, 4),
                "weight_mode": self.weight_mode,
            },
            "positions": positions,
            "summary": summary,
        }

        logger.info(
            f"Calculated ETF enhanced portfolio: {len(positions)} positions, "
            f"ETF={etf_weight:.1%}, Alpha={alpha_weight:.1%}"
        )

        return result

    def _extract_signals(self, signals: pd.DataFrame) -> Dict[str, float]:
        """
        Extract signals from DataFrame to dict format.

        Args:
            signals: DataFrame with signals (various formats supported)

        Returns:
            Dict mapping instrument to score
        """
        if signals is None or (isinstance(signals, pd.DataFrame) and signals.empty):
            return {}

        signal_dict = {}

        try:
            # Handle MultiIndex (datetime, instrument)
            if isinstance(signals, pd.DataFrame) and isinstance(
                signals.index, pd.MultiIndex
            ):
                # Get the latest date's signals
                latest_date = signals.index.get_level_values(0).max()
                signals = signals.loc[latest_date]

                # After loc, index should be instrument level
                # But if still MultiIndex or tuple, extract instrument part
                if isinstance(signals.index, pd.MultiIndex):
                    signals = signals.droplevel(0)

            # Helper function to extract clean instrument code
            def extract_instrument(idx) -> str:
                """Extract clean instrument code from various index formats."""
                if isinstance(idx, str):
                    # Convert lowercase to uppercase (sh600519 -> SH600519)
                    upper_idx = idx.upper()
                    if upper_idx.startswith("SH") or upper_idx.startswith("SZ"):
                        return upper_idx
                    return idx
                elif isinstance(idx, tuple):
                    # Handle (datetime, instrument) or (instrument,) tuples
                    for item in idx:
                        if isinstance(item, str):
                            upper_item = item.upper()
                            if upper_item.startswith("SH") or upper_item.startswith(
                                "SZ"
                            ):
                                return upper_item
                    # Fallback: return last string element
                    for item in reversed(idx):
                        if isinstance(item, str):
                            return (
                                item.upper()
                                if item.upper().startswith(("SH", "SZ"))
                                else item
                            )
                    return str(idx[-1]) if idx else str(idx)
                else:
                    result = str(idx)
                    upper_result = result.upper()
                    if upper_result.startswith("SH") or upper_result.startswith("SZ"):
                        return upper_result
                    return result

            # Handle DataFrame with 'score' column
            if isinstance(signals, pd.DataFrame):
                if "score" in signals.columns:
                    for idx, row in signals.iterrows():
                        inst = extract_instrument(idx)
                        signal_dict[inst] = float(row["score"])
                elif len(signals.columns) == 1:
                    col = signals.columns[0]
                    for idx, val in signals[col].items():
                        inst = extract_instrument(idx)
                        signal_dict[inst] = float(val)
            elif isinstance(signals, pd.Series):
                for idx, val in signals.items():
                    inst = extract_instrument(idx)
                    signal_dict[inst] = float(val)

        except Exception as e:
            logger.error(f"Failed to extract signals: {e}")

        logger.info(f"Extracted {len(signal_dict)} signals")
        return signal_dict

    def _get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get latest prices for symbols from Qlib data.

        Args:
            symbols: List of stock symbols in Qlib format (e.g., SZ159919, SH600519)

        Returns:
            Dict mapping symbol to price

        Raises:
            ValueError: If price data cannot be retrieved for any symbol
        """
        prices = {}
        failed_symbols = []

        import qlib
        from qlib.data import D

        # Initialize Qlib if not already done
        if not hasattr(qlib, "_default_config") or qlib._default_config is None:
            import os

            qlib_data_dir = os.environ.get("QLIB_DATA_DIR", "/app/qlib_data")
            qlib.init(provider_uri=qlib_data_dir, region="cn")

        # Use dynamic date range (last 1 year from today)
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        start_time_str = start_date.strftime("%Y-%m-%d")
        end_time_str = end_date.strftime("%Y-%m-%d")

        for symbol in symbols:
            try:
                # Get price data from Qlib - use dynamic date range
                df = D.features(
                    instruments=[symbol],
                    fields=["$close"],
                    start_time=start_time_str,
                    end_time=end_time_str,
                    freq="day",
                )

                if df.empty:
                    failed_symbols.append((symbol, "No data returned from Qlib"))
                    continue

                # DataFrame index is ['instrument', 'datetime']
                # Access data using the correct index order: df.loc[symbol]
                if symbol in df.index.get_level_values("instrument"):
                    # Get data for this symbol - index level 0 is instrument
                    symbol_data = df.loc[symbol, "$close"]
                    if not symbol_data.dropna().empty:
                        latest_price = float(symbol_data.dropna().iloc[-1])
                        if latest_price > 0:
                            prices[symbol] = latest_price
                            logger.debug(f"Price for {symbol}: {latest_price:.2f}")
                        else:
                            failed_symbols.append(
                                (symbol, f"Invalid price: {latest_price}")
                            )
                    else:
                        failed_symbols.append((symbol, "All price values are NaN"))
                else:
                    failed_symbols.append(
                        (symbol, f"Symbol not found in Qlib data index")
                    )

            except Exception as e:
                failed_symbols.append((symbol, str(e)))

        # Log warning for failed symbols but don't raise error
        # This allows the strategy to continue with available data
        if failed_symbols:
            error_details = "; ".join([f"{s}: {err}" for s, err in failed_symbols])
            logger.warning(
                f"Could not get prices for some symbols (skipping): {error_details}"
            )

        # Only raise error if ALL symbols failed
        if not prices:
            raise ValueError(f"Failed to get prices for all symbols")

        return prices

    def _get_next_trading_date(self, date: str) -> str:
        """
        Get the next trading date after the given date.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Next trading date string
        """
        # TODO: Implement actual trading calendar lookup
        # For now, just return the next day
        from datetime import timedelta

        dt = datetime.strptime(date, "%Y-%m-%d")
        next_dt = dt + timedelta(days=1)
        # Skip weekends
        while next_dt.weekday() >= 5:
            next_dt += timedelta(days=1)
        return next_dt.strftime("%Y-%m-%d")

    # ===== Smart Cache =====

    def _calculate_fingerprint(self) -> Dict[str, str]:
        """
        Calculate a fingerprint based on data source and factor configuration.

        The fingerprint includes:
        - data_end_date: Last date in Qlib data
        - factor_hash: Hash of active factor names

        Returns:
            Dict with fingerprint components
        """
        fingerprint = {
            "data_end_date": "",
            "factor_hash": "",
        }

        # Get data end date from Qlib
        try:
            import qlib
            from qlib.data import D
            import os

            # Initialize Qlib if not already done
            if not hasattr(qlib, "_default_config") or qlib._default_config is None:
                qlib_data_dir = os.environ.get("QLIB_DATA_DIR", "/app/qlib_data")
                qlib.init(provider_uri=qlib_data_dir, region="cn")

            calendar = D.calendar(freq="day")
            if calendar is not None and len(calendar) > 0:
                fingerprint["data_end_date"] = str(calendar[-1])[:10]
        except Exception as e:
            logger.warning(f"Failed to get data end date for fingerprint: {e}")

        # Get factor hash from database
        try:
            from sqlmodel import Session, select
            from app.core.db import engine
            from app.models import Factor, FactorStatus

            with Session(engine) as session:
                statement = (
                    select(Factor.name)
                    .where(Factor.status == FactorStatus.ACTIVE)
                    .order_by(Factor.name)
                )
                factor_names = session.exec(statement).all()

                # Create hash of sorted factor names
                factor_str = ",".join(sorted(factor_names))
                fingerprint["factor_hash"] = hashlib.md5(
                    factor_str.encode()
                ).hexdigest()[:8]
        except Exception as e:
            logger.warning(f"Failed to get factor hash for fingerprint: {e}")

        return fingerprint

    def check_cache_valid(
        self, trade_date: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if cached portfolio is valid for the given trade date.

        Cache is valid if:
        1. A recent portfolio file exists (uses latest portfolio, not by date)
        2. Data source has not changed (same data_end_date)
        3. Factors have not changed (same factor_hash)

        Args:
            trade_date: Trade date to check (YYYY-MM-DD) - used for logging only

        Returns:
            Tuple of (is_valid, cached_portfolio_data or None)
        """
        # Load the latest portfolio file (not by date, since trade_date may differ)
        cached_portfolio = self.load_latest_portfolio()

        if cached_portfolio is None:
            logger.info(f"No cached portfolio found for cache check")
            return False, None

        # Get cached fingerprint
        cached_fingerprint = cached_portfolio.get("fingerprint", {})
        if not cached_fingerprint:
            logger.info(f"Cached portfolio has no fingerprint, will recalculate")
            return False, None

        # Calculate current fingerprint
        current_fingerprint = self._calculate_fingerprint()

        # Compare fingerprints
        data_changed = cached_fingerprint.get(
            "data_end_date"
        ) != current_fingerprint.get("data_end_date")
        factor_changed = cached_fingerprint.get(
            "factor_hash"
        ) != current_fingerprint.get("factor_hash")

        if data_changed:
            logger.info(
                f"Data source changed: {cached_fingerprint.get('data_end_date')} -> "
                f"{current_fingerprint.get('data_end_date')}, will recalculate"
            )
            return False, None

        if factor_changed:
            logger.info(
                f"Factors changed: {cached_fingerprint.get('factor_hash')} -> "
                f"{current_fingerprint.get('factor_hash')}, will recalculate"
            )
            return False, None

        logger.info(
            f"Using cached portfolio for {trade_date} "
            f"(data_end_date={current_fingerprint.get('data_end_date')}, "
            f"factor_hash={current_fingerprint.get('factor_hash')})"
        )

        # Update positions with current holdings to recalculate actions
        # This ensures that if holdings were already applied, actions show as HOLD
        positions = cached_portfolio.get("positions", [])
        current_holdings = self._current_holdings.copy()

        for pos in positions:
            symbol = pos.get("symbol", "")
            target_shares = pos.get("target_shares", 0)
            # Update current_shares from actual holdings
            pos["current_shares"] = current_holdings.get(symbol, 0)
            # Recalculate action based on updated current_shares
            action, action_shares, action_lots = self.calculate_action(
                target_shares, pos["current_shares"]
            )
            pos["action"] = action
            pos["action_shares"] = action_shares
            pos["action_lots"] = action_lots

        # Update summary counts
        buy_count = sum(1 for p in positions if p.get("action") == "buy")
        sell_count = sum(1 for p in positions if p.get("action") == "sell")
        hold_count = sum(1 for p in positions if p.get("action") == "hold")

        if "summary" in cached_portfolio:
            cached_portfolio["summary"]["buy_count"] = buy_count
            cached_portfolio["summary"]["sell_count"] = sell_count
            cached_portfolio["summary"]["hold_count"] = hold_count

        return True, cached_portfolio

    # ===== Portfolio Persistence =====

    def save_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        date: Optional[str] = None,
    ) -> str:
        """
        Save target portfolio to JSON file with fingerprint.

        Args:
            portfolio_data: Portfolio data from calculate_target_portfolio()
            date: Date string for filename (defaults to today)

        Returns:
            Path to saved file
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Add fingerprint for cache validation
        portfolio_data["fingerprint"] = self._calculate_fingerprint()

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"etf_enhanced_{date}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(portfolio_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved ETF enhanced portfolio to {output_file}")
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
        output_file = output_dir / f"etf_enhanced_{date}.json"

        if not output_file.exists():
            logger.warning(f"Portfolio file not found: {output_file}")
            return None

        try:
            with open(output_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
            return None

    def load_latest_portfolio(self) -> Optional[Dict[str, Any]]:
        """
        Load the most recent portfolio file.

        Returns:
            Portfolio data or None if no portfolio files exist
        """
        output_dir = Path(self.output_dir)

        if not output_dir.exists():
            logger.warning(f"Portfolio directory not found: {output_dir}")
            return None

        # Find all portfolio files and sort by date (newest first)
        portfolio_files = sorted(output_dir.glob("etf_enhanced_*.json"), reverse=True)

        if not portfolio_files:
            logger.warning("No portfolio files found")
            return None

        latest_file = portfolio_files[0]
        logger.info(f"Loading latest portfolio from: {latest_file}")

        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load latest portfolio: {e}")
            return None

    def update_holdings(self, holdings: Dict[str, int]) -> None:
        """
        Update current holdings.

        Args:
            holdings: Dict mapping symbol to number of shares
        """
        self._current_holdings = holdings.copy()
        logger.info(f"Updated holdings: {len(holdings)} positions")

    def _get_holdings_file_path(self) -> Path:
        """Get the path to the holdings persistence file."""
        output_dir = Path(self.output_dir)
        return output_dir / "current_holdings.json"

    def _load_persisted_holdings(self) -> None:
        """Load holdings from persistence file on startup."""
        holdings_file = self._get_holdings_file_path()
        if holdings_file.exists():
            try:
                with open(holdings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._current_holdings = data.get("holdings", {})
                logger.info(
                    f"Loaded persisted holdings: {len(self._current_holdings)} positions "
                    f"(last updated: {data.get('updated_at', 'unknown')})"
                )
            except Exception as e:
                logger.warning(f"Failed to load persisted holdings: {e}")
                self._current_holdings = {}
        else:
            logger.info("No persisted holdings found, starting with empty portfolio")

    def save_holdings(
        self,
        holdings: Optional[Dict[str, int]] = None,
        trade_date: Optional[str] = None,
    ) -> str:
        """
        Save current holdings to persistence file.

        Args:
            holdings: Holdings to save (uses internal state if None)
            trade_date: Trade date for tracking (defaults to today)

        Returns:
            Path to saved file
        """
        if holdings is not None:
            self._current_holdings = holdings.copy()

        if trade_date is None:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        holdings_file = self._get_holdings_file_path()
        data = {
            "holdings": self._current_holdings,
            "updated_at": datetime.now().isoformat(),
            "trade_date": trade_date,  # Track which date these holdings are for
            "position_count": len(self._current_holdings),
        }

        with open(holdings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Saved holdings to {holdings_file}: {len(self._current_holdings)} positions (trade_date={trade_date})"
        )
        return str(holdings_file)

    def apply_trades_to_holdings(
        self, positions: List[Dict[str, Any]], trade_date: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Apply trades from target portfolio to update holdings.

        This simulates executing the trades and updates the internal holdings state.
        Should be called after the user confirms they have executed the trades.

        Note: Multiple executions on the same day are safe - the holdings will
        be updated to the latest target positions each time.

        Args:
            positions: List of position dicts from calculate_target_portfolio
            trade_date: Trade date for tracking

        Returns:
            Updated holdings dict
        """
        # Build new holdings from target positions (replace, not merge)
        new_holdings = {}
        for pos in positions:
            symbol = pos.get("symbol", "")
            target_shares = pos.get("target_shares", 0)
            if symbol and target_shares > 0:
                new_holdings[symbol] = target_shares

        # Replace current holdings with new holdings
        self._current_holdings = new_holdings

        # Persist the updated holdings with trade date
        self.save_holdings(trade_date=trade_date)

        logger.info(
            f"Applied trades, new holdings: {len(self._current_holdings)} positions"
        )
        return self._current_holdings.copy()


def get_etf_enhanced_indexing_service() -> ETFEnhancedIndexingService:
    """Get the singleton ETFEnhancedIndexingService instance."""
    return ETFEnhancedIndexingService()


def create_etf_enhanced_indexing_strategy(
    signal: pd.DataFrame,
    total_value: float = 1000000,
):
    """
    Create an ETF Enhanced Indexing Strategy for Qlib Backtest.

    This function creates a strategy that uses the ETFEnhancedIndexingService
    to calculate target weights based on model predictions.

    Args:
        signal: DataFrame with prediction scores (MultiIndex: datetime, instrument)
        total_value: Total portfolio value

    Returns:
        A Qlib-compatible strategy object
    """
    from qlib.contrib.strategy import WeightStrategyBase

    class _ETFEnhancedIndexingStrategy(WeightStrategyBase):
        """Internal ETF enhanced indexing strategy class."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._service = get_etf_enhanced_indexing_service()
            self._total_value = total_value

        def generate_target_weight_position(
            self, score, current, trade_start_time, trade_end_time
        ):
            """
            Generate target weight position based on ETF enhanced indexing.

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

            # Calculate dynamic weights
            etf_weight, alpha_weight, _ = self._service.calculate_dynamic_weights(
                signal_dict
            )

            # Get ETF code
            benchmark = self._service.detect_benchmark()
            etf_code = self._service.get_etf_code(benchmark)

            # Select top stocks
            sorted_signals = sorted(
                signal_dict.items(), key=lambda x: x[1], reverse=True
            )
            top_stocks = sorted_signals[: self._service.max_stocks]

            # Calculate weights
            target_weights = {}

            # ETF weight
            target_weights[etf_code] = etf_weight

            # Alpha stock weights (score-weighted)
            total_score = sum(s for _, s in top_stocks)
            if total_score > 0:
                for symbol, s in top_stocks:
                    target_weights[symbol] = (s / total_score) * alpha_weight
            else:
                # Equal weights fallback
                for symbol, _ in top_stocks:
                    target_weights[symbol] = alpha_weight / len(top_stocks)

            return target_weights

    return _ETFEnhancedIndexingStrategy(signal=signal)
