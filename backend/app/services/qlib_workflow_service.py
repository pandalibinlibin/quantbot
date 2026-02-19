"""
Qlib Training Workflow Service

This service executes Qlib training workflows based on YAML configuration.
Design follows qrun's _exe_task implementation pattern from qlib/model/trainer.py.

Key Features:
- Load training configuration from YAML file (no frontend config needed)
- Check data availability before training
- Support both day and minute frequency data
- Execute Record templates (SignalRecord for predictions)
- Save trained models to filesystem for later use

Usage:
    service = get_qlib_workflow_service()
    result = service.execute_training_from_config()  # Uses default config file
"""

import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from qlib.workflow import R
from qlib.utils import init_instance_by_config, fill_placeholder
from qlib.model.base import Model
from qlib.data.dataset import Dataset

from app.services.qlib_init_service import get_qlib_init_service
from app.core.timer import WorkflowTimer
from app.core.config import settings

logger = logging.getLogger(__name__)

# Model storage directory
MODELS_DIR = Path(settings.QLIB_DATA_PATH).parent / "models"

# Training configuration file path
CONFIG_DIR = Path(__file__).parent.parent / "config"
TRAINING_CONFIG_PATH = CONFIG_DIR / "training_config.yaml"


class QlibWorkflowService:
    """
    Service for executing Qlib workflows

    This service takes a workflow configuration and executes it using
    Qlib's workflow system. It handles model training, dataset preparation,
    and result recording.

    Design follows qrun's _exe_task implementation pattern.

    Key responsibilities:
    - Check data availability before training
    - Accept workflow configuration
    - Execute Qlib workflow with CustomFactorHandler
    - Execute Record templates (SignalRecord, PortAnaRecord)
    - Save trained models to filesystem
    - Return training results
    """

    def __init__(self):
        """Initialize the workflow service."""
        self.logger = logger
        # Ensure models directory exists
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

    def load_training_config(
        self, config_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Load training configuration from YAML file.

        Args:
            config_path: Path to config file (uses default if None)

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file does not exist
            yaml.YAMLError: If config file is invalid
        """
        if config_path is None:
            config_path = TRAINING_CONFIG_PATH

        if not config_path.exists():
            raise FileNotFoundError(f"Training config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self.logger.info(f"Loaded training config from: {config_path}")
        return config

    def execute_training_from_config(
        self, config_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute training workflow using configuration from file.

        This is the simplified entry point for training - just loads config
        from file and executes the workflow. No frontend configuration needed.

        Args:
            config_path: Path to config file (uses default if None)

        Returns:
            Training result dictionary
        """
        # Load configuration from file
        config = self.load_training_config(config_path)

        # Extract parameters from config
        experiment_name = config.get("experiment_name", "default")
        freq = config.get("freq", "day")
        model_name = config.get("model_name", None)

        # Execute training workflow
        return self.execute_training_workflow(
            config=config,
            experiment_name=experiment_name,
            model_name=model_name,
            freq=freq,
        )

    def get_provider_uri(self, freq: str = "day") -> str:
        """
        Get the correct provider_uri based on data frequency.

        Args:
            freq: Data frequency ("day", "1d", "1min", "1m")

        Returns:
            Path to the Qlib data directory
        """
        if freq in ("1min", "1m"):
            return str(settings.QLIB_DATA_PATH_1MIN)
        else:
            return str(settings.QLIB_DATA_PATH)

    def check_data_exists(self, freq: str = "day") -> Dict[str, Any]:
        """
        Check if required data exists for training.

        Args:
            freq: Data frequency to check

        Returns:
            Dictionary with:
                - exists: bool - whether data is available
                - message: str - status message
                - details: dict - detailed status of each component
        """
        provider_uri = Path(self.get_provider_uri(freq))

        details = {
            "provider_uri": str(provider_uri),
            "directory_exists": provider_uri.exists(),
            "calendars_exists": False,
            "instruments_exists": False,
            "features_exists": False,
            "calendar_count": 0,
            "instruments_count": 0,
            "features_count": 0,
        }

        if not provider_uri.exists():
            return {
                "exists": False,
                "message": f"Data directory does not exist: {provider_uri}",
                "details": details,
            }

        # Check calendars
        calendars_dir = provider_uri / "calendars"
        if calendars_dir.exists():
            calendar_files = list(calendars_dir.glob("*.txt"))
            details["calendars_exists"] = len(calendar_files) > 0
            details["calendar_count"] = len(calendar_files)

        # Check instruments
        instruments_dir = provider_uri / "instruments"
        if instruments_dir.exists():
            instruments_files = list(instruments_dir.glob("*.txt"))
            details["instruments_exists"] = len(instruments_files) > 0
            details["instruments_count"] = len(instruments_files)

        # Check features
        features_dir = provider_uri / "features"
        if features_dir.exists():
            # Count stock directories with .bin files
            stock_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
            details["features_exists"] = len(stock_dirs) > 0
            details["features_count"] = len(stock_dirs)

        # Determine overall status
        all_exists = (
            details["calendars_exists"]
            and details["instruments_exists"]
            and details["features_exists"]
        )

        if all_exists:
            message = f"Data available: {details['features_count']} stocks, {details['calendar_count']} calendars"
        else:
            missing = []
            if not details["calendars_exists"]:
                missing.append("calendars")
            if not details["instruments_exists"]:
                missing.append("instruments")
            if not details["features_exists"]:
                missing.append("features")
            message = f"Missing data components: {', '.join(missing)}"

        return {
            "exists": all_exists,
            "message": message,
            "details": details,
        }

    def execute_training_workflow(
        self,
        config: Dict[str, Any],
        experiment_name: str = "default",
        model_name: Optional[str] = None,
        freq: str = "day",
    ) -> Dict[str, Any]:
        """
        Execute a training workflow to train a new model.

        This is the main entry point for running a complete training workflow.
        Design follows qrun's _exe_task implementation pattern.

        Workflow steps:
        1. Check data availability
        2. Initialize Qlib with correct provider_uri
        3. Dataset preparation (using CustomFactorHandler)
        4. Model training
        5. Execute Records (SignalRecord, PortAnaRecord)
        6. Save model to filesystem

        Args:
            config: Workflow configuration dictionary with structure:
                {
                    "task": {
                        "model": {...},
                        "dataset": {...},
                        "record": [...] (optional)
                    }
                }
            experiment_name: Name of the experiment for tracking
            model_name: Name for the saved model file (auto-generated if None)
            freq: Data frequency ("day" or "1min")

        Returns:
            Dictionary containing:
                - status: "success" or "error"
                - model_path: Path to saved model
                - predictions_count: Number of predictions
                - timings: Execution time for each step
                - records: Results from Record templates

        Raises:
            ValueError: If data is not available
            Exception: If workflow execution fails
        """
        timer = WorkflowTimer()

        # Step 1: Check data availability
        with timer.step("data_check"):
            data_status = self.check_data_exists(freq)
            if not data_status["exists"]:
                raise ValueError(
                    f"Data not available for training. {data_status['message']}. "
                    "Please download data first using the Data Collection page."
                )
            self.logger.info(f"Data check passed: {data_status['message']}")

        # Step 2: Initialize Qlib (uses multi-frequency provider_uri from settings)
        with timer.step("qlib_init"):
            provider_uri = self.get_provider_uri(freq)
            qlib_service = get_qlib_init_service()
            # Initialize Qlib (it handles multi-frequency internally)
            qlib_service.initialize()
            self.logger.info(f"Qlib initialized, using provider_uri: {provider_uri}")

        try:
            # Start MLflow experiment
            with timer.step("experiment_setup"):
                with R.start(experiment_name=experiment_name):
                    self.logger.info(f"Started experiment: {experiment_name}")

                    # Execute workflow steps (following qrun's _exe_task pattern)
                    result = self._execute_workflow_steps(config, timer, model_name)

                    # Add timing information
                    result["timings"] = timer.get_summary()

                    self.logger.info("✅ Workflow completed successfully")
                    return result

        except Exception as e:
            self.logger.error(f"❌ Workflow execution failed: {str(e)}")
            raise

    def _execute_workflow_steps(
        self,
        config: Dict[str, Any],
        timer: WorkflowTimer,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the main workflow steps following qrun's _exe_task pattern.

        This method orchestrates the workflow steps:
        1. Dataset preparation
        2. Model training
        3. Save model to MLflow and filesystem
        4. Execute Record templates (SignalRecord, PortAnaRecord, etc.)

        Args:
            config: Workflow configuration dictionary
            timer: Timer for tracking execution time
            model_name: Name for the saved model file

        Returns:
            Dictionary with workflow results including metrics and model path
        """
        task_config = config.get("task", {})

        # Step 1: Create dataset
        with timer.step("dataset_preparation"):
            dataset = self._create_dataset(task_config.get("dataset", {}))
            self.logger.info("Dataset prepared successfully")

        # Step 2: Create and train model
        with timer.step("model_training"):
            model = self._create_and_train_model(task_config.get("model", {}), dataset)
            self.logger.info("Model trained successfully")

        # Step 3: Save model to MLflow (following qrun pattern)
        with timer.step("model_saving"):
            R.save_objects(**{"params.pkl": model})
            # Save dataset config for online inference (without concrete data)
            dataset.config(dump_all=False, recursive=True)
            R.save_objects(**{"dataset": dataset})
            self.logger.info("Model saved to MLflow")

        # Step 4: Save model to filesystem
        with timer.step("model_export"):
            model_path = self._save_model_to_filesystem(model, model_name)
            self.logger.info(f"Model exported to: {model_path}")

        # Step 5: Execute Record templates (following qrun pattern)
        record_results = []
        records_config = task_config.get("record", [])
        if records_config:
            with timer.step("record_execution"):
                record_results = self._execute_records(
                    records_config, model, dataset, task_config
                )
                self.logger.info(f"Executed {len(record_results)} records")

        # Step 6: Generate predictions on TEST set only (not entire dataset)
        with timer.step("prediction"):
            # Prepare test data only for prediction count
            test_data = dataset.prepare(
                segments="test",
                col_set="feature",
                data_key="learn",  # Use learn data key
            )
            test_predictions = model.predict(dataset, segment="test")
            test_count = len(test_predictions) if test_predictions is not None else 0
            self.logger.info(f"Test set predictions: {test_count}")

        return {
            "status": "success",
            "model_path": model_path,
            "test_predictions_count": test_count,
            "model_saved": True,
            "records": record_results,
            "experiment_name": None,  # Will be filled by caller
        }

    def _save_model_to_filesystem(
        self, model: Model, model_name: Optional[str] = None
    ) -> str:
        """
        Save trained model to filesystem.

        Args:
            model: Trained model object
            model_name: Name for the model file (auto-generated if None)

        Returns:
            Path to the saved model file
        """
        if model_name is None:
            # Generate model name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_class = type(model).__name__
            model_name = f"{model_class}_{timestamp}"

        # Ensure .pkl extension
        if not model_name.endswith(".pkl"):
            model_name = f"{model_name}.pkl"

        model_path = MODELS_DIR / model_name

        # Save model using pickle
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        self.logger.info(f"Model saved to filesystem: {model_path}")
        return str(model_path)

    def _execute_records(
        self,
        records_config: List[Dict[str, Any]],
        model: Model,
        dataset: Dataset,
        task_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Execute Record templates following qrun's _exe_task pattern.

        This method executes SignalRecord, PortAnaRecord, and other Record templates
        to generate predictions, backtest results, and analysis.

        Args:
            records_config: List of record configurations
            model: Trained model
            dataset: Dataset used for training
            task_config: Full task configuration

        Returns:
            List of record execution results
        """
        results = []
        rec = R.get_recorder()

        # Fill placeholders in task_config (following qrun pattern)
        placeholder_value = {"<MODEL>": model, "<DATASET>": dataset}
        task_config = fill_placeholder(task_config, placeholder_value)

        # Handle single dict config
        if isinstance(records_config, dict):
            records_config = [records_config]

        for record_config in records_config:
            try:
                record_class = record_config.get("class", "Unknown")
                self.logger.info(f"Executing record: {record_class}")

                # Initialize record instance (following qrun pattern)
                record = init_instance_by_config(
                    record_config,
                    recorder=rec,
                    default_module="qlib.workflow.record_temp",
                    try_kwargs={"model": model, "dataset": dataset},
                )

                # Generate record
                record.generate()

                results.append(
                    {
                        "class": record_class,
                        "status": "success",
                    }
                )
                self.logger.info(f"Record {record_class} executed successfully")

            except Exception as e:
                self.logger.error(f"Record {record_class} failed: {str(e)}")
                results.append(
                    {
                        "class": record_config.get("class", "Unknown"),
                        "status": "error",
                        "error": str(e),
                    }
                )

        return results

    def _create_dataset(self, dataset_config: Dict[str, Any]):
        """
        Create dataset from configuration.

        This method uses Qlib's init_instance_by_config to create a dataset
        object based on the provided configuration.

        Args:
            dataset_config: Dataset configuration dictionary

        Returns:
            Initialized dataset object (e.g., DatasetH instance)
        """
        self.logger.info("Creating dataset from configuration...")
        dataset = init_instance_by_config(dataset_config)
        return dataset

    def _create_and_train_model(self, model_config: Dict[str, Any], dataset):
        """
        Create and train model from configuration.

        This method:
        1. Creates a model instance using init_instance_by_config
        2. Trains the model using the fit() method (model will handle data preparation internally)

        Args:
            model_config: Model configuration dictionary
            dataset: Dataset object created by _create_dataset

        Returns:
            Trained model object
        """
        self.logger.info("Creating model from configuration...")
        model = init_instance_by_config(model_config)

        self.logger.info("Training model...")
        model.fit(dataset)

        self.logger.info("Model training completed")
        return model

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all trained models in the models directory.

        Returns:
            List of model information dictionaries
        """
        models = []
        if MODELS_DIR.exists():
            for model_file in MODELS_DIR.glob("*.pkl"):
                stat = model_file.stat()
                models.append(
                    {
                        "name": model_file.stem,
                        "path": str(model_file),
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                    }
                )
        return sorted(models, key=lambda x: x["modified_at"], reverse=True)

    def load_model(self, model_name: str) -> Model:
        """
        Load a trained model from filesystem.

        Args:
            model_name: Name of the model (with or without .pkl extension)

        Returns:
            Loaded model object

        Raises:
            FileNotFoundError: If model file does not exist
        """
        if not model_name.endswith(".pkl"):
            model_name = f"{model_name}.pkl"

        model_path = MODELS_DIR / model_name

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        self.logger.info(f"Model loaded from: {model_path}")
        return model


# Global instance
qlib_workflow_service = QlibWorkflowService()


def get_qlib_workflow_service() -> QlibWorkflowService:
    """Get the global QlibWorkflowService instance."""
    return qlib_workflow_service
