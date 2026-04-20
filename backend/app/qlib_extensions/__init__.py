"""
Qlib Extensions Module

This module contains custom extensions for Qlib, including:
- Data preprocessing processors (EMA smoothing, relative change, etc.)
- Data broadcast utilities (time/stock broadcasting for macro data)
- Custom data handlers
"""

from .preprocessing import (
    EMA5Processor,
    RelativeChangeProcessor,
    PreprocessedDataHandler,
)

__all__ = [
    "EMA5Processor",
    "RelativeChangeProcessor",
    "PreprocessedDataHandler",
]
