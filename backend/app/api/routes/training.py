"""
Training API Routes

Endpoints for model training workflows.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.qlib_workflow_service import get_qlib_workflow_service

router = APIRouter()


class TrainingStartResponse(BaseModel):
    """Response model for training start endpoint."""

    status: str
    message: str
    model_path: Optional[str] = None
    test_predictions_count: int = 0
    experiment_name: Optional[str] = None
    timings: Optional[dict] = None
    error: Optional[str] = None


class DataStatusResponse(BaseModel):
    """Response model for data status check."""

    exists: bool
    message: str
    details: dict


class ModelInfo(BaseModel):
    """Model information."""

    name: str
    path: str
    size_bytes: int
    created_at: str
    modified_at: str


@router.get("/data-status/{freq}", response_model=DataStatusResponse)
def check_data_status(freq: str = "day"):
    """
    Check if data is available for training.

    Args:
        freq: Data frequency ("day" or "1min")

    Returns:
        Data availability status
    """
    service = get_qlib_workflow_service()
    result = service.check_data_exists(freq)
    return DataStatusResponse(**result)


@router.post("/start", response_model=TrainingStartResponse)
def start_training():
    """
    Start training workflow using configuration from file.

    Training parameters are read from backend/app/config/qlib/training_config.yaml.

    Returns:
        Training result with model path and metrics
    """
    service = get_qlib_workflow_service()

    try:
        result = service.execute_training_from_config()

        return TrainingStartResponse(
            status="success",
            message="Training completed successfully",
            model_path=result.get("model_path"),
            test_predictions_count=result.get("test_predictions_count", 0),
            experiment_name=result.get("experiment_name"),
            timings=result.get("timings"),
        )

    except FileNotFoundError as e:
        return TrainingStartResponse(
            status="error",
            message="Training configuration file not found",
            error=str(e),
        )

    except ValueError as e:
        return TrainingStartResponse(
            status="error",
            message="Data not available for training",
            error=str(e),
        )

    except Exception as e:
        return TrainingStartResponse(
            status="error",
            message="Training failed",
            error=str(e),
        )


@router.get("/config")
def get_training_config():
    """
    Get current training configuration.

    Returns the configuration that will be used when training is started.
    """
    service = get_qlib_workflow_service()

    try:
        config = service.load_training_config()
        return {
            "status": "success",
            "config": config,
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "error": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/models")
def list_models():
    """
    List all trained models.

    Returns list of model files with metadata.
    """
    service = get_qlib_workflow_service()
    models = service.list_models()
    return {
        "status": "success",
        "count": len(models),
        "models": models,
    }
