"""
Qlib Training Workflow Service

This service executes Qlib training workflows based on YAML configuration.
Design follows qrun's _exe_task implementation pattern from qlib/model/trainer.py.

Key Features:
- Load training configuration from YAML file (no frontend config needed)
- Check data availability before training
- Daily frequency data for ETF stock selection
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
from app.services.etf_enhanced_indexing_service import get_etf_enhanced_indexing_service
from app.core.timer import WorkflowTimer
from app.core.config import settings

logger = logging.getLogger(__name__)

# Model storage directory
MODELS_DIR = Path(settings.QLIB_DATA_PATH).parent / "models"

# Configuration file paths (moved to config/qlib/ directory)
CONFIG_DIR = Path(__file__).parent.parent / "config" / "qlib"
TRAINING_CONFIG_PATH = CONFIG_DIR / "training_config.yaml"
BACKTEST_CONFIG_PATH = CONFIG_DIR / "backtest_config.yaml"


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

    def load_backtest_config(
        self, config_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Load backtest configuration from YAML file.

        Args:
            config_path: Path to config file (uses default if None)

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file does not exist
            yaml.YAMLError: If config file is invalid
        """
        if config_path is None:
            config_path = BACKTEST_CONFIG_PATH

        if not config_path.exists():
            raise FileNotFoundError(f"Backtest config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self.logger.info(f"Loaded backtest config from: {config_path}")
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
        model_name = config.get("model_name", None)

        # Use day frequency (only day-level data supported in stock selection system)
        freq = "day"

        # Execute training workflow
        return self.execute_training_workflow(
            config=config,
            experiment_name=experiment_name,
            model_name=model_name,
            freq=freq,
        )

    def get_provider_uri(self) -> str:
        """
        Get the provider_uri for day-level data.

        Returns:
            Path to the Qlib data directory
        """
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
            freq: Data frequency (only "day" is supported)

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

        # Step 2: Initialize Qlib
        with timer.step("qlib_init"):
            provider_uri = self.get_provider_uri()
            qlib_service = get_qlib_init_service()
            qlib_service.initialize()
            self.logger.info(f"Qlib initialized, using provider_uri: {provider_uri}")

        try:
            # Start MLflow experiment
            with timer.step("experiment_setup"):
                with R.start(experiment_name=experiment_name):
                    self.logger.info(f"Started experiment: {experiment_name}")

                    # Execute workflow steps (following qrun's _exe_task pattern)
                    result = self._execute_workflow_steps(
                        config, timer, model_name, freq
                    )

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
        freq: str = "day",
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
            freq: Data frequency (only "day" is supported)

        Returns:
            Dictionary with workflow results including metrics and model path
        """
        task_config = config.get("task", {})

        # Step 0: Get actual data time range and update config dynamically
        time_range = self._get_data_time_range()
        if time_range:
            task_config = self._apply_dynamic_time_config(task_config, time_range, freq)

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

        This method deletes all existing model files before saving the new one,
        ensuring only the latest model is kept in the system.

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

        # Delete all existing model files before saving new one
        for old_model in MODELS_DIR.glob("*.pkl"):
            try:
                old_model.unlink()
                self.logger.info(f"Deleted old model: {old_model}")
            except Exception as e:
                self.logger.warning(f"Failed to delete old model {old_model}: {e}")

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

        # Get actual data time range for dynamic backtest configuration
        data_time_range = self._get_data_time_range()

        for record_config in records_config:
            # For PortAnaRecord, dynamically set backtest time range from actual data
            if record_config.get("class") == "PortAnaRecord" and data_time_range:
                record_config = self._update_backtest_time_range(
                    record_config, data_time_range
                )
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

    def _get_data_time_range(self) -> Optional[Dict[str, str]]:
        """
        Get actual data time range from Qlib calendar.

        Returns:
            Dictionary with 'start_time' and 'end_time' keys, or None if unavailable
        """
        try:
            from qlib.data import D

            # Get calendar from Qlib data
            calendar = D.calendar(freq="day")
            if calendar is not None and len(calendar) > 0:
                start_time = str(calendar[0])[:10]  # Format: YYYY-MM-DD
                end_time = str(calendar[-1])[:10]
                self.logger.info(
                    f"Data time range: {start_time} to {end_time} ({len(calendar)} trading days)"
                )
                return {"start_time": start_time, "end_time": end_time}
        except Exception as e:
            self.logger.warning(f"Failed to get data time range: {e}")
        return None

    def _update_backtest_time_range(
        self, record_config: Dict[str, Any], time_range: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Update PortAnaRecord backtest configuration with actual data time range.

        Note: We set start_time and end_time to None to let PortAnaRecord
        automatically extract time range from prediction results. This avoids
        index out of bounds errors caused by calendar boundary issues.

        Args:
            record_config: Original record configuration
            time_range: Dictionary with 'start_time' and 'end_time' (for logging only)

        Returns:
            Updated record configuration
        """
        import copy

        config = copy.deepcopy(record_config)

        # Navigate to backtest config
        kwargs = config.get("kwargs", {})
        port_config = kwargs.get("config", {})
        backtest = port_config.get("backtest", {})

        # Set to None to let PortAnaRecord auto-extract from predictions
        # This avoids index out of bounds errors
        backtest["start_time"] = None
        backtest["end_time"] = None

        # Ensure the nested structure exists
        if "kwargs" not in config:
            config["kwargs"] = {}
        if "config" not in config["kwargs"]:
            config["kwargs"]["config"] = {}
        config["kwargs"]["config"]["backtest"] = backtest

        self.logger.info(
            f"Backtest will auto-extract time range from predictions (data range: {time_range['start_time']} to {time_range['end_time']})"
        )
        return config

    def _apply_dynamic_time_config(
        self, task_config: Dict[str, Any], time_range: Dict[str, str], freq: str = "day"
    ) -> Dict[str, Any]:
        """
        Apply dynamic time configuration to all parts of task config.

        This method sets time ranges and freq for:
        - data_handler (start_time, end_time, fit_start_time, fit_end_time, freq)
        - segments (train, valid, test) with 70/15/15 split
        - backtest (start_time, end_time)

        Args:
            task_config: Original task configuration
            time_range: Dictionary with 'start_time' and 'end_time'
            freq: Data frequency (only "day" is supported)

        Returns:
            Updated task configuration with dynamic time ranges and freq
        """
        import copy
        from datetime import datetime, timedelta

        config = copy.deepcopy(task_config)
        start = datetime.strptime(time_range["start_time"], "%Y-%m-%d")
        end = datetime.strptime(time_range["end_time"], "%Y-%m-%d")
        total_days = (end - start).days

        # Calculate segment boundaries (70% train, 15% valid, 15% test)
        train_days = int(total_days * 0.70)
        valid_days = int(total_days * 0.15)

        train_end = start + timedelta(days=train_days)
        valid_start = train_end + timedelta(days=1)
        valid_end = valid_start + timedelta(days=valid_days)
        test_start = valid_end + timedelta(days=1)

        # Format dates
        fmt = "%Y-%m-%d"
        train_range = [start.strftime(fmt), train_end.strftime(fmt)]
        valid_range = [valid_start.strftime(fmt), valid_end.strftime(fmt)]
        test_range = [test_start.strftime(fmt), end.strftime(fmt)]

        self.logger.info(
            f"Dynamic time split: train={train_range}, valid={valid_range}, test={test_range}"
        )

        # Update dataset handler config
        dataset_config = config.get("dataset", {})
        kwargs = dataset_config.get("kwargs", {})
        handler_config = kwargs.get("handler", {})
        handler_kwargs = handler_config.get("kwargs", {})

        handler_kwargs["start_time"] = time_range["start_time"]
        handler_kwargs["end_time"] = time_range["end_time"]
        handler_kwargs["fit_start_time"] = time_range["start_time"]
        handler_kwargs["fit_end_time"] = valid_end.strftime(fmt)
        handler_kwargs["freq"] = freq  # Set freq dynamically

        # Update segments
        kwargs["segments"] = {
            "train": train_range,
            "valid": valid_range,
            "test": test_range,
        }

        # Ensure nested structure
        handler_config["kwargs"] = handler_kwargs
        kwargs["handler"] = handler_config
        dataset_config["kwargs"] = kwargs
        config["dataset"] = dataset_config

        return config

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

    def _find_latest_predictions(self, mlruns_dir: Path) -> Optional[Any]:
        """
        Find the latest pred.pkl file from MLflow artifacts.

        Args:
            mlruns_dir: Path to MLflow runs directory

        Returns:
            Loaded predictions DataFrame or None if not found
        """
        if not mlruns_dir.exists():
            self.logger.warning(f"MLflow runs directory not found: {mlruns_dir}")
            return None

        # Search for pred.pkl files in all experiments/runs
        pred_files = list(mlruns_dir.glob("**/pred.pkl"))
        if not pred_files:
            self.logger.warning("No pred.pkl files found in MLflow artifacts")
            return None

        # Sort by modification time, get latest
        latest_pred = max(pred_files, key=lambda p: p.stat().st_mtime)
        self.logger.info(f"Found latest predictions: {latest_pred}")

        with open(latest_pred, "rb") as f:
            pred = pickle.load(f)

        return pred

    def load_backtest_config(
        self, config_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Load backtest configuration from YAML file.

        Args:
            config_path: Path to config file (uses default if None)

        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = BACKTEST_CONFIG_PATH

        if not config_path.exists():
            self.logger.warning(
                f"Backtest config not found: {config_path}, using defaults"
            )
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self.logger.info(f"Loaded backtest config from: {config_path}")
        return config

    def execute_backtest(
        self,
        benchmark: Optional[str] = None,
        topk: Optional[int] = None,
        n_drop: Optional[int] = None,
        account: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute backtest using model inference on all available data.

        This method:
        1. Loads the latest trained model
        2. Loads all feature data from bin files (excluding labels)
        3. Uses the model to generate predictions on all data
        4. Executes backtest using the predictions

        Configuration is loaded from backtest_config.yaml, with API parameters
        overriding config file values.

        Args:
            benchmark: Benchmark symbol for comparison (overrides config).
            topk: Number of stocks to hold (overrides config).
            n_drop: Number of stocks to drop each day (overrides config).
            account: Initial account value (overrides config).

        Returns:
            Dictionary with backtest results including report, metrics, and data time range.
        """
        import pandas as pd
        from qlib.contrib.strategy import TopkDropoutStrategy
        from qlib.data.dataset import DatasetH

        # Load config from file
        config = self.load_backtest_config()
        strategy_config = config.get("strategy", {}).get("kwargs", {})
        backtest_config = config.get("backtest", {})

        # Use config values as defaults, API params override
        topk = topk if topk is not None else strategy_config.get("topk", 50)
        n_drop = n_drop if n_drop is not None else strategy_config.get("n_drop", 5)
        account = (
            account
            if account is not None
            else backtest_config.get("account", 100000000)
        )
        benchmark = (
            benchmark
            if benchmark is not None
            else backtest_config.get("benchmark", "000300.SH")
        )
        exchange_kwargs = backtest_config.get(
            "exchange_kwargs",
            {
                "limit_threshold": 0.095,
                "deal_price": "close",
                "open_cost": 0.0003,
                "close_cost": 0.0013,
                "min_cost": 5,
            },
        )

        # Use day frequency (only day-level data supported in stock selection system)
        freq = "day"
        self.logger.info(f"Backtest using freq: {freq}")

        # Initialize Qlib
        qlib_service = get_qlib_init_service()
        qlib_service.initialize()

        # Step 1: Load the latest model
        models = self.list_models()
        if not models:
            return {
                "status": "error",
                "error": "No trained model found. Please train a model first.",
            }

        latest_model_path = models[0]["path"]
        self.logger.info(f"Loading model from: {latest_model_path}")

        try:
            with open(latest_model_path, "rb") as f:
                model = pickle.load(f)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to load model: {str(e)}",
            }

        # Step 2: Get data time range from bin files
        time_range = self._get_data_time_range()
        if not time_range:
            return {
                "status": "error",
                "error": "Failed to get data time range from bin files.",
            }

        data_start_time = time_range["start_time"]
        data_end_time = time_range["end_time"]
        self.logger.info(f"Data time range: {data_start_time} to {data_end_time}")

        # Step 3: Create dataset for inference (features only, no labels)
        try:
            from app.services.custom_factor_handler import CustomFactorHandler

            handler = CustomFactorHandler(
                instruments="all",
                start_time=data_start_time,
                end_time=data_end_time,
                freq=freq,
                infer_processors=[],  # No processing needed for inference
            )

            dataset = DatasetH(
                handler=handler,
                segments={
                    "backtest": [data_start_time, data_end_time],
                },
            )

            self.logger.info("Dataset created for backtest inference")

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to create dataset: {str(e)}",
            }

        # Step 4: Generate predictions using the model
        try:
            pred = model.predict(dataset, segment="backtest")
            self.logger.info(f"Generated predictions: {len(pred)} records")

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to generate predictions: {str(e)}",
            }

        # Step 5: Auto-detect time range from predictions for backtest
        # Note: Qlib's backtest has boundary issues on the last period,
        # so we need to shift back by 1 period to avoid index out of bounds error
        dt_values = pred.index.get_level_values("datetime")
        start_time = str(dt_values.min())[:10]
        end_time = str(dt_values.max() - pd.Timedelta(days=1))[:10]

        self.logger.info(f"Backtest period: {start_time} to {end_time}")

        # Step 6: Create strategy and execute backtest
        strategy = TopkDropoutStrategy(
            signal=pred,
            topk=topk,
            n_drop=n_drop,
        )

        try:
            # Use general backtest function that supports any frequency
            from qlib.backtest import backtest as backtest_func
            from qlib.backtest.executor import SimulatorExecutor
            from qlib.utils.time import Freq

            # Create executor with correct frequency
            executor_config = {
                "time_per_step": freq,
                "generate_portfolio_metrics": True,
            }
            executor = SimulatorExecutor(**executor_config)

            # Update exchange_kwargs with correct frequency
            _exchange_kwargs = {
                "freq": freq,
                "limit_threshold": exchange_kwargs.get("limit_threshold", 0.095),
                "deal_price": exchange_kwargs.get("deal_price", "close"),
                "open_cost": exchange_kwargs.get("open_cost", 0.0003),
                "close_cost": exchange_kwargs.get("close_cost", 0.0013),
                "min_cost": exchange_kwargs.get("min_cost", 5),
            }

            # Execute backtest
            portfolio_metric_dict, indicator_dict = backtest_func(
                start_time=start_time,
                end_time=end_time,
                strategy=strategy,
                executor=executor,
                account=account,
                benchmark=benchmark,
                exchange_kwargs=_exchange_kwargs,
            )

            # Extract report from the correct frequency key
            analysis_freq = "{0}{1}".format(*Freq.parse(freq))
            report_df, positions = portfolio_metric_dict.get(analysis_freq)

            # Calculate metrics
            total_return = (
                report_df["return"].sum() if "return" in report_df.columns else 0
            )
            total_cost = report_df["cost"].sum() if "cost" in report_df.columns else 0

            result = {
                "status": "success",
                "data_start_time": start_time,  # Use actual backtest range
                "data_end_time": end_time,  # Use actual backtest range
                "start_time": start_time,
                "end_time": end_time,
                "trading_days": len(report_df),
                "total_return": float(total_return),
                "total_cost": float(total_cost),
                "net_return": float(total_return - total_cost),
                "final_account": (
                    float(report_df["account"].iloc[-1])
                    if "account" in report_df.columns
                    else account
                ),
            }

            self.logger.info(
                f"Backtest completed: {result['trading_days']} trading days, return={result['total_return']:.4f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Backtest failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
            }

    def execute_etf_backtest(
        self,
        account: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute backtest using ETFEnhancedIndexingService strategy.

        This method uses the same ETFEnhancedIndexingService that Routine uses,
        ensuring consistency between backtest validation and live trading signals.

        Workflow:
        1. Load the latest trained model
        2. Generate predictions (scores) for all available data
        3. For each trading day, use ETFEnhancedIndexingService to calculate target portfolio
        4. Simulate trading based on portfolio changes
        5. Calculate returns and metrics

        Args:
            account: Initial account value (overrides config)

        Returns:
            Dictionary with backtest results including daily returns, metrics, and portfolio history
        """
        import pandas as pd
        import numpy as np
        from qlib.data.dataset import DatasetH

        # Load config from file
        config = self.load_backtest_config()
        backtest_config = config.get("backtest", {})

        # Get account value
        account = (
            account if account is not None else backtest_config.get("account", 1000000)
        )

        # Get exchange kwargs for cost calculation
        exchange_kwargs = backtest_config.get(
            "exchange_kwargs",
            {
                "open_cost": 0.0003,
                "close_cost": 0.0013,
                "min_cost": 5,
            },
        )

        freq = "day"
        self.logger.info(f"ETF Backtest using freq: {freq}, account: {account}")

        # Initialize Qlib
        qlib_service = get_qlib_init_service()
        qlib_service.initialize()

        # Step 1: Load the latest model
        models = self.list_models()
        if not models:
            return {
                "status": "error",
                "error": "No trained model found. Please train a model first.",
            }

        latest_model_path = models[0]["path"]
        self.logger.info(f"Loading model from: {latest_model_path}")

        try:
            with open(latest_model_path, "rb") as f:
                model = pickle.load(f)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to load model: {str(e)}",
            }

        # Step 2: Get data time range
        time_range = self._get_data_time_range()
        if not time_range:
            return {
                "status": "error",
                "error": "Failed to get data time range.",
            }

        data_start_time = time_range["start_time"]
        data_end_time = time_range["end_time"]
        self.logger.info(f"Data time range: {data_start_time} to {data_end_time}")

        # Step 3: Create dataset for inference
        try:
            from app.services.custom_factor_handler import CustomFactorHandler

            handler = CustomFactorHandler(
                instruments="all",
                start_time=data_start_time,
                end_time=data_end_time,
                freq=freq,
                infer_processors=[],
            )

            dataset = DatasetH(
                handler=handler,
                segments={
                    "backtest": [data_start_time, data_end_time],
                },
            )

            self.logger.info("Dataset created for ETF backtest")

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to create dataset: {str(e)}",
            }

        # Step 4: Generate predictions (scores)
        try:
            pred = model.predict(dataset, segment="backtest")
            self.logger.info(f"Generated predictions: {len(pred)} records")

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to generate predictions: {str(e)}",
            }

        # Step 5: Get ETFEnhancedIndexingService
        etf_service = get_etf_enhanced_indexing_service()
        if not etf_service.enabled:
            return {
                "status": "error",
                "error": "ETFEnhancedIndexingService is not enabled. Check system_config.yaml.",
            }

        # Override total_value with backtest account
        original_total_value = etf_service.total_value
        etf_service.total_value = account

        # Step 6: Simulate trading day by day
        try:
            # Get unique trading dates
            dates = pred.index.get_level_values("datetime").unique().sort_values()
            self.logger.info(f"Simulating {len(dates)} trading days")

            # Initialize tracking variables
            daily_returns = []
            portfolio_history = []
            current_holdings = {}  # symbol -> shares
            current_cash = account
            prev_portfolio_value = account

            open_cost = exchange_kwargs.get("open_cost", 0.0003)
            close_cost = exchange_kwargs.get("close_cost", 0.0013)
            min_cost = exchange_kwargs.get("min_cost", 5)

            for i, date in enumerate(dates):
                date_str = str(date)[:10]

                # Get signals for this date
                try:
                    day_signals = pred.loc[date]
                    if isinstance(day_signals, pd.Series):
                        day_signals = day_signals.to_frame(name="score")

                    # Create proper DataFrame with MultiIndex for ETFEnhancedIndexingService
                    day_signals_df = pd.DataFrame(
                        {
                            "score": (
                                day_signals["score"].values
                                if "score" in day_signals.columns
                                else day_signals.iloc[:, 0].values
                            )
                        },
                        index=pd.MultiIndex.from_tuples(
                            [(date, inst) for inst in day_signals.index],
                            names=["datetime", "instrument"],
                        ),
                    )
                except Exception as e:
                    self.logger.warning(f"Skip date {date_str}: {e}")
                    continue

                # Calculate target portfolio using ETFEnhancedIndexingService
                try:
                    portfolio_data = etf_service.calculate_target_portfolio(
                        signals=day_signals_df,
                        trade_date=date_str,
                        current_holdings=current_holdings,
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Portfolio calculation failed for {date_str}: {e}"
                    )
                    continue

                positions = portfolio_data.get("positions", [])
                if not positions:
                    continue

                # Calculate trading costs and update holdings
                total_cost = 0
                for pos in positions:
                    symbol = pos.get("symbol", "")
                    action = pos.get("action", "hold")
                    action_shares = pos.get("action_shares", 0)
                    price = pos.get("reference_price", 0)

                    if action == "buy" and action_shares > 0:
                        trade_value = action_shares * price
                        cost = max(trade_value * open_cost, min_cost)
                        total_cost += cost
                        current_holdings[symbol] = (
                            current_holdings.get(symbol, 0) + action_shares
                        )
                        current_cash -= trade_value + cost

                    elif action == "sell" and action_shares > 0:
                        trade_value = action_shares * price
                        cost = max(trade_value * close_cost, min_cost)
                        total_cost += cost
                        current_holdings[symbol] = (
                            current_holdings.get(symbol, 0) - action_shares
                        )
                        current_cash += trade_value - cost
                        if current_holdings[symbol] <= 0:
                            del current_holdings[symbol]

                # Calculate portfolio value
                portfolio_value = current_cash
                for pos in positions:
                    symbol = pos.get("symbol", "")
                    price = pos.get("reference_price", 0)
                    shares = current_holdings.get(symbol, 0)
                    portfolio_value += shares * price

                # Calculate daily return
                daily_return = (
                    (portfolio_value - prev_portfolio_value) / prev_portfolio_value
                    if prev_portfolio_value > 0
                    else 0
                )

                daily_returns.append(
                    {
                        "date": date_str,
                        "portfolio_value": portfolio_value,
                        "daily_return": daily_return,
                        "cost": total_cost,
                        "cash": current_cash,
                        "positions_count": len(
                            [p for p in positions if p.get("target_shares", 0) > 0]
                        ),
                    }
                )

                prev_portfolio_value = portfolio_value

                # Log progress every 50 days
                if (i + 1) % 50 == 0:
                    self.logger.info(
                        f"Processed {i + 1}/{len(dates)} days, portfolio value: {portfolio_value:,.0f}"
                    )

            # Restore original total_value
            etf_service.total_value = original_total_value

            # Calculate summary metrics
            if not daily_returns:
                return {
                    "status": "error",
                    "error": "No valid trading days in backtest period.",
                }

            returns_df = pd.DataFrame(daily_returns)
            total_return = (returns_df["portfolio_value"].iloc[-1] - account) / account
            total_cost = returns_df["cost"].sum()
            trading_days = len(returns_df)

            # Calculate annualized metrics
            annual_return = (
                total_return * (252 / trading_days) if trading_days > 0 else 0
            )
            daily_returns_series = returns_df["daily_return"]
            volatility = (
                daily_returns_series.std() * np.sqrt(252)
                if len(daily_returns_series) > 1
                else 0
            )
            sharpe_ratio = annual_return / volatility if volatility > 0 else 0

            # Calculate max drawdown
            cumulative = (1 + daily_returns_series).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            result = {
                "status": "success",
                "strategy": "etf_enhanced_indexing",
                "start_time": returns_df["date"].iloc[0],
                "end_time": returns_df["date"].iloc[-1],
                "trading_days": trading_days,
                "initial_account": account,
                "final_account": float(returns_df["portfolio_value"].iloc[-1]),
                "total_return": float(total_return),
                "total_cost": float(total_cost),
                "annual_return": float(annual_return),
                "volatility": float(volatility),
                "sharpe_ratio": float(sharpe_ratio),
                "max_drawdown": float(max_drawdown),
                "daily_returns": returns_df.to_dict(orient="records"),
            }

            self.logger.info(
                f"ETF Backtest completed: {trading_days} days, "
                f"return={total_return:.2%}, sharpe={sharpe_ratio:.2f}, max_dd={max_drawdown:.2%}"
            )
            return result

        except Exception as e:
            # Restore original total_value on error
            etf_service.total_value = original_total_value
            self.logger.error(f"ETF Backtest failed: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
            }


# Global instance
qlib_workflow_service = QlibWorkflowService()


def get_qlib_workflow_service() -> QlibWorkflowService:
    """Get the global QlibWorkflowService instance."""
    return qlib_workflow_service
