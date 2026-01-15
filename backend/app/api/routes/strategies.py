import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Strategy,
    StrategyCreate,
    StrategyPublic,
    StrategyUpdate,
    Message,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/", response_model=list[StrategyPublic])
def read_strategies(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve all trading strategies.
    """
    statement = select(Strategy).offset(skip).limit(limit)
    strategies = session.exec(statement).all()
    return strategies


@router.get("/{strategy_id}", response_model=StrategyPublic)
def read_strategy(
    session: SessionDep, current_user: CurrentUser, strategy_id: uuid.UUID
) -> Any:
    """
    Get Strategy by ID.
    """
    strategy = session.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.post("/", response_model=StrategyPublic)
def create_strategy(
    *, session: SessionDep, current_user: CurrentUser, strategy_in: StrategyCreate
) -> Any:
    """
    Create new trading strategy.
    """
    strategy = Strategy.model_validate(
        strategy_in, update={"created_by": current_user.id}
    )
    session.add(strategy)
    session.commit()
    session.refresh(strategy)
    return strategy


@router.put("/{strategy_id}", response_model=StrategyPublic)
def update_strategy(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    strategy_id: uuid.UUID,
    strategy_in: StrategyUpdate,
) -> Any:
    """
    Update a trading strategy.
    """
    strategy = session.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    update_dict = strategy_in.model_dump(exclude_unset=True)
    strategy.sqlmodel_update(update_dict)
    session.add(strategy)
    session.commit()
    session.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}")
def delete_strategy(
    session: SessionDep, current_user: CurrentUser, strategy_id: uuid.UUID
) -> Message:
    """
    Delete a trading strategy.
    """
    strategy = session.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    session.delete(strategy)
    session.commit()
    return Message(message="Strategy deleted successfully")
