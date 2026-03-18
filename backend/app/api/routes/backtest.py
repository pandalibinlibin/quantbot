"""
Backtest API routes.

This module provides REST API endpoints for backtest operations:
- GET /config: Get backtest configuration from YAML
- GET /status: Get backtest readiness status
- GET /latest-result: Get the latest backtest result
- POST /run: Execute a new backtest
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import logging
import json
from pathlib import Path

from app.services.online_serving_service import get_online_serving_service
from app.config.qlib import qlib_config

logger = logging.getLogger(__name__)

router = APIRouter()

# File path for persisting latest backtest result
BACKTEST_RESULT_FILE = Path("/app/mlruns/backtest_results/latest_result.json")


# Response Models


class BacktestConfigResponse(BaseModel):
    """Response model for backtest config endpoint."""

    status: str
    config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BacktestStatusResponse(BaseModel):
    """Response model for backtest status endpoint."""

    ready: bool
    message: Optional[str] = None
    latest_model: Optional[str] = None
    signal_count: Optional[int] = None
    data_start: Optional[str] = None
    data_end: Optional[str] = None


class BacktestRunRequest(BaseModel):
    """Request model for backtest run endpoint."""

    benchmark: Optional[str] = Field(
        None,
        description="Benchmark symbol for comparison (default: 000300.SH)",
        example="000300.SH",
    )
    account: Optional[float] = Field(
        None,
        description="Initial account value (default: 100000000)",
        example=100000000,
    )


class RiskMetrics(BaseModel):
    """Risk metrics for backtest results."""

    annualized_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    volatility: Optional[float] = None
    calmar_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    profit_loss_ratio: Optional[float] = None


class BacktestRunResponse(BaseModel):
    """Response model for backtest run endpoint."""

    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    data_start_time: Optional[str] = None
    data_end_time: Optional[str] = None
    freq: Optional[str] = None
    trading_days: Optional[int] = None
    signal_count: Optional[int] = None
    total_return: Optional[float] = None
    total_cost: Optional[float] = None
    net_return: Optional[float] = None
    final_account: Optional[float] = None
    strategy: Optional[str] = None
    max_deviation: Optional[float] = None
    benchmark: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    # Enhanced metrics
    risk_metrics: Optional[RiskMetrics] = None
    charts: Optional[Dict[str, Any]] = None


class LatestResultResponse(BaseModel):
    """Response model for latest result endpoint."""

    status: str
    result: Optional[BacktestRunResponse] = None
    error: Optional[str] = None


# Helper functions


def _save_backtest_result(result: Dict[str, Any]) -> None:
    """Save backtest result to file for persistence."""
    try:
        BACKTEST_RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BACKTEST_RESULT_FILE, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Saved backtest result to {BACKTEST_RESULT_FILE}")
    except Exception as e:
        logger.error(f"Failed to save backtest result: {e}")


def _load_backtest_result() -> Optional[Dict[str, Any]]:
    """Load latest backtest result from file."""
    try:
        if BACKTEST_RESULT_FILE.exists():
            with open(BACKTEST_RESULT_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load backtest result: {e}")
    return None


# API Endpoints


@router.get("/config", response_model=BacktestConfigResponse)
def get_backtest_configuration():
    """
    Get backtest configuration that uses routine's Enhanced Indexing Strategy.

    Returns the strategy configuration from system_config.yaml enhanced_indexing section
    and backtest parameters from backtest_config.yaml for consistency.
    """
    try:
        # Get base backtest config
        backtest_config = qlib_config.backtest_config

        # Get Enhanced Indexing config from system config (same as routine)
        enhanced_indexing_config = qlib_config.enhanced_indexing_config

        # Build unified config that shows actual strategy used
        unified_config = {
            "strategy": {
                "class": "EnhancedIndexingStrategy",
                "module_path": "app.services.enhanced_indexing_service",
                "kwargs": {
                    "max_deviation": enhanced_indexing_config.get(
                        "max_deviation", 0.02
                    ),
                    "min_weight": enhanced_indexing_config.get("min_weight", 0.0),
                    "benchmark": enhanced_indexing_config.get("benchmark", "auto"),
                },
            },
            "backtest": backtest_config.get("backtest", {}),
        }

        return BacktestConfigResponse(
            status="success",
            config=unified_config,
        )
    except Exception as e:
        logger.error(f"Failed to get backtest config: {e}")
        return BacktestConfigResponse(
            status="error",
            error=str(e),
        )


@router.get("/status", response_model=BacktestStatusResponse)
def get_backtest_status():
    """
    Get backtest readiness status.

    Checks if Online Serving is initialized and has signals available
    for backtesting.
    """
    try:
        service = get_online_serving_service()
        status = service.get_status()

        is_initialized = status.get("is_initialized", False)

        if not is_initialized:
            return BacktestStatusResponse(
                ready=False,
                message="Online Serving not initialized. Please run routine first.",
            )

        # Check if we have signals
        signals_result = service.get_signals()
        signal_count = signals_result.get("signal_count", 0)

        if signal_count == 0:
            return BacktestStatusResponse(
                ready=False,
                message="No signals available. Please run routine first.",
            )

        return BacktestStatusResponse(
            ready=True,
            message="Ready for backtest. Predictions available.",
            signal_count=signal_count,
        )

    except Exception as e:
        logger.error(f"Failed to get backtest status: {e}")
        return BacktestStatusResponse(
            ready=False,
            message=f"Error checking status: {str(e)}",
        )


@router.get("/latest-result", response_model=LatestResultResponse)
def get_latest_backtest_result():
    """
    Get the latest backtest result.

    Returns the most recent backtest result that was persisted to disk.
    This allows the frontend to display results across page navigations.
    """
    try:
        result = _load_backtest_result()

        if result is None:
            return LatestResultResponse(
                status="not_found",
                error="No backtest result found. Please run a backtest first.",
            )

        return LatestResultResponse(
            status="success",
            result=BacktestRunResponse(**result),
        )

    except Exception as e:
        logger.error(f"Failed to get latest backtest result: {e}")
        return LatestResultResponse(
            status="error",
            error=str(e),
        )


@router.post("/run", response_model=BacktestRunResponse)
def run_backtest(request: Optional[BacktestRunRequest] = None):
    """
    Execute a new backtest.

    This endpoint:
    1. Uses signals from Online Serving
    2. Executes backtest using Enhanced Indexing strategy
    3. Persists the result for later retrieval

    Args:
        request: Backtest configuration (all fields optional with defaults)

    Returns:
        Backtest results including returns, metrics, and configuration
    """
    try:
        service = get_online_serving_service()

        # Use default values if no request body provided
        if request is None:
            request = BacktestRunRequest()

        result = service.execute_backtest(
            benchmark=request.benchmark,
            account=request.account,
        )

        if result.get("status") == "error":
            return BacktestRunResponse(
                status="error",
                error=result.get("error"),
            )

        # Build response
        response_data = {
            "status": "success",
            "start_time": result.get("start_time"),
            "end_time": result.get("end_time"),
            "data_start_time": result.get("data_start_time", result.get("start_time")),
            "data_end_time": result.get("data_end_time", result.get("end_time")),
            "freq": result.get("freq"),
            "trading_days": result.get("trading_days"),
            "signal_count": result.get("signal_count"),
            "total_return": result.get("total_return"),
            "total_cost": result.get("total_cost"),
            "net_return": result.get("net_return"),
            "final_account": result.get("final_account"),
            "strategy": result.get("strategy"),
            "max_deviation": result.get("max_deviation"),
            "benchmark": result.get("benchmark"),
            "message": "Backtest completed successfully",
            # Enhanced metrics
            "risk_metrics": result.get("risk_metrics"),
            "charts": result.get("charts"),
        }

        # Persist result for later retrieval
        _save_backtest_result(response_data)

        return BacktestRunResponse(**response_data)

    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")
