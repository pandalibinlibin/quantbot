"""
Model handler service
Provides unified interface for all model handlers
"""

import logging
from typing import List, Dict, Any


class ModelHandlerRegistry:
    """
    Registry for model handlers
    Similar to FactorHandlerRegistry
    """

    def __init__(self):
        self._handlers = {}
        self.logger = logging.getLogger(__name__)

    def register(self, handler):
        """
        Register a model handler
        Args:
            handler: Model handler instance to register
        Raises:
            ValueError: If handler with same name already registered
        """
        if handler.name in self._handlers:
            existing_handler = self._handlers[handler.name]
            if existing_handler is handler:
                # Same instance, skip silently
                self.logger.debug(
                    f"Handler '{handler.name}' already registered (same instance)"
                )
                return
            else:
                # Different instance with same name - this is an error
                raise ValueError(
                    f"Model handler '{handler.name}' is already registered. "
                    f"Cannot register duplicate handler names."
                )
        self._handlers[handler.name] = handler
        self.logger.info(f"Registered model handler: {handler.name}")

    def get(self, name: str):
        """
        Get a model handler by name
        Args:
            name: Handler name
        Returns:
            Handler instance or None if not found
        """
        return self._handlers.get(name)

    def list_handler_names(self) -> List[str]:
        """
        List all registered handler names
        Returns:
            List of handler names
        """

        return list(self._handlers.keys())


class ModelHandlerService:
    """
    Service layer for model training and prediction
    Provides unified interface for all model handlers
    Similar to FactorHandlerService
    """

    def __init__(self):
        """
        Initialize ModelHandlerService
        """
        self.registry = ModelHandlerRegistry()
        self.logger = logging.getLogger(__name__)
        self._register_handlers()

    def _register_handlers(self):
        """Register all available model handlers"""
        from .models.lightgbm_handler import LightGBMHandler

        try:
            # Register LightGBM handler
            self.registry.register(LightGBMHandler())
            self.logger.info("Registered LightGBMHandler")
        except ValueError as e:
            self.logger.warning(f"Failed to register LightGBMHandler: {e}")

        # Future: register other handlers
        # try:
        #     self.registry.register(MLPHandler())
        # except ValueError as e:
        #     self.logger.warning(f"Failed to register MLPHandler: {e}")

    def get_handlers_info(self) -> List[Dict[str, str]]:
        """
        Get information about all registered handlers
        Returns:
            List of handler info dictionaries
        """
        handlers = self.registry.list_handler_names()
        result = []
        for name in handlers:
            handler = self.registry.get(name)
            if handler:
                result.append(
                    {
                        "name": handler.name,
                        "description": handler.description,
                    }
                )
        return result


# Singleton instance
_model_handler_service_instance = None


def get_model_handler_service() -> ModelHandlerService:
    """
    Get ModelHandlerService singleton instance

    Educational Notes:
    - Singleton Pattern: Only one instance exists
    - Ensures all API calls use the same service
    """
    global _model_handler_service_instance
    if _model_handler_service_instance is None:
        _model_handler_service_instance = ModelHandlerService()

    return _model_handler_service_instance
