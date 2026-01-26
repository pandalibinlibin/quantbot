"""
Model Training Execution Service

Educational Notes:
- Service Layer Pattern: Separate business logic from API layer
- Orchestrator Pattern: Coordinate multiple services (FactorHandler, ModelHandler)
- This service manages the complete model training workflow
"""

import logging
import uuid
from typing import Any, Dict, List
from sqlmodel import Session
from app.models import ModelTraining
from qlib.data.dataset.handler import DataHandlerLP


class ModelTrainingService:
    """
    Service for executing model training tasks.

    Educational Notes:
    - Coordinate factor data preparation and model training
    - Updates training task status throughout the process
    - Handles errors and save results
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _create_qlib_handler(
        self,
        factor_handler_name: str,
        instruments: List[str],
        start_time: str,
        end_time: str,
        fit_start_time: str,
        fit_end_time: str,
    ):
        """
        Create Qlib handler dynamically based on factor handler name.

        Educational Notes:
        - This method maps our factor handler names to Qlib handler classes
        - Alpha158 includes both features and labels
        - Label formula: Ref($close, -2)/Ref($close, -1) - 1 (T+1 to T+2 return)
        - New handlers can be added by updating the HANDLER_MAP
        """

        from qlib.contrib.data.handler import Alpha158 as QlibAlpha158

        # Handler mapping: our name -> Qlib class
        HANDLER_MAP = {
            "alpha158": QlibAlpha158,
            # Future: add more handlers here
            # "alpha360": QlibAlpha360,
            # "custom": CustomHandler,
        }

        handler_class = HANDLER_MAP.get(factor_handler_name.lower())
        if not handler_class:
            raise ValueError(
                f"Unsupported factor handler: {factor_handler_name}. "
                f"Supported handlers: {list(HANDLER_MAP.keys())}"
            )

        # Create handler using Alpha158's default configuration
        # Alpha158 is a pre-built handler that includes:
        # - 158 technical indicator features
        # - 1 label: Ref($close, -2)/Ref($close, -1) - 1 (T+1 to T+2 return)
        # - Built-in processors for data normalization
        # We use Qlib's default configuration without custom modifications
        return handler_class(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            fit_start_time=fit_start_time,
            fit_end_time=fit_end_time,
        )

    def execute_training(
        self, training_id: uuid.UUID, session: Session
    ) -> Dict[str, Any]:
        """
        Execute a model training task.

        Args:
            training_id: ID of the ModelTraining task
            session: Database session

        Returns:
            Dictionary with execution results
        """
        try:
            # Step 1: Load training task from database
            training = session.get(ModelTraining, training_id)
            if not training:
                raise ValueError(f"Training task {training_id} not found")

            self.logger.info(f"Starting training execution for task {training_id}")

            # Step 2: Update status to RUNNING
            from app.models import TrainingStatus
            from datetime import datetime

            training.status = TrainingStatus.RUNNING
            training.started_at = datetime.utcnow()
            training.progress = 10
            training.current_step = "Initializing training"
            session.add(training)
            session.commit()

            # Step 3: Calculate train/valid time segments from auto split config
            from datetime import datetime, timedelta
            import json

            # Parse dates
            data_start = datetime.strptime(training.data_start_time, "%Y-%m-%d")
            data_end = datetime.strptime(training.data_end_time, "%Y-%m-%d")

            # Calculate total days
            total_days = (data_end - data_start).days

            # Validate ratios
            if training.train_ratio + training.valid_ratio != 1.0:
                raise ValueError(
                    f"train_ratio ({training.train_ratio}) + valid_ratio ({training.valid_ratio}) "
                    f"must equal 1.0"
                )

            # Calculate split point
            train_days = int(total_days * training.train_ratio)

            # Calculate time segments
            train_start_time = training.data_start_time
            train_end = data_start + timedelta(days=train_days)
            train_end_time = train_end.strftime("%Y-%m-%d")

            valid_start = train_end + timedelta(days=1)
            valid_start_time = valid_start.strftime("%Y-%m-%d")
            valid_end_time = training.data_end_time

            self.logger.info(
                f"Auto split: train [{train_start_time} to {train_end_time}], "
                f"valid [{valid_start_time} to {valid_end_time}]"
            )

            # Step 4: Parse training configuration
            training_config = json.loads(training.training_config)
            factor_handler_name = training.factor_handler

            self.logger.info(f"Using factor handler: {factor_handler_name}")

            # Step 5: Get factor handler configuration
            factor_config = training_config.get("factor_handler_config", {})
            instruments = factor_config.get("instruments", [])

            if not instruments:
                raise ValueError(
                    "Missing 'factor_handler_config.instruments' in training_config. "
                    "Please specify instruments like: "
                    '{"factor_handler_config": {"instruments": ["000001.sz", "000002.sz"]}}'
                )

            # Normalize instruments to lowercase (Qlib requirement)
            instruments = [inst.lower() for inst in instruments]

            self.logger.info(
                f"Training with {len(instruments)} instruments: {instruments}"
            )

            # Step 6: Initialize Qlib and create factor handler
            from qlib.data.dataset import DatasetH
            from app.services.qlib_utils import init_qlib
            from app.core.config import settings

            init_qlib(region=settings.QLIB_REGION)

            # Step 7: Create factor handler and check if data exists
            try:
                self.logger.info(f"Creating {factor_handler_name} handler...")

                handler = self._create_qlib_handler(
                    factor_handler_name=factor_handler_name,
                    instruments=instruments,
                    start_time=training.data_start_time,
                    end_time=training.data_end_time,
                    fit_start_time=train_start_time,
                    fit_end_time=train_end_time,
                )

                # Try to fetch data to verify it exists
                self.logger.info("Checking if factor data exists...")
                test_data = handler.fetch(col_set="feature")

                if test_data is None or test_data.empty:
                    raise ValueError("Factor data is empty")

                self.logger.info(
                    f"Factor data found: {test_data.shape[0]} rows, "
                    f"{test_data.shape[1]} features"
                )
            except Exception as e:
                error_msg = (
                    f"Failed to load factor data: {str(e)}\n\n"
                    f"Please calculate factors first using:\n"
                    f"POST /api/v1/factors/calculate\n"
                    f"{{\n"
                    f'  "handler_name": "{factor_handler_name}",\n'
                    f'  "instruments": {json.dumps(instruments)},\n'
                    f'  "start_date": "{training.data_start_time}",\n'
                    f'  "end_date": "{training.data_end_time}"\n'
                    f"}}"
                )
                raise ValueError(error_msg)

            # Step 8: Create dataset with train/valid segments
            self.logger.info("Creating DatasetH with train/valid segments...")

            dataset = DatasetH(
                handler=handler,
                segments={
                    "train": (train_start_time, train_end_time),
                    "valid": (valid_start_time, valid_end_time),
                },
            )

            # Debug: Check handler data before DatasetH
            self.logger.info("Debugging handler data...")
            try:
                # Check what columns the handler provides
                handler_cols = handler.get_cols()
                self.logger.info(f"Handler columns: {handler_cols}")

                # Check raw data from handler
                raw_data = handler.fetch(col_set="__all")
                self.logger.info(f"Raw handler data shape: {raw_data.shape}")
                self.logger.info(
                    f"Raw handler data columns: {raw_data.columns.tolist()}"
                )

                # Check if there's any label data
                if "label" in raw_data.columns:
                    label_data = raw_data["label"]
                    self.logger.info(
                        f"Raw label data - Count: {len(label_data)}, NaN count: {label_data.isna().sum()}"
                    )
                    self.logger.info(
                        f"Raw label data sample: {label_data.head(10).tolist()}"
                    )
                else:
                    self.logger.error("No 'label' column found in raw handler data!")

            except Exception as e:
                self.logger.error(f"Failed to debug handler data: {e}")

            # Verify labels are present and valid
            self.logger.info("Verifying dataset labels...")
            try:
                df_train, df_valid = dataset.prepare(
                    ["train", "valid"],
                    col_set=["feature", "label"],  # Fetch feature and label columns
                    data_key=DataHandlerLP.DK_L,  # Use learning data (includes labels)
                )

                # Debug: Check dataset structure
                self.logger.info(
                    f"Train dataset shape: {df_train.shape}, columns: {df_train.columns.tolist()}"
                )
                self.logger.info(
                    f"Valid dataset shape: {df_valid.shape}, columns: {df_valid.columns.tolist()}"
                )

                # Check train labels
                if "label" in df_train.columns:
                    train_labels = df_train["label"]
                    train_count = int(len(train_labels))
                    train_mean = float(train_labels.mean())
                    train_std = float(train_labels.std())
                    train_min = float(train_labels.min())
                    train_max = float(train_labels.max())
                    train_nan_count = int(train_labels.isna().sum())

                    # Debug: Show sample of train labels
                    self.logger.info(
                        f"Train label sample: {train_labels.head(10).tolist()}"
                    )
                    self.logger.info(
                        f"Train label index sample: {train_labels.index[:5].tolist()}"
                    )

                    self.logger.info(
                        f"Train labels - Count: {train_count}, "
                        f"Mean: {train_mean:.6f}, "
                        f"Std: {train_std:.6f}, "
                        f"Min: {train_min:.6f}, "
                        f"Max: {train_max:.6f}, "
                        f"NaN count: {train_nan_count}"
                    )
                else:
                    self.logger.error("Train dataset does not contain 'label' column!")
                    raise ValueError("Train dataset missing label column")

                # Check valid labels
                if "label" in df_valid.columns:
                    valid_labels = df_valid["label"]
                    valid_count = int(len(valid_labels))
                    valid_mean = float(valid_labels.mean())
                    valid_std = float(valid_labels.std())
                    valid_min = float(valid_labels.min())
                    valid_max = float(valid_labels.max())
                    valid_nan_count = int(valid_labels.isna().sum())

                    # Debug: Show sample of valid labels
                    self.logger.info(
                        f"Valid label sample: {valid_labels.head(10).tolist()}"
                    )
                    self.logger.info(
                        f"Valid label index sample: {valid_labels.index[:5].tolist()}"
                    )

                    self.logger.info(
                        f"Valid labels - Count: {valid_count}, "
                        f"Mean: {valid_mean:.6f}, "
                        f"Std: {valid_std:.6f}, "
                        f"Min: {valid_min:.6f}, "
                        f"Max: {valid_max:.6f}, "
                        f"NaN count: {valid_nan_count}"
                    )
                else:
                    self.logger.error("Valid dataset does not contain 'label' column!")
                    raise ValueError("Valid dataset missing label column")

            except Exception as e:
                self.logger.error(f"Failed to verify labels: {e}")
                raise

            # Update progress
            training.progress = 40
            training.current_step = "Training model"
            session.add(training)
            session.commit()

            # Step 9: Training model
            self.logger.info("Starting model training...")

            from app.services.models.lightgbm_handler import LightGBMHandler
            from qlib.workflow import R

            model_handler = LightGBMHandler()

            # Get model parameters from training config
            model_params = training_config.get("model_params", {})

            # Start Qlib experiment and train
            experiment_name = f"training_{training_id}"

            with R.start(experiment_name=experiment_name):
                # Log training parameters
                R.log_params(
                    factor_handler=factor_handler_name,
                    instruments_count=len(instruments),
                    train_start=train_start_time,
                    train_end=train_end_time,
                    valid_start=valid_start_time,
                    valid_end=valid_end_time,
                )

                # Train model
                training_result = model_handler.train(
                    dataset=dataset, model_params=model_params if model_params else None
                )

                if not training_result.get("success"):
                    raise Exception(training_result.get("error", "Training failed"))

                # Save trained model using Qlib's mechanism
                R.save_objects(trained_model=model_handler.model)

                # Get recorder for model path
                recorder = R.get_recorder()
                recorder_id = recorder.id
                experiment_id = recorder.experiment_id
                model_file_path = (
                    f"mlruns/{experiment_id}/{recorder_id}/artifacts/trained_model"
                )

                self.logger.info(
                    f"Model saved with recorder ID: {recorder_id}, experiment ID: {experiment_id}"
                )

            # Step 10: Update training task with results
            training.status = TrainingStatus.COMPLETED
            training.progress = 100
            training.current_step = "Completed"
            training.completed_at = datetime.utcnow()

            # Save model file path and recorder ID
            training.model_file_path = model_file_path
            training.training_metrics = json.dumps(
                {
                    "recorder_id": recorder_id,
                    "experiment_name": experiment_name,
                    **training_result.get("metrics", {}),
                }
            )

            session.add(training)
            session.commit()

            self.logger.info(f"Training completed successfully for task {training_id}")

            return {
                "success": True,
                "training_id": str(training_id),
                "factor_handler": factor_handler_name,
                "instruments_count": len(instruments),
                "train_period": f"{train_start_time} to {train_end_time}",
                "valid_period": f"{valid_start_time} to {valid_end_time}",
                "training_time": training_result.get("training_time", 0),
                "metrics": training_result.get("metrics", {}),
                "message": "Model trained successfully",
            }

        except Exception as e:
            self.logger.error(f"Training execution failed: {e}", exc_info=True)
            return {"success": False, "training_id": str(training_id), "error": str(e)}
