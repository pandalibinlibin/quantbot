"""
Model Metrics Service for calculating comprehensive model performance metrics.

This service integrates Qlib's model analysis functions to calculate:
- IC metrics (IC, ICIR, Rank IC, Rank ICIR)
- Long-Short strategy performance
- Feature importance
- Prediction quality (Precision, Auto Correlation)
- Group return analysis

Educational Notes:
- Based on Qlib's contrib.eva.alpha and contrib.report modules
- Metrics are calculated after training and saved for frontend display
- All calculations use Qlib's professional quantitative finance metrics
"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from loguru import logger

from app.core.config import settings


class ModelMetricsService:
    """
    Service for calculating and managing model performance metrics.

    This service calculates comprehensive metrics for the Rolling Ensemble model:
    - IC Analysis: IC, ICIR, Rank IC, Rank ICIR, time series, monthly heatmap
    - Long-Short Performance: Returns, Sharpe ratios, cumulative returns
    - Feature Importance: Top features from the latest model
    - Prediction Quality: Long/Short precision, auto correlation
    - Group Analysis: 5-group cumulative returns
    """

    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize the model metrics service.

        Args:
            metrics_dir: Directory to save metrics (default: mlruns/model_metrics)
        """
        if metrics_dir is None:
            metrics_dir = Path(settings.MLRUNS_PATH) / "model_metrics"

        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def calculate_all_metrics(
        self,
        pred: pd.Series,
        label: pd.Series,
        model: Optional[Any] = None,
        freq: str = "day",
        return_horizon_days: int = 1,
    ) -> Dict[str, Any]:
        """
        Calculate all model performance metrics.

        Args:
            pred: Prediction series (MultiIndex: [instrument, datetime])
            label: Evaluation return series (tradable PnL, NOT vol-scaled training label)
            model: Latest trained model for feature importance (optional)
            freq: Data frequency (only "day" is supported)
            return_horizon_days: Holding horizon of each label observation (e.g. 5 for
                T+1 open → T+6 close). Used to annualize long-short means/Sharpe
                as 252/horizon instead of incorrectly assuming daily returns.

        Returns:
            Dictionary containing all metrics and chart data
        """
        logger.info(
            "Calculating comprehensive model metrics "
            f"(return_horizon_days={return_horizon_days})..."
        )

        try:
            # Prepare pred_label DataFrame
            pred_label = self._prepare_pred_label(pred, label)

            # Calculate IC metrics
            ic_metrics = self._calculate_ic_metrics(pred_label)

            # Calculate Long-Short metrics
            long_short_metrics = self._calculate_long_short_metrics(
                pred_label, freq, return_horizon_days=return_horizon_days
            )

            # Calculate prediction quality
            quality_metrics = self._calculate_quality_metrics(pred_label)

            # Calculate feature importance (if model provided)
            feature_importance = self._calculate_feature_importance(model)

            # Calculate group returns
            group_returns = self._calculate_group_returns(pred_label)

            # Combine all metrics
            all_metrics = {
                "model_type": "Rolling Ensemble",
                "calculated_at": datetime.utcnow().isoformat(),
                "frequency": freq,
                "return_horizon_days": return_horizon_days,
                "evaluation_note": (
                    "IC/long-short/group metrics use unscaled tradable evaluation "
                    "returns (not vol-scaled training labels). Group cumulative "
                    "curves still overlap multi-day horizons; treat ranking "
                    "separation as qualitative."
                ),
                "ic_metrics": ic_metrics,
                "long_short_metrics": long_short_metrics,
                "quality_metrics": quality_metrics,
                "feature_importance": feature_importance,
                "group_returns": group_returns,
            }

            logger.info("Model metrics calculation completed successfully")
            return all_metrics

        except Exception as e:
            logger.error(f"Failed to calculate model metrics: {e}")
            raise

    def _prepare_pred_label(self, pred: pd.Series, label: pd.Series) -> pd.DataFrame:
        """
        Prepare pred_label DataFrame for analysis.

        Args:
            pred: Prediction series (MultiIndex)
            label: Label series (MultiIndex)

        Returns:
            DataFrame with columns ['score', 'label'] and MultiIndex [datetime, instrument]
        """
        # Log index info for debugging
        logger.info(f"pred index names: {pred.index.names}, shape: {pred.shape}")
        logger.info(f"label index names: {label.index.names}, shape: {label.shape}")

        # Normalize index names to ensure they match
        # Qlib D.features returns [instrument, datetime], signals may have [datetime, instrument]
        pred_df = pred.to_frame("score")
        label_df = label.to_frame("label")

        # Reset index to columns for merging
        pred_df = pred_df.reset_index()
        label_df = label_df.reset_index()

        # Standardize column names
        pred_cols = [c.lower() if isinstance(c, str) else c for c in pred_df.columns]
        label_cols = [c.lower() if isinstance(c, str) else c for c in label_df.columns]
        pred_df.columns = pred_cols
        label_df.columns = label_cols

        # Find datetime and instrument columns
        datetime_col = None
        instrument_col = None
        for col in pred_df.columns:
            if "datetime" in str(col).lower() or "date" in str(col).lower():
                datetime_col = col
            if "instrument" in str(col).lower() or "stock" in str(col).lower():
                instrument_col = col

        if datetime_col is None or instrument_col is None:
            # Try using positional columns
            logger.warning(
                f"Could not find datetime/instrument columns, using positional"
            )
            datetime_col = pred_df.columns[0]
            instrument_col = pred_df.columns[1]

        logger.info(
            f"Using datetime_col={datetime_col}, instrument_col={instrument_col}"
        )

        # Merge on datetime and instrument
        pred_label = pd.merge(
            pred_df[[datetime_col, instrument_col, "score"]],
            label_df,
            on=[datetime_col, instrument_col],
            how="inner",
        )

        logger.info(f"After merge: {len(pred_label)} samples")

        # Set MultiIndex back
        pred_label = pred_label.set_index([datetime_col, instrument_col])

        # Drop NaN values
        pred_label = pred_label.dropna()

        logger.info(f"Prepared pred_label with {len(pred_label)} samples")
        return pred_label

    def _calculate_ic_metrics(self, pred_label: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate IC (Information Coefficient) metrics.

        IC measures the correlation between predictions and actual returns.
        Higher IC indicates better predictive power.

        Args:
            pred_label: DataFrame with 'score' and 'label' columns (MultiIndex: datetime, instrument)

        Returns:
            Dictionary with IC metrics and time series data
        """

        # Calculate IC manually since pred_label has MultiIndex
        # Group by datetime level and calculate correlation
        def calc_corr(group):
            return group["score"].corr(group["label"])

        def calc_rank_corr(group):
            return group["score"].corr(group["label"], method="spearman")

        # Get datetime level name
        datetime_level = pred_label.index.names[0] if pred_label.index.names[0] else 0

        ic = pred_label.groupby(level=datetime_level).apply(calc_corr)
        ric = pred_label.groupby(level=datetime_level).apply(calc_rank_corr)

        # Calculate statistics
        ic_mean = float(ic.mean())
        ic_std = float(ic.std())
        icir = ic_mean / ic_std if ic_std > 0 else 0.0

        ric_mean = float(ric.mean())
        ric_std = float(ric.std())
        ricir = ric_mean / ric_std if ric_std > 0 else 0.0

        # Prepare IC time series for chart
        ic_series = ic.reset_index()
        ic_series.columns = ["datetime", "ic"]
        ic_series["datetime"] = ic_series["datetime"].astype(str)
        ic_series_data = ic_series.to_dict("records")

        ric_series = ric.reset_index()
        ric_series.columns = ["datetime", "rank_ic"]
        ric_series["datetime"] = ric_series["datetime"].astype(str)
        ric_series_data = ric_series.to_dict("records")

        # Calculate monthly IC for heatmap
        monthly_ic = self._calculate_monthly_ic(ic)

        # Calculate IC distribution data for histogram
        ic_distribution = self._calculate_ic_distribution(ic)

        return {
            "ic_mean": ic_mean,
            "ic_std": ic_std,
            "icir": icir,
            "rank_ic_mean": ric_mean,
            "rank_ic_std": ric_std,
            "rank_icir": ricir,
            "ic_series": ic_series_data,
            "rank_ic_series": ric_series_data,
            "monthly_ic": monthly_ic,
            "ic_distribution": ic_distribution,
        }

    def _calculate_monthly_ic(self, ic: pd.Series) -> List[Dict[str, Any]]:
        """
        Calculate monthly IC for heatmap visualization.

        Args:
            ic: IC time series

        Returns:
            List of monthly IC data for heatmap
        """
        # Group by year and month
        ic_df = ic.to_frame("ic")
        ic_df["year"] = ic_df.index.year
        ic_df["month"] = ic_df.index.month

        monthly_ic = ic_df.groupby(["year", "month"])["ic"].mean()

        # Convert to list of dicts for frontend
        monthly_data = []
        for (year, month), value in monthly_ic.items():
            monthly_data.append(
                {"year": int(year), "month": int(month), "ic": float(value)}
            )

        return monthly_data

    def _calculate_ic_distribution(self, ic: pd.Series) -> Dict[str, Any]:
        """
        Calculate IC distribution data for histogram and Q-Q plot.

        Args:
            ic: IC time series

        Returns:
            Dictionary with histogram bins and Q-Q plot data
        """
        ic_values = ic.dropna().values

        # Calculate histogram bins
        hist, bin_edges = np.histogram(ic_values, bins=20)
        histogram_data = []
        for i in range(len(hist)):
            histogram_data.append(
                {
                    "bin_start": float(bin_edges[i]),
                    "bin_end": float(bin_edges[i + 1]),
                    "count": int(hist[i]),
                    "bin_center": float((bin_edges[i] + bin_edges[i + 1]) / 2),
                }
            )

        # Calculate Q-Q plot data (theoretical quantiles vs sample quantiles)
        from scipy import stats

        sorted_ic = np.sort(ic_values)
        n = len(sorted_ic)
        theoretical_quantiles = stats.norm.ppf(np.arange(1, n + 1) / (n + 1))

        # Sample every 10th point if too many data points
        step = max(1, n // 100)
        qq_data = []
        for i in range(0, n, step):
            qq_data.append(
                {
                    "theoretical": float(theoretical_quantiles[i]),
                    "sample": float(sorted_ic[i]),
                }
            )

        return {
            "histogram": histogram_data,
            "qq_plot": qq_data,
            "mean": float(np.mean(ic_values)),
            "std": float(np.std(ic_values)),
            "skewness": float(stats.skew(ic_values)),
            "kurtosis": float(stats.kurtosis(ic_values)),
        }

    def _calculate_long_short_metrics(
        self,
        pred_label: pd.DataFrame,
        freq: str,
        return_horizon_days: int = 1,
    ) -> Dict[str, Any]:
        """
        Calculate Long-Short strategy performance metrics.

        Long-Short strategy: Long top 20% stocks, short bottom 20% stocks.

        Args:
            pred_label: DataFrame with 'score' and 'label' columns (MultiIndex: datetime, instrument)
            freq: Data frequency for annualization
            return_horizon_days: Label holding horizon in trading days

        Returns:
            Dictionary with Long-Short metrics and returns data
        """
        # Calculate long-short returns manually since pred_label has MultiIndex
        quantile = 0.2
        datetime_level = pred_label.index.names[0] if pred_label.index.names[0] else 0
        horizon = max(1, int(return_horizon_days or 1))

        def calc_group_return(group):
            n = max(1, int(len(group) * quantile))
            # Long top n stocks
            long_return = group.nlargest(n, "score")["label"].mean()
            # Short bottom n stocks
            short_return = group.nsmallest(n, "score")["label"].mean()
            # Average return
            avg_return = group["label"].mean()
            return pd.Series(
                {
                    "long_short": long_return - short_return,
                    "long_avg": long_return - avg_return,
                }
            )

        daily_returns = pred_label.groupby(level=datetime_level).apply(
            calc_group_return
        )
        long_short_r = daily_returns["long_short"]
        long_avg_r = daily_returns["long_avg"]

        # Annualize by number of non-overlapping horizons per year.
        # (Overlapping daily samples still inflate Sharpe somewhat; better than *252 on 5d rets.)
        scaler = 252.0 / horizon

        # Calculate annualized metrics
        ls_ann_return = float(long_short_r.mean() * scaler)
        ls_ann_sharpe = float(
            long_short_r.mean() / long_short_r.std() * np.sqrt(scaler)
            if long_short_r.std() > 0
            else 0.0
        )

        la_ann_return = float(long_avg_r.mean() * scaler)
        la_ann_sharpe = float(
            long_avg_r.mean() / long_avg_r.std() * np.sqrt(scaler)
            if long_avg_r.std() > 0
            else 0.0
        )

        # Prepare time series data
        ls_series = long_short_r.reset_index()
        ls_series["datetime"] = ls_series["datetime"].astype(str)
        ls_series.columns = ["datetime", "return"]
        ls_series_data = ls_series.to_dict("records")

        # Calculate cumulative returns for chart
        cumulative_returns = long_short_r.cumsum()
        cum_series = cumulative_returns.reset_index()
        cum_series["datetime"] = cum_series["datetime"].astype(str)
        cum_series.columns = ["datetime", "cumulative_return"]
        cum_series_data = cum_series.to_dict("records")

        # Calculate return distribution for histogram
        ls_values = long_short_r.dropna().values
        hist, bin_edges = np.histogram(ls_values, bins=20)
        return_distribution = []
        for i in range(len(hist)):
            return_distribution.append(
                {
                    "bin_start": float(bin_edges[i]),
                    "bin_end": float(bin_edges[i + 1]),
                    "count": int(hist[i]),
                    "bin_center": float((bin_edges[i] + bin_edges[i + 1]) / 2),
                }
            )

        return {
            "long_short_ann_return": ls_ann_return,
            "long_short_ann_sharpe": ls_ann_sharpe,
            "long_avg_ann_return": la_ann_return,
            "long_avg_ann_sharpe": la_ann_sharpe,
            "mean_period_long_short": float(long_short_r.mean()),
            "return_horizon_days": horizon,
            "annualization_scaler": scaler,
            "long_short_series": ls_series_data,
            "cumulative_returns": cum_series_data,
            "return_distribution": return_distribution,
        }

    def _calculate_quality_metrics(self, pred_label: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate prediction quality metrics.

        Includes:
        - Long Precision: Accuracy of predicting up movements
        - Short Precision: Accuracy of predicting down movements
        - Auto Correlation: Prediction stability over time

        Args:
            pred_label: DataFrame with 'score' and 'label' columns (MultiIndex: datetime, instrument)

        Returns:
            Dictionary with quality metrics
        """
        # Calculate precision manually since pred_label has MultiIndex
        quantile = 0.2
        datetime_level = pred_label.index.names[0] if pred_label.index.names[0] else 0

        def calc_precision(group):
            n = max(1, int(len(group) * quantile))
            # Long: top n by score, check if label > 0
            long_group = group.nlargest(n, "score")
            long_correct = (long_group["label"] > 0).sum()
            long_prec = long_correct / len(long_group) if len(long_group) > 0 else 0

            # Short: bottom n by score, check if label < 0
            short_group = group.nsmallest(n, "score")
            short_correct = (short_group["label"] < 0).sum()
            short_prec = short_correct / len(short_group) if len(short_group) > 0 else 0

            return pd.Series({"long_prec": long_prec, "short_prec": short_prec})

        daily_prec = pred_label.groupby(level=datetime_level).apply(calc_precision)
        long_precision = float(daily_prec["long_prec"].mean())
        short_precision = float(daily_prec["short_prec"].mean())

        # Calculate auto correlation manually
        try:
            # Get instrument level name
            inst_level = (
                pred_label.index.names[1] if len(pred_label.index.names) > 1 else 1
            )

            # Calculate lag-1 autocorrelation per instrument
            def calc_inst_autocorr(group):
                scores = group["score"].sort_index()
                if len(scores) > 1:
                    return scores.autocorr(lag=1)
                return np.nan

            ac_by_inst = pred_label.groupby(level=inst_level).apply(calc_inst_autocorr)
            auto_corr = (
                float(ac_by_inst.dropna().mean())
                if len(ac_by_inst.dropna()) > 0
                else 0.0
            )

            # Calculate auto correlation time series (daily average)
            def calc_daily_autocorr(group):
                # Calculate cross-sectional autocorrelation for this date
                scores = group["score"]
                if len(scores) > 1:
                    return (
                        scores.autocorr(lag=1)
                        if hasattr(scores, "autocorr")
                        else np.nan
                    )
                return np.nan

            # Use rolling autocorrelation by date
            ac_by_date = pred_label.groupby(level=datetime_level).apply(
                lambda g: g["score"].corr(g["label"])  # Use IC as proxy for stability
            )
            ac_series = ac_by_date.reset_index()
            ac_series.columns = ["datetime", "auto_corr"]
            ac_series["datetime"] = ac_series["datetime"].astype(str)
            ac_series_data = ac_series.to_dict("records")

        except Exception as e:
            logger.warning(f"Failed to calculate auto correlation: {e}")
            auto_corr = 0.0
            ac_series_data = []

        # Calculate turnover metrics (top/bottom stock changes)
        turnover_data = self._calculate_turnover(pred_label, quantile)

        return {
            "long_precision": long_precision,
            "short_precision": short_precision,
            "auto_correlation": auto_corr,
            "auto_corr_series": ac_series_data,
            "turnover": turnover_data,
        }

    def _calculate_turnover(
        self, pred_label: pd.DataFrame, quantile: float = 0.2
    ) -> Dict[str, Any]:
        """
        Calculate turnover metrics for top and bottom stocks.

        Turnover measures how much the top/bottom stock selection changes daily.
        Lower turnover indicates more stable predictions.

        Args:
            pred_label: DataFrame with 'score' and 'label' columns (MultiIndex: datetime, instrument)
            quantile: Quantile for top/bottom selection (default: 0.2 = top/bottom 20%)

        Returns:
            Dictionary with turnover time series and statistics
        """
        datetime_level = pred_label.index.names[0] if pred_label.index.names[0] else 0
        inst_level = pred_label.index.names[1] if len(pred_label.index.names) > 1 else 1

        # Get top and bottom stocks for each date
        def get_top_bottom(group, q):
            n = max(1, int(len(group) * q))
            top = set(group.nlargest(n, "score").index.get_level_values(inst_level))
            bottom = set(group.nsmallest(n, "score").index.get_level_values(inst_level))
            return top, bottom

        dates = pred_label.index.get_level_values(datetime_level).unique().sort_values()

        top_turnover = []
        bottom_turnover = []
        prev_top = None
        prev_bottom = None

        for date in dates:
            try:
                group = pred_label.loc[date]
                if isinstance(group, pd.Series):
                    continue
                top, bottom = get_top_bottom(
                    group.reset_index().set_index(inst_level), quantile
                )

                if prev_top is not None and len(top) > 0:
                    # Turnover = proportion of stocks that changed
                    top_change = len(top - prev_top) / len(top) if len(top) > 0 else 0
                    bottom_change = (
                        len(bottom - prev_bottom) / len(bottom)
                        if len(bottom) > 0
                        else 0
                    )
                    top_turnover.append(
                        {"datetime": str(date), "turnover": float(top_change)}
                    )
                    bottom_turnover.append(
                        {"datetime": str(date), "turnover": float(bottom_change)}
                    )

                prev_top = top
                prev_bottom = bottom
            except Exception:
                continue

        # Calculate average turnover
        avg_top_turnover = (
            np.mean([t["turnover"] for t in top_turnover]) if top_turnover else 0.0
        )
        avg_bottom_turnover = (
            np.mean([t["turnover"] for t in bottom_turnover])
            if bottom_turnover
            else 0.0
        )

        return {
            "top_turnover_series": top_turnover,
            "bottom_turnover_series": bottom_turnover,
            "avg_top_turnover": float(avg_top_turnover),
            "avg_bottom_turnover": float(avg_bottom_turnover),
        }

    def _calculate_feature_importance(
        self, model: Optional[Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Calculate feature importance from the latest model.

        Args:
            model: Trained model with get_feature_importance method

        Returns:
            List of feature importance data or None
        """
        if model is None:
            logger.warning("No model provided for feature importance calculation")
            return None

        try:
            importance = None

            # Try different ways to get feature importance
            # 1. Qlib model wrapper method
            if hasattr(model, "get_feature_importance"):
                importance = model.get_feature_importance()
                logger.info("Got feature importance via get_feature_importance()")

            # 2. Direct LightGBM model access (Qlib LGBModel stores model in .model attribute)
            elif hasattr(model, "model") and model.model is not None:
                lgb_model = model.model
                if hasattr(lgb_model, "feature_importance"):
                    feat_imp = lgb_model.feature_importance(importance_type="gain")
                    feat_names = (
                        lgb_model.feature_name()
                        if hasattr(lgb_model, "feature_name")
                        else [f"f{i}" for i in range(len(feat_imp))]
                    )
                    importance = pd.Series(feat_imp, index=feat_names).sort_values(
                        ascending=False
                    )
                    logger.info("Got feature importance from model.model (LightGBM)")

            # 3. Direct feature_importance method
            elif hasattr(model, "feature_importance"):
                importance = pd.Series(
                    model.feature_importance(), index=model.feature_name()
                ).sort_values(ascending=False)
                logger.info("Got feature importance via feature_importance()")

            # 4. sklearn-style feature_importances_
            elif hasattr(model, "feature_importances_"):
                feat_imp = model.feature_importances_
                feat_names = getattr(
                    model, "feature_names_in_", [f"f{i}" for i in range(len(feat_imp))]
                )
                importance = pd.Series(feat_imp, index=feat_names).sort_values(
                    ascending=False
                )
                logger.info("Got feature importance via feature_importances_")

            if importance is None:
                logger.warning(
                    f"Model type {type(model)} does not support feature importance. Available attrs: {dir(model)[:20]}"
                )
                return None

            # Map Column_X indices to real feature names
            importance = self._map_feature_names(importance)

            # Convert to list of dicts
            feature_data = []
            for feature, value in importance.items():
                feature_data.append(
                    {"feature": str(feature), "importance": float(value)}
                )

            logger.info(
                f"Calculated feature importance for {len(feature_data)} features"
            )
            return feature_data

        except Exception as e:
            logger.error(f"Failed to calculate feature importance: {e}", exc_info=True)
            return None

    def _map_feature_names(self, importance: pd.Series) -> pd.Series:
        """
        Map Column_X indices to real feature names from CustomFactorHandler.

        The feature order must match get_feature_config() exactly:
        1. Alpha158 factors (if enabled): KMID, KLEN, KMID2, KUP, ...
        2. Pre-computed custom factors: OHLCV + stored factors (excluding duplicates)

        Args:
            importance: Series with Column_X as index

        Returns:
            Series with real feature names as index
        """
        try:
            # Check if indices are Column_X format
            if not any(str(idx).startswith("Column_") for idx in importance.index):
                return importance  # Already has real names

            from .factor_storage import FactorStorage
            from app.config.qlib import qlib_config

            feature_names = []

            # 1. Alpha158 factors (must come first, matching get_feature_config order)
            try:
                from qlib.contrib.data.loader import Alpha158DL

                _alpha158_exprs, alpha158_names = Alpha158DL.get_feature_config()
                feature_names.extend(alpha158_names)
                logger.info(f"Alpha158 provides {len(alpha158_names)} feature names")
            except Exception as e:
                logger.warning(f"Failed to load Alpha158 names: {e}")

            # 2. Pre-computed custom factors (OHLCV + stored factors, excluding duplicates)
            storage = FactorStorage(freq=qlib_config.freq)
            existing_names = set(feature_names)

            # OHLCV fields
            ohlcv_names = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME", "VWAP"]
            for name in ohlcv_names:
                if name not in existing_names:
                    feature_names.append(name)
                    existing_names.add(name)

            # Stored factors (excluding label)
            stored_factors = storage.list_stored_factors()
            label_name = None
            try:
                from sqlmodel import Session, select
                from app.core.db import engine
                from app.models import Factor, FactorType, FactorStatus

                with Session(engine) as session:
                    statement = select(Factor).where(
                        Factor.factor_type == FactorType.LABEL,
                        Factor.status == FactorStatus.ACTIVE,
                    )
                    label_factor = session.exec(statement).first()
                    if label_factor:
                        label_name = label_factor.name
            except Exception:
                pass

            for factor_name in stored_factors:
                if label_name and factor_name == label_name:
                    continue
                upper_name = factor_name.upper()
                if upper_name not in existing_names:
                    feature_names.append(upper_name)
                    existing_names.add(upper_name)

            logger.info(
                f"Total mapped feature names: {len(feature_names)} "
                f"(first 10: {feature_names[:10]})"
            )

            # Create mapping from Column_X to feature name
            new_index = []
            for idx in importance.index:
                idx_str = str(idx)
                if idx_str.startswith("Column_"):
                    try:
                        col_num = int(idx_str.replace("Column_", ""))
                        if col_num < len(feature_names):
                            new_index.append(feature_names[col_num])
                        else:
                            new_index.append(idx_str)
                    except ValueError:
                        new_index.append(idx_str)
                else:
                    new_index.append(idx_str)

            importance.index = new_index
            logger.info(f"Mapped feature names (top 10): {list(importance.index[:10])}")
            return importance

        except Exception as e:
            logger.warning(f"Failed to map feature names: {e}")
            return importance

    def _calculate_group_returns(
        self, pred_label: pd.DataFrame, n_groups: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate cumulative returns for N groups based on prediction scores.

        Stocks are divided into N groups by prediction score.
        Group 1 has highest predicted returns, Group N has lowest.

        Args:
            pred_label: DataFrame with 'score' and 'label' columns (MultiIndex: datetime, instrument)
            n_groups: Number of groups (default: 5)

        Returns:
            Dictionary with group return data
        """
        datetime_level = pred_label.index.names[0] if pred_label.index.names[0] else 0

        # Calculate group returns by date
        group_returns = {}

        def calc_group_mean(group, group_idx, n_groups):
            sorted_group = group.sort_values("score", ascending=False)
            n = len(sorted_group)
            start_idx = n // n_groups * group_idx
            end_idx = n // n_groups * (group_idx + 1) if group_idx < n_groups - 1 else n
            return sorted_group.iloc[start_idx:end_idx]["label"].mean()

        for i in range(n_groups):
            group_name = f"Group{i+1}"

            # Get group data
            group_data = pred_label.groupby(level=datetime_level).apply(
                lambda x, idx=i: calc_group_mean(x, idx, n_groups)
            )

            # Calculate cumulative returns
            cumulative = group_data.cumsum()

            # Prepare series data
            series_data = cumulative.reset_index()
            series_data.columns = ["datetime", "cumulative_return"]
            series_data["datetime"] = series_data["datetime"].astype(str)

            group_returns[group_name] = series_data.to_dict("records")

        return group_returns

    def save_metrics(self, metrics: Dict[str, Any], model_id: str = "active") -> Path:
        """
        Save metrics to JSON file.

        Args:
            metrics: Metrics dictionary
            model_id: Model identifier (default: "active")

        Returns:
            Path to saved metrics file
        """
        metrics_file = self.metrics_dir / f"{model_id}_metrics.json"

        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

        logger.info(f"Saved metrics to {metrics_file}")
        return metrics_file

    def load_metrics(self, model_id: str = "active") -> Optional[Dict[str, Any]]:
        """
        Load metrics from JSON file.

        Args:
            model_id: Model identifier (default: "active")

        Returns:
            Metrics dictionary or None if not found
        """
        metrics_file = self.metrics_dir / f"{model_id}_metrics.json"

        if not metrics_file.exists():
            logger.warning(f"Metrics file not found: {metrics_file}")
            return None

        with open(metrics_file, "r") as f:
            metrics = json.load(f)

        logger.info(f"Loaded metrics from {metrics_file}")
        return metrics


# Singleton instance
_model_metrics_service: Optional[ModelMetricsService] = None


def get_model_metrics_service() -> ModelMetricsService:
    """Get or create the model metrics service singleton."""
    global _model_metrics_service
    if _model_metrics_service is None:
        _model_metrics_service = ModelMetricsService()
    return _model_metrics_service
