import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Factor,
    FactorCreate,
    FactorPublic,
    FactorUpdate,
    Message,
)

router = APIRouter(prefix="/factors", tags=["factors"])


@router.get("/", response_model=list[FactorPublic])
def read_factors(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve all factors.
    """
    statement = select(Factor).offset(skip).limit(limit)
    factors = session.exec(statement).all()
    return factors


@router.get("/{factor_id}", response_model=FactorPublic)
def read_factor(
    session: SessionDep, current_user: CurrentUser, factor_id: uuid.UUID
) -> Any:
    """
    Get factor by ID.
    """
    factor = session.get(Factor, factor_id)
    if not factor:
        raise HTTPException(status_code=404, detail="Factor not found")
    return factor


@router.post("/", response_model=FactorPublic)
def create_factor(
    *, session: SessionDep, current_user: CurrentUser, factor_in: FactorCreate
) -> Any:
    """
    Create new factor.
    """
    factor = Factor.model_validate(factor_in, update={"created_by": current_user.id})
    session.add(factor)
    session.commit()
    session.refresh(factor)
    return factor


@router.put("/{factor_id}", response_model=FactorPublic)
def update_factor(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    factor_id: uuid.UUID,
    factor_in: FactorUpdate,
) -> Any:
    """
    Update a factor.
    """
    factor = session.get(Factor, factor_id)
    if not factor:
        raise HTTPException(status_code=404, detail="Factor not found")

    update_dict = factor_in.model_dump(exclude_unset=True)
    factor.sqlmodel_update(update_dict)
    session.add(factor)
    session.commit()
    session.refresh(factor)
    return factor


@router.delete("/{factor_id}")
def delete_factor(
    session: SessionDep, current_user: CurrentUser, factor_id: uuid.UUID
) -> Message:
    """
    Delete a factor.
    """
    factor = session.get(Factor, factor_id)
    if not factor:
        raise HTTPException(status_code=404, detail="Factor not found")

    session.delete(factor)
    session.commit()
    return Message(message="Factor deleted successfully")
