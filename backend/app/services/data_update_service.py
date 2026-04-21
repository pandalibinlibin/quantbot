"""
Data Update Service - Delegates to OnlineServingService.update_data()

Handles:
1. Incremental data download (via data_source_manager)
2. Qlib initialization
3. OnlineManager routine (rolling model training + prediction)
4. Signal generation

Does NOT include portfolio optimization or signal export (those belong to Run Signal).
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

import logging

from app.services.online_serving_service import get_online_serving_service

logger = logging.getLogger(__name__)


class DataUpdateService:
    """Data update service - delegates to OnlineServingService.update_data()"""

    def __init__(self):
        self.online_service = get_online_serving_service()

    async def run_full_update_workflow(self) -> Dict[str, Any]:
        """
        Execute data update workflow by calling
        OnlineServingService.update_data() (steps 1-4 only).

        update_data() is synchronous and may take minutes, so we run it
        in a thread executor to avoid blocking the event loop.

        Returns:
            Result dictionary from update_data()
        """
        logger.info(
            "Starting data update workflow via OnlineServingService.update_data()..."
        )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.online_service.update_data)

            if result.get("success"):
                logger.info(
                    f"Data update workflow completed in "
                    f"{result.get('total_duration_seconds', 0):.2f}s"
                )
            else:
                logger.error(
                    f"Data update workflow failed: {result.get('error', 'unknown')}"
                )

            return result

        except Exception as e:
            logger.error(f"Data update workflow exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "executed_at": datetime.now().isoformat(),
                "steps": [],
                "total_duration_seconds": 0,
            }

    async def get_data_status(self) -> Dict[str, Any]:
        """
        Get current data/system status from OnlineServingService.

        Returns:
            Status dictionary
        """
        try:
            return self.online_service.get_status()
        except Exception as e:
            logger.error(f"Failed to get data status: {e}")
            return {
                "is_initialized": False,
                "error": str(e),
            }


# Global singleton
_data_update_service = None


def get_data_update_service() -> DataUpdateService:
    """Get DataUpdateService singleton"""
    global _data_update_service
    if _data_update_service is None:
        _data_update_service = DataUpdateService()
    return _data_update_service
