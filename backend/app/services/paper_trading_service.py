"""
Paper Trading Service

This service manages paper trading (simulated trading) workflow:
- Generate trading plans based on signals (percentage-based)
- Track virtual portfolio positions
- Execute simulated trades
- Record trade history
- Calculate performance metrics

Key Design:
- Trading plans use PERCENTAGES instead of absolute quantities
- This ensures consistency between paper trading and real trading
- Sell orders: sell X% of current position (usually 100%)
- Buy orders: allocate X% of total assets to this stock (target_weight)

The paper trading uses TopkDropoutStrategy to generate trading decisions
based on the signals from OnlineManager.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from app.config.qlib import qlib_config
from app.services.online_serving_service import get_online_serving_service

logger = logging.getLogger(__name__)

# Paper trading state file path
PAPER_TRADING_DIR = Path(qlib_config.qlib_data_path).parent / "paper_trading"
PORTFOLIO_FILE = PAPER_TRADING_DIR / "portfolio.json"
TRADES_FILE = PAPER_TRADING_DIR / "trades.json"
DAILY_RECORDS_FILE = PAPER_TRADING_DIR / "daily_records.json"
TRADING_STARTED_FILE = (
    PAPER_TRADING_DIR / "trading_started.json"
)  # Track if trading has started


class PaperTradingService:
    """
    Paper Trading Service

    Manages simulated trading based on Online Serving signals.
    """

    def __init__(self):
        """Initialize the Paper Trading service."""
        self.logger = logger
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure paper trading directories exist."""
        PAPER_TRADING_DIR.mkdir(parents=True, exist_ok=True)

    def _load_portfolio(self) -> Dict[str, Any]:
        """Load portfolio from file."""
        if PORTFOLIO_FILE.exists():
            try:
                with open(PORTFOLIO_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load portfolio: {e}")

        # Default portfolio
        return {
            "cash": qlib_config.initial_cash,
            "positions": {},  # {instrument: {"shares": int, "avg_cost": float}}
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def _save_portfolio(self, portfolio: Dict[str, Any]):
        """Save portfolio to file."""
        portfolio["updated_at"] = datetime.now().isoformat()
        try:
            with open(PORTFOLIO_FILE, "w") as f:
                json.dump(portfolio, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save portfolio: {e}")

    def _load_trades(self) -> List[Dict[str, Any]]:
        """Load trade history from file."""
        if TRADES_FILE.exists():
            try:
                with open(TRADES_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load trades: {e}")
        return []

    def _save_trades(self, trades: List[Dict[str, Any]]):
        """Save trade history to file."""
        try:
            with open(TRADES_FILE, "w") as f:
                json.dump(trades, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save trades: {e}")

    def _load_daily_records(self) -> List[Dict[str, Any]]:
        """Load daily records from file."""
        if DAILY_RECORDS_FILE.exists():
            try:
                with open(DAILY_RECORDS_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load daily records: {e}")
        return []

    def _save_daily_records(self, records: List[Dict[str, Any]]):
        """Save daily records to file."""
        try:
            with open(DAILY_RECORDS_FILE, "w") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save daily records: {e}")

    def get_portfolio(self) -> Dict[str, Any]:
        """
        Get current portfolio status.

        Returns:
            Portfolio with cash, positions, and total value
        """
        portfolio = self._load_portfolio()

        # Calculate position values using current market prices
        total_position_value = 0.0
        position_details = []

        # Fetch current prices from Qlib for accurate valuation
        position_instruments = list(portfolio.get("positions", {}).keys())
        current_prices = (
            self._get_latest_prices(position_instruments)
            if position_instruments
            else {}
        )

        for instrument, pos in portfolio.get("positions", {}).items():
            shares = pos.get("shares", 0)
            avg_cost = pos.get("avg_cost", 0.0)
            current_price = current_prices.get(instrument)
            if current_price is not None:
                current_value = shares * current_price
            else:
                # Fallback to avg_cost if no current price available
                logger.warning(
                    f"No current price for {instrument}, using avg_cost for valuation"
                )
                current_value = shares * avg_cost
                current_price = avg_cost
            total_position_value += current_value
            position_details.append(
                {
                    "instrument": instrument,
                    "shares": shares,
                    "avg_cost": avg_cost,
                    "current_price": current_price,
                    "current_value": current_value,
                }
            )

        total_value = portfolio.get("cash", 0) + total_position_value

        return {
            "success": True,
            "cash": portfolio.get("cash", 0),
            "positions": position_details,
            "position_count": len(position_details),
            "total_position_value": total_position_value,
            "total_value": total_value,
            "created_at": portfolio.get("created_at"),
            "updated_at": portfolio.get("updated_at"),
        }

    def _get_latest_prices(self, instruments: List[str]) -> Dict[str, float]:
        """
        Get latest prices for instruments from Qlib data.

        Args:
            instruments: List of instrument codes (e.g., "SH600000", "SZ000001")

        Returns:
            Dict mapping instrument to latest close price
        """
        prices = {}

        if not instruments:
            return prices

        try:
            from qlib.data import D

            # Convert instrument format: SH600000 -> sh600000 (lowercase for Qlib)
            qlib_instruments = []
            instrument_map = {}  # Map qlib format back to original
            for inst in instruments:
                # Qlib uses lowercase format: sh600000, sz000001
                qlib_inst = inst.lower()
                qlib_instruments.append(qlib_inst)
                instrument_map[qlib_inst] = inst

            # Get latest close prices from Qlib
            try:
                df = D.features(
                    qlib_instruments,
                    fields=["$close"],
                    start_time=None,  # Will use available data
                    end_time=None,
                    freq="day",
                )

                if df is not None and not df.empty:
                    # Get the latest price for each instrument
                    for qlib_inst in qlib_instruments:
                        try:
                            # Filter for this instrument and get latest close
                            inst_data = df.xs(qlib_inst, level="instrument")
                            if not inst_data.empty:
                                latest_close = inst_data["$close"].dropna().iloc[-1]
                                original_inst = instrument_map[qlib_inst]
                                prices[original_inst] = float(latest_close)
                        except (KeyError, IndexError):
                            pass
            except Exception as e:
                logger.warning(f"Failed to fetch prices from Qlib: {e}")

        except ImportError:
            logger.warning("Qlib not available for price fetching")
        except Exception as e:
            logger.warning(f"Error fetching prices: {e}")

        # Log missing prices (do not fill with fake values)
        for inst in instruments:
            if inst not in prices:
                logger.warning(f"Could not fetch price for {inst} from Qlib")

        return prices

    def _is_trading_started(self) -> bool:
        """Check if paper trading has been started (at least one trade executed)."""
        return TRADING_STARTED_FILE.exists()

    def _mark_trading_started(self):
        """Mark that paper trading has started."""
        try:
            with open(TRADING_STARTED_FILE, "w") as f:
                json.dump({"started_at": datetime.now().isoformat()}, f)
        except Exception as e:
            self.logger.error(f"Failed to mark trading started: {e}")

    def get_trading_plan(
        self,
        date: Optional[str] = None,
        topk: int = 50,
        n_drop: int = 5,
        slippage: float = 0.001,
    ) -> Dict[str, Any]:
        """
        Generate a percentage-based trading plan (public API).

        Returns empty plan if trading hasn't started yet.
        Always includes last_executed_trades if available.
        """
        # Always load last executed trades (even if Online Serving not initialized)
        last_executed_trades = self._get_last_executed_trades()

        # Check if trading has started - if not, return empty plan with last executed trades
        if not self._is_trading_started():
            return {
                "success": False,
                "error": "Paper trading not started. Click 'Execute Trades' to start.",
                "last_executed_trades": last_executed_trades,
            }

        result = self._generate_trading_plan(date, topk, n_drop, slippage)

        # Ensure last_executed_trades is always included
        if not result.get("last_executed_trades"):
            result["last_executed_trades"] = last_executed_trades

        return result

    def _get_last_executed_trades(self) -> Dict[str, Any]:
        """Get last executed trades from trades.json."""
        all_trades = self._load_trades()
        last_executed_sells = []
        last_executed_buys = []

        if all_trades:
            # Get the latest trade date
            latest_trade_date = max(t.get("date", "") for t in all_trades)
            # Filter trades for the latest date
            for t in all_trades:
                if t.get("date") == latest_trade_date:
                    if t.get("action") == "SELL":
                        last_executed_sells.append(
                            {
                                "instrument": t.get("instrument"),
                                "direction": "SELL",
                                "shares": t.get("shares"),
                                "price": t.get("price"),
                                "value": t.get("value"),
                                "sell_pct": t.get("sell_pct"),
                                "executed_at": t.get("executed_at"),
                            }
                        )
                    elif t.get("action") == "BUY":
                        last_executed_buys.append(
                            {
                                "instrument": t.get("instrument"),
                                "direction": "BUY",
                                "shares": t.get("shares"),
                                "price": t.get("price"),
                                "value": t.get("value"),
                                "target_weight": t.get("target_weight"),
                                "executed_at": t.get("executed_at"),
                            }
                        )

        return {
            "sells": last_executed_sells,
            "buys": last_executed_buys,
            "sell_count": len(last_executed_sells),
            "buy_count": len(last_executed_buys),
        }

    def _generate_trading_plan(
        self,
        date: Optional[str] = None,
        topk: int = 50,
        n_drop: int = 5,
        slippage: float = 0.001,
    ) -> Dict[str, Any]:
        """
        Internal method to generate a percentage-based trading plan.

        This method:
        1. Gets signals from OnlineManager
        2. Filters signals for the specified date (or latest)
        3. Applies TopkDropout strategy logic
        4. Returns trading plan with percentages (not absolute quantities)

        Key Design:
        - Sell orders: sell_pct (percentage of position to sell, usually 100%)
        - Buy orders: target_weight (percentage of total assets to allocate)
        - This ensures consistency between paper trading and real trading

        Args:
            date: Date in YYYY-MM-DD format (None for latest)
            topk: Number of stocks to hold
            n_drop: Number of stocks to drop each day
            slippage: Expected slippage for price estimation (default 0.1%)

        Returns:
            Trading plan with sell_orders, buy_orders, hold_orders
        """
        try:
            # Get online serving service
            online_service = get_online_serving_service()

            if not online_service.is_initialized:
                return {
                    "success": False,
                    "error": "Online Serving not initialized. Call /routine first.",
                }

            # Get all signals (no limit) for paper trading
            signals_result = online_service.get_signals(limit=None)
            if not signals_result.get("success"):
                return {
                    "success": False,
                    "error": signals_result.get("error", "Failed to get signals"),
                }

            signals = signals_result.get("signals", [])
            if not signals:
                return {
                    "success": False,
                    "error": "No signals available",
                }

            # Filter signals by date
            if date:
                signals = [s for s in signals if s.get("datetime", "").startswith(date)]
            else:
                # Get latest date
                dates = set(
                    s.get("datetime", "")[:10] for s in signals if s.get("datetime")
                )
                # Log available dates for debugging
                if dates:
                    sorted_dates = sorted(dates)
                    logger.info(
                        f"Available signal dates: {len(sorted_dates)} dates, range: {sorted_dates[0]} to {sorted_dates[-1]}"
                    )
                    logger.info(f"Last 5 dates: {sorted_dates[-5:]}")
                if dates:
                    latest_date = max(dates)
                    signals = [
                        s
                        for s in signals
                        if s.get("datetime", "").startswith(latest_date)
                    ]
                    date = latest_date

            if not signals:
                return {
                    "success": False,
                    "error": f"No signals for date {date}",
                }

            # Sort by score descending
            signals.sort(key=lambda x: x.get("score", 0), reverse=True)

            # Create signal lookup by instrument
            signal_lookup = {s.get("instrument"): s for s in signals}

            # Get current portfolio
            portfolio = self._load_portfolio()
            positions = portfolio.get("positions", {})
            cash = portfolio.get("cash", 0)

            # Calculate total portfolio value
            total_position_value = sum(
                p.get("shares", 0) * p.get("avg_cost", 0) for p in positions.values()
            )
            total_value = cash + total_position_value

            # Calculate current weights
            current_weights = {}
            for instrument, pos in positions.items():
                pos_value = pos.get("shares", 0) * pos.get("avg_cost", 0)
                current_weights[instrument] = (
                    (pos_value / total_value * 100) if total_value > 0 else 0
                )

            # TopkDropout strategy logic
            # Target weight per stock = 100% / topk
            target_weight_per_stock = 100.0 / topk

            # Top k instruments by score
            top_k_instruments = [s.get("instrument") for s in signals[:topk]]
            top_k_set = set(top_k_instruments)

            # Current holdings with their scores and ranks
            holding_scores = []
            for instrument in positions.keys():
                sig = signal_lookup.get(instrument, {})
                score = sig.get("score", 0)
                # Find rank in signals
                rank = next(
                    (
                        i + 1
                        for i, s in enumerate(signals)
                        if s.get("instrument") == instrument
                    ),
                    len(signals) + 1,
                )
                holding_scores.append(
                    {
                        "instrument": instrument,
                        "score": score,
                        "rank": rank,
                        "current_weight": current_weights.get(instrument, 0),
                    }
                )

            # Sort holdings by score (worst first)
            holding_scores.sort(key=lambda x: x["score"])

            # Determine sell orders
            sell_orders = []
            instruments_to_sell = set()

            # Sell worst n_drop from current holdings that are not in top_k
            for hs in holding_scores[:n_drop]:
                if hs["instrument"] not in top_k_set:
                    instruments_to_sell.add(hs["instrument"])

            # Also sell any holdings not in top_k
            for instrument in positions.keys():
                if instrument not in top_k_set:
                    instruments_to_sell.add(instrument)

            # Get prices for sell orders
            sell_prices = self._get_latest_prices(list(instruments_to_sell))

            for instrument in instruments_to_sell:
                sig = signal_lookup.get(instrument, {})
                price = sell_prices.get(instrument, 10.0)
                limit_price = price * (
                    1 - slippage * 5
                )  # Limit price with max slippage
                sell_orders.append(
                    {
                        "instrument": instrument,
                        "direction": "SELL",
                        "sell_pct": 100.0,  # Sell 100% of position
                        "current_weight": current_weights.get(instrument, 0),
                        "reference_price": price,
                        "limit_price": limit_price,
                        "score": sig.get("score", 0),
                        "reason": "dropped_from_topk",
                        "instruction": f"挂限价单 ≥{limit_price:.2f} 卖出全部持仓，若未成交则改市价单",
                    }
                )

            # Determine buy orders
            buy_orders = []
            instruments_to_buy = []

            for instrument in top_k_instruments:
                if instrument not in positions:
                    instruments_to_buy.append(instrument)

            # Get prices for buy orders
            buy_prices = self._get_latest_prices(instruments_to_buy)

            for instrument in instruments_to_buy:
                sig = signal_lookup.get(instrument, {})
                price = buy_prices.get(instrument, 10.0)
                limit_price = price * (
                    1 + slippage * 5
                )  # Limit price with max slippage
                rank = next(
                    (
                        i + 1
                        for i, s in enumerate(signals)
                        if s.get("instrument") == instrument
                    ),
                    len(signals) + 1,
                )
                buy_orders.append(
                    {
                        "instrument": instrument,
                        "direction": "BUY",
                        "target_weight": target_weight_per_stock,  # Target % of total assets
                        "reference_price": price,
                        "limit_price": limit_price,
                        "score": sig.get("score", 0),
                        "instruction": f"挂限价单 ≤{limit_price:.2f} 买入(金额=总资产×{target_weight_per_stock:.1f}%)，若未成交则改市价单",
                        "score_rank": rank,
                    }
                )

            # Determine hold orders (current positions that remain in top_k)
            hold_orders = []
            for hs in holding_scores:
                instrument = hs["instrument"]
                if instrument in top_k_set and instrument not in instruments_to_sell:
                    hold_orders.append(
                        {
                            "instrument": instrument,
                            "direction": "HOLD",
                            "current_weight": hs["current_weight"],
                            "target_weight": target_weight_per_stock,
                            "score": hs["score"],
                            "score_rank": hs["rank"],
                        }
                    )

            # Get last executed trades from trades.json
            all_trades = self._load_trades()
            last_executed_sells = []
            last_executed_buys = []
            if all_trades:
                # Get the latest trade date
                latest_trade_date = max(t.get("date", "") for t in all_trades)
                # Filter trades for the latest date
                for t in all_trades:
                    if t.get("date") == latest_trade_date:
                        if t.get("action") == "SELL":
                            last_executed_sells.append(
                                {
                                    "instrument": t.get("instrument"),
                                    "direction": "SELL",
                                    "shares": t.get("shares"),
                                    "price": t.get("price"),
                                    "value": t.get("value"),
                                    "sell_pct": t.get("sell_pct"),
                                    "executed_at": t.get("executed_at"),
                                }
                            )
                        elif t.get("action") == "BUY":
                            last_executed_buys.append(
                                {
                                    "instrument": t.get("instrument"),
                                    "direction": "BUY",
                                    "shares": t.get("shares"),
                                    "price": t.get("price"),
                                    "value": t.get("value"),
                                    "target_weight": t.get("target_weight"),
                                    "executed_at": t.get("executed_at"),
                                }
                            )

            return {
                "success": True,
                "date": date,
                "generated_at": datetime.now().isoformat(),
                "strategy": "TopkDropout",
                "topk": topk,
                "n_drop": n_drop,
                "target_weight_per_stock": target_weight_per_stock,
                "slippage": slippage,
                "portfolio_summary": {
                    "total_value": total_value,
                    "cash": cash,
                    "position_value": total_position_value,
                    "position_count": len(positions),
                },
                "sell_orders": sell_orders,
                "buy_orders": buy_orders,
                "hold_orders": hold_orders,
                "summary": {
                    "sell_count": len(sell_orders),
                    "buy_count": len(buy_orders),
                    "hold_count": len(hold_orders),
                },
                "last_executed_trades": {
                    "sells": last_executed_sells,
                    "buys": last_executed_buys,
                    "sell_count": len(last_executed_sells),
                    "buy_count": len(last_executed_buys),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to generate trading plan: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_trading_decisions(
        self,
        date: Optional[str] = None,
        topk: int = 50,
        n_drop: int = 5,
    ) -> Dict[str, Any]:
        """
        Get trading decisions (legacy method, calls get_trading_plan).

        Deprecated: Use get_trading_plan() instead for percentage-based plans.
        """
        return self.get_trading_plan(date=date, topk=topk, n_drop=n_drop)

    def execute_trades(
        self,
        date: Optional[str] = None,
        topk: int = 50,
        n_drop: int = 5,
        slippage: float = 0.001,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute paper trades based on percentage-based trading plan.

        Uses market order simulation with slippage:
        - Buy price = reference_price * (1 + slippage)
        - Sell price = reference_price * (1 - slippage)

        Args:
            date: Date in YYYY-MM-DD format (None for latest)
            topk: Number of stocks to hold
            n_drop: Number of stocks to drop each day
            slippage: Slippage for price simulation (default 0.1%)
            dry_run: If True, only simulate without saving

        Returns:
            Execution result with trades made
        """
        try:
            # Get trading plan (use internal method to bypass trading_started check)
            plan = self._generate_trading_plan(
                date=date, topk=topk, n_drop=n_drop, slippage=slippage
            )
            if not plan.get("success"):
                return plan

            portfolio = self._load_portfolio()
            trades = self._load_trades()
            trade_date = plan.get("date", datetime.now().strftime("%Y-%m-%d"))

            executed_sells = []
            executed_buys = []
            cash = portfolio.get("cash", 0)
            positions = portfolio.get("positions", {})

            # Calculate total portfolio value before trades
            total_position_value = sum(
                p.get("shares", 0) * p.get("avg_cost", 0) for p in positions.values()
            )
            total_value = cash + total_position_value

            # Execute sells first (based on sell_pct)
            for sell_order in plan.get("sell_orders", []):
                instrument = sell_order.get("instrument")
                sell_pct = sell_order.get("sell_pct", 100.0)
                reference_price = sell_order.get("reference_price", 10.0)

                if instrument in positions:
                    pos = positions[instrument]
                    total_shares = pos.get("shares", 0)
                    shares_to_sell = int(total_shares * sell_pct / 100)

                    # Apply slippage (sell at lower price)
                    sell_price = reference_price * (1 - slippage)
                    sell_value = shares_to_sell * sell_price
                    cash += sell_value

                    trade = {
                        "date": trade_date,
                        "instrument": instrument,
                        "action": "SELL",
                        "shares": shares_to_sell,
                        "price": sell_price,
                        "value": sell_value,
                        "sell_pct": sell_pct,
                        "executed_at": datetime.now().isoformat(),
                    }
                    executed_sells.append(trade)
                    trades.append(trade)

                    # Update or remove position
                    remaining_shares = total_shares - shares_to_sell
                    if remaining_shares > 0:
                        positions[instrument]["shares"] = remaining_shares
                    else:
                        del positions[instrument]

            # Recalculate total value after sells
            total_position_value = sum(
                p.get("shares", 0) * p.get("avg_cost", 0) for p in positions.values()
            )
            total_value = cash + total_position_value

            # Execute buys (based on target_weight)
            for buy_order in plan.get("buy_orders", []):
                instrument = buy_order.get("instrument")
                target_weight = buy_order.get("target_weight", 2.0)
                reference_price = buy_order.get("reference_price", 10.0)

                # Calculate target value based on percentage
                target_value = total_value * target_weight / 100

                # Apply slippage (buy at higher price)
                buy_price = reference_price * (1 + slippage)

                # Calculate shares (round down to 100)
                shares = int(target_value / buy_price / 100) * 100

                if shares > 0 and cash >= shares * buy_price:
                    buy_value = shares * buy_price
                    cash -= buy_value

                    positions[instrument] = {
                        "shares": shares,
                        "avg_cost": buy_price,
                    }

                    trade = {
                        "date": trade_date,
                        "instrument": instrument,
                        "action": "BUY",
                        "shares": shares,
                        "price": buy_price,
                        "value": buy_value,
                        "target_weight": target_weight,
                        "executed_at": datetime.now().isoformat(),
                    }
                    executed_buys.append(trade)
                    trades.append(trade)

            # Update portfolio
            portfolio["cash"] = cash
            portfolio["positions"] = positions

            # Save if not dry run
            if not dry_run:
                self._save_portfolio(portfolio)
                self._save_trades(trades)
                self._mark_trading_started()  # Mark that trading has started

                # Record daily snapshot
                daily_records = self._load_daily_records()
                final_position_value = sum(
                    p.get("shares", 0) * p.get("avg_cost", 0)
                    for p in positions.values()
                )
                daily_records.append(
                    {
                        "date": trade_date,
                        "cash": cash,
                        "position_count": len(positions),
                        "position_value": final_position_value,
                        "total_value": cash + final_position_value,
                        "sells": len(executed_sells),
                        "buys": len(executed_buys),
                        "recorded_at": datetime.now().isoformat(),
                    }
                )
                self._save_daily_records(daily_records)

            return {
                "success": True,
                "date": trade_date,
                "dry_run": dry_run,
                "slippage": slippage,
                "sells_executed": len(executed_sells),
                "buys_executed": len(executed_buys),
                "executed_sells": executed_sells,
                "executed_buys": executed_buys,
                "final_cash": cash,
                "final_position_count": len(positions),
                # Include trading plan for display
                "trading_plan": {
                    "sell_orders": plan.get("sell_orders", []),
                    "buy_orders": plan.get("buy_orders", []),
                    "hold_orders": plan.get("hold_orders", []),
                    "summary": plan.get("summary", {}),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to execute trades: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_trade_history(
        self,
        limit: int = 100,
        instrument: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get trade history.

        Args:
            limit: Maximum number of trades to return
            instrument: Filter by instrument (optional)

        Returns:
            Trade history
        """
        trades = self._load_trades()

        if instrument:
            trades = [t for t in trades if t.get("instrument") == instrument]

        # Sort by date descending
        trades.sort(key=lambda x: x.get("executed_at", ""), reverse=True)

        return {
            "success": True,
            "total_trades": len(trades),
            "trades": trades[:limit],
        }

    def get_performance(self) -> Dict[str, Any]:
        """
        Get paper trading performance metrics.

        Returns:
            Performance metrics including extended risk metrics
        """
        portfolio = self._load_portfolio()
        daily_records = self._load_daily_records()
        trades = self._load_trades()

        initial_cash = qlib_config.initial_cash

        # Use real current prices for accurate performance calculation
        position_instruments = list(portfolio.get("positions", {}).keys())
        current_prices = (
            self._get_latest_prices(position_instruments)
            if position_instruments
            else {}
        )
        position_value = 0.0
        for inst, pos in portfolio.get("positions", {}).items():
            shares = pos.get("shares", 0)
            price = current_prices.get(inst, pos.get("avg_cost", 0))
            position_value += shares * price
        current_value = portfolio.get("cash", 0) + position_value

        total_return = (
            (current_value - initial_cash) / initial_cash if initial_cash > 0 else 0
        )

        # Calculate trade statistics
        buy_trades = [t for t in trades if t.get("action") == "BUY"]
        sell_trades = [t for t in trades if t.get("action") == "SELL"]
        trading_days = len(daily_records)

        # Extended metrics - provide reasonable defaults for single day
        annualized_return = None
        annualized_return_pct = None
        max_drawdown = 0.0  # Default to 0 for single day
        max_drawdown_pct = "0.00%"
        sharpe_ratio = None
        win_rate = None
        win_rate_pct = None

        # Calculate win rate from completed sell trades
        if sell_trades:
            profitable_trades = 0
            total_evaluated = 0
            for trade in sell_trades:
                sell_price = trade.get("price", 0)
                instrument = trade.get("instrument", "")
                # Find the matching buy trade to compare
                matching_buys = [
                    b
                    for b in buy_trades
                    if b.get("instrument") == instrument
                    and b.get("date", "") <= trade.get("date", "")
                ]
                if matching_buys and sell_price > 0:
                    last_buy_price = matching_buys[-1].get("price", 0)
                    if last_buy_price > 0:
                        total_evaluated += 1
                        if sell_price > last_buy_price:
                            profitable_trades += 1
            if total_evaluated > 0:
                win_rate = profitable_trades / total_evaluated
                win_rate_pct = f"{win_rate * 100:.1f}%"
            else:
                win_rate = None
                win_rate_pct = "N/A"

        if trading_days > 0:
            # Annualized return (assuming 252 trading days per year)
            years = trading_days / 252
            if years > 0:
                # Use compound annual growth rate formula
                # Handle total_return = 0 case
                annualized_return = (1 + total_return) ** (1 / years) - 1
                annualized_return_pct = f"{annualized_return * 100:.2f}%"

            # Calculate max drawdown from daily records (daily_records is a list)
            if daily_records:
                # Sort by date
                sorted_records = sorted(daily_records, key=lambda x: x.get("date", ""))
                values = [r.get("total_value", initial_cash) for r in sorted_records]

                if values:
                    peak = values[0]
                    max_dd = 0
                    for v in values:
                        if v > peak:
                            peak = v
                        dd = (peak - v) / peak if peak > 0 else 0
                        if dd > max_dd:
                            max_dd = dd
                    max_drawdown = max_dd
                    max_drawdown_pct = f"{max_dd * 100:.2f}%"

            # Calculate Sharpe ratio (simplified, assuming risk-free rate = 0)
            if len(daily_records) >= 2:
                sorted_records = sorted(daily_records, key=lambda x: x.get("date", ""))
                daily_returns = []
                for i in range(1, len(sorted_records)):
                    prev_val = sorted_records[i - 1].get("total_value", initial_cash)
                    curr_val = sorted_records[i].get("total_value", initial_cash)
                    if prev_val > 0:
                        daily_returns.append((curr_val - prev_val) / prev_val)

                if daily_returns:
                    import numpy as np

                    mean_return = np.mean(daily_returns)
                    std_return = np.std(daily_returns)
                    if std_return > 0:
                        sharpe_ratio = (mean_return * 252) / (std_return * np.sqrt(252))
            elif trading_days == 1:
                # For single day, Sharpe ratio is not meaningful
                sharpe_ratio = None

        return {
            "success": True,
            "initial_cash": initial_cash,
            "current_value": current_value,
            "total_return": total_return,
            "total_return_pct": f"{total_return * 100:.2f}%",
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "trading_days": trading_days,
            "position_count": len(portfolio.get("positions", {})),
            # Extended metrics
            "annualized_return": annualized_return,
            "annualized_return_pct": annualized_return_pct,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "win_rate_pct": win_rate_pct,
        }

    def reset(self) -> Dict[str, Any]:
        """
        Reset paper trading state.

        Returns:
            Reset result
        """
        try:
            # Remove all paper trading files
            if PORTFOLIO_FILE.exists():
                PORTFOLIO_FILE.unlink()
            if TRADES_FILE.exists():
                TRADES_FILE.unlink()
            if DAILY_RECORDS_FILE.exists():
                DAILY_RECORDS_FILE.unlink()
            if TRADING_STARTED_FILE.exists():
                TRADING_STARTED_FILE.unlink()

            return {
                "success": True,
                "message": "Paper trading state reset successfully",
            }

        except Exception as e:
            self.logger.error(f"Failed to reset paper trading: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# Singleton instance
_paper_trading_service: Optional[PaperTradingService] = None


def get_paper_trading_service() -> PaperTradingService:
    """Get or create the Paper Trading service singleton."""
    global _paper_trading_service
    if _paper_trading_service is None:
        _paper_trading_service = PaperTradingService()
    return _paper_trading_service
