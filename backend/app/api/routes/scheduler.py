"""
Scheduler API endpoints for viewing scheduler status.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.scheduler_service import get_scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scheduler"])


class JobInfo(BaseModel):
    """Job information."""

    id: str
    name: str
    next_run_time: Optional[str] = None


class TaskConfig(BaseModel):
    """Task configuration."""

    enabled: bool = False
    time: str = ""


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    routine: Optional[TaskConfig] = None
    execute_trades: Optional[TaskConfig] = None
    timezone: str = "Asia/Shanghai"
    config_check_interval: int = 60


class SchedulerStatusResponse(BaseModel):
    """Scheduler status response."""

    is_running: bool
    config: Dict[str, Any]
    jobs: List[JobInfo]


@router.get("/status", response_model=SchedulerStatusResponse)
def get_scheduler_status():
    """
    Get current scheduler status.

    Returns scheduler running state, configuration, and scheduled jobs.
    """
    service = get_scheduler_service()
    status = service.get_status()

    return SchedulerStatusResponse(
        is_running=status["is_running"],
        config=status["config"],
        jobs=[JobInfo(**job) for job in status["jobs"]],
    )
