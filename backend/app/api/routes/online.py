"""
Online Serving API routes.

This module provides REST API endpoints for Qlib Online Serving operations:
- POST /routine: Execute daily routine (main entry point)
- GET /status: Get current status
- GET /signals: Get latest trading signals
- POST /reset: Reset state (for debugging)

The routine endpoint is the main entry point that should be called
by a scheduled task (e.g., cron job) after market close each day.

Note: Backtest functionality has been moved to /api/v1/backtest router.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging

from app.services.online_serving_service import get_online_serving_service
from app.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models


class RoutineRequest(BaseModel):
    """Request model for routine endpoint."""

    cur_time: Optional[str] = Field(
        None,
        description="Current time in YYYY-MM-DD format. None for latest.",
        example="2025-02-22",
    )


class StepResult(BaseModel):
    """Result of a single step in the routine."""

    step: str
    success: bool
    duration_seconds: Optional[float] = None
    details: Dict[str, Any] = {}


class PortfolioItem(BaseModel):
    """Single item in target portfolio."""

    rank: int
    instrument: str
    benchmark_weight: float
    score: float
    target_weight: float
    deviation: float
    deviation_pct: str
    action: str


class PortfolioSummary(BaseModel):
    """Summary of target portfolio."""

    benchmark: str
    benchmark_name: str
    total_stocks: int
    total_weight: float
    overweight_count: int
    underweight_count: int
    neutral_count: int
    max_deviation: float
    generated_at: str
    target_date: str


class RoutineResponse(BaseModel):
    """Response model for routine endpoint."""

    success: bool
    message: Optional[str] = None
    cur_time: Optional[str] = None
    executed_at: str
    steps: List[StepResult] = []
    total_duration_seconds: Optional[float] = None
    error: Optional[str] = None
    target_portfolio: Optional[List[Any]] = (
        None  # Allow any structure to preserve all fields
    )
    portfolio_summary: Optional[Dict[str, Any]] = (
        None  # Allow any structure for ETF Enhanced Indexing
    )
    # ETF Enhanced Indexing fields
    generated_at: Optional[str] = None
    trade_date: Optional[str] = None
    signal_for_date: Optional[str] = None
    total_value: Optional[float] = None
    region: Optional[str] = None
    lot_size: Optional[int] = None
    weights: Optional[Dict[str, Any]] = None
    strategy: Optional[str] = None


class DataRange(BaseModel):
    """Data range information."""

    start_date: str
    end_date: str


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    is_initialized: bool
    freq: str
    last_routine_time: Optional[str] = None
    initialization_error: Optional[str] = None
    config: Dict[str, Any] = {}
    data_range: Optional[DataRange] = None
    signal_count: Optional[int] = None


class SignalItem(BaseModel):
    """Single signal item."""

    datetime: Optional[str] = None
    instrument: Optional[str] = None
    key: Optional[str] = None
    score: float


class SignalsResponse(BaseModel):
    """Response model for signals endpoint."""

    success: bool
    signal_count: int = 0
    signals: List[SignalItem] = []
    error: Optional[str] = None


class ResetResponse(BaseModel):
    """Response model for reset endpoint."""

    success: bool
    message: str


# API Endpoints


@router.post("/routine", response_model=RoutineResponse)
def execute_routine(request: RoutineRequest = None):
    """
    Execute daily routine (main entry point).

    This endpoint should be called by a scheduled task after market close.
    It performs the following steps:
    1. Auto-initializes Online Serving if not yet initialized
    2. Updates data incrementally
    3. Executes OnlineManager.routine() - checks training, updates models
    4. Generates trading signals

    The first call will take longer as it needs to initialize and train
    initial models.
    """
    try:
        service = get_online_serving_service()
        cur_time = request.cur_time if request else None

        logger.info(f"Executing routine with cur_time={cur_time}")
        result = service.routine(cur_time=cur_time)

        # Convert to response model
        steps = [
            StepResult(
                step=s["step"],
                success=s["success"],
                duration_seconds=s.get("duration_seconds"),
                details=s.get("details", {}),
            )
            for s in result.get("steps", [])
        ]

        # Pass through target_portfolio as-is to preserve all fields
        target_portfolio = result.get("target_portfolio")

        # Pass through portfolio_summary as-is to preserve all fields (ETF Enhanced Indexing format)
        portfolio_summary = result.get("portfolio_summary")

        response = RoutineResponse(
            success=result.get("success", False),
            message=result.get("message"),
            cur_time=result.get("cur_time"),
            executed_at=result.get("executed_at", ""),
            steps=steps,
            total_duration_seconds=result.get("total_duration_seconds"),
            error=result.get("error"),
            target_portfolio=target_portfolio,
            portfolio_summary=portfolio_summary,
            # ETF Enhanced Indexing fields
            generated_at=result.get("generated_at"),
            trade_date=result.get("trade_date"),
            signal_for_date=result.get("signal_for_date"),
            total_value=result.get("total_value"),
            region=result.get("region"),
            lot_size=result.get("lot_size"),
            weights=result.get("weights"),
            strategy=result.get("strategy"),
        )

        # Note: Email notification is now handled in online_serving_service._send_etf_portfolio_email()
        # which is called during _calculate_enhanced_indexing(). No need to send duplicate email here.

        return response

    except Exception as e:
        logger.error(f"Routine execution failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Routine execution failed: {str(e)}"
        )


@router.get("/status", response_model=StatusResponse)
def get_status():
    """
    Get current status of Online Serving.

    Returns information about:
    - Initialization state
    - Data frequency
    - Last routine execution time
    - Configuration
    - Online models count
    """
    try:
        service = get_online_serving_service()
        status = service.get_status()

        return StatusResponse(**status)

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/signals", response_model=SignalsResponse)
def get_signals():
    """
    Get latest trading signals.

    Returns the most recent trading signals generated by the online models.
    Signals include stock codes and prediction scores.

    Note: Returns at most 100 signals to limit response size.
    """
    try:
        service = get_online_serving_service()
        result = service.get_signals()

        # Convert signals to response format
        signals = []
        for s in result.get("signals", []):
            signals.append(
                SignalItem(
                    datetime=s.get("datetime"),
                    instrument=s.get("instrument"),
                    key=s.get("key"),
                    score=s.get("score", 0.0),
                )
            )

        return SignalsResponse(
            success=result.get("success", False),
            signal_count=result.get("signal_count", 0),
            signals=signals,
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to get signals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get signals: {str(e)}")


@router.post("/reset", response_model=ResetResponse)
def reset_state():
    """
    Reset Online Serving state (for debugging).

    This clears all state and allows re-initialization on the next
    routine call. Use with caution in production.
    """
    try:
        service = get_online_serving_service()
        result = service.reset()

        return ResetResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
        )

    except Exception as e:
        logger.error(f"Failed to reset state: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset state: {str(e)}")


# Holdings Management Endpoints


class HoldingsResponse(BaseModel):
    """Response model for holdings endpoints."""

    success: bool
    holdings: Dict[str, int] = {}
    position_count: int = 0
    updated_at: Optional[str] = None
    message: str = ""


class UpdateHoldingsRequest(BaseModel):
    """Request model for updating holdings."""

    holdings: Dict[str, int] = Field(..., description="Holdings dict: symbol -> shares")


@router.get("/holdings", response_model=HoldingsResponse)
def get_holdings():
    """
    Get current holdings state.

    Returns the persisted holdings that will be used for calculating
    the next day's trading signals.
    """
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )

        etf_service = get_etf_enhanced_indexing_service()
        holdings = etf_service._current_holdings.copy()

        # Try to get updated_at from file
        holdings_file = etf_service._get_holdings_file_path()
        updated_at = None
        if holdings_file.exists():
            import json

            with open(holdings_file, "r") as f:
                data = json.load(f)
                updated_at = data.get("updated_at")

        return HoldingsResponse(
            success=True,
            holdings=holdings,
            position_count=len(holdings),
            updated_at=updated_at,
            message=f"Current holdings: {len(holdings)} positions",
        )
    except Exception as e:
        logger.error(f"Failed to get holdings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get holdings: {str(e)}")


@router.post("/holdings", response_model=HoldingsResponse)
def update_holdings(request: UpdateHoldingsRequest):
    """
    Update current holdings state.

    Use this to manually set holdings if they differ from the
    auto-applied trades (e.g., partial fills, manual adjustments).
    """
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )

        etf_service = get_etf_enhanced_indexing_service()
        etf_service.save_holdings(request.holdings)

        return HoldingsResponse(
            success=True,
            holdings=etf_service._current_holdings.copy(),
            position_count=len(etf_service._current_holdings),
            message=f"Holdings updated: {len(request.holdings)} positions",
        )
    except Exception as e:
        logger.error(f"Failed to update holdings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update holdings: {str(e)}"
        )


@router.delete("/holdings", response_model=HoldingsResponse)
def clear_holdings():
    """
    Clear all holdings (reset to empty portfolio).

    Use with caution - this will make the next signal calculation
    assume you have no existing positions.
    """
    try:
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )

        etf_service = get_etf_enhanced_indexing_service()
        etf_service.save_holdings({})

        return HoldingsResponse(
            success=True,
            holdings={},
            position_count=0,
            message="Holdings cleared",
        )
    except Exception as e:
        logger.error(f"Failed to clear holdings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to clear holdings: {str(e)}"
        )
