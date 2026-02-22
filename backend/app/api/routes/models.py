"""
Models API routes for model metrics and analysis.

This module provides endpoints for:
- Getting active model metrics
- Getting chart data for various visualizations
- Accessing feature importance data

Educational Notes:
- Metrics are pre-calculated during routine to avoid delays
- All data is loaded from JSON files saved by ModelMetricsService
- Supports comprehensive model performance analysis
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from loguru import logger

from app.models import (
    ModelMetricsResponse,
    ChartDataResponse,
    ICMetrics,
    LongShortMetrics,
    QualityMetrics,
    FeatureImportanceItem,
)
from app.services.model_metrics_service import get_model_metrics_service

router = APIRouter()


@router.get("/active/metrics", response_model=ModelMetricsResponse)
def get_active_model_metrics() -> ModelMetricsResponse:
    """
    Get comprehensive metrics for the active Rolling Ensemble model.

    Returns:
        Complete model metrics including IC, Long-Short, Quality, and Feature Importance

    Raises:
        HTTPException: If metrics file not found or invalid

    Educational Notes:
    - Metrics are calculated during routine after model training
    - Returns pre-calculated metrics to avoid page load delays
    - Includes all metrics needed for comprehensive analysis
    """
    try:
        metrics_service = get_model_metrics_service()
        metrics = metrics_service.load_metrics(model_id="active")

        if metrics is None:
            raise HTTPException(
                status_code=404,
                detail="Model metrics not found. Please run routine first to train models and calculate metrics.",
            )

        # Parse metrics into response model
        response = ModelMetricsResponse(
            model_type=metrics.get("model_type", "Unknown"),
            calculated_at=metrics.get("calculated_at", ""),
            frequency=metrics.get("frequency", "day"),
            ic_metrics=ICMetrics(**metrics.get("ic_metrics", {})),
            long_short_metrics=LongShortMetrics(
                **metrics.get("long_short_metrics", {})
            ),
            quality_metrics=QualityMetrics(**metrics.get("quality_metrics", {})),
            feature_importance=(
                [
                    FeatureImportanceItem(**item)
                    for item in metrics.get("feature_importance", [])
                ]
                if metrics.get("feature_importance")
                else None
            ),
        )

        logger.info("Successfully retrieved active model metrics")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active model metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve model metrics: {str(e)}"
        )


@router.get("/active/charts/ic-series", response_model=ChartDataResponse)
def get_ic_series_chart() -> ChartDataResponse:
    """
    Get IC time series data for chart visualization.

    Returns:
        IC and Rank IC time series data

    Educational Notes:
    - Daily IC values show prediction quality over time
    - Both IC (Pearson) and Rank IC (Spearman) are included
    """
    try:
        metrics_service = get_model_metrics_service()
        metrics = metrics_service.load_metrics(model_id="active")

        if metrics is None:
            raise HTTPException(status_code=404, detail="Model metrics not found")

        ic_metrics = metrics.get("ic_metrics", {})

        return ChartDataResponse(
            chart_type="ic_series",
            data={
                "ic": ic_metrics.get("ic_series", []),
                "rank_ic": ic_metrics.get("rank_ic_series", []),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get IC series chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/charts/monthly-ic", response_model=ChartDataResponse)
def get_monthly_ic_chart() -> ChartDataResponse:
    """
    Get monthly IC data for heatmap visualization.

    Returns:
        Monthly IC aggregated by year and month

    Educational Notes:
    - Shows IC stability across different time periods
    - Useful for identifying seasonal patterns
    """
    try:
        metrics_service = get_model_metrics_service()
        metrics = metrics_service.load_metrics(model_id="active")

        if metrics is None:
            raise HTTPException(status_code=404, detail="Model metrics not found")

        ic_metrics = metrics.get("ic_metrics", {})

        return ChartDataResponse(
            chart_type="monthly_ic", data=ic_metrics.get("monthly_ic", [])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get monthly IC chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/charts/group-returns", response_model=ChartDataResponse)
def get_group_returns_chart() -> ChartDataResponse:
    """
    Get group return data for cumulative return visualization.

    Returns:
        Cumulative returns for 5 groups (Group1-Group5)

    Educational Notes:
    - Group1 has highest predicted returns, Group5 has lowest
    - If model is effective, Group1 should outperform Group5
    - Clear separation indicates good ranking ability
    """
    try:
        metrics_service = get_model_metrics_service()
        metrics = metrics_service.load_metrics(model_id="active")

        if metrics is None:
            raise HTTPException(status_code=404, detail="Model metrics not found")

        group_returns = metrics.get("group_returns", {})

        return ChartDataResponse(chart_type="group_returns", data=group_returns)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get group returns chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/charts/long-short-series", response_model=ChartDataResponse)
def get_long_short_series_chart() -> ChartDataResponse:
    """
    Get long-short return time series data.

    Returns:
        Daily long-short returns

    Educational Notes:
    - Shows daily performance of long-short strategy
    - Used for distribution analysis and Sharpe calculation
    """
    try:
        metrics_service = get_model_metrics_service()
        metrics = metrics_service.load_metrics(model_id="active")

        if metrics is None:
            raise HTTPException(status_code=404, detail="Model metrics not found")

        long_short_metrics = metrics.get("long_short_metrics", {})

        return ChartDataResponse(
            chart_type="long_short_series",
            data=long_short_metrics.get("long_short_series", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get long-short series chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/charts/auto-correlation", response_model=ChartDataResponse)
def get_auto_correlation_chart() -> ChartDataResponse:
    """
    Get auto correlation time series data.

    Returns:
        Daily auto correlation values

    Educational Notes:
    - Measures prediction stability over time
    - Values 0.1-0.3 are normal
    - Too high (>0.9) may indicate overfitting
    """
    try:
        metrics_service = get_model_metrics_service()
        metrics = metrics_service.load_metrics(model_id="active")

        if metrics is None:
            raise HTTPException(status_code=404, detail="Model metrics not found")

        quality_metrics = metrics.get("quality_metrics", {})

        return ChartDataResponse(
            chart_type="auto_correlation",
            data=quality_metrics.get("auto_corr_series", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get auto correlation chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/feature-importance", response_model=List[FeatureImportanceItem])
def get_feature_importance(limit: Optional[int] = None) -> List[FeatureImportanceItem]:
    """
    Get feature importance data.

    Args:
        limit: Optional limit on number of features to return (default: all)

    Returns:
        List of features with importance values

    Educational Notes:
    - Shows which factors contribute most to predictions
    - Based on latest model (Model 13)
    - Critical for factor engineering and understanding model behavior
    """
    try:
        metrics_service = get_model_metrics_service()
        metrics = metrics_service.load_metrics(model_id="active")

        if metrics is None:
            raise HTTPException(status_code=404, detail="Model metrics not found")

        feature_importance = metrics.get("feature_importance")

        if feature_importance is None:
            return []

        # Convert to FeatureImportanceItem objects
        features = [FeatureImportanceItem(**item) for item in feature_importance]

        # Apply limit if specified
        if limit is not None and limit > 0:
            features = features[:limit]

        logger.info(f"Retrieved {len(features)} feature importance items")
        return features

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feature importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
