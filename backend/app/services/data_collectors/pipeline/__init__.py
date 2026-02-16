"""
Data Pipeline Module

Educational Notes:
- Provides unified data acquisition pipeline
- Integrates collector → normalize → dump workflow
- Compatible with existing API structure
- Follows Qlib's proven data processing patterns
"""

from .service import execute_data_pipeline

__all__ = [
    "execute_data_pipeline",
]
