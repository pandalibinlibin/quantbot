from fastapi import APIRouter

from app.api.routes import (
    items,
    login,
    models,
    model_trainings,
    backtests,
    strategies,
    private,
    users,
    utils,
    data_collection,
    factor_handlers,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(models.router)
api_router.include_router(model_trainings.router)
api_router.include_router(backtests.router)
api_router.include_router(strategies.router)
api_router.include_router(data_collection.router)
api_router.include_router(
    factor_handlers.router,
    prefix="/factor-handlers",
    tags=["factor-handlers"],
)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
