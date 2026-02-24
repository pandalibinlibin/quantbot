"""
Scheduler Service for QuantBot

This service manages scheduled tasks for:
- Routine execution (data update + model training + signal generation)
- Execute trades (paper trading execution)

The scheduler reads configuration from system_config.yaml and automatically
detects configuration changes every 60 seconds (configurable).
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Scheduler Service for managing scheduled tasks.

    Features:
    - Reads configuration from system_config.yaml
    - Automatically detects configuration changes
    - Supports routine and execute_trades tasks
    - Uses APScheduler for reliable scheduling
    """

    def __init__(self):
        """Initialize the scheduler service."""
        self._scheduler: Optional[BackgroundScheduler] = None
        self._config_path = Path("/app/app/config/qlib/system_config.yaml")
        self._config_hash: Optional[str] = None
        self._is_running = False
        self._current_config: Dict[str, Any] = {}

    def _load_config(self) -> Dict[str, Any]:
        """
        Load scheduler configuration from YAML file.

        Returns:
            Scheduler configuration dictionary
        """
        try:
            if not self._config_path.exists():
                logger.warning(f"Config file not found: {self._config_path}")
                return self._get_default_config()

            with open(self._config_path, "r") as f:
                config = yaml.safe_load(f)

            scheduler_config = config.get("scheduler", {})
            return scheduler_config

        except Exception as e:
            logger.error(f"Failed to load scheduler config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default scheduler configuration."""
        return {
            "routine": {
                "enabled": False,
                "time": "23:00",
            },
            "execute_trades": {
                "enabled": False,
                "time": "09:35",
            },
            "timezone": "Asia/Shanghai",
            "config_check_interval": 60,
        }

    def _get_config_hash(self) -> str:
        """
        Calculate hash of current configuration for change detection.

        Returns:
            MD5 hash of configuration
        """
        config = self._load_config()
        config_str = str(sorted(config.items()))
        return hashlib.md5(config_str.encode()).hexdigest()

    def _check_config_changes(self) -> None:
        """
        Check if configuration has changed and update jobs accordingly.
        This is called periodically by the scheduler.
        """
        try:
            new_hash = self._get_config_hash()

            if new_hash != self._config_hash:
                logger.info("Scheduler configuration changed, updating jobs...")
                self._config_hash = new_hash
                self._update_jobs()

        except Exception as e:
            logger.error(f"Error checking config changes: {e}")

    def _update_jobs(self) -> None:
        """Update scheduled jobs based on current configuration."""
        if self._scheduler is None:
            return

        config = self._load_config()
        self._current_config = config
        timezone = config.get("timezone", "Asia/Shanghai")

        # Update routine job
        routine_config = config.get("routine", {})
        self._update_job(
            job_id="routine_task",
            enabled=routine_config.get("enabled", False),
            time_str=routine_config.get("time", "23:00"),
            timezone=timezone,
            func=self._execute_routine,
        )

        # Update execute_trades job
        trades_config = config.get("execute_trades", {})
        self._update_job(
            job_id="execute_trades_task",
            enabled=trades_config.get("enabled", False),
            time_str=trades_config.get("time", "09:35"),
            timezone=timezone,
            func=self._execute_trades,
        )

        logger.info(
            f"Jobs updated - routine: {routine_config.get('enabled', False)} at {routine_config.get('time', '23:00')}, "
            f"execute_trades: {trades_config.get('enabled', False)} at {trades_config.get('time', '09:35')}"
        )

    def _update_job(
        self,
        job_id: str,
        enabled: bool,
        time_str: str,
        timezone: str,
        func: callable,
    ) -> None:
        """
        Update or remove a scheduled job.

        Args:
            job_id: Unique job identifier
            enabled: Whether the job should be enabled
            time_str: Time in HH:MM format
            timezone: Timezone string
            func: Function to execute
        """
        if self._scheduler is None:
            return

        # Remove existing job if present
        existing_job = self._scheduler.get_job(job_id)
        if existing_job:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        # Add new job if enabled
        if enabled:
            try:
                hour, minute = map(int, time_str.split(":"))
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=timezone,
                )
                self._scheduler.add_job(
                    func,
                    trigger=trigger,
                    id=job_id,
                    name=job_id,
                    replace_existing=True,
                )
                logger.info(f"Added job: {job_id} at {time_str} ({timezone})")

            except Exception as e:
                logger.error(f"Failed to add job {job_id}: {e}")

    def _execute_routine(self) -> None:
        """
        Execute the routine task.
        Calls OnlineServingService.routine()
        """
        logger.info("Scheduler: Executing routine task...")
        try:
            from app.services.online_serving_service import get_online_serving_service

            service = get_online_serving_service()
            result = service.routine()

            if result.get("success"):
                logger.info("Scheduler: Routine task completed successfully")
            else:
                logger.error(f"Scheduler: Routine task failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Scheduler: Routine task error: {e}")

    def _execute_trades(self) -> None:
        """
        Execute the paper trading task.
        Calls PaperTradingService.execute_trades()
        """
        logger.info("Scheduler: Executing trades task...")
        try:
            from app.services.paper_trading_service import get_paper_trading_service
            from app.services.notification_service import get_notification_service

            service = get_paper_trading_service()
            result = service.execute_trades()

            if result.get("success"):
                logger.info("Scheduler: Execute trades completed successfully")

                # Send email notification if configured
                try:
                    notification_service = get_notification_service()
                    trading_plan = result.get("trading_plan", {})
                    notification_service.send_trading_plan_email(trading_plan)
                except Exception as e:
                    logger.warning(f"Scheduler: Failed to send email notification: {e}")
            else:
                logger.error(f"Scheduler: Execute trades failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Scheduler: Execute trades error: {e}")

    def start(self) -> None:
        """Start the scheduler."""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        try:
            self._scheduler = BackgroundScheduler()

            # Load initial configuration
            config = self._load_config()
            self._current_config = config
            self._config_hash = self._get_config_hash()

            # Add config watcher job
            check_interval = config.get("config_check_interval", 60)
            self._scheduler.add_job(
                self._check_config_changes,
                "interval",
                seconds=check_interval,
                id="config_watcher",
                name="Config Watcher",
            )

            # Initialize jobs based on config
            self._update_jobs()

            # Start the scheduler
            self._scheduler.start()
            self._is_running = True

            logger.info(f"Scheduler started (config check interval: {check_interval}s)")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._is_running or self._scheduler is None:
            logger.warning("Scheduler is not running")
            return

        try:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            self._is_running = False
            logger.info("Scheduler stopped")

        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status.

        Returns:
            Status dictionary with job information
        """
        status = {
            "is_running": self._is_running,
            "config": self._current_config,
            "jobs": [],
        }

        if self._scheduler and self._is_running:
            for job in self._scheduler.get_jobs():
                if job.id != "config_watcher":
                    job_info = {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": (
                            job.next_run_time.isoformat() if job.next_run_time else None
                        ),
                    }
                    status["jobs"].append(job_info)

        return status


# Singleton instance
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """
    Get the singleton SchedulerService instance.

    Returns:
        SchedulerService instance
    """
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
