"""
Dashboard API endpoints for aggregated system status and metrics.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.online_serving_service import get_online_serving_service


def _safe_float(value, default=0.0):
    """Safely convert a value to float, handling nan and inf values."""
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])

# File paths for persisted data
BACKTEST_RESULT_FILE = Path("/app/mlruns/backtest_results/latest_result.json")
TARGET_PORTFOLIO_DIR = Path("/app/data/target_portfolio")
MODEL_METRICS_FILE = Path("/app/mlruns/model_metrics/active_metrics.json")


# Response Models
class BacktestSummary(BaseModel):
    """Backtest results summary for dashboard."""

    has_results: bool = False
    total_return: float = 0.0  # Gross return (before costs)
    total_return_pct: str = "0.00%"
    net_return: float = 0.0  # Net return (after costs) - actual investor return
    net_return_pct: str = "0.00%"
    annualized_return: float = 0.0
    annualized_return_pct: str = "0.00%"
    cagr: float = 0.0  # Gross CAGR (before costs)
    cagr_pct: str = "0.00%"
    net_cagr: float = 0.0  # Net CAGR (after costs) - actual investor return
    net_cagr_pct: str = "0.00%"
    max_drawdown: float = 0.0
    max_drawdown_pct: str = "0.00%"
    sharpe_ratio: float = 0.0
    trading_days: int = 0
    backtest_date: Optional[str] = None


class ModelSummary(BaseModel):
    """Model metrics summary for dashboard."""

    ic: Optional[float] = None
    icir: Optional[float] = None
    evaluation: str = "N/A"
    has_metrics: bool = False


class RebalanceInfo(BaseModel):
    """Rebalancing schedule information."""

    rebalance_period_days: int = 1  # Rebalancing period in trading days
    is_rebalance_day: bool = True  # Whether today is a rebalancing day
    next_rebalance_date: Optional[str] = None  # Next rebalancing date (YYYY-MM-DD)
    days_until_rebalance: int = 0  # Trading days until next rebalance


class SystemSummary(BaseModel):
    """System status summary for dashboard."""

    is_initialized: bool = False
    signal_count: int = 0
    last_routine_time: Optional[str] = None
    data_range_start: Optional[str] = None
    data_range_end: Optional[str] = None
    rebalance: Optional[RebalanceInfo] = None


class TargetPositionItem(BaseModel):
    """Single position item from target portfolio."""

    rank: int
    instrument: str
    name: str = ""
    type: str = "alpha"  # "etf" or "alpha"
    weight: float = 0.0
    target_value: float = 0.0
    target_shares: int = 0
    action: str = "hold"


class AlertItem(BaseModel):
    """Single alert item."""

    level: str  # "info", "warning", "error"
    message: str
    action: Optional[str] = None


class DashboardResponse(BaseModel):
    """Complete dashboard summary response."""

    success: bool
    backtest: BacktestSummary
    model: ModelSummary
    system: SystemSummary
    target_positions: List[TargetPositionItem] = []
    alerts: List[AlertItem] = []
    error: Optional[str] = None


def _get_model_evaluation(ic: float) -> str:
    """Get evaluation label based on IC value."""
    if ic is None:
        return "N/A"
    abs_ic = abs(ic)
    if abs_ic >= 0.05:
        return "Excellent"
    elif abs_ic >= 0.03:
        return "Good"
    elif abs_ic >= 0.02:
        return "Fair"
    else:
        return "Weak"


class LatestPortfolioResponse(BaseModel):
    """Response for latest portfolio endpoint."""

    success: bool
    trade_date: Optional[str] = None
    signal_for_date: Optional[str] = None
    generated_at: Optional[str] = None
    total_value: float = 0
    positions: List[Dict[str, Any]] = []
    weights: Dict[str, Any] = {}
    summary: Dict[str, Any] = {}
    error: Optional[str] = None


@router.get("/latest-portfolio", response_model=LatestPortfolioResponse)
def get_latest_portfolio():
    """
    Get the latest target portfolio from file.

    This reads directly from the most recent etf_enhanced_*.json file,
    and recalculates actions based on current holdings to ensure
    accurate buy/sell/hold status.
    """
    try:
        if not TARGET_PORTFOLIO_DIR.exists():
            return LatestPortfolioResponse(
                success=False, error="Portfolio directory not found"
            )

        # Find the latest portfolio file
        portfolio_files = sorted(
            TARGET_PORTFOLIO_DIR.glob("etf_enhanced_*.json"), reverse=True
        )

        if not portfolio_files:
            return LatestPortfolioResponse(
                success=False, error="No portfolio files found"
            )

        latest_file = portfolio_files[0]

        with open(latest_file, "r", encoding="utf-8") as f:
            portfolio_data = json.load(f)

        # Use the portfolio file data directly - it contains the correct
        # current_shares (snapshot at generation time) and action calculations.
        # Do NOT recalculate from current_holdings.json, as that file
        # is updated to target_shares after signal generation for next rebalance.
        positions = portfolio_data.get("positions", [])
        summary = portfolio_data.get("summary", {})

        return LatestPortfolioResponse(
            success=True,
            trade_date=portfolio_data.get("trade_date"),
            signal_for_date=portfolio_data.get("signal_for_date"),
            generated_at=portfolio_data.get("generated_at"),
            total_value=portfolio_data.get("total_value", 0),
            positions=positions,
            weights=portfolio_data.get("weights", {}),
            summary=summary,
        )

    except Exception as e:
        logger.error(f"Failed to get latest portfolio: {e}")
        return LatestPortfolioResponse(success=False, error=str(e))


@router.get("/summary", response_model=DashboardResponse)
def get_dashboard_summary():
    """
    Get aggregated dashboard summary.

    Returns backtest results, model metrics, system status,
    target positions, and alerts.
    """
    try:
        # Initialize response components
        backtest_summary = BacktestSummary()
        model_summary = ModelSummary()
        system_summary = SystemSummary()
        target_positions: List[TargetPositionItem] = []
        alerts: List[AlertItem] = []

        # 1. Get Backtest Results
        try:
            if BACKTEST_RESULT_FILE.exists():
                with open(BACKTEST_RESULT_FILE, "r") as f:
                    backtest_data = json.load(f)

                total_return = _safe_float(backtest_data.get("total_return", 0))
                net_return = _safe_float(backtest_data.get("net_return", 0))
                risk_metrics = backtest_data.get("risk_metrics", {})
                annualized_return = _safe_float(
                    risk_metrics.get("annualized_return", 0)
                )
                cagr = _safe_float(risk_metrics.get("cagr", 0))
                net_cagr = _safe_float(risk_metrics.get("net_cagr", 0))
                max_drawdown = _safe_float(risk_metrics.get("max_drawdown", 0))
                sharpe_ratio = _safe_float(risk_metrics.get("sharpe_ratio", 0))

                backtest_summary = BacktestSummary(
                    has_results=True,
                    total_return=total_return,
                    total_return_pct=f"{total_return * 100:+.2f}%",
                    net_return=net_return,
                    net_return_pct=f"{net_return * 100:+.2f}%",
                    annualized_return=annualized_return,
                    annualized_return_pct=f"{annualized_return * 100:+.2f}%",
                    cagr=cagr,
                    cagr_pct=f"{cagr * 100:+.2f}%",
                    net_cagr=net_cagr,
                    net_cagr_pct=f"{net_cagr * 100:+.2f}%",
                    max_drawdown=max_drawdown,
                    max_drawdown_pct=f"{max_drawdown * 100:.2f}%",
                    sharpe_ratio=sharpe_ratio,
                    trading_days=backtest_data.get("trading_days", 0),
                    backtest_date=backtest_data.get("end_time"),
                )
        except Exception as e:
            logger.warning(f"Failed to get backtest results: {e}")

        # 2. Get Target Portfolio (from latest ETF enhanced portfolio file)
        portfolio_summary_info = {}
        try:
            if TARGET_PORTFOLIO_DIR.exists():
                # Find the latest portfolio file
                portfolio_files = sorted(
                    TARGET_PORTFOLIO_DIR.glob("etf_enhanced_*.json"), reverse=True
                )
                if portfolio_files:
                    latest_file = portfolio_files[0]
                    # Extract date from filename (etf_enhanced_YYYY-MM-DD.json)
                    portfolio_date = latest_file.stem.replace("etf_enhanced_", "")

                    with open(latest_file, "r", encoding="utf-8") as f:
                        portfolio_data = json.load(f)

                    # Use portfolio file data directly - it contains the correct
                    # current_shares and action calculations from generation time
                    positions = portfolio_data.get("positions", [])
                    summary = portfolio_data.get("summary", {})

                    # Store summary info for alerts
                    portfolio_summary_info = {
                        "date": portfolio_date,
                        "total_positions": len(positions),
                        "buy_count": summary.get("buy_count", 0),
                        "sell_count": summary.get("sell_count", 0),
                        "hold_count": summary.get("hold_count", 0),
                    }

                    # Filter to only include positions with holdings (target_shares > 0)
                    # then sort by rank and take top 10
                    holdings_only = [
                        p for p in positions if p.get("target_shares", 0) > 0
                    ]
                    sorted_positions = sorted(
                        holdings_only, key=lambda x: x.get("rank", 999)
                    )[:10]

                    for pos in sorted_positions:
                        # Determine position type
                        pos_type = pos.get("type", "alpha")
                        if pos_type == "etf" or pos_type == "stock":
                            pos_type = "etf" if pos_type == "etf" else "alpha"

                        # ETF service uses "symbol" field, not "instrument"
                        symbol = pos.get("symbol", "") or pos.get("instrument", "")

                        target_positions.append(
                            TargetPositionItem(
                                rank=pos.get("rank", 0),
                                instrument=symbol,
                                name=pos.get("name", ""),
                                type=pos_type,
                                weight=pos.get("weight", 0)
                                * 100,  # Convert to percentage
                                target_value=pos.get("target_value", 0),
                                target_shares=pos.get("target_shares", 0),
                                action=pos.get("action", "hold"),
                            )
                        )
        except Exception as e:
            logger.warning(f"Failed to get target portfolio: {e}")

        # 3. Get Model Metrics
        try:
            if MODEL_METRICS_FILE.exists():
                with open(MODEL_METRICS_FILE, "r") as f:
                    metrics = json.load(f)

                ic_metrics = metrics.get("ic_metrics", {})
                ic = ic_metrics.get("ic_mean")
                icir = ic_metrics.get("icir")
                model_summary = ModelSummary(
                    ic=ic,
                    icir=icir,
                    evaluation=_get_model_evaluation(ic) if ic is not None else "N/A",
                    has_metrics=ic is not None,
                )

                # Check if IC is below threshold
                if ic is not None and abs(ic) < 0.02:
                    alerts.append(
                        AlertItem(
                            level="warning",
                            message=f"Model IC ({ic:.4f}) is below recommended threshold",
                            action="retrain_model",
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed to get model metrics: {e}")

        # 4. Get System Status and Rebalance Info
        try:
            online_service = get_online_serving_service()
            status = online_service.get_status()

            # Get rebalance info from ETF service
            rebalance_info = None
            try:
                from app.services.etf_enhanced_indexing_service import (
                    get_etf_enhanced_indexing_service,
                )

                etf_service = get_etf_enhanced_indexing_service()
                rebalance_period = etf_service.rebalance_period_days

                # Get today's date for rebalance check
                today = datetime.now().strftime("%Y-%m-%d")
                is_rebalance = etf_service.is_rebalance_day(today)
                next_rebalance = etf_service.get_next_rebalance_day(today)
                days_until = etf_service.get_days_until_rebalance(today)

                rebalance_info = RebalanceInfo(
                    rebalance_period_days=rebalance_period,
                    is_rebalance_day=is_rebalance,
                    next_rebalance_date=next_rebalance,
                    days_until_rebalance=days_until,
                )
            except Exception as e:
                logger.warning(f"Failed to get rebalance info: {e}")

            if status.get("is_initialized"):
                system_summary = SystemSummary(
                    is_initialized=True,
                    signal_count=status.get("signal_count", 0),
                    last_routine_time=status.get("last_routine_time"),
                    data_range_start=(
                        status.get("data_range", {}).get("start_date")
                        if status.get("data_range")
                        else None
                    ),
                    data_range_end=(
                        status.get("data_range", {}).get("end_date")
                        if status.get("data_range")
                        else None
                    ),
                    rebalance=rebalance_info,
                )
            elif model_summary.has_metrics:
                # Routine was run before but service restarted
                system_summary = SystemSummary(
                    is_initialized=True,
                    signal_count=0,
                    last_routine_time=None,
                    data_range_start=None,
                    data_range_end=None,
                    rebalance=rebalance_info,
                )
            else:
                system_summary = SystemSummary(
                    is_initialized=False,
                    signal_count=0,
                    last_routine_time=None,
                    data_range_start=None,
                    data_range_end=None,
                    rebalance=rebalance_info,
                )
                alerts.append(
                    AlertItem(
                        level="info",
                        message="System not initialized. Click 'Daily Task' to run routine and backtest.",
                        action="run_routine",
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to get system status: {e}")
            alerts.append(
                AlertItem(
                    level="error",
                    message="System status unavailable",
                    action=None,
                )
            )

        # Add info alert if no backtest results
        if not backtest_summary.has_results and not any(
            a.action == "run_routine" for a in alerts
        ):
            alerts.append(
                AlertItem(
                    level="info",
                    message="No backtest results yet. Run Daily Task to generate.",
                    action="run_routine",
                )
            )

        # Add portfolio summary alert if we have portfolio data
        if portfolio_summary_info:
            buy_count = portfolio_summary_info.get("buy_count", 0)
            sell_count = portfolio_summary_info.get("sell_count", 0)
            hold_count = portfolio_summary_info.get("hold_count", 0)
            portfolio_date = portfolio_summary_info.get("date", "")

            if buy_count > 0 or sell_count > 0:
                alerts.insert(
                    0,
                    AlertItem(
                        level="info",
                        message=f"Signal {portfolio_date}: {buy_count} buy, {sell_count} sell, {hold_count} hold",
                        action=None,
                    ),
                )

        # Add success alert if backtest results are good
        if backtest_summary.has_results:
            sharpe = backtest_summary.sharpe_ratio
            total_ret = backtest_summary.total_return
            if sharpe >= 1.0 and total_ret > 0:
                alerts.insert(
                    0,
                    AlertItem(
                        level="info",
                        message=f"Strategy performing well: {backtest_summary.total_return_pct} return, Sharpe {sharpe:.2f}",
                        action=None,
                    ),
                )

        return DashboardResponse(
            success=True,
            backtest=backtest_summary,
            model=model_summary,
            system=system_summary,
            target_positions=target_positions,
            alerts=alerts,
        )

    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard summary: {str(e)}"
        )
