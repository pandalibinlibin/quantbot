"""
Qlib Workflow API Routes - Basic Framework

Educational Notes:
- This file defines API endpoints for Qlib workflow
- Uses FastAPI Router to organize related endpoints
- Will be registered with the main FastAPI application
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models import TrainingWorkflowRequest, TrainingWorkflowResponse
from app.services.qlib_component_registry import qlib_component_registry
from app.services.qlib_workflow_service import get_qlib_workflow_service

# Create router with prefix and tags
router = APIRouter(prefix="/qlib", tags=["Qlib Workflows"])


class TrainingStartResponse(BaseModel):
    """Response model for simplified training start endpoint."""

    status: str
    message: str
    model_path: Optional[str] = None
    test_predictions_count: int = 0  # Number of predictions on TEST set only
    experiment_name: Optional[str] = None
    timings: Optional[dict] = None
    error: Optional[str] = None


class DataStatusResponse(BaseModel):
    """Response model for data status check."""

    exists: bool
    message: str
    details: dict


@router.get("/health")
def health_check():
    """
    Simple health check endpoint.

    Educational Notes:
    - Returns basic status information
    - Used to verify the API is working
    - No complex logic, just a simple response
    """

    return {
        "status": "healthy",
        "service": "qlib_workflow",
        "message": "Qlib workflow service is ready",
    }


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


@router.post("/training/start", response_model=TrainingStartResponse)
def start_training():
    """
    Start training workflow using configuration from file.

    This is a simplified endpoint - no configuration needed from frontend.
    Training parameters are read from backend/app/config/qlib/training_config.yaml.

    Returns:
        Training result with model path and metrics
    """
    service = get_qlib_workflow_service()

    try:
        # Execute training from config file
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
        # Data not available
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


@router.get("/training/config")
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
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/training-workflow", response_model=TrainingWorkflowResponse)
async def execute_training_workflow(
    request: TrainingWorkflowRequest,
) -> TrainingWorkflowResponse:
    """
    Execute Qlib training workflow.

    Educational Notes:
    - Uses our Pydantic models for request/response validation
    - Calls existing QlibWorkflowService for business logic
    - Returns structured response with training results
    """
    try:
        from app.services.qlib_workflow_service import QlibWorkflowService

        # Convert Pydantic request to config dictionary
        config_dict = _convert_request_to_config(request)

        # Execute training workflow
        service = QlibWorkflowService()
        result = service.execute_training_workflow(
            config=config_dict, experiment_name=request.experiment_name
        )

        # Return success response
        return TrainingWorkflowResponse(
            status="success",
            predictions_count=result.get("predictions_count", 0),
            model_saved=result.get("model_saved", False),
            experiment_name=request.experiment_name,
            error_message=None,
        )
    except Exception as e:
        # Return error response
        return TrainingWorkflowResponse(
            status="error",
            predictions_count=0,
            model_saved=False,
            experiment_name=request.experiment_name,
            error_message=str(e),
        )


def _convert_request_to_config(request: TrainingWorkflowRequest) -> dict:
    """
    Convert TrainingWorkflowRequest to Qlib configuration dictionary.

    Automatically fills in module_path fields using QlibComponentRegistry
    if they are not provided by the frontend.
    """
    # Build basic config structure
    config = {
        "task": {
            "model": {
                "class": request.task.model.class_name,
                "kwargs": request.task.model.kwargs,
            },
            "dataset": {
                "class": request.task.dataset.class_name,
                "kwargs": {
                    "handler": {
                        "class": request.task.dataset.kwargs.handler.class_name,
                        "kwargs": request.task.dataset.kwargs.handler.kwargs,
                    },
                    "segments": {
                        "train": request.task.dataset.kwargs.segments.train,
                        "valid": request.task.dataset.kwargs.segments.valid,
                        "test": request.task.dataset.kwargs.segments.test,
                    },
                },
            },
        }
    }

    # Use registry to automatically fill in module_path fields
    config = qlib_component_registry.enrich_config_with_module_paths(config)

    return config
