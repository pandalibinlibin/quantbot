"""
Simple timing utility for monitoring execution time.
This module provides a simple context manager for tracking
execution time and logging it.
"""

import time
import logging
from contextlib import contextmanager
from typing import Dict

logger = logging.getLogger(__name__)


@contextmanager
def Timer(operation: str):
    """
    Simple context manager for timing code blocks.

    Usage:
        with Timer("model_training"):
            model.fit(dataset)

    This will log:
        ⏱️  [model_training] Started
        ⏱️  [model_training] Completed in 123.45s

    Args:
        operation: name of the operation being timed
    """
    logger.info(f"⏱️  [{operation}] Started")
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"⏱️  [{operation}] Completed in {duration:.2f}s")


class WorkflowTimer:
    """
    Timer for tracking multiple steps in a workflow.

    Usage:
        timer = WorkflowTimer()

        with timer.step("data_loading"):
            load_data()

        with timer.step("model_training"):
            train_model()

        summary = timer.get_summary()
        # Returns: {"data_loading": 10.5, "model_training": 123.4, "total": 133.9}
    """

    def __init__(self):
        self.timings: Dict[str, float] = {}
        self.workflow_start = time.time()

    @contextmanager
    def step(self, operation: str):
        """
        Time a single step in the workflow.

        Args:
            operation: Name of the operation
        """
        logger.info(f"⏱️  [{operation}] Started")
        start_time = time.time()

        try:
            yield
        finally:
            duration = time.time() - start_time
            self.timings[operation] = duration
            logger.info(f"⏱️  [{operation}] Completed in {duration:.2f}s")

    def get_summary(self) -> Dict[str, float]:
        """
        Get timing summary for all steps.

        Returns:
            Dictionary with timing for each step and total time
        """
        total_time = time.time() - self.workflow_start
        return {**self.timings, "total": total_time}
