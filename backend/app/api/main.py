from fastapi import APIRouter

from app.api.routes import (
    datasources,
    factors,
    items,
    login,
    models,
    strategies,
    private,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(datasources.router)
api_router.include_router(factors.router)
api_router.include_router(models.router)
api_router.include_router(strategies.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
