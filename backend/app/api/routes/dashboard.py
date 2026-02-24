"""
Dashboard API endpoints for aggregated system status and metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.paper_trading_service import get_paper_trading_service
from app.services.online_serving_service import get_online_serving_service
from app.services.model_metrics_service import get_model_metrics_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


# Response Models
class PortfolioSummary(BaseModel):
    """Portfolio summary for dashboard."""

    total_value: float = 0.0
    initial_cash: float = 0.0
    total_return: float = 0.0
    total_return_pct: str = "0.00%"
    annualized_return_pct: Optional[str] = None
    position_count: int = 0
    trading_started: bool = False


class ModelSummary(BaseModel):
    """Model metrics summary for dashboard."""

    ic: Optional[float] = None
    icir: Optional[float] = None
    evaluation: str = "N/A"
    has_metrics: bool = False


class SystemSummary(BaseModel):
    """System status summary for dashboard."""

    is_initialized: bool = False
    signal_count: int = 0
    last_routine_time: Optional[str] = None
    data_range_start: Optional[str] = None
    data_range_end: Optional[str] = None


class HoldingItem(BaseModel):
    """Single holding item for top holdings."""

    instrument: str
    value: float
    weight: float
    shares: int = 0


class ActivityItem(BaseModel):
    """Single activity item for recent activities."""

    time: str
    type: str
    message: str
    success: bool = True


class AlertItem(BaseModel):
    """Single alert item."""

    level: str  # "info", "warning", "error"
    message: str
    action: Optional[str] = None


class DashboardResponse(BaseModel):
    """Complete dashboard summary response."""

    success: bool
    portfolio: PortfolioSummary
    model: ModelSummary
    system: SystemSummary
    top_holdings: List[HoldingItem] = []
    recent_activities: List[ActivityItem] = []
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


@router.get("/summary", response_model=DashboardResponse)
def get_dashboard_summary():
    """
    Get aggregated dashboard summary.

    Returns portfolio metrics, model metrics, system status,
    top holdings, recent activities, and alerts.
    """
    try:
        # Initialize response components
        portfolio_summary = PortfolioSummary()
        model_summary = ModelSummary()
        system_summary = SystemSummary()
        top_holdings: List[HoldingItem] = []
        recent_activities: List[ActivityItem] = []
        alerts: List[AlertItem] = []

        # 1. Get Portfolio Data
        try:
            paper_service = get_paper_trading_service()
            performance = paper_service.get_performance()

            if performance.get("success"):
                portfolio_summary = PortfolioSummary(
                    total_value=performance.get("current_value", 0.0),
                    initial_cash=performance.get("initial_cash", 0.0),
                    total_return=performance.get("total_return", 0.0),
                    total_return_pct=performance.get("total_return_pct", "0.00%"),
                    annualized_return_pct=performance.get("annualized_return_pct"),
                    position_count=performance.get("position_count", 0),
                    trading_started=performance.get("position_count", 0) > 0
                    or performance.get("total_trades", 0) > 0,
                )

            # Get top holdings
            portfolio = paper_service.get_portfolio()
            if portfolio.get("success"):
                positions = portfolio.get("positions", [])
                total_value = portfolio.get("total_value", 1.0)
                if total_value <= 0:
                    total_value = 1.0

                # Sort by value and take top 5
                sorted_positions = sorted(
                    positions, key=lambda x: x.get("current_value", 0), reverse=True
                )[:5]

                for pos in sorted_positions:
                    current_value = pos.get("current_value", 0)
                    weight = (
                        (current_value / total_value) * 100 if total_value > 0 else 0
                    )
                    top_holdings.append(
                        HoldingItem(
                            instrument=pos.get("instrument", ""),
                            value=current_value,
                            weight=round(weight, 2),
                            shares=pos.get("shares", 0),
                        )
                    )

            # Get recent trades for activities
            trades = paper_service.get_trade_history(limit=5)
            if trades.get("success"):
                for trade in trades.get("trades", [])[:3]:
                    executed_at = trade.get("executed_at", "")
                    if executed_at:
                        try:
                            dt = datetime.fromisoformat(
                                executed_at.replace("Z", "+00:00")
                            )
                            time_str = dt.strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            time_str = (
                                executed_at[:16]
                                if len(executed_at) >= 16
                                else executed_at
                            )
                    else:
                        time_str = "Unknown"

                    action = trade.get("action", "TRADE")
                    instrument = trade.get("instrument", "")
                    shares = trade.get("shares", 0)

                    recent_activities.append(
                        ActivityItem(
                            time=time_str,
                            type="trade",
                            message=f"{action} {instrument} ({shares} shares)",
                            success=True,
                        )
                    )

        except Exception as e:
            logger.warning(f"Failed to get portfolio data: {e}")
            alerts.append(
                AlertItem(
                    level="warning",
                    message="Portfolio data unavailable",
                    action=None,
                )
            )

        # 2. Get Model Metrics - read directly from file
        try:
            import json
            from pathlib import Path

            metrics_file = Path("/app/mlruns/model_metrics/active_metrics.json")
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    metrics = json.load(f)

                # IC metrics are nested under ic_metrics
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
            else:
                logger.warning(f"Model metrics file not found: {metrics_file}")
        except Exception as e:
            logger.warning(f"Failed to get model metrics: {e}")

        # 3. Get System Status - check from model metrics file and data
        try:
            # Check if model metrics exist (indicates routine has been run)
            has_metrics = metrics_file.exists() if "metrics_file" in dir() else False

            # Try to get signal count from online service
            online_service = get_online_serving_service()
            status = online_service.get_status()

            # If online service says initialized, use its data
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
                )
            else:
                # Check if we have model metrics (indicates routine was run before restart)
                if model_summary.has_metrics:
                    # Read signal count from metrics file
                    signal_count = 0
                    if "metrics" in dir() and metrics:
                        # Get signal count from metrics if available
                        signal_count = metrics.get("sample_count", 0)

                    system_summary = SystemSummary(
                        is_initialized=True,  # We have metrics, so routine was run
                        signal_count=signal_count,
                        last_routine_time=None,  # Unknown after restart
                        data_range_start=None,
                        data_range_end=None,
                    )
                else:
                    system_summary = SystemSummary(
                        is_initialized=False,
                        signal_count=0,
                        last_routine_time=None,
                        data_range_start=None,
                        data_range_end=None,
                    )
                    # Only add alert if no metrics exist
                    alerts.append(
                        AlertItem(
                            level="warning",
                            message="Online Serving not initialized. Run routine to start.",
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

        # Sort activities by time (most recent first)
        recent_activities = recent_activities[:5]

        # Add welcome alert if no trading started
        if not portfolio_summary.trading_started and not any(
            a.action == "run_routine" for a in alerts
        ):
            alerts.insert(
                0,
                AlertItem(
                    level="info",
                    message="Paper trading not started. Run routine and execute trades to begin.",
                    action="run_routine",
                ),
            )

        return DashboardResponse(
            success=True,
            portfolio=portfolio_summary,
            model=model_summary,
            system=system_summary,
            top_holdings=top_holdings,
            recent_activities=recent_activities,
            alerts=alerts,
        )

    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard summary: {str(e)}"
        )
