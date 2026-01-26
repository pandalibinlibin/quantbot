"""
LightGBM Model Handler for Qlib integration.
This module provides a wrapper around Qlib's LGBModel.
"""

import logging
from typing import Any, Dict, List


class LightGBMHandler:
    """
    Handler for LightGBM model using Qlib's implementation.

    Educational Notes:
    - Adapter pattern: Adapts Qlib's LGBModel to our API interface
    - We use Qlib's built-in LGBModel, not reimplementing it
    """

    def __init__(self):
        """
        Initialize LightGBM handler.

        Educational Notes:
        - Region is read from config file, not passed as parameter
        - This ensures consistency with factor handlers
        - Follows the Single Source of Truth principle
        """
        from app.core.config import settings

        self.region = settings.QLIB_REGION
        self.model = None
        self.logger = logging.getLogger(__name__)
        self.name = "lightgbm"
        self.description = "LightGBM model for stock prediction using Qlib"

    def train(
        self,
        dataset,  # Qlib DatasetH object
        model_params: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Train LightGBM model using Qlib.

        Educational Notes:
        - Accepts pre-prepared Qlib DatasetH object
        - Dataset should contain features (from any factor handler) and labels
        - This design separates factor calculation from model training
        - Follows the Single Responsibility Principle

        Args:
            dataset: Qlib DatasetH object with train/valid/test segments
            model_params: Optional model parameters to override defaults
            **kwargs: Additional training parameters

        Returns:
            Dictionary with training results

        Example:
            # Step 1: Calculate factors (done separately)
            factor_data = alpha158_handler.fetch(...)

            # Step 2: Create dataset
            dataset = DatasetH(handler, segments={...})

            # Step 3: Train model
            result = lightgbm_handler.train(dataset)
        """
        try:
            import time
            from qlib.contrib.model.gbdt import LGBModel

            self.logger.info("Training LightGBM model with provided dataset")

            start_time = time.time()

            # Step 1: Configure LightGBM parameters (Qlib's recommended defaults)
            default_params = {
                "loss": "mse",
                "colsample_bytree": 0.8879,
                "learning_rate": 0.0421,
                "subsample": 0.8789,
                "lambda_l1": 205.6999,
                "lambda_l2": 580.9768,
                "max_depth": 8,
                "num_leaves": 210,
                "num_threads": 20,
            }

            # Override with user-provided parameters
            if model_params:
                default_params.update(model_params)

            self.logger.info(f"Creating LightGBM model with params: {default_params}")

            # Step 2: Create and train model using Qlib's LGBModel
            model = LGBModel(**default_params)

            self.logger.info("Training model with Qlib's LGBModel.fit()...")
            model.fit(dataset, **kwargs)

            # Step 3: Store trained model
            self.model = model

            training_time = time.time() - start_time

            # Step 4: Extract training metrics
            train_metrics = {}
            if hasattr(model, "model") and hasattr(model.model, "best_score"):
                train_metrics = model.model.best_score

            self.logger.info(
                f"Model training completed in {training_time:.2f}s. "
                f"Metrics: {train_metrics}"
            )

            return {
                "success": True,
                "model_name": self.name,
                "training_time": training_time,
                "metrics": train_metrics,
                "model_params": default_params,
                "message": "Model trained successfully using Qlib's LGBModel",
            }
        except Exception as e:
            self.logger.error(f"Model training failed: {e}", exc_info=True)
            return {
                "success": False,
                "model_name": self.name,
                "error": str(e),
                "training_time": (
                    time.time() - start_time if "start_time" in locals() else 0
                ),
            }

    def predict(
        self,
        instruments: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Make predictions using trained model.

        Educational Notes:
        - Requires a trained model (call train() first)
        - Uses the same Alpha158 features as training
        - Returns prediction scores for each instrument and date

        Args:
            instruments: List of instrument codes
            start_date: Prediction start date
            end_date: Prediction end date

        Returns:
            Dictionary with prediction results
        """
        try:
            if self.model is None:
                raise ValueError(
                    "Model not trained. Please train the model first using train() method."
                )

            self.logger.info(f"Making predictions for {len(instruments)} instruments")

            # TODO: Implement prediction logic using Qlib
            # Will be implemented in next step

            return {
                "success": True,
                "model_name": self.name,
                "message": "Prediction method placeholder - to be implemented",
            }

        except Exception as e:
            self.logger.error(f"Prediction failed: {e}", exc_info=True)
            return {"success": False, "model_name": self.name, "error": str(e)}
