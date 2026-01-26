import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ModelTraining,
    ModelTrainingCreate,
    ModelTrainingPublic,
    ModelTrainingUpdate,
    Message,
)

router = APIRouter(prefix="/model-trainings", tags=["model-trainings"])


@router.get("/", response_model=list[ModelTrainingPublic])
def read_model_trainings(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve all model training tasks.
    """
    statement = select(ModelTraining).offset(skip).limit(limit)
    trainings = session.exec(statement).all()
    return trainings


@router.get("/{training_id}", response_model=ModelTrainingPublic)
def read_model_training(
    session: SessionDep, current_user: CurrentUser, training_id: uuid.UUID
) -> Any:
    """
    Get model training task by ID.
    """
    training = session.get(ModelTraining, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Model training task not found")
    return training


@router.post("/", response_model=ModelTrainingPublic)
def create_model_training(
    *, session: SessionDep, current_user: CurrentUser, training_in: ModelTrainingCreate
) -> Any:
    """
    Create new model training task.
    """
    training = ModelTraining.model_validate(
        training_in, update={"created_by": current_user.id}
    )
    session.add(training)
    session.commit()
    session.refresh(training)
    return training


@router.put("/{training_id}", response_model=ModelTrainingPublic)
def update_model_training(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    training_id: uuid.UUID,
    training_in: ModelTrainingUpdate,
) -> Any:
    """
    Update a model training task.
    """
    training = session.get(ModelTraining, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Model training task not found")
    update_dict = training_in.model_dump(exclude_unset=True)
    training.sqlmodel_update(update_dict)
    session.add(training)
    session.commit()
    session.refresh(training)
    return training


@router.delete("/{training_id}")
def delete_model_training(
    session: SessionDep, current_user: CurrentUser, training_id: uuid.UUID
) -> Message:
    """
    Delete a model training task.
    """
    training = session.get(ModelTraining, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Model training task not found")
    session.delete(training)
    session.commit()
    return Message(message="Model training task deleted successfully")


@router.post("/{training_id}/execute")
def execute_model_training(
    session: SessionDep, current_user: CurrentUser, training_id: uuid.UUID
) -> Any:
    """
    Execute a model training task.

    This endpoint triggers the actual training process:
    1. Validates that factor data exists
    2. Creates Qlib DatasetH with train/valid splits
    3. Trains the model using LightGBM
    4. Saves the trained model using Qlib's R.save_objects()
    5. Updates training status and metrics

    Returns:
        Training execution result with recorder_id and metrics
    """
    from app.services.model_training_service import ModelTrainingService

    # Check if training task exists
    training = session.get(ModelTraining, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Model training task not found")

    # Check if training is already running or completed
    from app.models import TrainingStatus

    if training.status == TrainingStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Training is already running")

    # Execute training
    service = ModelTrainingService()
    result = service.execute_training(training_id=training_id, session=session)

    if not result.get("success"):
        raise HTTPException(
            status_code=500, detail=result.get("error", "Training execution failed")
        )

    return result
