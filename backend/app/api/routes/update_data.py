"""
Update Data API Routes - Data preparation and preprocessing

Workflow:
- Incremental data download
- Qlib initialization
- OnlineManager routine (rolling model training + prediction)
- Signal generation
- Model performance metrics

Prepares data for Run Signal and Run Backtest.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import logging

from app.api import deps
from app.services.data_update_service import get_data_update_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run")
async def update_data(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Execute data update - full data preparation workflow.

    Steps:
    1. Incremental data download
    2. Qlib initialization (if needed)
    3. OnlineManager routine (rolling model training + prediction)
    4. Signal generation
    5. Model performance metrics

    Prepares data for Run Signal and Run Backtest.
    """
    try:
        logger.info(f"User {current_user.email} triggered data update")

        data_update_service = get_data_update_service()

        # Delegates to OnlineServingService.update_data()
        result = await data_update_service.run_full_update_workflow()

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(
                status_code=500, detail=f"Data update failed: {error_msg}"
            )

        logger.info("Data update workflow completed successfully")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data update failed: {str(e)}")


@router.get("/status")
async def get_data_status(
    current_user=Depends(deps.get_current_user),
):
    """
    Get data readiness status.

    Returns initialization state, last update time,
    signal availability, and data coverage.
    """
    try:
        data_update_service = get_data_update_service()
        status = await data_update_service.get_data_status()

        return {
            "success": True,
            "data": status,
        }

    except Exception as e:
        logger.error(f"Failed to get data status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get data status: {str(e)}"
        )
