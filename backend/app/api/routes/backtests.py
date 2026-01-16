import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Backtest,
    BacktestCreate,
    BacktestPublic,
    BacktestUpdate,
    Message,
)

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("/", response_model=list[BacktestPublic])
def read_backtests(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve all backtest tasks.
    """
    statement = select(Backtest).offset(skip).limit(limit)
    backtests = session.exec(statement).all()
    return backtests


@router.get("/{backtest_id}", response_model=BacktestPublic)
def read_backtest(
    session: SessionDep, current_user: CurrentUser, backtest_id: uuid.UUID
) -> Any:
    """
    Get backtest task by ID.
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest task not found")
    return backtest


@router.post("/", response_model=BacktestPublic)
def create_backtest(
    *, session: SessionDep, current_user: CurrentUser, backtest_in: BacktestCreate
) -> Any:
    """
    Create new backtest task.
    """
    backtest = Backtest.model_validate(
        backtest_in, update={"created_by": current_user.id}
    )
    session.add(backtest)
    session.commit()
    session.refresh(backtest)
    return backtest


@router.put("/{backtest_id}", response_model=BacktestPublic)
def update_backtest(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    backtest_id: uuid.UUID,
    backtest_in: BacktestUpdate,
) -> Any:
    """
    Update a backtest task.
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest task not found")
    update_dict = backtest_in.model_dump(exclude_unset=True)
    backtest.sqlmodel_update(update_dict)
    session.add(backtest)
    session.commit()
    session.refresh(backtest)
    return backtest


@router.delete("/{backtest_id}")
def delete_backtest(
    session: SessionDep, current_user: CurrentUser, backtest_id: uuid.UUID
) -> Message:
    """
    Delete a backtest task.
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest task not found")
    session.delete(backtest)
    session.commit()
    return Message(message="Backtest task deleted successfully")
