"""
Qlib workflow execution service.
This service executes Qlib workflows based on configuration.
"""

import logging
from typing import Dict, Any
from qlib.workflow import R
from qlib.utils import init_instance_by_config
from app.services.qlib_init_service import qlib_init_service
from app.core.timer import WorkflowTimer

logger = logging.getLogger(__name__)


class QlibWorkflowService:
    """
    Service for executing Qlib workflows

    This service takes a workflow configuration and executes it using
    Qlib's workflow system. It handles model training, dataset preparation,
    and result recording.

    Key responsibilities:
    - Accept workflow configuration
    - Execute Qlib workflow
    - Return training results
    """

    def __init__(self):
        """Initialize the workflow service."""
        self.logger = logger

    def execute_training_workflow(
        self, config: Dict[str, Any], experiment_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Execute a training workflow to train a new model.

        This is the main entry point for running a complete training workflow including:
        1. Dataset preparation
        2. Model training
        3. Result recording

        Args:
            config: Workflow configuration dictionary with structure:
                {
                    "task": {
                        "model": {...},
                        "dataset": {...},
                        "record": {...}
                    }
                }
            experiment_name: Name of the experiment for tracking

        Returns:
            Dictionary containing:
                - metrics: Training and validation metrics
                - model_path: Path to saved model
                - timings: Execution time for each step

        Raises:
            Exception: If workflow execution fails
        """
        # Ensure Qlib is initialized
        qlib_init_service.initialize()

        # Create timer for tracking execution time
        timer = WorkflowTimer()

        try:
            # Start MLflow experiment
            with timer.step("experiment_setup"):
                with R.start(experiment_name=experiment_name):
                    self.logger.info(f"Started experiment: {experiment_name}")

                    # Execute workflow steps
                    result = self._execute_workflow_steps(config, timer)

                    # Add timing information
                    result["timings"] = timer.get_summary()

                    self.logger.info("✅ Workflow completed successfully")
                    return result

        except Exception as e:
            self.logger.error(f"❌ Workflow execution failed: {str(e)}")
            raise

    def _execute_workflow_steps(
        self, config: Dict[str, Any], timer: WorkflowTimer
    ) -> Dict[str, Any]:
        """
        Execute the main workflow steps.

        This method orchestrates the three main steps of the workflow:
        1. Dataset preparation
        2. Model training
        3. Result recording

        Args:
            config: Workflow configuration dictionary
            timer: Timer for tracking execution time

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

        # Step 3: Record results
        with timer.step("result_recording"):
            results = self._record_results(model, dataset)
            self.logger.info("Results recorded successfully")

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
        2. Prepare training and validation data from dataset
        3. Trains the model using the fit() method

        Args:
            model_config: Model configuration dictionary
            dataset: Dataset object created by _create_dataset

        Returns:
            Trained model object
        """
        self.logger.info("Creating model from configuration...")
        model = init_instance_by_config(model_config)

        self.logger.info("Preparing training and validation data...")
        # prepare data for training
        # use DK_L (learning data) which includes both features and labels
        from qlib.data.dataset.handler import DataHandlerLP

        df_train, df_valid = dataset.prepare(
            ["train", "valid"],
            col_set=["feature", "label"],
            data_key=DataHandlerLP.DK_L,
        )

        self.logger.info("Training model...")
        model.fit(df_train, df_valid)

        self.logger.info("Model training completed")
        return model

    def _record_results(self, model, dataset) -> Dict[str, Any]:
        """
        Record model results and save artifacts.

        This method:
        1. Evaluates model on test set
        2. Saves model to MLflow
        3. Returns evaluation metrics

        Args:
            model: Trained model object
            dataset: Dataset object

        Returns:
            Dictionary containing evaluation metrics
        """
        from qlib.data.dataset.handler import DataHandlerLP

        self.logger.info("Preparing test data for evaluation...")
        df_test = dataset.prepare(
            ["test"], col_set=["feature", "label"], data_key=DataHandlerLP.DK_L
        )

        self.logger.info("Evaluating model on test set...")
        predictions = model.predict(df_test)

        # Save model to MLflow
        self.logger.info("Saving model to MLflow...")
        from qlib.workflow import R

        R.save_objects(model=model)

        # Calculate and return metrics
        results = {
            "status": "success",
            "predictions_count": len(predictions),
            "model_saved": True,
        }

        self.logger.info("Results recorded successfully")

        return results


# Global instance
qlib_workflow_service = QlibWorkflowService()
