"""
Model Hyperparameter Configuration.

This file defines default hyperparameters for different Qlib models.
Users can modify these values to adjust model behavior without changing code.

Educational Notes:
- Each model has its own set of hyperparameters
- These are sensible defaults based on Qlib documentation and best practices
- Users can tune these values based on their specific use case
"""

from typing import Dict, Any


# LightGBM Model Hyperparameters
LGBMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "loss": "mse",  # Loss function: mse (mean squared error) for regression
    "num_leaves": 31,  # Maximum number of leaves in one tree
    "learning_rate": 0.05,  # Learning rate for gradient boosting
    "num_boost_round": 100,  # Number of boosting iterations
    "verbose": -1,  # Verbosity level (-1 = silent, 0 = warning, 1 = info)
    "feature_fraction": 0.8,  # Fraction of features to use in each iteration
    "bagging_fraction": 0.8,  # Fraction of data to use in each iteration
    "bagging_freq": 5,  # Frequency for bagging
    "min_data_in_leaf": 20,  # Minimum number of data in one leaf
}

# XGBoost Model Hyperparameters
XGBMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "objective": "reg:squarederror",  # Objective function for regression
    "max_depth": 6,  # Maximum depth of a tree
    "learning_rate": 0.05,  # Learning rate (eta)
    "n_estimators": 100,  # Number of boosting rounds
    "subsample": 0.8,  # Subsample ratio of the training instances
    "colsample_bytree": 0.8,  # Subsample ratio of columns when constructing each tree
    "reg_alpha": 0.0,  # L1 regularization term on weights
    "reg_lambda": 1.0,  # L2 regularization term on weights
    "verbosity": 0,  # Verbosity of printing messages (0 = silent)
}

# CatBoost Model Hyperparameters
CATBOOSTMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "loss_function": "RMSE",  # Loss function for regression
    "iterations": 100,  # Number of boosting iterations
    "learning_rate": 0.05,  # Learning rate
    "depth": 6,  # Depth of the tree
    "l2_leaf_reg": 3.0,  # L2 regularization coefficient
    "verbose": False,  # Verbosity
}

# Linear Model Hyperparameters
LINEARMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "fit_intercept": True,  # Whether to calculate the intercept
    "normalize": False,  # Whether to normalize features before fitting
}

# MLP (Multi-Layer Perceptron) Model Hyperparameters
MLPMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "lr": 0.001,  # Learning rate
    "n_epochs": 100,  # Number of training epochs
    "batch_size": 2000,  # Batch size for training
    "early_stop": 20,  # Early stopping patience
    "optimizer": "adam",  # Optimizer: adam, sgd, etc.
}

# GRU Model Hyperparameters
GRUMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "lr": 0.001,  # Learning rate
    "n_epochs": 100,  # Number of training epochs
    "batch_size": 2000,  # Batch size for training
    "early_stop": 20,  # Early stopping patience
    "hidden_size": 64,  # Hidden layer size
    "num_layers": 2,  # Number of GRU layers
    "dropout": 0.0,  # Dropout rate
}

# LSTM Model Hyperparameters
LSTMMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "lr": 0.001,  # Learning rate
    "n_epochs": 100,  # Number of training epochs
    "batch_size": 2000,  # Batch size for training
    "early_stop": 20,  # Early stopping patience
    "hidden_size": 64,  # Hidden layer size
    "num_layers": 2,  # Number of LSTM layers
    "dropout": 0.0,  # Dropout rate
}

# GATs (Graph Attention Networks) Model Hyperparameters
GATS_HYPERPARAMETERS: Dict[str, Any] = {
    "lr": 0.001,  # Learning rate
    "n_epochs": 100,  # Number of training epochs
    "batch_size": 2000,  # Batch size for training
    "early_stop": 20,  # Early stopping patience
    "hidden_size": 64,  # Hidden layer size
    "num_layers": 2,  # Number of GAT layers
}

# ALSTM (Attention-based LSTM) Model Hyperparameters
ALSTM_HYPERPARAMETERS: Dict[str, Any] = {
    "lr": 0.001,  # Learning rate
    "n_epochs": 100,  # Number of training epochs
    "batch_size": 2000,  # Batch size for training
    "early_stop": 20,  # Early stopping patience
    "hidden_size": 64,  # Hidden layer size
    "num_layers": 2,  # Number of LSTM layers
    "dropout": 0.0,  # Dropout rate
}

# Transformer Model Hyperparameters
TRANSFORMERMODEL_HYPERPARAMETERS: Dict[str, Any] = {
    "lr": 0.001,  # Learning rate
    "n_epochs": 100,  # Number of training epochs
    "batch_size": 2000,  # Batch size for training
    "early_stop": 20,  # Early stopping patience
    "d_model": 64,  # Dimension of the model
    "nhead": 4,  # Number of attention heads
    "num_layers": 2,  # Number of transformer layers
    "dropout": 0.1,  # Dropout rate
}


# Registry mapping model class names to their hyperparameters
MODEL_HYPERPARAMETERS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "LGBModel": LGBMODEL_HYPERPARAMETERS,
    "XGBModel": XGBMODEL_HYPERPARAMETERS,
    "CatBoostModel": CATBOOSTMODEL_HYPERPARAMETERS,
    "LinearModel": LINEARMODEL_HYPERPARAMETERS,
    "MLPModel": MLPMODEL_HYPERPARAMETERS,
    "GRUModel": GRUMODEL_HYPERPARAMETERS,
    "LSTMModel": LSTMMODEL_HYPERPARAMETERS,
    "GATs": GATS_HYPERPARAMETERS,
    "ALSTM": ALSTM_HYPERPARAMETERS,
    "TransformerModel": TRANSFORMERMODEL_HYPERPARAMETERS,
}


def get_model_hyperparameters(model_class_name: str) -> Dict[str, Any]:
    """
    Get default hyperparameters for a model class.

    Args:
        model_class_name: Model class name (e.g., "LGBModel")

    Returns:
        Dictionary of hyperparameters with default values

    Raises:
        ValueError: If model class name is not found in registry
    """
    if model_class_name not in MODEL_HYPERPARAMETERS_REGISTRY:
        raise ValueError(
            f"Unknown model class: {model_class_name}. "
            f"Available models: {list(MODEL_HYPERPARAMETERS_REGISTRY.keys())}"
        )

    # Return a copy to prevent modification of the original
    return MODEL_HYPERPARAMETERS_REGISTRY[model_class_name].copy()
