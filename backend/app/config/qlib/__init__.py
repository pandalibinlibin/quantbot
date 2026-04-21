"""
Qlib Configuration Module

This module provides centralized configuration management for Qlib-related settings.
Business logic configurations are stored in YAML files under this directory.
Path configurations are read from environment variables via app.core.config.settings.

Configuration Files:
- system_config.yaml: Data source, stock pool, freq, region, MongoDB, Online Serving
- training_config.yaml: Model configuration, dataset configuration, training parameters
- backtest_config.yaml: Strategy configuration, backtest parameters, trading costs
- paper_trading_config.yaml: Portfolio settings, strategy settings, risk management
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Configuration file paths
CONFIG_DIR = Path(__file__).parent
SYSTEM_CONFIG_FILE = CONFIG_DIR / "system_config.yaml"
TRAINING_CONFIG_FILE = CONFIG_DIR / "training_config.yaml"
BACKTEST_CONFIG_FILE = CONFIG_DIR / "backtest_config.yaml"
PAPER_TRADING_CONFIG_FILE = CONFIG_DIR / "paper_trading_config.yaml"


def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    """Load a YAML configuration file."""
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        else:
            logger.warning(f"Config file not found: {file_path}")
            return {}
    except Exception as e:
        logger.error(f"Failed to load config {file_path}: {e}")
        return {}


class QlibConfig:
    """
    Centralized Qlib configuration manager.

    Loads and provides access to all Qlib-related configurations from YAML files.
    """

    _instance: Optional["QlibConfig"] = None
    _config: Dict[str, Any] = {}
    _training_config: Dict[str, Any] = {}
    _backtest_config: Dict[str, Any] = {}
    _paper_trading_config: Dict[str, Any] = {}
    _loaded: bool = False

    def __new__(cls) -> "QlibConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self.reload()

    def reload(self) -> None:
        """Reload all configuration files."""
        try:
            # Load system config
            self._config = load_yaml_config(SYSTEM_CONFIG_FILE)
            logger.info(f"Loaded system config from {SYSTEM_CONFIG_FILE}")

            # Load training config
            self._training_config = load_yaml_config(TRAINING_CONFIG_FILE)
            logger.info(f"Loaded training config from {TRAINING_CONFIG_FILE}")

            # Load backtest config
            self._backtest_config = load_yaml_config(BACKTEST_CONFIG_FILE)
            logger.info(f"Loaded backtest config from {BACKTEST_CONFIG_FILE}")

            # Load paper trading config
            self._paper_trading_config = load_yaml_config(PAPER_TRADING_CONFIG_FILE)
            logger.info(f"Loaded paper trading config from {PAPER_TRADING_CONFIG_FILE}")

            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load Qlib configs: {e}")
            self._config = {}
            self._training_config = {}
            self._backtest_config = {}
            self._paper_trading_config = {}

    @property
    def data(self) -> Dict[str, Any]:
        """Get data configuration section."""
        return self._config.get("data", {})

    @property
    def freq(self) -> str:
        """Get data frequency (only 'day' is supported in stock selection system)."""
        return "day"

    @property
    def source(self) -> str:
        """Get data source: 'tushare' (A-shares), 'eod' (US stocks via EOD Historical Data)."""
        return self.data.get("source", "tushare")

    @property
    def stock_pool(self) -> str:
        """Get stock pool: 'etf_universe'."""
        return self.data.get("stock_pool", "etf_universe")

    @property
    def region(self) -> str:
        """Get market region: 'cn' or 'us'."""
        return self.data.get("region", "cn")

    @property
    def download_days(self) -> int:
        """Get download range in days."""
        download_days_config = self.data.get("download_days", {})
        return download_days_config.get("day", 365)

    @property
    def qlib_data_path(self) -> str:
        """Get Qlib data path (from environment settings)."""
        from app.core.config import settings

        return settings.QLIB_DATA_PATH

    @property
    def qlib_data_path_day(self) -> str:
        """Get day-level Qlib data path (from environment settings)."""
        from app.core.config import settings

        return settings.QLIB_DATA_PATH

    @property
    def csv_data_path(self) -> str:
        """Get CSV data path (from environment settings)."""
        from app.core.config import settings

        return settings.CSV_DATA_PATH

    @property
    def mlruns_path(self) -> str:
        """Get MLflow runs path (from YAML config)."""
        return self._config.get("paths", {}).get("mlruns", "/app/mlruns")

    @property
    def mongodb(self) -> Dict[str, str]:
        """Get MongoDB configuration."""
        return self._config.get("mongodb", {})

    @property
    def mongodb_uri(self) -> str:
        """Get MongoDB URI."""
        return self.mongodb.get("uri", "mongodb://mongodb:27017")

    @property
    def mongodb_database(self) -> str:
        """Get MongoDB database name."""
        return self.mongodb.get("database", "quantbot_qlib")

    @property
    def online_serving(self) -> Dict[str, Any]:
        """Get online serving configuration."""
        return self._config.get("online_serving", {})

    @property
    def experiment_name(self) -> str:
        """Get online serving experiment name."""
        return self.online_serving.get("experiment_name", "quantbot_online")

    @property
    def rolling_step(self) -> int:
        """Get rolling step in trading days."""
        return self.online_serving.get("rolling_step", 20)

    @property
    def rolling_type(self) -> str:
        """Get rolling type: 'expanding' or 'sliding'."""
        return self.online_serving.get("rolling_type", "expanding")

    @property
    def paper_trading(self) -> Dict[str, Any]:
        """Get paper trading configuration (from paper_trading_config.yaml)."""
        return self._paper_trading_config

    @property
    def initial_cash(self) -> float:
        """Get paper trading initial cash."""
        portfolio = self._paper_trading_config.get("portfolio", {})
        return portfolio.get("initial_cash", 100000000.0)

    @property
    def topk(self) -> int:
        """Get paper trading topk (number of stocks to hold)."""
        strategy = self._paper_trading_config.get("strategy", {})
        return strategy.get("topk", 50)

    @property
    def n_drop(self) -> int:
        """Get paper trading n_drop (number of stocks to drop each day)."""
        strategy = self._paper_trading_config.get("strategy", {})
        return strategy.get("n_drop", 5)

    # Training config accessors
    @property
    def training_config(self) -> Dict[str, Any]:
        """Get training configuration (from training_config.yaml)."""
        return self._training_config

    @property
    def task_config(self) -> Dict[str, Any]:
        """Get task configuration for training."""
        return self._training_config.get("task", {})

    # Backtest config accessors
    @property
    def backtest_config(self) -> Dict[str, Any]:
        """Get backtest configuration (from backtest_config.yaml)."""
        return self._backtest_config

    @property
    def backtest_strategy(self) -> Dict[str, Any]:
        """Get backtest strategy configuration."""
        return self._backtest_config.get("strategy", {})

    @property
    def backtest_params(self) -> Dict[str, Any]:
        """Get backtest parameters."""
        return self._backtest_config.get("backtest", {})

    @property
    def data_quality(self) -> Dict[str, Any]:
        """Get data quality check configuration."""
        return self._config.get("data_quality", {})

    @property
    def enhanced_indexing_config(self) -> Dict[str, Any]:
        """Get enhanced indexing configuration."""
        return self._config.get("enhanced_indexing", {})

    def get_data_config_hash(self) -> str:
        """
        Get a hash string representing current data configuration.
        Used to detect configuration changes.
        """
        return f"{self.freq}|{self.source}|{self.stock_pool}|{self.region}|{self.download_days}"

    def to_dict(self) -> Dict[str, Any]:
        """Return all configurations as dictionary."""
        return {
            "system": self._config,
            "training": self._training_config,
            "backtest": self._backtest_config,
            "paper_trading": self._paper_trading_config,
        }


# Global singleton instance
qlib_config = QlibConfig()
