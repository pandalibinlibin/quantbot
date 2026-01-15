import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    MLModel,
    ModelCreate,
    ModelPublic,
    ModelUpdate,
    Message,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", response_model=list[ModelPublic])
def read_models(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve all machine learning models.
    """
    statement = select(MLModel).offset(skip).limit(limit)
    models = session.exec(statement).all()
    return models


@router.get("/{model_id}", response_model=ModelPublic)
def read_model(
    session: SessionDep, current_user: CurrentUser, model_id: uuid.UUID
) -> Any:
    """
    Get model by ID.
    """
    model = session.get(MLModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/", response_model=ModelPublic)
def create_model(
    *, session: SessionDep, current_user: CurrentUser, model_in: ModelCreate
) -> Any:
    """
    Create new machine learning model.
    """
    model = MLModel.model_validate(model_in, update={"created_by": current_user.id})
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@router.put("/{model_id}", response_model=ModelPublic)
def update_model(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    model_id: uuid.UUID,
    model_in: ModelUpdate,
) -> Any:
    """
    Update a machine learning model.
    """
    model = session.get(MLModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    update_dict = model_in.model_dump(exclude_unset=True)
    model.sqlmodel_update(update_dict)
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@router.delete("/{model_id}")
def delete_model(
    session: SessionDep, current_user: CurrentUser, model_id: uuid.UUID
) -> Message:
    """
    Delete a machine learning model.
    """
    model = session.get(MLModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    session.delete(model)
    session.commit()
    return Message(message="Model deleted successfully")
