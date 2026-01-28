"""
Qlib Workflow API Routes - Basic Framework

Educational Notes:
- This file defines API endpoints for Qlib workflow
- Uses FastAPI Router to organize related endpoints
- Will be registered with the main FastAPI application
"""

from fastapi import APIRouter
from app.models import TrainingWorkflowRequest, TrainingWorkflowResponse

# Create router with prefix and tags
router = APIRouter(prefix="/qlib", tags=["Qlib Workflows"])


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
    """Convert TrainingWorkflowRequest to Qlib configuration dictionary."""
    return {
        "task": {
            "model": {
                "class": request.task.model.class_name,
                "module_path": request.task.model.module_path,
                "kwargs": request.task.model.kwargs,
            },
            "dataset": {
                "class": request.task.dataset.class_name,
                "module_path": request.task.dataset.module_path,
                "kwargs": {
                    "handler": {
                        "class": request.task.dataset.kwargs.handler.class_name,
                        "module_path": request.task.dataset.kwargs.handler.module_path,
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
