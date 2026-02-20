"""
Backtest API Routes

Endpoints for backtesting strategies using model predictions.
"""

import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path

from app.services.qlib_workflow_service import get_qlib_workflow_service
from app.core.config import settings

router = APIRouter()

# File path for persisting latest backtest result
BACKTEST_RESULTS_DIR = Path(settings.QLIB_DATA_PATH).parent / "backtest_results"
LATEST_RESULT_FILE = BACKTEST_RESULTS_DIR / "latest_result.json"


def _save_backtest_result(result: dict) -> None:
    """Save backtest result to JSON file."""
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LATEST_RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2)


def _load_backtest_result() -> Optional[dict]:
    """Load backtest result from JSON file."""
    if LATEST_RESULT_FILE.exists():
        with open(LATEST_RESULT_FILE, "r") as f:
            return json.load(f)
    return None


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

    benchmark: str = "SH000300"  # Benchmark symbol
    topk: int = 50  # Number of stocks to hold
    n_drop: int = 5  # Number of stocks to drop each day
    account: float = 100000000  # Initial account value


class BacktestResponse(BaseModel):
    """Response model for backtest endpoint."""

    status: str
    message: str
    data_start_time: Optional[str] = None  # Data range start (from bin files)
    data_end_time: Optional[str] = None  # Data range end (from bin files)
    start_time: Optional[str] = None  # Actual backtest start time
    end_time: Optional[str] = None  # Actual backtest end time
    trading_days: int = 0
    total_return: float = 0.0
    total_cost: float = 0.0
    net_return: float = 0.0
    final_account: float = 0.0
    error: Optional[str] = None


@router.get("/config")
def get_backtest_config():
    """
    Get current backtest configuration.

    Returns the strategy and backtest parameters from backtest_config.yaml.
    """
    service = get_qlib_workflow_service()

    try:
        config = service.load_backtest_config()
        return {
            "status": "success",
            "config": config,
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "error": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/latest-result")
def get_latest_backtest_result():
    """
    Get the latest backtest result.

    Returns the most recent backtest result if available.
    Result is loaded from persistent file storage.
    """
    result = _load_backtest_result()

    if result is None:
        return {
            "status": "no_result",
            "message": "No backtest has been run yet",
        }

    return {
        "status": "success",
        "result": result,
    }


@router.get("/status", response_model=BacktestStatusResponse)
def get_backtest_status():
    """
    Check if backtest is ready to run.

    Backtest requires a trained model to perform inference on all available data.
    Returns information about available models and data.
    """

    service = get_qlib_workflow_service()

    # Check for trained models
    models = service.list_models()
    models_count = len(models)
    latest_model = models[0]["name"] if models else None
    latest_model_time = models[0]["modified_at"] if models else None

    # Check for data availability
    data_status = service.check_data_exists()
    data_available = data_status.get("exists", False)

    # Determine if ready: need both model and data
    ready = models_count > 0 and data_available

    if ready:
        message = f"Ready for backtest. Model: {latest_model}, data available."
    elif models_count > 0 and not data_available:
        message = "Model available but no data found. Please download data first."
    elif models_count == 0 and data_available:
        message = "Data available but no model found. Please train a model first."
    else:
        message = "No model or data available. Please download data and train a model."

    return BacktestStatusResponse(
        ready=ready,
        message=message,
        models_count=models_count,
        predictions_available=data_available,  # Reuse field to indicate data availability
        latest_model=latest_model,
        latest_prediction_time=latest_model_time,  # Reuse field for model time
    )


@router.post("/run", response_model=BacktestResponse)
def execute_backtest(request: Optional[BacktestRequest] = None):
    """
    Execute backtest using model inference on all available data.

    This endpoint:
    1. Loads the latest trained model
    2. Loads all feature data from bin files (excluding labels)
    3. Uses the model to generate predictions on all data
    4. Executes backtest using the predictions
    5. Saves result to persistent file storage

    Args:
        request: Backtest configuration (all fields optional with defaults)

    Returns:
        Backtest results including returns, metrics, and data time range
    """
    service = get_qlib_workflow_service()

    # Use default values if no request body provided
    if request is None:
        request = BacktestRequest()

    try:
        result = service.execute_backtest(
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

        # Save the successful result to persistent file
        backtest_result = {
            "status": "success",
            "message": "Backtest completed successfully",
            "data_start_time": result.get("data_start_time"),
            "data_end_time": result.get("data_end_time"),
            "start_time": result.get("start_time"),
            "end_time": result.get("end_time"),
            "trading_days": result.get("trading_days", 0),
            "total_return": result.get("total_return", 0.0),
            "total_cost": result.get("total_cost", 0.0),
            "net_return": result.get("net_return", 0.0),
            "final_account": result.get("final_account", 0.0),
            "executed_at": datetime.now().isoformat(),
        }
        _save_backtest_result(backtest_result)

        return BacktestResponse(
            status="success",
            message="Backtest completed successfully",
            data_start_time=result.get("data_start_time"),
            data_end_time=result.get("data_end_time"),
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
