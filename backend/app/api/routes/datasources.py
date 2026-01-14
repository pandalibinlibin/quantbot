import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    DataSource,
    DataSourceCreate,
    DataSourcePublic,
    DataSourceUpdate,
    Message,
)

router = APIRouter(prefix="/datasources", tags=["datasources"])


@router.get("/", response_model=list[DataSourcePublic])
def read_datasources(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve all data sources.
    """
    statement = select(DataSource).offset(skip).limit(limit)
    datasources = session.exec(statement).all()
    return datasources


@router.get("/{datasource_id}", response_model=DataSourcePublic)
def read_datasource(
    session: SessionDep, current_user: CurrentUser, datasource_id: uuid.UUID
) -> Any:
    """
    Get data source by ID.
    """
    datasource = session.get(DataSource, datasource_id)
    if not datasource:
        raise HTTPException(status_code=404, detail="Data source not found")
    return datasource


@router.post("/", response_model=DataSourcePublic)
def create_datasource(
    *, session: SessionDep, current_user: CurrentUser, datasource_in: DataSourceCreate
) -> Any:
    """
    Create new data source.
    """
    datasource = DataSource.model_validate(
        datasource_in, update={"created_by": current_user.id}
    )
    session.add(datasource)
    session.commit()
    session.refresh(datasource)
    return datasource


@router.put("/{datasource_id}", response_model=DataSourcePublic)
def update_datasource(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    datasource_id: uuid.UUID,
    datasource_in: DataSourceUpdate,
) -> Any:
    """
    Update a data source.
    """
    datasource = session.get(DataSource, datasource_id)
    if not datasource:
        raise HTTPException(status_code=404, detail="Data source not found")

    update_dict = datasource_in.model_dump(exclude_unset=True)
    datasource.sqlmodel_update(update_dict)
    session.add(datasource)
    session.commit()
    session.refresh(datasource)
    return datasource


@router.delete("/{datasource_id}")
def delete_datasource(
    session: SessionDep, current_user: CurrentUser, datasource_id: uuid.UUID
) -> Message:
    """
    Delete a data source.
    """
    datasource = session.get(DataSource, datasource_id)
    if not datasource:
        raise HTTPException(status_code=404, detail="Data source not found")

    session.delete(datasource)
    session.commit()
    return Message(message="Data source deleted successfully")
