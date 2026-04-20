from fastapi import APIRouter

from app.api.routes import (
    items,
    login,
    private,
    users,
    utils,
    data_source,
    factors,
    training,
    online,
    paper_trading,
    models,
    backtest,
    dashboard,
    scheduler,
    run_task,
    update_data,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)

# Quantbot API routes - organized by domain
api_router.include_router(
    data_source.router, prefix="/data-source", tags=["Data Source"]
)
api_router.include_router(factors.router, prefix="/factors", tags=["Factors"])
api_router.include_router(models.router, prefix="/models", tags=["Models"])
api_router.include_router(training.router, prefix="/training", tags=["Training"])
api_router.include_router(online.router, prefix="/online", tags=["Online Serving"])
api_router.include_router(
    paper_trading.router, prefix="/paper-trading", tags=["Paper Trading"]
)
api_router.include_router(backtest.router, prefix="/backtest", tags=["Backtest"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["Scheduler"])
api_router.include_router(
    update_data.router, prefix="/update-data", tags=["Update Data"]
)
api_router.include_router(run_task.router, prefix="/run-task", tags=["Run Task"])

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
