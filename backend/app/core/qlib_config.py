"""
Qlib configuration settings.
This module defines all Qlib-related configuration parameters.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class QlibSettings(BaseSettings):
    """
    Qlib configuration settings.

    These settings control how Qlib is initialized and used.
    """

    # Qlib data directory
    # This is where Qlib stores market data in binary format
    QLIB_DATA_DIR: str = "/app/qlib_data"

    # Qlib region: "cn" for China market, "us" for US market
    QLIB_REGION: str = "cn"

    # MLflow experiment tracking directory
    # Qlib uses MLflow to track experiments and results
    QLIB_MLRUNS_DIR: str = "/app/mlruns"

    # Redis configuration for Qlib caching
    # Qlib uses Redis for distributed caching to improve performance
    QLIB_REDIS_HOST: str = "redis"
    QLIB_REDIS_PORT: int = 6379

    # Enable expression cache
    # This caches factor calculation results for faster recomputation
    QLIB_EXPRESSION_CACHE: bool = True

    # Enable dataset cache
    # This caches prepared datasets for faster loading
    QLIB_DATASET_CACHE: bool = True

    # Logging level for Qlib
    QLIB_LOGGING_LEVEL: str = "INFO"

    class Config:
        case_sensitive = True
        env_file = ".env"


@lru_cache()
def get_qlib_settings() -> QlibSettings:
    """
    Get cached Qlib settings instance.

    Using lru_cache ensures we only create one settings instance.
    This is a form of singleton pattern.

    Returns:
        QlibSettings: The cached Qlib settings instance.
    """
    return QlibSettings()
