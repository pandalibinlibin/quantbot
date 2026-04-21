"""
Run Signal API (v1) - Portfolio optimization and signal export

Workflow (requires Update Data to have been run first):
1. Portfolio Optimization (Enhanced Indexing Strategy)
2. Export trading signals for VeighNa
3. Send email notification (handled inside portfolio optimization)
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import logging

from app.api import deps
from app.services.online_serving_service import get_online_serving_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run", response_model=dict)
async def run_task(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Execute Run Signal - Portfolio optimization and signal export.

    Prerequisite: Update Data must have been run first.

    Workflow:
    1. Generate target portfolio via Enhanced Indexing Strategy
    2. Export trading signals for VeighNa
    3. Send email notification (handled inside portfolio optimization)
    """
    try:
        logger.info(f"User {current_user.email} triggered Run Signal (v1)")

        online_service = get_online_serving_service()

        # generate_portfolio() is synchronous and may take time
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, online_service.generate_portfolio)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(
                status_code=500,
                detail=f"Run Signal failed: {error_msg}",
            )

        logger.info("Run Signal (v1) completed successfully")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run Signal (v1) failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Run Signal failed: {str(e)}")
