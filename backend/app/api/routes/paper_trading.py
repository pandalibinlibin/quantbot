"""
Paper Trading API routes.

This module provides REST API endpoints for paper trading operations:
- GET /portfolio: Get current portfolio status
- POST /plan: Generate percentage-based trading plan
- POST /execute: Execute paper trades
- GET /trades: Get trade history
- GET /performance: Get performance metrics
- POST /reset: Reset paper trading state

Key Design:
- Trading plans use PERCENTAGES instead of absolute quantities
- Sell orders: sell_pct (percentage of position to sell)
- Buy orders: target_weight (percentage of total assets to allocate)
- This ensures consistency between paper trading and real trading
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging

from app.services.paper_trading_service import get_paper_trading_service
from app.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models


class PositionItem(BaseModel):
    """Single position item."""

    instrument: str
    shares: int
    avg_cost: float
    current_value: float


class PortfolioResponse(BaseModel):
    """Response model for portfolio endpoint."""

    success: bool
    cash: float = 0.0
    positions: List[PositionItem] = []
    position_count: int = 0
    total_position_value: float = 0.0
    total_value: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


class SellOrder(BaseModel):
    """Sell order in trading plan."""

    instrument: str
    direction: str = "SELL"
    sell_pct: float  # Percentage of position to sell (usually 100%)
    current_weight: float  # Current weight in portfolio
    reference_price: float
    limit_price: float  # Limit order price (reference_price * (1 - max_slippage))
    score: float
    reason: str
    instruction: str  # Trading instruction for trader


class BuyOrder(BaseModel):
    """Buy order in trading plan."""

    instrument: str
    direction: str = "BUY"
    target_weight: float  # Target percentage of total assets
    reference_price: float
    limit_price: float  # Limit order price (reference_price * (1 + max_slippage))
    score: float
    instruction: str  # Trading instruction for trader
    score_rank: int


class HoldOrder(BaseModel):
    """Hold order in trading plan."""

    instrument: str
    direction: str = "HOLD"
    current_weight: float
    target_weight: float
    score: float
    score_rank: int


class PortfolioSummary(BaseModel):
    """Portfolio summary in trading plan."""

    total_value: float
    cash: float
    position_value: float
    position_count: int


class PlanSummary(BaseModel):
    """Summary of trading plan."""

    sell_count: int
    buy_count: int
    hold_count: int


class ExecutedTrade(BaseModel):
    """Executed trade item."""

    instrument: str
    direction: str
    shares: Optional[int] = None
    price: Optional[float] = None
    value: Optional[float] = None
    sell_pct: Optional[float] = None
    target_weight: Optional[float] = None
    executed_at: Optional[str] = None


class LastExecutedTrades(BaseModel):
    """Last executed trades summary."""

    sells: List[ExecutedTrade] = []
    buys: List[ExecutedTrade] = []
    sell_count: int = 0
    buy_count: int = 0


class TradingPlanRequest(BaseModel):
    """Request model for trading plan endpoint."""

    date: Optional[str] = Field(
        None,
        description="Date in YYYY-MM-DD format (None for latest)",
        example="2026-02-13",
    )
    topk: int = Field(
        50,
        description="Number of stocks to hold",
        ge=1,
        le=500,
    )
    n_drop: int = Field(
        5,
        description="Number of stocks to drop each day",
        ge=0,
        le=50,
    )
    slippage: float = Field(
        0.001,
        description="Expected slippage for price estimation (default 0.1%)",
        ge=0,
        le=0.1,
    )


class TradingPlanResponse(BaseModel):
    """Response model for trading plan endpoint."""

    success: bool
    date: Optional[str] = None
    generated_at: Optional[str] = None
    strategy: str = "TopkDropout"
    topk: int = 50
    n_drop: int = 5
    target_weight_per_stock: float = 2.0
    slippage: float = 0.001
    portfolio_summary: Optional[PortfolioSummary] = None
    sell_orders: List[SellOrder] = []
    buy_orders: List[BuyOrder] = []
    hold_orders: List[HoldOrder] = []
    summary: Optional[PlanSummary] = None
    last_executed_trades: Optional[LastExecutedTrades] = None
    error: Optional[str] = None


class ExecuteRequest(BaseModel):
    """Request model for execute endpoint."""

    date: Optional[str] = Field(
        None,
        description="Date in YYYY-MM-DD format (None for latest)",
        example="2026-02-13",
    )
    topk: int = Field(
        50,
        description="Number of stocks to hold",
        ge=1,
        le=500,
    )
    n_drop: int = Field(
        5,
        description="Number of stocks to drop each day",
        ge=0,
        le=50,
    )
    slippage: float = Field(
        0.001,
        description="Slippage for price simulation (default 0.1%)",
        ge=0,
        le=0.1,
    )
    dry_run: bool = Field(
        False,
        description="If True, simulate without saving",
    )


class TradeItem(BaseModel):
    """Single trade item."""

    date: str
    instrument: str
    action: str
    shares: int
    price: float
    value: float
    sell_pct: Optional[float] = None  # For sell orders
    target_weight: Optional[float] = None  # For buy orders
    executed_at: str


class TradingPlanSummary(BaseModel):
    """Trading plan summary included in execute response."""

    sell_orders: List[Dict[str, Any]] = []
    buy_orders: List[Dict[str, Any]] = []
    hold_orders: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}


class ExecuteResponse(BaseModel):
    """Response model for execute endpoint."""

    success: bool
    date: Optional[str] = None
    dry_run: bool = False
    slippage: float = 0.001
    sells_executed: int = 0
    buys_executed: int = 0
    executed_sells: List[TradeItem] = []
    executed_buys: List[TradeItem] = []
    final_cash: float = 0.0
    final_position_count: int = 0
    trading_plan: Optional[TradingPlanSummary] = None
    error: Optional[str] = None


class TradesRequest(BaseModel):
    """Request model for trades endpoint."""

    limit: int = Field(
        100,
        description="Maximum number of trades to return",
        ge=1,
        le=1000,
    )
    instrument: Optional[str] = Field(
        None,
        description="Filter by instrument",
    )


class TradesResponse(BaseModel):
    """Response model for trades endpoint."""

    success: bool
    total_trades: int = 0
    trades: List[TradeItem] = []
    error: Optional[str] = None


class PerformanceResponse(BaseModel):
    """Response model for performance endpoint."""

    success: bool
    initial_cash: float = 0.0
    current_value: float = 0.0
    total_return: float = 0.0
    total_return_pct: str = "0.00%"
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    trading_days: int = 0
    position_count: int = 0
    # Extended metrics
    annualized_return: Optional[float] = None
    annualized_return_pct: Optional[str] = None
    max_drawdown: Optional[float] = None
    max_drawdown_pct: Optional[str] = None
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    win_rate_pct: Optional[str] = None
    error: Optional[str] = None


class ResetResponse(BaseModel):
    """Response model for reset endpoint."""

    success: bool
    message: str = ""
    error: Optional[str] = None


# API Endpoints


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio():
    """
    Get current portfolio status.

    Returns cash balance, positions, and total value.
    """
    try:
        service = get_paper_trading_service()
        result = service.get_portfolio()

        # Convert positions to response format
        positions = [PositionItem(**p) for p in result.get("positions", [])]

        return PortfolioResponse(
            success=result.get("success", False),
            cash=result.get("cash", 0.0),
            positions=positions,
            position_count=result.get("position_count", 0),
            total_position_value=result.get("total_position_value", 0.0),
            total_value=result.get("total_value", 0.0),
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get portfolio: {str(e)}"
        )


@router.post("/plan", response_model=TradingPlanResponse)
def get_trading_plan(request: TradingPlanRequest = None):
    """
    Generate a percentage-based trading plan.

    Returns trading plan with:
    - sell_orders: stocks to sell with sell_pct (percentage of position)
    - buy_orders: stocks to buy with target_weight (percentage of total assets)
    - hold_orders: stocks to hold

    This plan can be given to traders for execution.
    The percentage-based design ensures consistency between paper trading and real trading.
    """
    try:
        service = get_paper_trading_service()

        date = request.date if request else None
        topk = request.topk if request else 50
        n_drop = request.n_drop if request else 5
        slippage = request.slippage if request else 0.001

        result = service.get_trading_plan(
            date=date, topk=topk, n_drop=n_drop, slippage=slippage
        )

        # Convert last_executed_trades even for error responses
        last_executed_trades = None
        if result.get("last_executed_trades"):
            let_data = result["last_executed_trades"]
            last_executed_trades = LastExecutedTrades(
                sells=[ExecutedTrade(**s) for s in let_data.get("sells", [])],
                buys=[ExecutedTrade(**b) for b in let_data.get("buys", [])],
                sell_count=let_data.get("sell_count", 0),
                buy_count=let_data.get("buy_count", 0),
            )

        if not result.get("success"):
            return TradingPlanResponse(
                success=False,
                error=result.get("error"),
                last_executed_trades=last_executed_trades,
            )

        # Convert to response format
        sell_orders = [SellOrder(**s) for s in result.get("sell_orders", [])]
        buy_orders = [BuyOrder(**b) for b in result.get("buy_orders", [])]
        hold_orders = [HoldOrder(**h) for h in result.get("hold_orders", [])]

        portfolio_summary = None
        if result.get("portfolio_summary"):
            portfolio_summary = PortfolioSummary(**result["portfolio_summary"])

        summary = None
        if result.get("summary"):
            summary = PlanSummary(**result["summary"])

        return TradingPlanResponse(
            success=True,
            date=result.get("date"),
            generated_at=result.get("generated_at"),
            strategy=result.get("strategy", "TopkDropout"),
            topk=result.get("topk", topk),
            n_drop=result.get("n_drop", n_drop),
            target_weight_per_stock=result.get("target_weight_per_stock", 2.0),
            slippage=result.get("slippage", slippage),
            portfolio_summary=portfolio_summary,
            sell_orders=sell_orders,
            buy_orders=buy_orders,
            hold_orders=hold_orders,
            summary=summary,
            last_executed_trades=last_executed_trades,
        )

    except Exception as e:
        logger.error(f"Failed to generate trading plan: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate trading plan: {str(e)}"
        )


@router.post("/execute", response_model=ExecuteResponse)
def execute_trades(request: ExecuteRequest = None):
    """
    Execute paper trades based on percentage-based trading plan.

    Uses market order simulation with slippage:
    - Buy price = reference_price * (1 + slippage)
    - Sell price = reference_price * (1 - slippage)

    Use dry_run=True to simulate without saving.
    """
    try:
        service = get_paper_trading_service()

        date = request.date if request else None
        topk = request.topk if request else 50
        n_drop = request.n_drop if request else 5
        slippage = request.slippage if request else 0.001
        dry_run = request.dry_run if request else False

        result = service.execute_trades(
            date=date, topk=topk, n_drop=n_drop, slippage=slippage, dry_run=dry_run
        )

        # Convert trades to response format
        executed_sells = [TradeItem(**t) for t in result.get("executed_sells", [])]
        executed_buys = [TradeItem(**t) for t in result.get("executed_buys", [])]

        # Convert trading plan to response format
        trading_plan_data = result.get("trading_plan")
        trading_plan = None
        if trading_plan_data:
            trading_plan = TradingPlanSummary(
                sell_orders=trading_plan_data.get("sell_orders", []),
                buy_orders=trading_plan_data.get("buy_orders", []),
                hold_orders=trading_plan_data.get("hold_orders", []),
                summary=trading_plan_data.get("summary", {}),
            )

        response = ExecuteResponse(
            success=result.get("success", False),
            date=result.get("date"),
            dry_run=result.get("dry_run", False),
            slippage=result.get("slippage", slippage),
            sells_executed=result.get("sells_executed", 0),
            buys_executed=result.get("buys_executed", 0),
            executed_sells=executed_sells,
            executed_buys=executed_buys,
            final_cash=result.get("final_cash", 0.0),
            final_position_count=result.get("final_position_count", 0),
            trading_plan=trading_plan,
            error=result.get("error"),
        )

        # Send email notification if execution was successful and not dry run
        if result.get("success") and not dry_run:
            try:
                notification_service = get_notification_service()
                # Build email data from result
                email_data = {
                    "date": result.get("date"),
                    "strategy": "TopkDropout",
                    "sells_executed": result.get("sells_executed", 0),
                    "buys_executed": result.get("buys_executed", 0),
                    "sell_orders": (
                        trading_plan_data.get("sell_orders", [])
                        if trading_plan_data
                        else []
                    ),
                    "buy_orders": (
                        trading_plan_data.get("buy_orders", [])
                        if trading_plan_data
                        else []
                    ),
                    "portfolio": {
                        "total_value": result.get("final_cash", 0)
                        + sum(
                            t.get("value", 0) for t in result.get("executed_buys", [])
                        ),
                        "cash": result.get("final_cash", 0),
                    },
                }
                email_result = notification_service.send_trading_plan_email(email_data)
                if email_result.get("success"):
                    logger.info(
                        f"Trading plan email sent: {email_result.get('message')}"
                    )
                else:
                    logger.warning(
                        f"Failed to send trading plan email: {email_result.get('error')}"
                    )
            except Exception as email_error:
                logger.warning(f"Email notification failed: {email_error}")

        return response

    except Exception as e:
        logger.error(f"Failed to execute trades: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to execute trades: {str(e)}"
        )


@router.get("/trades", response_model=TradesResponse)
def get_trade_history(limit: int = 100, instrument: Optional[str] = None):
    """
    Get trade history.

    Returns list of executed trades, optionally filtered by instrument.
    """
    try:
        service = get_paper_trading_service()
        result = service.get_trade_history(limit=limit, instrument=instrument)

        # Convert trades to response format
        trades = [TradeItem(**t) for t in result.get("trades", [])]

        return TradesResponse(
            success=result.get("success", False),
            total_trades=result.get("total_trades", 0),
            trades=trades,
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to get trade history: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get trade history: {str(e)}"
        )


@router.get("/performance", response_model=PerformanceResponse)
def get_performance():
    """
    Get paper trading performance metrics.

    Returns total return, trade statistics, and other metrics.
    """
    try:
        service = get_paper_trading_service()
        result = service.get_performance()

        return PerformanceResponse(
            success=result.get("success", False),
            initial_cash=result.get("initial_cash", 0.0),
            current_value=result.get("current_value", 0.0),
            total_return=result.get("total_return", 0.0),
            total_return_pct=result.get("total_return_pct", "0.00%"),
            total_trades=result.get("total_trades", 0),
            buy_trades=result.get("buy_trades", 0),
            sell_trades=result.get("sell_trades", 0),
            trading_days=result.get("trading_days", 0),
            position_count=result.get("position_count", 0),
            annualized_return=result.get("annualized_return"),
            annualized_return_pct=result.get("annualized_return_pct"),
            max_drawdown=result.get("max_drawdown"),
            max_drawdown_pct=result.get("max_drawdown_pct"),
            sharpe_ratio=result.get("sharpe_ratio"),
            win_rate=result.get("win_rate"),
            win_rate_pct=result.get("win_rate_pct"),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to get performance: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get performance: {str(e)}"
        )


@router.post("/reset", response_model=ResetResponse)
def reset_paper_trading():
    """
    Reset paper trading state.

    Clears all positions, trades, and daily records.
    Use with caution - this cannot be undone.
    """
    try:
        service = get_paper_trading_service()
        result = service.reset()

        return ResetResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to reset paper trading: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to reset paper trading: {str(e)}"
        )


# ============== Notification API ==============


class NotificationConfig(BaseModel):
    """Notification configuration model."""

    enabled: bool = False
    recipients: List[str] = []
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_tls: Optional[bool] = True
    from_email: Optional[str] = None
    from_name: Optional[str] = "QuantBot"
    updated_at: Optional[str] = None


class NotificationConfigResponse(BaseModel):
    """Response model for notification config."""

    success: bool
    config: Optional[NotificationConfig] = None
    error: Optional[str] = None


class UpdateNotificationConfigRequest(BaseModel):
    """Request model for updating notification config."""

    enabled: Optional[bool] = None
    recipients: Optional[List[str]] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: Optional[bool] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None


class AddRecipientRequest(BaseModel):
    """Request model for adding a recipient."""

    email: str


class RecipientResponse(BaseModel):
    """Response model for recipient operations."""

    success: bool
    message: Optional[str] = None
    recipients: Optional[List[str]] = None
    error: Optional[str] = None


class TestEmailRequest(BaseModel):
    """Request model for sending test email."""

    recipient: Optional[str] = None


class TestEmailResponse(BaseModel):
    """Response model for test email."""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


@router.get("/notification/config", response_model=NotificationConfigResponse)
def get_notification_config():
    """
    Get current notification configuration.

    Returns notification settings including enabled status, recipients, and SMTP config.
    """
    try:
        service = get_notification_service()
        result = service.get_config()

        config = None
        if result.get("config"):
            config = NotificationConfig(**result["config"])

        return NotificationConfigResponse(
            success=result.get("success", False),
            config=config,
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to get notification config: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get notification config: {str(e)}"
        )


@router.put("/notification/config", response_model=NotificationConfigResponse)
def update_notification_config(request: UpdateNotificationConfigRequest):
    """
    Update notification configuration.

    Allows updating enabled status, recipients, and SMTP settings.
    """
    try:
        service = get_notification_service()
        result = service.update_config(
            enabled=request.enabled,
            recipients=request.recipients,
            smtp_host=request.smtp_host,
            smtp_port=request.smtp_port,
            smtp_user=request.smtp_user,
            smtp_password=request.smtp_password,
            smtp_tls=request.smtp_tls,
            from_email=request.from_email,
            from_name=request.from_name,
        )

        config = None
        if result.get("config"):
            config = NotificationConfig(**result["config"])

        return NotificationConfigResponse(
            success=result.get("success", False),
            config=config,
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to update notification config: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update notification config: {str(e)}"
        )


@router.post("/notification/recipient", response_model=RecipientResponse)
def add_recipient(request: AddRecipientRequest):
    """
    Add a recipient email address.
    """
    try:
        service = get_notification_service()
        result = service.add_recipient(request.email)

        return RecipientResponse(
            success=result.get("success", False),
            message=result.get("message"),
            recipients=result.get("recipients"),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to add recipient: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to add recipient: {str(e)}"
        )


@router.delete("/notification/recipient/{email}", response_model=RecipientResponse)
def remove_recipient(email: str):
    """
    Remove a recipient email address.
    """
    try:
        service = get_notification_service()
        result = service.remove_recipient(email)

        return RecipientResponse(
            success=result.get("success", False),
            message=result.get("message"),
            recipients=result.get("recipients"),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to remove recipient: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to remove recipient: {str(e)}"
        )


@router.post("/notification/test", response_model=TestEmailResponse)
def send_test_email(request: TestEmailRequest = None):
    """
    Send a test email to verify notification configuration.

    Optionally specify a recipient, otherwise uses the first configured recipient.
    """
    try:
        service = get_notification_service()
        recipient = request.recipient if request else None
        result = service.send_test_email(recipient=recipient)

        return TestEmailResponse(
            success=result.get("success", False),
            message=result.get("message"),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to send test email: {str(e)}"
        )
