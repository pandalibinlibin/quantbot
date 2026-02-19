"""
Backtest API Routes

Endpoints for backtesting strategies using model predictions.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.qlib_workflow_service import get_qlib_workflow_service
from app.core.config import settings
from pathlib import Path

router = APIRouter()


class BacktestStatusResponse(BaseModel):
    """Response model for backtest status check."""

    ready: bool
    message: str
    models_count: int = 0
    predictions_available: bool = False
    latest_model: Optional[str] = None
    latest_prediction_time: Optional[str] = None


class BacktestRequest(BaseModel):
    """Request model for backtest endpoint."""

    pred_path: Optional[str] = None  # Path to predictions file, None for latest
    start_time: Optional[str] = None  # Backtest start time, None for auto-detect
    end_time: Optional[str] = None  # Backtest end time, None for auto-detect
    benchmark: str = "SH000300"  # Benchmark symbol
    topk: int = 50  # Number of stocks to hold
    n_drop: int = 5  # Number of stocks to drop each day
    account: float = 100000000  # Initial account value


class BacktestResponse(BaseModel):
    """Response model for backtest endpoint."""

    status: str
    message: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    trading_days: int = 0
    total_return: float = 0.0
    total_cost: float = 0.0
    net_return: float = 0.0
    final_account: float = 0.0
    error: Optional[str] = None


@router.get("/status", response_model=BacktestStatusResponse)
def get_backtest_status():
    """
    Check if backtest is ready to run.

    Returns information about available models and predictions.
    """
    from datetime import datetime

    service = get_qlib_workflow_service()

    # Check for trained models
    models = service.list_models()
    models_count = len(models)
    latest_model = models[0]["name"] if models else None

    # Check for predictions in MLflow artifacts
    mlruns_dir = Path(settings.QLIB_DATA_PATH).parent / "mlruns"
    pred_files = list(mlruns_dir.glob("**/pred.pkl")) if mlruns_dir.exists() else []
    predictions_available = len(pred_files) > 0

    latest_prediction_time = None
    if pred_files:
        latest_pred = max(pred_files, key=lambda p: p.stat().st_mtime)
        latest_prediction_time = datetime.fromtimestamp(
            latest_pred.stat().st_mtime
        ).isoformat()

    # Determine if ready
    ready = predictions_available

    if ready:
        message = (
            f"Ready for backtest. {models_count} models available, predictions found."
        )
    elif models_count > 0:
        message = (
            "Models available but no predictions found. Please run training first."
        )
    else:
        message = "No models or predictions available. Please run training first."

    return BacktestStatusResponse(
        ready=ready,
        message=message,
        models_count=models_count,
        predictions_available=predictions_available,
        latest_model=latest_model,
        latest_prediction_time=latest_prediction_time,
    )


@router.post("/run", response_model=BacktestResponse)
def execute_backtest(request: Optional[BacktestRequest] = None):
    """
    Execute backtest using latest predictions.

    This endpoint runs backtest independently from training workflow.
    It uses the latest predictions from MLflow artifacts.

    Args:
        request: Backtest configuration (all fields optional with defaults)

    Returns:
        Backtest results including returns and metrics
    """
    service = get_qlib_workflow_service()

    # Use default values if no request body provided
    if request is None:
        request = BacktestRequest()

    try:
        result = service.execute_backtest(
            pred_path=request.pred_path,
            start_time=request.start_time,
            end_time=request.end_time,
            benchmark=request.benchmark,
            topk=request.topk,
            n_drop=request.n_drop,
            account=request.account,
        )

        if result.get("status") == "error":
            return BacktestResponse(
                status="error",
                message="Backtest failed",
                error=result.get("error"),
            )

        return BacktestResponse(
            status="success",
            message="Backtest completed successfully",
            start_time=result.get("start_time"),
            end_time=result.get("end_time"),
            trading_days=result.get("trading_days", 0),
            total_return=result.get("total_return", 0.0),
            total_cost=result.get("total_cost", 0.0),
            net_return=result.get("net_return", 0.0),
            final_account=result.get("final_account", 0.0),
        )

    except Exception as e:
        return BacktestResponse(
            status="error",
            message="Backtest failed",
            error=str(e),
        )
