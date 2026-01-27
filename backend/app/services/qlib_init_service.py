"""
Qlib initialization service.
This service manages Qlib initialization and ensure it's only initialized once.
"""

import logging
import qlib
from qlib.constant import REG_CN, REG_US
from app.core.qlib_config import get_qlib_settings
from app.core.timer import Timer

logger = logging.getLogger(__name__)


class QlibInitService:
    """
    Service for managing Qlib initialization.

    This class ensures Qlib is initialized only once and provides
    a centralized place for initialization logic.

    Design Pattern: Singleton Pattern
    - Only one instance of this class should exist
    - Qlib can only be initialized once per process
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """
        Create or return the singleton instance.

        This method is called before __init__ when creating an instance.
        It ensures only one instance exists.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the service (only runs once due to singleton.)"""
        # Don't re-initialize if already done
        if not hasattr(self, "settings"):
            self.settings = get_qlib_settings()

    def initialize(self) -> bool:
        """
        Initialize Qlib with configured settings.

        This method can be called multiple times safely - it will only
        initialize Qlib once.

        Returns:
            bool: True if initialization was successful or already done

        Raises:
            Exception: If Qlib initialization fails
        """
        if self._initialized:
            logger.info("Qlib already initialized, skipping")
            return True

        try:
            with Timer("qlib_initialization"):
                # Map region string to Qlib constant
                region = REG_CN if self.settings.QLIB_REGION == "cn" else REG_US

                logger.info(
                    f"Initializing Qlib with region: {self.settings.QLIB_REGION}"
                )
                logger.info(f"Data directory: {self.settings.QLIB_DATA_DIR}")
                logger.info(f"MLflow directory: {self.settings.QLIB_MLRUNS_DIR}")

                # Initialize Qlib
                qlib.init(
                    provider_uri=self.settings.QLIB_DATA_DIR,
                    region=region,
                    exp_manager={
                        "class": "MLflowExpManager",
                        "module_path": "qlib.workflow.expm",
                        "kwargs": {
                            "uri": f"file://{self.settings.QLIB_MLRUNS_DIR}",
                            "default_exp_name": "quantbot",
                        },
                    },
                    redis_host=self.settings.QLIB_REDIS_HOST,
                    redis_port=self.settings.QLIB_REDIS_PORT,
                    expression_cache=self.settings.QLIB_EXPRESSION_CACHE,
                    dataset_cache=self.settings.QLIB_DATASET_CACHE,
                    logging_level=self.settings.QLIB_LOGGING_LEVEL,
                )

                self._initialized = True
                logger.info("✅ Qlib initialized successfully")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qlib: {str(e)}")
            raise

    def is_initialized(self) -> bool:
        """
        Check if Qlib is initialized.

        Returns:
            bool: True if Qlib is initialized
        """
        return self._initialized

    @classmethod
    def reset(cls):
        """
        Reset the initialization state.

        WARNING: This is mainly for testing purpose.
        In production, Qlib should only be initialized once per process.
        """
        cls._initialized = False
        logger.warning("⚠️  Qlib initialization state reset")


# Global instance (singleton)
qlib_init_service = QlibInitService()
