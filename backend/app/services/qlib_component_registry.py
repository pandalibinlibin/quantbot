"""
Qlib Component Registry Service.
Maps component class names to their module paths and default hyperparameters.
"""

from typing import Dict, Any
from app.config.model_hyperparameters import get_model_hyperparameters


class QlibComponentRegistry:
    """
    Registry for Qlib component class names and their module paths.

    This service provides a centralized mapping of component class names
    to their Python module paths, allowing the frontend to only send
    class names while the backend automatically fills in the module paths.
    """

    # Model class name to module path mapping
    MODEL_REGISTRY: Dict[str, str] = {
        "LGBModel": "qlib.contrib.model.gbdt",
        "XGBModel": "qlib.contrib.model.gbdt",
        "CatBoostModel": "qlib.contrib.model.gbdt",
        "LinearModel": "qlib.contrib.model.linear",
        "MLPModel": "qlib.contrib.model.pytorch_nn",
        "GRUModel": "qlib.contrib.model.pytorch_gru",
        "LSTMModel": "qlib.contrib.model.pytorch_lstm",
        "GATs": "qlib.contrib.model.pytorch_gats",
        "ALSTM": "qlib.contrib.model.pytorch_alstm",
        "TransformerModel": "qlib.contrib.model.pytorch_transformer",
    }

    # Data handler class name to module path mapping
    HANDLER_REGISTRY: Dict[str, str] = {
        "Alpha158": "qlib.contrib.data.handler",
        "Alpha101": "qlib.contrib.data.handler",
        "Alpha360": "qlib.contrib.data.handler",
        "DataHandlerLP": "qlib.contrib.data.handler",
    }

    # Dataset class name to module path mapping
    DATASET_REGISTRY: Dict[str, str] = {
        "DatasetH": "qlib.data.dataset",
        "TSDatasetH": "qlib.data.dataset",
    }

    @classmethod
    def get_model_module_path(cls, class_name: str) -> str:
        """
        Get module path for a model class name.

        Args:
            class_name: Model class name (e.g., "LGBModel")

        Returns:
            Module path (e.g., "qlib.contrib.model.gbdt")

        Raises:
            ValueError: If class name is not found in registry
        """
        if class_name not in cls.MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model class: {class_name}. "
                f"Available models: {list(cls.MODEL_REGISTRY.keys())}"
            )
        return cls.MODEL_REGISTRY[class_name]

    @classmethod
    def get_handler_module_path(cls, class_name: str) -> str:
        """
        Get module path for a data handler class name.

        Args:
            class_name: Handler class name (e.g., "Alpha158")

        Returns:
            Module path (e.g., "qlib.contrib.data.handler")

        Raises:
            ValueError: If class name is not found in registry
        """
        if class_name not in cls.HANDLER_REGISTRY:
            raise ValueError(
                f"Unknown handler class: {class_name}. "
                f"Available handlers: {list(cls.HANDLER_REGISTRY.keys())}"
            )
        return cls.HANDLER_REGISTRY[class_name]

    @classmethod
    def get_dataset_module_path(cls, class_name: str) -> str:
        """
        Get module path for a dataset class name.

        Args:
            class_name: Dataset class name (e.g., "DatasetH")

        Returns:
            Module path (e.g., "qlib.data.dataset")

        Raises:
            ValueError: If class name is not found in registry
        """
        if class_name not in cls.DATASET_REGISTRY:
            raise ValueError(
                f"Unknown dataset class: {class_name}. "
                f"Available datasets: {list(cls.DATASET_REGISTRY.keys())}"
            )
        return cls.DATASET_REGISTRY[class_name]

    @classmethod
    def enrich_config_with_module_paths(cls, config: Dict) -> Dict:
        """
        Automatically fill in module_path fields and default hyperparameters.

        This method takes a configuration dict with only class names and
        automatically adds:
        1. The corresponding module_path fields
        2. Default hyperparameters (if not provided by user)

        Args:
            config: Configuration dict with structure:
                {
                    "task": {
                        "model": {"class": "LGBModel", "kwargs": {...}},
                        "dataset": {
                            "class": "DatasetH",
                            "kwargs": {
                                "handler": {"class": "Alpha158", "kwargs": {...}},
                                "segments": {...}
                            }
                        }
                    }
                }

        Returns:
            Enriched configuration with module_path and default hyperparameters
        """
        enriched_config = config.copy()

        # Add module_path and default hyperparameters for model
        if "task" in enriched_config and "model" in enriched_config["task"]:
            model_config = enriched_config["task"]["model"]
            if "class" in model_config:
                model_class = model_config["class"]

                # Add module_path
                model_config["module_path"] = cls.get_model_module_path(model_class)

                # Add default hyperparameters if kwargs is empty or not provided
                if not model_config.get("kwargs"):
                    try:
                        model_config["kwargs"] = get_model_hyperparameters(model_class)
                    except ValueError:
                        # If hyperparameters not found, use empty dict
                        model_config["kwargs"] = {}

        # Add module_path for dataset
        if "task" in enriched_config and "dataset" in enriched_config["task"]:
            dataset_config = enriched_config["task"]["dataset"]
            if "class" in dataset_config:
                dataset_config["module_path"] = cls.get_dataset_module_path(
                    dataset_config["class"]
                )

            # Add module_path for handler
            if "kwargs" in dataset_config and "handler" in dataset_config["kwargs"]:
                handler_config = dataset_config["kwargs"]["handler"]
                if "class" in handler_config:
                    handler_config["module_path"] = cls.get_handler_module_path(
                        handler_config["class"]
                    )

        return enriched_config


# Global instance
qlib_component_registry = QlibComponentRegistry()
