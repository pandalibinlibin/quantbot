"""
Qlib Online Serving Service

This service manages the complete Qlib Online Serving workflow:
- Auto-initialization on first routine call
- Data incremental update
- Rolling model training (via TrainerRM + MongoDB)
- Signal generation
- Integration with paper trading (Phase 4)

Key Components:
- OnlineManager: Manages online strategies and models
- RollingStrategy: Defines rolling training strategy
- TrainerRM: Trainer based on TaskManager (MongoDB)
- RollingGen: Generates rolling tasks

Usage:
    service = get_online_serving_service()
    result = service.routine()  # Auto-initializes if needed
"""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.config.qlib import qlib_config


def _safe_float(value, default=0.0):
    """
    Safely convert a value to float, handling nan and inf values.

    JSON does not support nan or inf values, so we need to convert them
    to a default value (usually 0.0 or None).
    """
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


from app.services.qlib_init_service import get_qlib_init_service
from app.services.etf_enhanced_indexing_service import get_etf_enhanced_indexing_service
from app.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)


class OnlineServingService:
    """
    Qlib Online Serving Service

    Manages the complete online serving workflow including:
    - Auto-initialization on first routine call
    - Data incremental update
    - Rolling model training
    - Signal generation
    """

    # Persistence paths for surviving hot-reload / restart
    SIGNALS_PERSIST_DIR = Path("/app/data/signals")
    SIGNALS_PERSIST_FILE = Path("/app/data/signals/_latest_signals.pkl")
    SIGNALS_META_FILE = Path("/app/data/signals/_signals_meta.json")

    def __init__(self):
        """Initialize the Online Serving service."""
        self._online_manager = None
        self._is_initialized: bool = False
        self._freq: str = "day"
        self._last_routine_time: Optional[datetime] = None
        self._initialization_error: Optional[str] = None
        self._experiment_name: str = qlib_config.experiment_name
        self.logger = logger

        # Restore persisted state from disk (survives hot-reload)
        self._restore_persisted_state()

    @property
    def is_initialized(self) -> bool:
        """Check if OnlineManager is initialized."""
        return self._is_initialized and self._online_manager is not None

    def _get_factor_fingerprint(self) -> str:
        """
        Compute a fingerprint (hash) of active factor configuration.
        Used to detect factor definition changes between update_data runs.

        Returns:
            Hex digest string representing the current factor config
        """
        import hashlib

        try:
            from app.models import Factor, FactorStatus
            from app.core.db import engine
            from sqlmodel import Session, select

            with Session(engine) as session:
                statement = (
                    select(Factor)
                    .where(Factor.status == FactorStatus.ACTIVE)
                    .order_by(Factor.name)
                )
                active_factors = session.exec(statement).all()

            # Build a stable string from factor names, expressions, and types
            parts = []
            for f in active_factors:
                parts.append(f"{f.name}|{f.expression}|{f.factor_type}")
            fingerprint_str = ";".join(parts)
            return hashlib.md5(fingerprint_str.encode()).hexdigest()

        except Exception as e:
            self.logger.warning(f"Failed to compute factor fingerprint: {e}")
            return "unknown"

    def _persist_signals_state(self, signals: pd.DataFrame, signal_count: int) -> None:
        """
        Persist signals and metadata to disk so they survive hot-reload/restart.

        Args:
            signals: The signals DataFrame to persist
            signal_count: Number of signals generated
        """
        import json
        import pickle

        try:
            self.SIGNALS_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

            # Save signals DataFrame
            with open(self.SIGNALS_PERSIST_FILE, "wb") as f:
                pickle.dump(signals, f)

            # Save metadata (signal_count, timestamp, factor fingerprint, etc.)
            meta = {
                "signal_count": signal_count,
                "last_routine_time": (
                    self._last_routine_time.isoformat()
                    if self._last_routine_time
                    else None
                ),
                "factor_fingerprint": self._get_factor_fingerprint(),
                "persisted_at": datetime.now().isoformat(),
            }
            with open(self.SIGNALS_META_FILE, "w") as f:
                json.dump(meta, f)

            self.logger.info(
                f"Persisted {signal_count} signals to {self.SIGNALS_PERSIST_FILE}"
            )

        except Exception as e:
            self.logger.error(f"Failed to persist signals: {e}", exc_info=True)

    def _restore_persisted_state(self) -> None:
        """
        Restore persisted signals metadata on startup (after hot-reload/restart).
        Only restores signal_count and last_routine_time for Dashboard display.
        Full OnlineManager re-initialization happens on next update_data() call.
        """
        import json

        try:
            if self.SIGNALS_META_FILE.exists():
                with open(self.SIGNALS_META_FILE, "r") as f:
                    meta = json.load(f)

                self._persisted_signal_count = meta.get("signal_count", 0)
                self._persisted_factor_fingerprint = meta.get("factor_fingerprint", "")
                last_time = meta.get("last_routine_time")
                if last_time:
                    self._last_routine_time = datetime.fromisoformat(last_time)

                self.logger.info(
                    f"Restored persisted state: signal_count={self._persisted_signal_count}, "
                    f"last_routine_time={self._last_routine_time}, "
                    f"factor_fingerprint={self._persisted_factor_fingerprint}"
                )
            else:
                self._persisted_signal_count = 0
                self._persisted_factor_fingerprint = ""
                self.logger.info("No persisted signal state found")

        except Exception as e:
            self._persisted_signal_count = 0
            self._persisted_factor_fingerprint = ""
            self.logger.error(f"Failed to restore persisted state: {e}")

    def _get_data_frequency(self) -> str:
        """
        Get data frequency for stock selection system.

        Returns:
            "day" frequency
        """
        return "day"

    def _ensure_qlib_initialized(self) -> bool:
        """
        Ensure Qlib is initialized before any operation.

        Returns:
            True if Qlib is initialized successfully
        """
        qlib_service = get_qlib_init_service()
        # Note: is_initialized is a method, not a property
        if not qlib_service.is_initialized():
            self.logger.info("Initializing Qlib...")
            qlib_service.initialize()
        return qlib_service.is_initialized()

    def _get_data_time_range(self) -> tuple:
        """
        Get data time range from Qlib calendar.

        Returns:
            Tuple of (start_time, end_time) as strings
        """
        from qlib.data import D

        try:
            # Get calendar for the detected frequency
            cal = D.calendar(freq=self._freq)
            if cal is not None and len(cal) > 0:
                start_time = cal[0].strftime("%Y-%m-%d")
                end_time = cal[-1].strftime("%Y-%m-%d")
                self.logger.info(f"Data time range: {start_time} to {end_time}")
                return start_time, end_time
        except Exception as e:
            self.logger.warning(f"Failed to get calendar: {e}")

        # Fallback to default range
        return "2020-01-01", "2025-12-31"

    def _build_task_template(self) -> Dict[str, Any]:
        """
        Build task template for RollingStrategy.

        This template defines the model, dataset, and record configuration
        for rolling training tasks. Uses dynamic detection for:
        - Data frequency (day)
        - Time range (from actual data)
        - Instruments (all available stocks)

        Returns:
            Task template dictionary
        """
        # Get frequency (only day-level data supported)
        self._freq = self._get_data_frequency()

        # Get actual data time range
        start_time, end_time = self._get_data_time_range()

        # Build task template based on frequency
        # Use CustomFactorHandler and "all" instruments like training_config.yaml
        task_template = {
            "model": {
                "class": "LGBModel",
                "module_path": "qlib.contrib.model.gbdt",
                "kwargs": {
                    "loss": "mse",
                    "colsample_bytree": 0.8879,
                    "learning_rate": 0.05,
                    "subsample": 0.8789,
                    "lambda_l1": 205.6999,
                    "lambda_l2": 580.9768,
                    "max_depth": 8,
                    "num_leaves": 210,
                    "num_threads": 4,
                    "num_boost_round": 100,
                    "verbose": -1,
                },
            },
            "dataset": {
                "class": "DatasetH",
                "module_path": "qlib.data.dataset",
                "kwargs": {
                    "handler": {
                        "class": "CustomFactorHandler",
                        "module_path": "app.services.custom_factor_handler",
                        "kwargs": {
                            "start_time": start_time,
                            "end_time": end_time,
                            "fit_start_time": start_time,
                            "fit_end_time": end_time,
                            "instruments": "all",
                            "freq": self._freq,
                            "enable_alpha158": False,
                        },
                    },
                    "segments": {
                        "train": (start_time, end_time),
                        "valid": (start_time, end_time),
                        "test": (start_time, end_time),
                    },
                },
            },
            "record": [
                {
                    "class": "SignalRecord",
                    "module_path": "qlib.workflow.record_temp",
                },
            ],
        }

        return task_template

    def _get_latest_data_date(self) -> Optional[str]:
        """
        Get the latest date available in Qlib data.

        Returns:
            Latest date string in YYYY-MM-DD format, or None if not available
        """
        try:
            import qlib
            from qlib.data import D

            # Get calendar (trading days)
            calendar = D.calendar(freq=self._freq)
            if calendar is not None and len(calendar) > 0:
                latest_date = calendar[-1]
                # Convert to string format
                if hasattr(latest_date, "strftime"):
                    return latest_date.strftime("%Y-%m-%d")
                return str(latest_date)[:10]
            return None
        except Exception as e:
            self.logger.warning(f"Failed to get latest data date: {e}")
            return None

    def _prepare_signals_with_online_filter(self) -> None:
        """
        Re-prepare signals using only "online" tagged recorders.

        This fixes the issue where offline recorders' predictions (with older data)
        override online recorders' predictions (with latest data) due to duplicate
        rec_key in RollingStrategy.get_collector().
        """
        try:
            from qlib.workflow.online.utils import OnlineToolR
            from qlib.model.ens.ensemble import RollingEnsemble, AverageEnsemble
            from qlib.workflow.task.collect import MergeCollector

            # Create OnlineToolR instance to access get_online_tag method
            online_tool = OnlineToolR()

            # Create filter function to only use "online" tagged recorders
            def online_filter(rec):
                return online_tool.get_online_tag(rec) == OnlineToolR.ONLINE_TAG

            # Get collector with online filter for each strategy
            collector_dict = {}
            for strategy in self._online_manager.strategies:
                # Get collector with rec_filter_func to filter only online recorders
                collector = strategy.get_collector(
                    process_list=[RollingEnsemble()], rec_filter_func=online_filter
                )
                collector_dict[strategy.name_id] = collector

            # Merge collectors
            merge_collector = MergeCollector(collector_dict, process_list=[])

            # Prepare signals using AverageEnsemble
            signals = AverageEnsemble()(merge_collector())

            # Update OnlineManager's signals
            self._online_manager.signals = signals

            self.logger.info(
                f"Re-prepared signals with online filter, total {len(signals)} signals"
            )

            # Log date range for verification
            if signals is not None and len(signals) > 0:
                dates = signals.index.get_level_values("datetime").unique()
                self.logger.info(f"Signal date range: {dates.min()} to {dates.max()}")

        except Exception as e:
            self.logger.error(f"Failed to re-prepare signals with online filter: {e}")
            raise

    def _extend_signals_to_latest_date(self, signals: pd.DataFrame) -> pd.DataFrame:
        """
        Extend signals to cover all available data dates using the latest model.

        If signals end before the latest data date, use the most recent model
        to predict signals for the remaining dates.

        Args:
            signals: Existing signals DataFrame with MultiIndex (datetime, instrument)

        Returns:
            Extended signals DataFrame covering all data dates
        """
        try:
            from qlib.data import D

            # Get signal date range
            signal_dates = signals.index.get_level_values("datetime").unique()
            signal_end_date = signal_dates.max()

            # Get data date range
            latest_data_date = self._get_latest_data_date()
            if latest_data_date is None:
                self.logger.warning("Could not determine latest data date")
                return signals

            latest_data_date = pd.Timestamp(latest_data_date)

            # Check if signals already cover all data
            if signal_end_date >= latest_data_date:
                self.logger.info(
                    f"Signals already cover all data dates (signal_end={signal_end_date}, data_end={latest_data_date})"
                )
                return signals

            self.logger.info(
                f"Extending signals from {signal_end_date} to {latest_data_date}"
            )

            # Get the latest model from online recorders
            from qlib.workflow.online.utils import OnlineToolR
            from qlib.workflow import R

            online_tool = OnlineToolR()

            # Find the latest online recorder
            latest_recorder = None
            latest_exp_name = None

            for strategy in self._online_manager.strategies:
                exp = R.get_exp(experiment_name=strategy.name_id)
                recorders = exp.list_recorders()

                for rec_id, rec in recorders.items():
                    if online_tool.get_online_tag(rec) == OnlineToolR.ONLINE_TAG:
                        latest_recorder = rec
                        latest_exp_name = strategy.name_id
                        break
                if latest_recorder:
                    break

            if latest_recorder is None:
                self.logger.warning("No online recorder found for signal extension")
                return signals

            # Load the model from the recorder
            model = latest_recorder.load_object("params.pkl")
            self.logger.info(f"Loaded model from recorder for signal extension")

            # Create dataset for the missing date range
            from app.services.custom_factor_handler import CustomFactorHandler
            from qlib.data.dataset import DatasetH

            # Get the day after signal_end_date
            calendar = D.calendar(freq="day")
            calendar_list = list(calendar)

            # Find the index of signal_end_date in calendar
            try:
                end_idx = calendar_list.index(signal_end_date)
                start_date = (
                    calendar_list[end_idx + 1]
                    if end_idx + 1 < len(calendar_list)
                    else None
                )
            except ValueError:
                # signal_end_date not in calendar, find the next trading day
                start_date = None
                for cal_date in calendar_list:
                    if cal_date > signal_end_date:
                        start_date = cal_date
                        break

            if start_date is None or start_date > latest_data_date:
                self.logger.info("No additional dates to predict")
                return signals

            self.logger.info(
                f"Predicting signals for dates: {start_date} to {latest_data_date}"
            )

            # Create handler for the missing date range
            handler = CustomFactorHandler(
                start_time=str(start_date.date()),
                end_time=str(latest_data_date.date()),
                freq="day",
            )

            dataset = DatasetH(
                handler=handler,
                segments={
                    "predict": (start_date, latest_data_date),
                },
            )

            # Generate predictions
            new_predictions = model.predict(dataset, segment="predict")

            if new_predictions is None or len(new_predictions) == 0:
                self.logger.warning("No new predictions generated")
                return signals

            self.logger.info(f"Generated {len(new_predictions)} new predictions")

            # Combine original signals with new predictions
            # Ensure both have the same column name
            if isinstance(new_predictions, pd.Series):
                new_predictions = new_predictions.to_frame(name="score")
            if isinstance(signals, pd.Series):
                signals = signals.to_frame(name="score")

            # Ensure column names match
            if signals.columns[0] != new_predictions.columns[0]:
                new_predictions.columns = signals.columns

            # Concatenate and sort
            extended_signals = pd.concat([signals, new_predictions])
            extended_signals = extended_signals.sort_index()

            # Remove duplicates (keep first)
            extended_signals = extended_signals[
                ~extended_signals.index.duplicated(keep="first")
            ]

            self.logger.info(
                f"Extended signals: {len(signals)} -> {len(extended_signals)} "
                f"(added {len(extended_signals) - len(signals)} predictions)"
            )

            return extended_signals

        except Exception as e:
            self.logger.error(f"Failed to extend signals: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            # Return original signals on error
            return signals

    def _auto_init(self) -> Dict[str, Any]:
        """
        Auto-initialize OnlineManager on first routine call.

        This method:
        1. Ensures Qlib is initialized
        2. Creates RollingGen for rolling task generation
        3. Creates RollingStrategy with task template
        4. Creates TrainerRM (MongoDB-based trainer)
        5. Creates OnlineManager
        6. Calls first_train() to train initial models

        Returns:
            Initialization result dictionary
        """
        try:
            self.logger.info("Auto-initializing Online Serving...")

            # Ensure Qlib is initialized
            if not self._ensure_qlib_initialized():
                raise RuntimeError("Failed to initialize Qlib")

            # Import Qlib components
            from qlib.workflow.online.manager import OnlineManager
            from qlib.workflow.online.strategy import RollingStrategy
            from qlib.workflow.task.gen import RollingGen
            from qlib.model.trainer import TrainerRM

            # Configure MongoDB for TaskManager
            import qlib

            qlib.config.C["mongo"] = {
                "task_url": qlib_config.mongodb_uri,
                "task_db_name": qlib_config.mongodb_database,
            }

            # Set MLflow/Recorder path
            mlruns_path = Path(qlib_config.mlruns_path)
            mlruns_path.mkdir(parents=True, exist_ok=True)

            # Build task template (this also sets self._freq)
            task_template = self._build_task_template()

            # Get begin_time from data range
            start_time, end_time = self._get_data_time_range()

            # Create RollingGen
            rolling_gen = RollingGen(
                step=qlib_config.rolling_step,
                rtype=qlib_config.rolling_type,
            )

            # Create RollingStrategy
            experiment_name = qlib_config.experiment_name
            strategy = RollingStrategy(
                name_id=experiment_name,
                task_template=task_template,
                rolling_gen=rolling_gen,
            )

            # Create TrainerRM (MongoDB-based)
            trainer = TrainerRM(
                experiment_name=experiment_name,
                task_pool=experiment_name,
            )

            # Create OnlineManager with dynamic begin_time
            self._online_manager = OnlineManager(
                strategies=strategy,
                trainer=trainer,
                begin_time=start_time,
                freq=self._freq,
            )

            # First train - train initial models
            self.logger.info("Executing first_train() to train initial models...")
            self._online_manager.first_train()

            self._is_initialized = True
            self._initialization_error = None

            # Generate initial signals by calling routine with latest data date
            # This ensures signals are generated up to the latest available data
            self.logger.info(f"Generating initial signals up to {end_time}...")
            self._online_manager.routine(cur_time=end_time)

            # Re-prepare signals with online-only filter to fix the issue where
            # offline recorders' predictions override online recorders' predictions
            self._prepare_signals_with_online_filter()

            self.logger.info("Online Serving initialized successfully")

            return {
                "success": True,
                "message": "Online Serving initialized successfully",
                "experiment_name": experiment_name,
                "rolling_step": qlib_config.rolling_step,
                "rolling_type": qlib_config.rolling_type,
                "freq": self._freq,
            }

        except Exception as e:
            self._initialization_error = str(e)
            self.logger.error(f"Failed to initialize Online Serving: {e}")
            raise

    def update_data(self, cur_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute data update workflow (steps 1-5).

        This method:
        1. Updates data incrementally (download + preprocess + factors)
        2. Auto-initializes Qlib if not yet initialized
        3. Calls OnlineManager.routine() - rolling model training + prediction
        4. Retrieves generated signals for verification
        5. Calculates model performance metrics (updates Models page)

        Does NOT include portfolio optimization or signal export.
        Those belong to Run Signal (generate_portfolio).

        Args:
            cur_time: Current time string (YYYY-MM-DD), None for latest

        Returns:
            Execution result dictionary with step timing
        """
        import time

        start_time = time.time()
        result = {
            "success": False,
            "cur_time": cur_time,
            "executed_at": datetime.now().isoformat(),
            "steps": [],
            "total_duration_seconds": 0,
        }

        try:
            # Step 1: Update data first (before Qlib initialization)
            step_start = time.time()
            self.logger.info("Updating data incrementally...")
            data_update_result = self._update_data_incrementally()
            step_duration = time.time() - step_start
            data_update_success = data_update_result.get("success", False)
            result["steps"].append(
                {
                    "step": "Data Update",
                    "success": data_update_success,
                    "duration_seconds": round(step_duration, 2),
                    "details": {
                        "description": "Download latest market data and calculate factors",
                        **data_update_result,
                    },
                }
            )

            # Fail fast if data update failed
            if not data_update_success:
                error_msg = data_update_result.get("error", "Unknown error")
                self.logger.error(f"Data update failed: {error_msg}")
                result["error"] = f"Data update failed: {error_msg}"
                result["total_duration_seconds"] = round(time.time() - start_time, 2)
                return result

            # Short-circuit: if data didn't change AND factors didn't change
            # AND signals already exist, skip expensive Steps 2-5
            data_changed = data_update_result.get("data_changed", True)
            has_signals_in_memory = (
                self.is_initialized
                and self._online_manager is not None
                and self._online_manager.get_signals() is not None
                and len(self._online_manager.get_signals()) > 0
            )
            has_persisted_signals = getattr(self, "_persisted_signal_count", 0) > 0

            # Check if factor definitions changed since last signal generation
            current_factor_fp = self._get_factor_fingerprint()
            persisted_factor_fp = getattr(self, "_persisted_factor_fingerprint", "")
            factors_changed = current_factor_fp != persisted_factor_fp

            self.logger.info(
                f"Short-circuit check: data_changed={data_changed}, "
                f"factors_changed={factors_changed} "
                f"(current={current_factor_fp}, persisted={persisted_factor_fp}), "
                f"has_signals_in_memory={has_signals_in_memory}, "
                f"has_persisted_signals={has_persisted_signals}"
            )

            if (
                not data_changed
                and not factors_changed
                and (has_signals_in_memory or has_persisted_signals)
            ):
                signal_count = (
                    len(self._online_manager.get_signals())
                    if has_signals_in_memory
                    else self._persisted_signal_count
                )
                self.logger.info(
                    f"No new data and no factor changes detected. "
                    f"{signal_count} signals already exist. "
                    f"Skipping model training and signal generation."
                )
                result["success"] = True
                result["message"] = "No new data - using existing signals"
                result["skipped_reason"] = "data_unchanged"
                result["total_duration_seconds"] = round(time.time() - start_time, 2)
                result["steps"].append(
                    {
                        "step": "Short-circuit",
                        "success": True,
                        "duration_seconds": 0,
                        "details": {
                            "description": "Data and factors unchanged, reusing existing signals",
                            "signal_count": signal_count,
                            "source": (
                                "memory" if has_signals_in_memory else "persisted"
                            ),
                        },
                    }
                )
                return result

            if factors_changed:
                self.logger.info(
                    "Factor configuration changed, proceeding with full pipeline"
                )

            # Step 2: Auto-initialize if needed (after data is available)
            if not self.is_initialized:
                step_start = time.time()
                self.logger.info("Online Serving not initialized, auto-initializing...")
                init_result = self._auto_init()
                step_duration = time.time() - step_start
                result["steps"].append(
                    {
                        "step": "System Initialization",
                        "success": True,
                        "duration_seconds": round(step_duration, 2),
                        "details": {
                            "description": "Initialize Qlib engine and load trained models",
                            **init_result,
                        },
                    }
                )

            # Step 3: Execute OnlineManager routine (model training + prediction)
            step_start = time.time()
            effective_cur_time = cur_time
            if effective_cur_time is None:
                effective_cur_time = self._get_latest_data_date()
                self.logger.info(
                    f"cur_time not provided, using latest data date: {effective_cur_time}"
                )
            else:
                latest_data_date = self._get_latest_data_date()
                if latest_data_date and effective_cur_time < latest_data_date:
                    self.logger.warning(
                        f"Provided cur_time {effective_cur_time} is earlier than "
                        f"latest data date {latest_data_date}, using latest data date"
                    )
                    effective_cur_time = latest_data_date

            self.logger.info(
                f"Executing OnlineManager routine with cur_time={effective_cur_time}..."
            )
            self._online_manager.routine(cur_time=effective_cur_time)
            self._prepare_signals_with_online_filter()

            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "Online Model Training",
                    "success": True,
                    "duration_seconds": round(step_duration, 2),
                    "details": {
                        "description": "Incrementally train models with new data (rolling update)",
                        "message": "Online model training completed",
                    },
                }
            )

            # Step 4: Get signals (for logging/verification)
            step_start = time.time()
            signals = self._online_manager.get_signals()
            signal_count = len(signals) if signals is not None else 0
            self.logger.info(
                f"update_data Step 4: signal_count={signal_count}, "
                f"signals type={type(signals)}, "
                f"signals is None={signals is None}"
            )
            if signals is not None and signal_count > 0 and hasattr(signals, "index"):
                dates = signals.index.get_level_values("datetime").unique()
                self.logger.info(
                    f"update_data Step 4: signal dates {dates.min()} to {dates.max()}, "
                    f"unique dates={len(dates)}"
                )
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "Signal Generation",
                    "success": True,
                    "duration_seconds": round(step_duration, 2),
                    "details": {
                        "description": "Run model inference on latest data to generate trading signals",
                        "signal_count": signal_count,
                    },
                }
            )

            # Step 5: Calculate model metrics (updates Models page)
            step_start = time.time()
            metrics_result = self._calculate_model_metrics(signals)
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "Performance Evaluation",
                    "success": metrics_result.get("success", False),
                    "duration_seconds": round(step_duration, 2),
                    "details": {
                        "description": "Calculate model accuracy, IC, and other performance metrics",
                        **metrics_result,
                    },
                }
            )

            self._last_routine_time = datetime.now()
            result["success"] = True
            result["message"] = "Data update completed successfully"
            result["total_duration_seconds"] = round(time.time() - start_time, 2)

            # Persist signals to disk (survives hot-reload / restart)
            if signals is not None and signal_count > 0:
                self._persist_signals_state(signals, signal_count)

            self.logger.info(
                f"Data update completed, generated {signal_count} signals "
                f"in {result['total_duration_seconds']}s"
            )

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["total_duration_seconds"] = round(time.time() - start_time, 2)
            self.logger.error(f"Data update failed: {e}")

        return result

    def generate_portfolio(self, cur_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate portfolio and export signals (Run Signal workflow).

        This method uses the signals already produced by update_data() to:
        1. Calculate target portfolio via Enhanced Indexing Strategy
        2. Export trading signals for VeighNa

        Prerequisite: update_data() must have been run first so that
        signals are available in OnlineManager.

        Args:
            cur_time: Current time string (YYYY-MM-DD), None for latest

        Returns:
            Execution result dictionary with portfolio and signal export details
        """
        import time

        start_time = time.time()
        result = {
            "success": False,
            "cur_time": cur_time,
            "executed_at": datetime.now().isoformat(),
            "steps": [],
            "total_duration_seconds": 0,
        }

        try:
            # Check that system is initialized and signals exist
            if not self.is_initialized:
                result["error"] = (
                    "System not initialized. Please run Update Data first."
                )
                return result

            signals = self._online_manager.get_signals()
            if signals is None or len(signals) == 0:
                result["error"] = "No signals available. Please run Update Data first."
                return result

            signal_count = len(signals)
            self.logger.info(
                f"Starting portfolio generation with {signal_count} signals..."
            )

            # Determine effective cur_time
            effective_cur_time = cur_time
            if effective_cur_time is None:
                effective_cur_time = self._get_latest_data_date()

            # Step 1: Calculate target portfolio
            # Try TopK strategy first, then fall back to ETF Enhanced Indexing
            step_start = time.time()
            topk_config = qlib_config._config.get("topk_dropout_strategy", {})
            topk_enabled = topk_config.get("enabled", False)

            if topk_enabled:
                portfolio_result = self._calculate_topk_portfolio(
                    signals, effective_cur_time
                )
                strategy_desc = "Generate target portfolio using TopK strategy"
            else:
                portfolio_result = self._calculate_enhanced_indexing(
                    signals, effective_cur_time
                )
                strategy_desc = (
                    "Generate target portfolio using ETF Enhanced Indexing strategy"
                )

            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "Portfolio Optimization",
                    "success": portfolio_result.get("success", False),
                    "duration_seconds": round(step_duration, 2),
                    "details": {
                        "description": strategy_desc,
                        **portfolio_result.get("summary", {}),
                    },
                }
            )

            # Add target portfolio to result
            if portfolio_result.get("success"):
                result["target_portfolio"] = portfolio_result.get(
                    "target_portfolio", []
                )
                result["strategy"] = portfolio_result.get("strategy", "unknown")
                result["generated_at"] = portfolio_result.get(
                    "generated_at", datetime.now().isoformat()
                )
                result["trade_date"] = portfolio_result.get("trade_date", "")
                result["signal_for_date"] = portfolio_result.get("signal_for_date", "")
                result["portfolio_summary"] = portfolio_result.get("summary", {})

                # Strategy-specific fields
                if portfolio_result.get("strategy") == "topk":
                    result["confidence"] = portfolio_result.get("confidence", 0)
                    result["confidence_percentile"] = portfolio_result.get(
                        "confidence_percentile"
                    )
                    result["confidence_label"] = portfolio_result.get(
                        "confidence_label", ""
                    )
                    result["confidence_interpretation"] = portfolio_result.get(
                        "confidence_interpretation", ""
                    )
                    result["topk"] = portfolio_result.get("topk", 10)
                    result["weight_method"] = portfolio_result.get(
                        "weight_method", "score_weighted"
                    )
                else:
                    # ETF Enhanced Indexing specific fields
                    result["total_value"] = portfolio_result.get("total_value", 1000000)
                    result["region"] = portfolio_result.get("region", "cn")
                    result["lot_size"] = portfolio_result.get("lot_size", 100)
                    result["weights"] = portfolio_result.get("weights", {})

            # Step 2: Export Trading Signals
            step_start = time.time()
            signal_export_result = self._export_trading_signals(
                portfolio_result, effective_cur_time
            )
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "Signal Export",
                    "success": signal_export_result.get("success", False),
                    "duration_seconds": round(step_duration, 2),
                    "details": {
                        "description": "Export trading signals for VeighNa (ETF + Alpha stocks)",
                        **signal_export_result,
                    },
                }
            )

            result["success"] = True
            result["message"] = "Portfolio generation completed successfully"
            result["total_duration_seconds"] = round(time.time() - start_time, 2)

            self.logger.info(
                f"Portfolio generation completed in {result['total_duration_seconds']}s"
            )

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["total_duration_seconds"] = round(time.time() - start_time, 2)
            self.logger.error(f"Portfolio generation failed: {e}")

        return result

    def routine(self, cur_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute daily routine (main entry point).

        Composes update_data() + generate_portfolio() into a single workflow.
        Used by scheduled tasks that need the full pipeline.

        Args:
            cur_time: Current time string (YYYY-MM-DD), None for latest

        Returns:
            Combined execution result dictionary
        """
        import time

        routine_start = time.time()

        # Phase 1: Data update (steps 1-5)
        update_result = self.update_data(cur_time)
        if not update_result.get("success"):
            return update_result

        # Phase 2: Portfolio generation (steps 6-7)
        portfolio_result = self.generate_portfolio(cur_time)

        # Merge results: combine steps from both phases
        result = {
            **portfolio_result,
            "cur_time": cur_time,
            "executed_at": update_result["executed_at"],
            "steps": update_result["steps"] + portfolio_result["steps"],
            "total_duration_seconds": round(time.time() - routine_start, 2),
            "message": (
                "Routine completed successfully"
                if portfolio_result.get("success")
                else portfolio_result.get("error")
            ),
        }

        self.logger.info(f"Routine completed in {result['total_duration_seconds']}s")

        return result

    # ===== Confidence History Helpers =====

    def _get_confidence_history_path(self) -> Path:
        """Get path to confidence_history.json."""
        topk_config = qlib_config._config.get("topk_dropout_strategy", {})
        output_dir = topk_config.get("output_dir", "/app/data/target_portfolio")
        return Path(output_dir) / "confidence_history.json"

    def _load_confidence_history(self) -> List[Dict[str, Any]]:
        """Load confidence history from JSON file."""
        import json

        path = self._get_confidence_history_path()
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("history", [])
        except Exception as e:
            self.logger.warning(f"Failed to load confidence history: {e}")
            return []

    def _save_confidence_history(self, history: List[Dict[str, Any]]) -> None:
        """Save confidence history to JSON file."""
        import json

        path = self._get_confidence_history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"history": history}, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Saved confidence history: {len(history)} entries to {path}")

    def _append_confidence_history(
        self, date: str, confidence: float, source: str = "live"
    ) -> None:
        """Append a confidence entry to history, avoiding duplicates."""
        history = self._load_confidence_history()
        # Remove existing entry for the same date (in case of re-run)
        history = [h for h in history if h.get("date") != date]
        history.append(
            {"date": date, "confidence": round(confidence, 4), "source": source}
        )
        # Sort by date
        history.sort(key=lambda x: x["date"])
        self._save_confidence_history(history)

    def _calculate_confidence_percentile(self, confidence: float) -> Dict[str, Any]:
        """
        Calculate percentile rank and interpretation for a confidence value.

        Returns:
            Dict with percentile, label, and interpretation text
        """
        import numpy as np

        history = self._load_confidence_history()
        historical_values = [h["confidence"] for h in history]

        min_history = 5
        if len(historical_values) < min_history:
            return {
                "percentile": None,
                "label": "历史数据不足",
                "interpretation": (
                    f"需要至少{min_history}次历史记录才能计算百分位"
                    f"（当前{len(historical_values)}次）。"
                    "请先运行 Run Backtest 生成历史基线。"
                ),
            }

        # Calculate percentile: what % of historical values are <= current
        rank = sum(1 for v in historical_values if v <= confidence)
        percentile = round(rank / len(historical_values) * 100, 1)

        # Map to label and interpretation
        if percentile >= 90:
            label = "极强"
            interpretation = (
                "模型区分度极高，推荐持仓可信度很强。" "建议严格按照系统推荐持仓执行。"
            )
        elif percentile >= 75:
            label = "较强"
            interpretation = (
                "模型区分度良好，推荐持仓可信度较高。" "建议紧密跟随系统推荐。"
            )
        elif percentile >= 25:
            label = "正常"
            interpretation = "模型区分度正常，推荐持仓处于常规可信水平。"
        elif percentile >= 10:
            label = "较弱"
            interpretation = (
                "模型区分度较低，推荐持仓可信度下降。"
                "可适当偏离系统推荐，结合自身判断。"
            )
        else:
            label = "极弱"
            interpretation = (
                "模型区分度很低，推荐持仓可靠性不足。" "建议以自主判断为主。"
            )

        return {
            "percentile": percentile,
            "label": label,
            "interpretation": interpretation,
        }

    @staticmethod
    def _calculate_confidence_from_signals(
        signal_dict: Dict[str, float], topk: int
    ) -> tuple:
        """
        Calculate confidence and score_spread from a signal dictionary.

        Confidence measures how well the model differentiates top vs bottom ETFs.
        Uses std-normalized spread: confidence = clip(spread / (k * std), 0, 1)
        where k=4, so confidence=1.0 only when spread covers 4+ standard deviations.

        Returns:
            (confidence, score_spread) tuple
        """
        import numpy as np

        # Filter out NaN scores
        clean_scores = {
            k: v
            for k, v in signal_dict.items()
            if not (isinstance(v, float) and np.isnan(v))
        }

        if len(clean_scores) >= topk * 2:
            all_scores = sorted(clean_scores.values(), reverse=True)
            top_avg = float(np.mean(all_scores[:topk]))
            bottom_avg = float(np.mean(all_scores[-topk:]))
            score_spread = top_avg - bottom_avg

            # Normalize by score std for adaptive scaling
            score_std = float(np.std(list(clean_scores.values())))
            if score_std > 0:
                # How many stdevs the spread covers; k=4 means 4-sigma = full confidence
                confidence = float(np.clip(score_spread / (4.0 * score_std), 0, 1))
            else:
                confidence = 0.5  # All scores identical = no differentiation
        else:
            score_spread = 0.0
            confidence = 0.0
        return confidence, score_spread

    def _generate_confidence_history_from_signals(self, signals, topk: int) -> None:
        """
        Generate confidence_history.json from backtest signals.

        Uses a two-pass approach for backtest data:
        1. First pass: calculate raw confidence for each date
        2. Second pass: convert to percentile rank for meaningful distribution

        This ensures confidence values have a full [0,1] range instead of
        clustering at 1.0 due to fixed normalization.
        """
        import numpy as np

        try:
            etf_service = get_etf_enhanced_indexing_service()

            self.logger.info(
                f"Generating confidence history: signals type={type(signals).__name__}, "
                f"index type={type(signals.index).__name__}"
            )

            if not isinstance(signals.index, pd.MultiIndex):
                self.logger.warning("Signals not MultiIndex, cannot generate history")
                return

            dates = signals.index.get_level_values(0).unique().sort_values()
            self.logger.info(f"Processing {len(dates)} unique dates for confidence")

            # --- Pass 1: Calculate raw confidence per date ---
            raw_entries = []  # list of (date_str, raw_confidence, score_spread)
            skipped = 0
            errors = 0

            for date in dates:
                try:
                    date_signals = signals.loc[date]
                    signal_dict = etf_service._extract_signals(date_signals)
                    if not signal_dict:
                        skipped += 1
                        continue
                    raw_conf, score_spread = self._calculate_confidence_from_signals(
                        signal_dict, topk
                    )
                    date_str = str(date.date()) if hasattr(date, "date") else str(date)
                    raw_entries.append((date_str, raw_conf, score_spread))
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        self.logger.warning(f"Confidence calc failed for {date}: {e}")
                    continue

            self.logger.info(
                f"Pass 1 done: {len(raw_entries)} entries, {skipped} skipped, {errors} errors"
            )

            if not raw_entries:
                self.logger.warning("No confidence entries generated!")
                return

            # --- Pass 2: Percentile rank normalization ---
            raw_values = np.array([c for _, c, _ in raw_entries])
            valid_mask = ~np.isnan(raw_values)
            valid_values = raw_values[valid_mask]

            if len(valid_values) > 1:
                self.logger.info(
                    f"Raw confidence stats: min={np.min(valid_values):.4f}, "
                    f"max={np.max(valid_values):.4f}, mean={np.mean(valid_values):.4f}, "
                    f"std={np.std(valid_values):.4f}"
                )

            history = []
            for date_str, raw_conf, score_spread in raw_entries:
                if np.isnan(raw_conf) or len(valid_values) < 2:
                    pct_conf = 0.0
                else:
                    # Percentile rank: fraction of values <= this value
                    pct_conf = float(
                        np.sum(valid_values <= raw_conf) / len(valid_values)
                    )
                history.append(
                    {
                        "date": date_str,
                        "confidence": round(pct_conf, 4),
                        "raw_confidence": round(
                            float(raw_conf) if not np.isnan(raw_conf) else 0, 4
                        ),
                        "score_spread": round(float(score_spread), 6),
                        "source": "backtest",
                    }
                )

            # Merge with existing live entries (keep live, replace backtest)
            existing = self._load_confidence_history()
            live_entries = [h for h in existing if h.get("source") == "live"]
            live_dates = {h["date"] for h in live_entries}
            merged = [h for h in history if h["date"] not in live_dates]
            merged.extend(live_entries)
            merged.sort(key=lambda x: x["date"])
            self._save_confidence_history(merged)

            final_confs = [h["confidence"] for h in history]
            self.logger.info(
                f"Saved confidence history: {len(merged)} total "
                f"({len(history)} backtest, {len(live_entries)} live). "
                f"Percentile range: [{min(final_confs):.3f}, {max(final_confs):.3f}]"
            )

        except Exception as e:
            self.logger.error(f"Failed to generate confidence history: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    def _calculate_topk_portfolio(
        self, signals: pd.DataFrame, cur_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate target portfolio using pure TopK strategy.

        Strategy: Select top K ETFs from signal scores, assign score-weighted weights.
        When topk == n_drop, this is a full-position rebalance each time.

        Args:
            signals: Model prediction signals DataFrame
            cur_time: Current time string for date reference

        Returns:
            Dict containing positions, summary, confidence, and success status
        """
        import json
        import numpy as np

        try:
            from app.config.qlib import qlib_config

            # Load TopK config from system_config.yaml
            topk_config = qlib_config._config.get("topk_dropout_strategy", {})
            topk = topk_config.get("topk", 10)
            weight_method = topk_config.get("weight_method", "score_weighted")
            output_dir = topk_config.get("output_dir", "/app/data/target_portfolio")

            date_str = cur_time if cur_time else datetime.now().strftime("%Y-%m-%d")

            # Reuse ETF service for signal extraction, price lookup, and stock names
            etf_service = get_etf_enhanced_indexing_service()
            signal_dict = etf_service._extract_signals(signals)

            if not signal_dict:
                return {"success": False, "error": "No signals", "positions": []}

            # Sort by score descending, select top K
            sorted_signals = sorted(
                signal_dict.items(), key=lambda x: x[1], reverse=True
            )
            top_k = sorted_signals[:topk]

            # Calculate confidence from score spread
            confidence, score_spread = self._calculate_confidence_from_signals(
                signal_dict, topk
            )

            # Calculate percentile against historical confidence
            confidence_context = self._calculate_confidence_percentile(confidence)

            # Append today's confidence to history
            self._append_confidence_history(date_str, confidence, source="live")

            # Calculate weights
            if weight_method == "score_weighted":
                total_score = sum(score for _, score in top_k)
                if total_score <= 0:
                    # Fallback to equal weights
                    weights_list = [(symbol, 1.0 / topk) for symbol, _ in top_k]
                else:
                    weights_list = [
                        (symbol, score / total_score) for symbol, score in top_k
                    ]
            else:
                # Equal weight
                weights_list = [(symbol, 1.0 / topk) for symbol, _ in top_k]

            # Batch fetch stock names and prices
            all_symbols = [s for s, _ in top_k]
            etf_service._batch_fetch_stock_names(all_symbols)
            prices = etf_service._get_latest_prices(all_symbols)

            # Build positions list
            positions = []
            for rank, (symbol, weight) in enumerate(weights_list, start=1):
                score = signal_dict.get(symbol, 0.0)
                price = prices.get(symbol)
                name = etf_service.get_stock_name(symbol)

                positions.append(
                    {
                        "rank": rank,
                        "symbol": symbol,
                        "name": name,
                        "score": round(score, 6),
                        "weight": round(weight, 6),
                    }
                )

            # Calculate signal_for_date (next trading date)
            signal_for_date = etf_service._get_next_trading_date(date_str)

            # Build portfolio data
            portfolio_data = {
                "strategy": "topk",
                "generated_at": datetime.now().isoformat(),
                "trade_date": date_str,
                "signal_for_date": signal_for_date,
                "topk": topk,
                "weight_method": weight_method,
                "confidence": round(confidence, 4),
                "score_spread": round(score_spread, 4),
                "confidence_percentile": confidence_context.get("percentile"),
                "confidence_label": confidence_context.get("label", ""),
                "confidence_interpretation": confidence_context.get(
                    "interpretation", ""
                ),
                "positions": positions,
                "summary": {
                    "total_positions": len(positions),
                },
            }

            # Save portfolio JSON file
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = output_path / f"topk_portfolio_{date_str}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(portfolio_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"TopK portfolio saved to {output_file}: "
                f"{len(positions)} positions, confidence={confidence:.2f}"
            )

            # Send email notification
            self._send_topk_portfolio_email(portfolio_data)

            return {
                "success": True,
                "strategy": "topk",
                "target_portfolio": positions,
                "summary": portfolio_data["summary"],
                "generated_at": portfolio_data["generated_at"],
                "trade_date": date_str,
                "signal_for_date": signal_for_date,
                "confidence": round(confidence, 4),
                "score_spread": round(score_spread, 4),
                "confidence_percentile": confidence_context.get("percentile"),
                "confidence_label": confidence_context.get("label", ""),
                "confidence_interpretation": confidence_context.get(
                    "interpretation", ""
                ),
                "topk": topk,
                "weight_method": weight_method,
            }

        except Exception as e:
            self.logger.error(f"TopK portfolio calculation failed: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "target_portfolio": [],
                "summary": {},
            }

    def _send_topk_portfolio_email(self, portfolio_data: Dict[str, Any]) -> None:
        """Send TopK portfolio email notification."""
        try:
            topk_config = qlib_config._config.get("topk_dropout_strategy", {})
            email_config = topk_config.get("email_notification", {})

            if not email_config.get("enabled", False):
                self.logger.info("TopK portfolio email notification is disabled")
                return

            notification_service = get_notification_service()
            result = notification_service.send_topk_portfolio_email(portfolio_data)

            if result.get("success"):
                self.logger.info(f"TopK portfolio email sent: {result.get('message')}")
            else:
                self.logger.warning(
                    f"Failed to send TopK portfolio email: {result.get('error')}"
                )

        except Exception as e:
            self.logger.error(f"Error sending TopK portfolio email: {e}")

    def _calculate_enhanced_indexing(
        self, signals: pd.DataFrame, cur_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate target portfolio using ETF Enhanced Indexing strategy.

        Strategy: 1 ETF + 9 alpha stocks (via ETFEnhancedIndexingService)

        Args:
            signals: Model prediction signals DataFrame
            cur_time: Current time string for date reference

        Returns:
            Dict containing target_portfolio/positions, summary, and success status
        """
        try:
            # Try ETF Enhanced Indexing first (new strategy)
            etf_service = get_etf_enhanced_indexing_service()

            if etf_service.enabled:
                date_str = cur_time if cur_time else datetime.now().strftime("%Y-%m-%d")

                # Check if today is a rebalancing day
                is_rebalance_day = etf_service.is_rebalance_day(date_str)
                days_until_rebalance = etf_service.get_days_until_rebalance(date_str)

                if not is_rebalance_day:
                    # Not a rebalancing day - return current holdings with HOLD action
                    self.logger.info(
                        f"Not a rebalancing day ({date_str}). "
                        f"Next rebalance in {days_until_rebalance} trading days. "
                        f"Skipping portfolio recalculation."
                    )

                    # Load the most recent portfolio file and set all actions to hold
                    cached_portfolio = etf_service.load_latest_portfolio()

                    if cached_portfolio:
                        positions = cached_portfolio.get("positions", [])
                        # Set all actions to hold (no trading on non-rebalance days)
                        for pos in positions:
                            pos["action"] = "hold"
                            pos["action_shares"] = 0
                            pos["action_lots"] = 0

                        # Build portfolio data for email
                        hold_portfolio_data = {
                            **cached_portfolio,
                            "positions": positions,
                            "summary": {
                                **cached_portfolio.get("summary", {}),
                                "buy_count": 0,
                                "sell_count": 0,
                                "hold_count": len(positions),
                            },
                            "trade_date": date_str,
                            "generated_at": datetime.now().isoformat(),
                            "is_rebalance_day": False,
                            "message": f"Not a rebalancing day. Next rebalance in {days_until_rebalance} trading days.",
                        }

                        # Send email notification even for hold (non-rebalance day)
                        self._send_etf_portfolio_email(hold_portfolio_data)

                        return {
                            "success": True,
                            "cached": True,
                            "is_rebalance_day": False,
                            "days_until_rebalance": days_until_rebalance,
                            "target_portfolio": positions,
                            "summary": {
                                **cached_portfolio.get("summary", {}),
                                "buy_count": 0,
                                "sell_count": 0,
                                "hold_count": len(positions),
                            },
                            "weights": cached_portfolio.get("weights", {}),
                            "strategy": "etf_enhanced_indexing",
                            "generated_at": datetime.now().isoformat(),
                            "trade_date": date_str,
                            "signal_for_date": cached_portfolio.get(
                                "signal_for_date", ""
                            ),
                            "total_value": cached_portfolio.get("total_value", 1000000),
                            "lot_size": cached_portfolio.get("lot_size", 100),
                            "region": cached_portfolio.get("region", "cn"),
                            "message": f"Not a rebalancing day. Next rebalance in {days_until_rebalance} trading days.",
                        }
                    else:
                        # No previous portfolio, need to calculate even on non-rebalance day
                        self.logger.warning(
                            "No previous portfolio found. Will calculate initial portfolio."
                        )

                # Smart cache: Check if we can use cached result
                # Cache is valid if same day AND no data/factor changes
                cache_valid, cached_portfolio = etf_service.check_cache_valid(date_str)

                if cache_valid and cached_portfolio:
                    self.logger.info(
                        f"Using cached portfolio for {date_str} (no data/factor changes)"
                    )
                    portfolio_data = cached_portfolio

                    # Save updated portfolio (with recalculated actions based on current holdings)
                    saved_path = etf_service.save_portfolio(portfolio_data, date_str)
                    self.logger.info(f"Updated portfolio saved to {saved_path}")

                    # Update holdings to target_shares for next rebalance calculation
                    etf_service.apply_trades_to_holdings(
                        portfolio_data.get("positions", []), trade_date=date_str
                    )
                    self.logger.info(
                        "Holdings updated to target positions for next rebalance"
                    )

                    # Send email notification even when using cache
                    self._send_etf_portfolio_email(portfolio_data)

                    # Return cached result with cache indicator
                    return {
                        "success": True,
                        "cached": True,
                        "is_rebalance_day": True,
                        "days_until_rebalance": 0,
                        "target_portfolio": portfolio_data.get("positions", []),
                        "summary": portfolio_data.get("summary", {}),
                        "weights": portfolio_data.get("weights", {}),
                        "strategy": "etf_enhanced_indexing",
                        "generated_at": portfolio_data.get(
                            "generated_at", datetime.now().isoformat()
                        ),
                        "trade_date": portfolio_data.get("trade_date", cur_time or ""),
                        "signal_for_date": portfolio_data.get("signal_for_date", ""),
                        "total_value": portfolio_data.get("total_value", 1000000),
                        "lot_size": portfolio_data.get("lot_size", 100),
                        "region": portfolio_data.get("region", "cn"),
                    }

                # Cache invalid or not found, calculate new portfolio
                self.logger.info(
                    "Calculating target portfolio using ETF Enhanced Indexing strategy..."
                )

                # Calculate target portfolio with ETF + top stocks
                # This uses current holdings to calculate action (buy/sell/hold)
                portfolio_data = etf_service.calculate_target_portfolio(
                    signals=signals,
                    trade_date=cur_time,
                )

                # Save portfolio to file (includes fingerprint for future cache validation)
                if portfolio_data.get("positions"):
                    # Save portfolio FIRST (with current_shares showing pre-trade state)
                    # This file is used by frontend API and email - preserves the action info
                    saved_path = etf_service.save_portfolio(portfolio_data, date_str)
                    self.logger.info(f"ETF enhanced portfolio saved to {saved_path}")

                    # Then update holdings to target_shares for next rebalance calculation
                    # This is safe because frontend API reads from portfolio file (not holdings)
                    etf_service.apply_trades_to_holdings(
                        portfolio_data.get("positions", []), trade_date=date_str
                    )
                    self.logger.info(
                        "Holdings updated to target positions for next rebalance"
                    )

                position_count = len(portfolio_data.get("positions", []))
                self.logger.info(
                    f"ETF Enhanced Indexing completed: {position_count} positions "
                    f"(ETF weight: {portfolio_data.get('weights', {}).get('etf_weight', 0):.1%})"
                )

                # Send email notification if enabled
                self._send_etf_portfolio_email(portfolio_data)

                return {
                    "success": True,
                    "cached": False,
                    "target_portfolio": portfolio_data.get("positions", []),
                    "summary": portfolio_data.get("summary", {}),
                    "weights": portfolio_data.get("weights", {}),
                    "strategy": "etf_enhanced_indexing",
                    "generated_at": portfolio_data.get(
                        "generated_at", datetime.now().isoformat()
                    ),
                    "trade_date": portfolio_data.get("trade_date", cur_time or ""),
                    "signal_for_date": portfolio_data.get("signal_for_date", ""),
                    "total_value": portfolio_data.get("total_value", 1000000),
                    "lot_size": portfolio_data.get("lot_size", 100),
                    "region": portfolio_data.get("region", "cn"),
                }

            # No fallback - ETF Enhanced Indexing is required
            raise RuntimeError(
                "ETF Enhanced Indexing service is disabled. "
                "This system requires ETF Enhanced Indexing to be enabled. "
                "Please check the configuration and ensure the service is properly initialized."
            )

        except Exception as e:
            self.logger.error(f"Enhanced indexing calculation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "target_portfolio": [],
                "summary": {},
            }

    def _send_etf_portfolio_email(self, portfolio_data: Dict[str, Any]) -> None:
        """
        Send ETF enhanced portfolio email notification.

        Args:
            portfolio_data: Complete portfolio data from ETFEnhancedIndexingService
        """
        try:
            # Check if email notification is enabled in config
            etf_config = qlib_config._config.get("etf_enhanced_indexing", {})
            email_config = etf_config.get("email_notification", {})

            if not email_config.get("enabled", False):
                self.logger.info("ETF enhanced indexing email notification is disabled")
                return

            notification_service = get_notification_service()
            result = notification_service.send_etf_enhanced_portfolio_email(
                portfolio_data
            )

            if result.get("success"):
                self.logger.info(f"ETF portfolio email sent: {result.get('message')}")
            else:
                self.logger.warning(
                    f"Failed to send ETF portfolio email: {result.get('error')}"
                )

        except Exception as e:
            self.logger.error(f"Error sending ETF portfolio email: {e}")

    def _export_trading_signals(
        self, enhanced_indexing_result: Dict[str, Any], cur_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export trading signals for VeighNa consumption.

        Args:
            enhanced_indexing_result: Result from enhanced indexing calculation
            cur_time: Current time string for trade date

        Returns:
            Dict containing export result and summary
        """
        try:
            # Skip export if enhanced indexing failed
            if not enhanced_indexing_result.get("success", False):
                self.logger.info("Enhanced indexing failed, skipping signal export")
                return {
                    "success": False,
                    "message": "Skipped due to portfolio optimization failure",
                    "signal_file": None,
                }

            from app.services.signal_export_service import get_signal_export_service

            # Get signal export service
            signal_service = get_signal_export_service()

            # Prepare portfolio data for export
            # Note: enhanced_indexing_result contains target_portfolio and summary
            # but signal_export_service expects portfolio data in the format saved by EnhancedIndexingService
            portfolio_data = {
                "portfolio": enhanced_indexing_result.get("target_portfolio", []),
                "summary": enhanced_indexing_result.get("summary", {}),
            }

            # Determine trade date
            trade_date = cur_time if cur_time else datetime.now().strftime("%Y-%m-%d")

            # Export signals
            self.logger.info(f"Exporting trading signals for date: {trade_date}")
            signal_file = signal_service.export_signals(
                portfolio_data=portfolio_data,
                trade_date=trade_date,
            )

            # Get signal summary for logging
            import json

            try:
                with open(signal_file, "r", encoding="utf-8") as f:
                    signal_data = json.load(f)

                summary = signal_data.get("summary", {})
                total_positions = summary.get("total_positions", 0)
                etf_positions = summary.get("etf_positions", 0)
                stock_positions = summary.get("stock_positions", 0)
                total_weight = summary.get("total_weight", 0)

                self.logger.info(
                    f"Signal export completed: {total_positions} positions "
                    f"({etf_positions} ETF + {stock_positions} stocks), "
                    f"total_weight={total_weight:.4f}"
                )

                return {
                    "success": True,
                    "message": "Trading signals exported successfully",
                    "signal_file": signal_file,
                    "total_positions": total_positions,
                    "etf_positions": etf_positions,
                    "stock_positions": stock_positions,
                    "total_weight": round(total_weight, 4),
                }

            except Exception as read_error:
                # Signal file created but couldn't read summary
                self.logger.warning(
                    f"Signal exported but couldn't read summary: {read_error}"
                )
                return {
                    "success": True,
                    "message": "Trading signals exported successfully",
                    "signal_file": signal_file,
                    "warning": f"Couldn't read signal summary: {read_error}",
                }

        except Exception as e:
            self.logger.error(f"Signal export failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "signal_file": None,
            }

    def _update_data_incrementally(self) -> Dict[str, Any]:
        """
        Update data incrementally or download default data if none exists.

        Logic:
        1. If bin data exists: perform incremental update on existing data
        2. If no data exists: download data based on system_config.yaml settings

        Returns:
            Data update result dictionary
        """
        try:
            from app.services.data_source_manager import data_source_manager

            # Check for config changes and cleanup if needed
            config_changed = data_source_manager.check_and_handle_config_change()
            if config_changed:
                self.logger.info("Data configuration changed, data has been cleaned up")

            # Check if data exists
            has_data = data_source_manager.has_data()

            # Case 1: No data exists - download data based on config
            if not has_data:
                self.logger.info(
                    f"No data found, downloading {qlib_config.stock_pool} {qlib_config.freq} data..."
                )
                return self._download_default_data()

            # Case 2: Data exists - perform incremental update
            self.logger.info("Data exists, performing incremental update...")
            return self._perform_incremental_update()

        except Exception as e:
            self.logger.error(f"Data update failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _download_default_data(self) -> Dict[str, Any]:
        """
        Download data based on system_config.yaml settings when no data exists.

        Returns:
            Download result dictionary
        """
        try:
            from app.services.data_collectors.pipeline import execute_data_pipeline
            from app.models import DownloadDataRequest
            from app.services.data_source_manager import data_source_manager
            from datetime import datetime, timedelta

            # Get date range from config
            start_date_str, end_date_str = data_source_manager.get_download_date_range()

            interval = "1d"

            request = DownloadDataRequest(
                stock_pool=qlib_config.stock_pool,
                start_date=start_date_str,
                end_date=end_date_str,
                incremental=False,
                interval=interval,
            )

            self.logger.info(
                f"Downloading {qlib_config.stock_pool} {interval} data "
                f"from {request.start_date} to {request.end_date}..."
            )

            result = execute_data_pipeline(request)

            # Log the actual status for debugging
            self.logger.info(
                f"Pipeline result: status='{result.status}', message='{result.message}'"
            )

            # Check for successful status (completed or started)
            # Note: "completed" is returned for both successful data collection AND
            # when no new data is available (weekends/holidays/already up-to-date)
            is_success = result.status in ("completed", "started")

            if is_success:
                self.logger.info(
                    f"Data download completed successfully: {result.message}"
                )
                return {
                    "success": True,
                    "data_changed": True,
                    "message": f"Downloaded {qlib_config.stock_pool} {interval} data",
                    "task_id": result.task_id,
                    "stock_pool": qlib_config.stock_pool,
                    "freq": qlib_config.freq,
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                }
            else:
                return {
                    "success": False,
                    "error": f"Download failed (status={result.status}): {result.message}",
                }

        except Exception as e:
            self.logger.error(f"Failed to download data: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _perform_incremental_update(self) -> Dict[str, Any]:
        """
        Perform incremental update on existing data based on system_config.yaml.

        Returns:
            Update result dictionary
        """
        try:
            from app.services.data_collectors.pipeline import execute_data_pipeline
            from app.models import DownloadDataRequest
            from datetime import datetime, timedelta

            # Use config values directly
            stock_pool = qlib_config.stock_pool
            interval = "1d"

            # For incremental update, use the last 30 days as the range
            # The pipeline will detect and fill gaps
            request = DownloadDataRequest(
                stock_pool=stock_pool,
                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                incremental=True,
                interval=interval,
            )

            self.logger.info(
                f"Performing incremental update for {interval} data, stock_pool={stock_pool}..."
            )

            result = execute_data_pipeline(request)

            # Log the actual status for debugging
            self.logger.info(
                f"Pipeline result: status='{result.status}', message='{result.message}'"
            )

            # Check for successful status (completed or started)
            # Note: "completed" is returned for both successful data collection AND
            # when no new data is available (weekends/holidays/already up-to-date)
            is_success = result.status in ("completed", "started")

            if is_success:
                # Detect whether data actually changed based on pipeline message
                # Two scenarios where data didn't change:
                # 1. "No missing data found" - calendar has no gaps
                # 2. "No new data available" - gaps exist but market was closed
                no_new_data = result.message and (
                    "No missing data found" in result.message
                    or "No new data available" in result.message
                )
                self.logger.info(
                    f"Incremental update completed successfully: {result.message} "
                    f"(data_changed={not no_new_data})"
                )
                return {
                    "success": True,
                    "data_changed": not no_new_data,
                    "message": result.message or "Incremental update completed",
                    "task_id": result.task_id,
                    "stock_pool": stock_pool,
                    "freq": qlib_config.freq,
                    "interval": interval,
                }
            else:
                return {
                    "success": False,
                    "error": f"Incremental update failed (status={result.status}): {result.message}",
                }

        except Exception as e:
            self.logger.error(f"Incremental update failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_signals(self, limit: Optional[int] = 100) -> Dict[str, Any]:
        """
        Get latest trading signals.

        Args:
            limit: Maximum number of signals to return. None for all signals.

        Returns:
            Trading signals dictionary
        """
        if not self.is_initialized:
            return {
                "success": False,
                "error": "Online Serving not initialized",
                "signals": None,
            }

        try:
            signals = self._online_manager.get_signals()

            # Convert signals to serializable format
            if signals is not None:
                # Signals are typically a pandas Series or DataFrame
                signals_list = []
                if hasattr(signals, "to_dict"):
                    signals_dict = signals.to_dict()
                    for key, value in signals_dict.items():
                        if isinstance(key, tuple):
                            # MultiIndex: (datetime, instrument)
                            signals_list.append(
                                {
                                    "datetime": str(key[0]),
                                    "instrument": str(key[1]),
                                    "score": float(value),
                                }
                            )
                        else:
                            signals_list.append(
                                {
                                    "key": str(key),
                                    "score": float(value),
                                }
                            )

                # Apply limit if specified
                result_signals = signals_list if limit is None else signals_list[:limit]
                return {
                    "success": True,
                    "signal_count": len(signals_list),
                    "signals": result_signals,
                }
            else:
                return {
                    "success": True,
                    "signal_count": 0,
                    "signals": [],
                }

        except Exception as e:
            self.logger.error(f"Failed to get signals: {e}")
            return {
                "success": False,
                "error": str(e),
                "signals": None,
            }

    def execute_backtest(
        self,
        benchmark: Optional[str] = None,
        account: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute backtest using Qlib's TopkDropoutStrategy.

        This method uses the signals from Online Serving (generated by Routine)
        to perform a historical backtest using the TopK strategy.

        The backtest:
        1. Uses signals already generated by Online Serving
        2. Applies Qlib's TopkDropoutStrategy with configured parameters
        3. Uses Qlib's standard backtest framework
        4. Calculates returns and metrics

        Args:
            benchmark: Benchmark symbol (default: SH000300)
            account: Initial account value (default from config)

        Returns:
            Dictionary with backtest results including daily returns, metrics
        """
        try:
            self.logger.info("Starting TopK Strategy backtest...")

            # Check if Online Serving is initialized and has signals
            if not self.is_initialized:
                # Try to auto-initialize
                self.logger.info("Online Serving not initialized, auto-initializing...")
                try:
                    self._auto_init()
                except Exception as init_e:
                    return {
                        "status": "error",
                        "error": f"Failed to initialize Online Serving: {str(init_e)}. Please run Routine first.",
                    }

            # Get signals from Online Serving
            if self._online_manager is None:
                return {
                    "status": "error",
                    "error": "OnlineManager not available. Please run Routine first to generate signals.",
                }

            signals = self._online_manager.get_signals()
            if signals is None or (hasattr(signals, "empty") and signals.empty):
                return {
                    "status": "error",
                    "error": "No signals available. Please run Routine first to generate signals.",
                }

            self.logger.info(
                f"Using {len(signals)} signals from Online Serving for backtest"
            )

            # Extend signals to cover all available data dates
            signals = self._extend_signals_to_latest_date(signals)

            # Execute TopK backtest using Qlib's standard framework
            result = self._execute_topk_backtest(signals, benchmark, account)

            if result.get("status") == "error":
                return result

            self.logger.info(
                f"TopK Backtest completed: {result.get('trading_days', 0)} trading days, "
                f"return={_safe_float(result.get('total_return', 0)):.4f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"TopK Backtest failed: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
            }

    def _execute_signal_based_backtest(
        self, signals: pd.DataFrame, account: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute backtest using pre-generated signals from Online Serving.

        Args:
            signals: DataFrame with signals (datetime, instrument, score)
            account: Initial account value

        Returns:
            Backtest results dictionary
        """
        import numpy as np
        from app.services.etf_enhanced_indexing_service import (
            get_etf_enhanced_indexing_service,
        )
        from app.config.qlib import qlib_config

        # Get backtest config
        backtest_config = qlib_config.backtest_config.get("backtest", {})
        account = (
            account if account is not None else backtest_config.get("account", 1000000)
        )

        # Get exchange costs
        exchange_kwargs = backtest_config.get(
            "exchange_kwargs",
            {
                "open_cost": 0.0003,
                "close_cost": 0.0013,
                "min_cost": 5,
            },
        )
        open_cost = exchange_kwargs.get("open_cost", 0.0003)
        close_cost = exchange_kwargs.get("close_cost", 0.0013)

        # Get ETF service for portfolio calculation
        etf_service = get_etf_enhanced_indexing_service()

        # Group signals by date
        if isinstance(signals.index, pd.MultiIndex):
            # Reset index to get datetime and instrument as columns
            signals_df = signals.reset_index()
            if "level_0" in signals_df.columns:
                signals_df = signals_df.rename(
                    columns={"level_0": "datetime", "level_1": "instrument"}
                )
            elif "datetime" not in signals_df.columns:
                signals_df.columns = ["datetime", "instrument", "score"]
        else:
            signals_df = signals.reset_index()
            signals_df.columns = (
                ["datetime", "instrument", "score"]
                if len(signals_df.columns) == 3
                else signals_df.columns
            )

        # Ensure datetime column exists
        if "datetime" not in signals_df.columns:
            self.logger.error(f"Signals columns: {signals_df.columns.tolist()}")
            return {
                "status": "error",
                "error": "Invalid signal format: missing datetime column",
            }

        # Get unique dates
        signals_df["datetime"] = pd.to_datetime(signals_df["datetime"])
        unique_dates = sorted(signals_df["datetime"].unique())

        if len(unique_dates) < 2:
            return {
                "status": "error",
                "error": f"Not enough trading days for backtest: {len(unique_dates)}",
            }

        self.logger.info(
            f"Backtest period: {unique_dates[0]} to {unique_dates[-1]}, {len(unique_dates)} days"
        )

        # Initialize backtest state
        portfolio_value = account
        current_holdings = {}  # symbol -> shares
        daily_returns = []
        total_cost = 0.0

        # Get price data for all instruments
        try:
            from qlib.data import D

            instruments = signals_df["instrument"].unique().tolist()
            # Add benchmark index for chart comparison
            if "SH000300" not in instruments:
                instruments = instruments + ["SH000300"]

            # Get close prices
            price_data = D.features(
                instruments=instruments,
                fields=["$close"],
                start_time=str(unique_dates[0].date()),
                end_time=str(unique_dates[-1].date()),
                freq="day",
            )
            price_data = (
                price_data.droplevel(1, axis=1)
                if price_data.columns.nlevels > 1
                else price_data
            )
            price_data.columns = ["close"]

        except Exception as e:
            self.logger.error(f"Failed to load price data: {e}")
            return {
                "status": "error",
                "error": f"Failed to load price data: {str(e)}",
            }

        # Get rebalancing period from config
        rebalance_period = etf_service.rebalance_period_days
        self.logger.info(
            f"Backtest rebalancing period: every {rebalance_period} trading days"
        )

        # Run backtest day by day
        prev_portfolio_value = account
        current_weights = {}  # Persist weights between rebalancing days
        current_etf_weight = 0.5  # Default ETF weight
        rebalance_count = 0  # Track actual rebalancing days

        for i, date in enumerate(
            unique_dates[:-1]
        ):  # Skip last day (no next day return)
            next_date = unique_dates[i + 1]

            # Check if this is a rebalancing day using ETF service (consistent with online serving)
            date_str = str(date.date()) if hasattr(date, "date") else str(date)[:10]
            is_rebalance_day = etf_service.is_rebalance_day(date_str)

            # Get signals for this date
            day_signals = signals_df[signals_df["datetime"] == date]
            signal_dict = dict(
                zip(
                    day_signals["instrument"],
                    (
                        day_signals["score"]
                        if "score" in day_signals.columns
                        else day_signals.iloc[:, -1]
                    ),
                )
            )

            # Only recalculate target weights on rebalancing days
            if is_rebalance_day:
                rebalance_count += 1  # Increment rebalance counter
                # Calculate target portfolio using ETF service logic
                try:
                    etf_weight, alpha_weight, _ = etf_service.calculate_dynamic_weights(
                        signal_dict
                    )
                    current_etf_weight = etf_weight

                    # Get top stocks
                    sorted_signals = sorted(
                        signal_dict.items(), key=lambda x: x[1], reverse=True
                    )
                    top_stocks = sorted_signals[: etf_service.max_stocks]

                    # Calculate target weights
                    target_weights = {}

                    # ETF weight (simplified - use cash equivalent)
                    etf_value = portfolio_value * etf_weight

                    # Stock weights
                    total_score = sum(max(0, s) for _, s in top_stocks)
                    if total_score > 0:
                        for symbol, score in top_stocks:
                            target_weights[symbol] = (
                                max(0, score) / total_score
                            ) * alpha_weight
                    else:
                        for symbol, _ in top_stocks:
                            target_weights[symbol] = alpha_weight / len(top_stocks)

                    # Update current weights for non-rebalance days
                    current_weights = target_weights.copy()

                except Exception as e:
                    self.logger.warning(f"Failed to calculate weights for {date}: {e}")
                    continue
            else:
                # Use existing weights (no rebalancing)
                target_weights = current_weights
                if not target_weights:
                    continue  # Skip if no weights yet

            # Calculate daily return based on holdings
            daily_return = 0.0
            day_cost = 0.0

            # Get prices for this date and next date
            # Qlib D.features returns DataFrame with MultiIndex (instrument, datetime)
            # instrument is level=0, datetime is level=1
            try:
                available_instruments = price_data.index.get_level_values(0).unique()

                for symbol, weight in target_weights.items():
                    if symbol not in available_instruments:
                        continue

                    try:
                        # Get price at date and next_date using level=0 for instrument
                        symbol_prices = price_data.xs(symbol, level=0)

                        if (
                            date in symbol_prices.index
                            and next_date in symbol_prices.index
                        ):
                            price_today = symbol_prices.loc[date, "close"]
                            price_next = symbol_prices.loc[next_date, "close"]

                            if price_today > 0 and price_next > 0:
                                stock_return = (price_next - price_today) / price_today
                                daily_return += weight * stock_return
                    except Exception as e:
                        self.logger.debug(f"Price lookup failed for {symbol}: {e}")
                        continue

                # Add ETF return (use index sh000300 if available)
                try:
                    if "sh000300" in available_instruments:
                        index_prices = price_data.xs("sh000300", level=0)
                        if (
                            date in index_prices.index
                            and next_date in index_prices.index
                        ):
                            idx_today = index_prices.loc[date, "close"]
                            idx_next = index_prices.loc[next_date, "close"]
                            if idx_today > 0 and idx_next > 0:
                                etf_return = (idx_next - idx_today) / idx_today
                                daily_return += etf_weight * etf_return
                except Exception:
                    # No index data available, assume zero return for ETF portion
                    pass

            except Exception as e:
                self.logger.warning(f"Error calculating return for {date}: {e}")

            # Apply trading costs only on rebalancing days
            # Cost = portfolio_value * (open_cost + close_cost) * turnover_ratio
            # On rebalance day, assume full portfolio turnover for alpha portion
            if is_rebalance_day:
                # Only alpha portion incurs trading costs (ETF portion is index tracking)
                # Use current_etf_weight which is updated on each rebalance day
                current_alpha_weight = 1.0 - current_etf_weight
                day_cost = (
                    portfolio_value * (open_cost + close_cost) * current_alpha_weight
                )
                total_cost += day_cost

            # Store old portfolio value for net return calculation
            old_portfolio_value = portfolio_value

            # Update portfolio value (after costs)
            portfolio_value = portfolio_value * (1 + daily_return) - day_cost

            # Calculate net daily return (after costs)
            net_daily_return = (
                (portfolio_value - old_portfolio_value) / old_portfolio_value
                if old_portfolio_value > 0
                else 0.0
            )

            # Calculate benchmark return for this day
            benchmark_return = 0.0
            try:
                if "SH000300" in available_instruments:
                    bench_prices = price_data.xs("SH000300", level=0)
                    if date in bench_prices.index and next_date in bench_prices.index:
                        bench_today = bench_prices.loc[date, "close"]
                        bench_next = bench_prices.loc[next_date, "close"]
                        if bench_today > 0 and bench_next > 0:
                            benchmark_return = float(
                                (bench_next - bench_today) / bench_today
                            )
            except Exception:
                pass

            daily_returns.append(
                {
                    "date": str(date.date()),
                    "daily_return": daily_return,  # Gross return (before costs)
                    "net_daily_return": net_daily_return,  # Net return (after costs)
                    "benchmark_return": benchmark_return,
                    "portfolio_value": portfolio_value,
                    "cost": day_cost,
                }
            )

        # Calculate final metrics
        if not daily_returns:
            return {
                "status": "error",
                "error": "No valid trading days in backtest",
            }

        returns_array = np.array([d["daily_return"] for d in daily_returns])
        # Net return (after costs) - based on actual portfolio value
        net_return = (portfolio_value - account) / account
        # Gross return (before costs) - compound daily returns
        gross_return = float(np.prod(1 + returns_array) - 1)
        trading_days = len(daily_returns)

        # Use Qlib's risk_analysis for standard metrics
        try:
            from qlib.contrib.evaluate import risk_analysis

            # Create a pandas Series with date index for Qlib's risk_analysis
            dates = pd.to_datetime([d["date"] for d in daily_returns])
            returns_series = pd.Series(returns_array, index=dates, name="return")

            # Use Qlib's risk_analysis - returns a DataFrame with 'risk' column
            # Metrics: mean, std, annualized_return, information_ratio, max_drawdown
            analysis_df = risk_analysis(returns_series, freq="day")

            # Extract metrics from Qlib's analysis
            annual_return = float(analysis_df.loc["annualized_return", "risk"])
            max_drawdown = float(analysis_df.loc["max_drawdown", "risk"])
            sharpe_ratio = float(analysis_df.loc["information_ratio", "risk"])
            volatility = float(analysis_df.loc["std", "risk"])

            self.logger.info(
                f"Qlib risk_analysis: annualized_return={annual_return:.4f}, "
                f"max_drawdown={max_drawdown:.4f}, sharpe={sharpe_ratio:.4f}, "
                f"volatility={volatility:.4f}"
            )

        except Exception as e:
            self.logger.warning(
                f"Failed to use Qlib risk_analysis, falling back to manual: {e}"
            )
            # Fallback to manual calculation if Qlib fails
            annual_factor = 252 / trading_days if trading_days > 0 else 1
            annual_return = (1 + gross_return) ** annual_factor - 1
            volatility = (
                float(np.std(returns_array, ddof=1) * np.sqrt(252))
                if len(returns_array) > 1
                else 0.0
            )
            sharpe_ratio = annual_return / volatility if volatility > 0.0001 else 0.0
            cumulative = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            max_drawdown = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Calculate additional custom metrics
        # Calmar Ratio = Annualized Return / |Max Drawdown|
        if max_drawdown != 0:
            calmar_ratio = abs(annual_return / max_drawdown)
        else:
            calmar_ratio = 0.0

        # Win Rate = Positive days / Total days
        positive_days = np.sum(returns_array > 0)
        win_rate = float(positive_days / trading_days) if trading_days > 0 else 0.0

        # Profit/Loss Ratio = Average profit / Average loss
        profits = returns_array[returns_array > 0]
        losses = returns_array[returns_array < 0]
        avg_profit = float(np.mean(profits)) if len(profits) > 0 else 0.0
        avg_loss = float(np.abs(np.mean(losses))) if len(losses) > 0 else 0.0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        # Compound Annual Growth Rate (CAGR) = (1 + return)^(252/trading_days) - 1
        # Calculate both gross and net CAGR
        # Gross CAGR - for benchmark comparison (before costs)
        if trading_days > 0 and gross_return > -1:
            cagr = float((1 + gross_return) ** (252 / trading_days) - 1)
        else:
            cagr = 0.0

        # Net CAGR - actual investor return (after costs)
        if trading_days > 0 and net_return > -1:
            net_cagr = float((1 + net_return) ** (252 / trading_days) - 1)
        else:
            net_cagr = 0.0

        # Cost Efficiency Metrics
        # 1. Cost Ratio = Total Cost / Initial Account (cost as % of capital)
        cost_ratio = float(total_cost / account) if account > 0 else 0.0

        # 2. Cost to Profit Ratio = Total Cost / Gross Profit
        #    Lower is better. If > 1, costs exceed profits (bad)
        gross_profit = gross_return * account  # Profit in currency
        if gross_profit > 0:
            cost_to_profit_ratio = float(total_cost / gross_profit)
        else:
            # Use 0.0 instead of inf to avoid JSON serialization errors
            cost_to_profit_ratio = 0.0

        # 3. Turnover Rate = Total Traded Value / Initial Account
        #    Estimates how many times the portfolio was turned over
        #    Since total_cost = traded_value * cost_rate, we can derive:
        #    traded_value = total_cost / cost_rate
        #    turnover = traded_value / account
        cost_rate = 0.003  # 0.3% round-trip cost assumption
        if account > 0 and cost_rate > 0:
            # Estimate total traded value from cost
            total_traded_value = total_cost / cost_rate
            # Turnover = traded value / initial capital
            # Divide by 2 because each trade involves buy and sell
            turnover_rate = float(total_traded_value / account / 2)
        else:
            turnover_rate = 0.0

        # Log metrics for debugging
        self.logger.info(
            f"Backtest metrics: gross_return={gross_return:.4f}, net_return={net_return:.4f}, "
            f"annual_return={annual_return:.4f}, cagr={cagr:.4f}, net_cagr={net_cagr:.4f}, "
            f"sharpe={sharpe_ratio:.4f}, max_dd={max_drawdown:.4f}, "
            f"calmar={calmar_ratio:.4f}, win_rate={win_rate:.4f}, "
            f"cost_ratio={cost_ratio:.4f}, cost_to_profit={cost_to_profit_ratio:.4f}, "
            f"turnover={turnover_rate:.2f}, rebalance_days={rebalance_count}"
        )

        return {
            "status": "success",
            "start_time": str(unique_dates[0].date()),
            "end_time": str(unique_dates[-1].date()),
            "trading_days": trading_days,
            "rebalance_days": rebalance_count,  # Actual rebalancing days
            "rebalance_period": rebalance_period,  # Rebalancing period config
            "total_return": _safe_float(
                gross_return
            ),  # Gross return (before costs) for benchmark comparison
            "net_return": _safe_float(
                net_return
            ),  # Net return (after costs) - actual investor return
            "total_cost": _safe_float(total_cost),
            "final_account": _safe_float(portfolio_value),
            # Qlib risk_analysis metrics (arithmetic annualized)
            "annual_return": _safe_float(annual_return),
            "volatility": _safe_float(volatility),
            "sharpe_ratio": _safe_float(sharpe_ratio),
            "max_drawdown": _safe_float(max_drawdown),
            # Custom additional metrics
            "cagr": _safe_float(
                cagr
            ),  # Compound Annual Growth Rate (geometric) - gross
            "net_cagr": _safe_float(
                net_cagr
            ),  # Net CAGR (after costs) - actual investor return
            "calmar_ratio": _safe_float(calmar_ratio),
            "win_rate": _safe_float(win_rate),
            "profit_loss_ratio": _safe_float(profit_loss_ratio),
            # Cost efficiency metrics
            "cost_ratio": _safe_float(cost_ratio),  # Cost as % of capital
            "cost_to_profit_ratio": _safe_float(cost_to_profit_ratio),  # Cost / Profit
            "turnover_rate": _safe_float(turnover_rate),  # Portfolio turnover
            "daily_returns": daily_returns,
        }

    def _generate_etf_backtest_charts(
        self,
        daily_returns: list,
        qlib_max_drawdown: float = None,
        initial_account: float = None,
    ) -> Dict[str, Any]:
        """Generate chart data from ETF backtest daily returns.

        Args:
            daily_returns: List of daily return records
            qlib_max_drawdown: Max drawdown from Qlib's risk_analysis (for consistency)
            initial_account: Initial account value for net return calculation
        """
        if not daily_returns:
            self.logger.warning("No daily returns data for chart generation")
            return {}

        try:
            import numpy as np

            # Cumulative returns chart - frontend expects "strategy" key
            cumulative_returns = []
            cum_return = 1.0
            cum_benchmark = 1.0  # Track benchmark cumulative return
            max_cum_return = 1.0
            max_drawdown = 0.0

            # Track the peak that led to max drawdown (not the latest peak)
            current_peak_date = None
            current_peak_value = 0.0
            max_drawdown_peak_date = None
            max_drawdown_peak_value = 0.0
            max_drawdown_date = None

            # Track recovery: the first date after max_drawdown_date when cum_return >= max_drawdown_peak_cum_return
            max_drawdown_peak_cum_return = 1.0
            recovery_date = None
            found_max_drawdown = False

            # Use initial_account for accurate net return calculation
            # If not provided, back-calculate from first day's data
            if initial_account is not None and initial_account > 0:
                initial_value = initial_account
            else:
                initial_value = (
                    daily_returns[0].get("portfolio_value", 0) if daily_returns else 0
                )
                first_return = (
                    daily_returns[0].get("daily_return", 0) if daily_returns else 0
                )
                first_cost = daily_returns[0].get("cost", 0) if daily_returns else 0
                # Back-calculate: pv = prev * (1 + ret) - cost => prev = (pv + cost) / (1 + ret)
                if first_return != -1:
                    initial_value = (initial_value + first_cost) / (1 + first_return)

            # Track both gross and net cumulative returns
            cum_gross = 1.0  # Gross return (before costs) - for benchmark comparison
            cum_net = 1.0  # Net return (after costs) - actual investor return

            for row in daily_returns:
                daily_ret = row.get("daily_return", 0)
                benchmark_ret = row.get("benchmark_return", 0)
                portfolio_value = row.get("portfolio_value", 0)

                # Gross return: compound daily returns (no costs)
                cum_gross *= 1 + daily_ret
                cum_gross_pct = float(cum_gross - 1)

                # Net return: based on actual portfolio value (includes costs)
                if initial_value > 0:
                    cum_net = portfolio_value / initial_value
                    cum_net_pct = float(cum_net - 1)
                else:
                    cum_net *= 1 + daily_ret
                    cum_net_pct = float(cum_net - 1)

                cum_benchmark *= 1 + benchmark_ret
                cum_benchmark_pct = float(cum_benchmark - 1)

                # Track current peak using gross return (for fair comparison)
                cum_return = cum_gross  # Use gross for drawdown calculation
                if cum_return > max_cum_return:
                    max_cum_return = cum_return
                    current_peak_date = row.get("date")
                    current_peak_value = cum_gross_pct

                # Calculate drawdown from current peak
                current_drawdown = (cum_return - max_cum_return) / max_cum_return

                # If this is a new max drawdown, record the peak that led to it
                if current_drawdown < max_drawdown:
                    max_drawdown = current_drawdown
                    max_drawdown_date = row.get("date")
                    max_drawdown_peak_date = current_peak_date
                    max_drawdown_peak_value = current_peak_value
                    max_drawdown_peak_cum_return = max_cum_return
                    recovery_date = None  # Reset recovery when new max drawdown found
                    found_max_drawdown = True

                # Check for recovery after max drawdown
                if found_max_drawdown and recovery_date is None:
                    if cum_return >= max_drawdown_peak_cum_return:
                        recovery_date = row.get("date")

                chart_point = {
                    "date": row.get("date"),
                    "strategy": cum_gross_pct,  # Gross return (before costs) for benchmark comparison
                    "net_return": cum_net_pct,  # Net return (after costs) - actual investor return
                }
                # Add benchmark if available
                if benchmark_ret != 0 or cum_benchmark != 1.0:
                    chart_point["benchmark"] = cum_benchmark_pct
                cumulative_returns.append(chart_point)

            # Portfolio value chart
            portfolio_values = [
                {"date": row.get("date"), "value": row.get("portfolio_value", 0)}
                for row in daily_returns
            ]

            # Max drawdown info for chart annotations
            max_drawdown_info = None
            if max_drawdown_peak_date and max_drawdown_date:
                # Calculate drawdown days
                from datetime import datetime

                try:
                    peak_dt = datetime.strptime(max_drawdown_peak_date, "%Y-%m-%d")
                    trough_dt = datetime.strptime(max_drawdown_date, "%Y-%m-%d")
                    drawdown_days = (trough_dt - peak_dt).days
                except Exception:
                    drawdown_days = 0

                # Use Qlib's max_drawdown if provided for consistency with risk_metrics
                final_max_drawdown = (
                    qlib_max_drawdown if qlib_max_drawdown is not None else max_drawdown
                )

                max_drawdown_info = {
                    "peak_date": max_drawdown_peak_date,
                    "peak_value": max_drawdown_peak_value,
                    "max_drawdown_date": max_drawdown_date,
                    "max_drawdown": final_max_drawdown,  # Use Qlib's value for consistency
                    "drawdown_days": drawdown_days,
                    "recovery_date": recovery_date,
                }

            # Calculate yearly and monthly returns
            yearly_returns = self._calculate_periodic_returns(daily_returns, "yearly")
            monthly_returns = self._calculate_periodic_returns(daily_returns, "monthly")

            self.logger.info(
                f"Generated chart data: {len(cumulative_returns)} points, "
                f"max_drawdown={max_drawdown:.4f}, "
                f"yearly_periods={len(yearly_returns)}, monthly_periods={len(monthly_returns)}"
            )

            return {
                "cumulative_returns": cumulative_returns,
                "portfolio_values": portfolio_values,
                "max_drawdown_info": max_drawdown_info,
                "yearly_returns": yearly_returns,
                "monthly_returns": monthly_returns,
            }
        except Exception as e:
            self.logger.error(f"Failed to generate chart data: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {}

    def _calculate_periodic_returns(
        self, daily_returns: list, period: str = "yearly"
    ) -> list:
        """
        Calculate periodic (yearly or monthly) returns for strategy and benchmark.

        Args:
            daily_returns: List of daily return records with 'date', 'daily_return', 'benchmark_return'
            period: 'yearly' or 'monthly'

        Returns:
            List of periodic return records with strategy_return, benchmark_return, and excess_return
        """
        if not daily_returns:
            return []

        try:
            from collections import defaultdict

            # Group daily returns by period
            period_data = defaultdict(lambda: {"strategy": [], "benchmark": []})

            for row in daily_returns:
                date_str = row.get("date", "")
                if not date_str:
                    continue

                # Extract period key (YYYY for yearly, YYYY-MM for monthly)
                if period == "yearly":
                    period_key = date_str[:4]  # YYYY
                else:  # monthly
                    period_key = date_str[:7]  # YYYY-MM

                # Use net_daily_return for strategy (after costs) - reflects actual investor return
                # Fallback to daily_return if net_daily_return not available (backward compatibility)
                period_data[period_key]["strategy"].append(
                    row.get("net_daily_return", row.get("daily_return", 0))
                )
                period_data[period_key]["benchmark"].append(
                    row.get("benchmark_return", 0)
                )

            # Calculate compounded returns for each period
            results = []
            for period_key in sorted(period_data.keys()):
                data = period_data[period_key]

                # Compound daily returns: (1+r1) * (1+r2) * ... - 1
                strategy_cum = 1.0
                for r in data["strategy"]:
                    strategy_cum *= 1 + r
                strategy_return = strategy_cum - 1

                benchmark_cum = 1.0
                for r in data["benchmark"]:
                    benchmark_cum *= 1 + r
                benchmark_return = benchmark_cum - 1

                # Excess return (alpha)
                excess_return = strategy_return - benchmark_return

                results.append(
                    {
                        "period": period_key,
                        "strategy_return": round(strategy_return, 6),
                        "benchmark_return": round(benchmark_return, 6),
                        "excess_return": round(excess_return, 6),
                        "trading_days": len(data["strategy"]),
                    }
                )

            return results

        except Exception as e:
            self.logger.error(f"Failed to calculate {period} returns: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of Online Serving.

        Returns:
            Status dictionary
        """
        status = {
            "is_initialized": self.is_initialized,
            "freq": self._freq,
            "last_routine_time": (
                self._last_routine_time.isoformat() if self._last_routine_time else None
            ),
            "initialization_error": self._initialization_error,
            "config": {
                "experiment_name": qlib_config.experiment_name,
                "rolling_step": qlib_config.rolling_step,
                "rolling_type": qlib_config.rolling_type,
                "mongodb_uri": qlib_config.mongodb_uri,
                "mlruns_path": qlib_config.mlruns_path,
                "stock_pool": qlib_config.stock_pool,
                "source": qlib_config.source,
                "region": qlib_config.region,
            },
        }

        # Add data range info
        try:
            data_range = self._get_data_range()
            if data_range:
                status["data_range"] = data_range
        except Exception as e:
            self.logger.warning(f"Failed to get data range: {e}")

        # Add signal count if available
        if self.is_initialized and self._online_manager is not None:
            try:
                signals = self._online_manager.get_signals()
                if signals is not None:
                    status["signal_count"] = len(signals)
                    self.logger.debug(
                        f"get_status: signal_count={len(signals)}, type={type(signals)}"
                    )
                else:
                    status["signal_count"] = 0
                    self.logger.warning("get_status: get_signals() returned None")
            except Exception as e:
                self.logger.error(
                    f"get_status: Failed to get signal count: {e}", exc_info=True
                )
                status["signal_count"] = 0
        else:
            # OnlineManager not in memory (e.g., after hot-reload) — use persisted count
            status["signal_count"] = getattr(self, "_persisted_signal_count", 0)

        return status

    def _get_data_range(self) -> Optional[Dict[str, str]]:
        """
        Get the date range of available Qlib data.

        Returns:
            Dictionary with start_date and end_date, or None if not available
        """
        try:
            from qlib.data import D

            # Get calendar (trading days)
            calendar = D.calendar(freq=self._freq)
            if calendar is not None and len(calendar) > 0:
                start_date = calendar[0]
                end_date = calendar[-1]

                # Convert to string format
                start_str = (
                    start_date.strftime("%Y-%m-%d")
                    if hasattr(start_date, "strftime")
                    else str(start_date)[:10]
                )
                end_str = (
                    end_date.strftime("%Y-%m-%d")
                    if hasattr(end_date, "strftime")
                    else str(end_date)[:10]
                )

                return {
                    "start_date": start_str,
                    "end_date": end_str,
                    "trading_days": len(calendar),
                }
            return None
        except Exception as e:
            self.logger.warning(f"Failed to get data range: {e}")
            return None

    def _calculate_model_metrics(self, signals: pd.Series) -> Dict[str, Any]:
        """
        Calculate comprehensive model performance metrics for the Rolling Ensemble.

        This method:
        1. Loads label data corresponding to the signals
        2. Calls ModelMetricsService to calculate all metrics
        3. Saves metrics to file for frontend access

        Args:
            signals: Ensemble predictions from OnlineManager

        Returns:
            Result dictionary with success status
        """
        try:
            from app.services.model_metrics_service import get_model_metrics_service
            from qlib.data.dataset.loader import QlibDataLoader

            if signals is None or len(signals) == 0:
                self.logger.warning("No signals available for metrics calculation")
                return {"success": False, "error": "No signals available"}

            self.logger.info(f"Calculating metrics for {len(signals)} predictions...")

            # Get label data
            # We need to load the same label data that was used in training
            try:
                # Get the task template to extract label configuration
                task_template = self._build_task_template()
                dataset_config = task_template.get("dataset", {})

                # Extract label from dataset config
                # The label is typically in dataset.kwargs.segments.train
                label_expr = None
                if "kwargs" in dataset_config:
                    kwargs = dataset_config["kwargs"]
                    if "handler" in kwargs:
                        handler_config = kwargs["handler"]
                        if (
                            isinstance(handler_config, dict)
                            and "kwargs" in handler_config
                        ):
                            handler_kwargs = handler_config["kwargs"]
                            if "label" in handler_kwargs:
                                label_expr = handler_kwargs["label"]

                if label_expr is None:
                    # Default label expression
                    label_expr = ["Ref($close, -2)/Ref($close, -1) - 1"]

                self.logger.info(f"Loading label data with expression: {label_expr}")

                # Load label data using Qlib
                from qlib.data import D

                # Get instruments and date range from signals
                instruments = (
                    signals.index.get_level_values("instrument").unique().tolist()
                )
                start_date = signals.index.get_level_values("datetime").min()
                end_date = signals.index.get_level_values("datetime").max()

                # Load label data
                label_data = D.features(
                    instruments=instruments,
                    fields=label_expr,
                    start_time=start_date,
                    end_time=end_date,
                    freq=self._freq,
                )

                if label_data is None or label_data.empty:
                    self.logger.warning("Failed to load label data")
                    return {"success": False, "error": "Failed to load label data"}

                # Convert to Series (take first column if multiple)
                if isinstance(label_data, pd.DataFrame):
                    label = label_data.iloc[:, 0]
                else:
                    label = label_data

                self.logger.info(f"Loaded {len(label)} label samples")

            except Exception as e:
                self.logger.error(f"Failed to load label data: {e}")
                return {
                    "success": False,
                    "error": f"Failed to load label data: {str(e)}",
                }

            # Get the latest model for feature importance
            # Try to get the latest recorder from the strategy
            latest_model = None
            try:
                from qlib.workflow import R
                from qlib.workflow.online.utils import OnlineToolR

                online_tool = OnlineToolR()

                # Get experiment recorders directly
                exp = R.get_exp(experiment_name=self._experiment_name)
                recorders = exp.list_recorders()

                if recorders:
                    # Filter for online recorders
                    online_recorders = []
                    for rec_id, rec_info in recorders.items():
                        try:
                            rec = exp.get_recorder(recorder_id=rec_id)
                            if (
                                online_tool.get_online_tag(rec)
                                == OnlineToolR.ONLINE_TAG
                            ):
                                online_recorders.append(rec)
                        except Exception:
                            continue

                    if online_recorders:
                        # Get the latest recorder (last in list)
                        latest_recorder = online_recorders[-1]
                        self.logger.info(
                            f"Found {len(online_recorders)} online recorders, using latest"
                        )

                        # Try different model file names
                        model_files = ["trained_model.pkl", "model.pkl", "params.pkl"]
                        for model_file in model_files:
                            try:
                                latest_model = latest_recorder.load_object(model_file)
                                self.logger.info(
                                    f"Loaded model from {model_file} for feature importance"
                                )
                                break
                            except Exception as e:
                                self.logger.debug(f"Could not load {model_file}: {e}")
                                continue

                        if latest_model is None:
                            self.logger.warning(
                                "Could not load model from any known file"
                            )
                    else:
                        self.logger.warning("No online recorders found")

            except Exception as e:
                self.logger.warning(f"Failed to load latest model: {e}")

            # Calculate metrics
            metrics_service = get_model_metrics_service()
            all_metrics = metrics_service.calculate_all_metrics(
                pred=signals, label=label, model=latest_model, freq=self._freq
            )

            # Save metrics
            metrics_service.save_metrics(all_metrics, model_id="active")

            self.logger.info("Model metrics calculated and saved successfully")

            return {
                "success": True,
                "message": "Model metrics calculated successfully",
                "metrics_summary": {
                    "ic": all_metrics["ic_metrics"]["ic_mean"],
                    "icir": all_metrics["ic_metrics"]["icir"],
                    "long_short_sharpe": all_metrics["long_short_metrics"][
                        "long_short_ann_sharpe"
                    ],
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to calculate model metrics: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_risk_metrics(
        self, report_df: pd.DataFrame, freq: str
    ) -> Dict[str, Any]:
        """
        Calculate risk metrics from backtest report.

        Uses Qlib's risk_analysis for standard metrics:
        - Annualized Return
        - Max Drawdown
        - Sharpe Ratio (Information Ratio)
        - Volatility (Std)

        Args:
            report_df: Backtest report DataFrame with 'return' column
            freq: Data frequency (only 'day' is supported)

        Returns:
            Dictionary of risk metrics
        """
        try:
            from qlib.contrib.evaluate import risk_analysis

            if "return" not in report_df.columns:
                return {}

            returns = report_df["return"]

            # Use Qlib's risk_analysis - returns a DataFrame with 'risk' column
            analysis_df = risk_analysis(returns, freq=freq)

            # Extract key metrics from the DataFrame
            # The result is a DataFrame with index: mean, std, annualized_return, information_ratio, max_drawdown
            # and column: 'risk'
            metrics = {
                "annualized_return": float(
                    analysis_df.loc["annualized_return", "risk"]
                ),
                "max_drawdown": float(analysis_df.loc["max_drawdown", "risk"]),
                "sharpe_ratio": float(analysis_df.loc["information_ratio", "risk"]),
                "volatility": float(analysis_df.loc["std", "risk"]),
            }

            # Calculate additional metrics
            # Calmar Ratio = Annualized Return / |Max Drawdown|
            if metrics["max_drawdown"] != 0:
                metrics["calmar_ratio"] = abs(
                    metrics["annualized_return"] / metrics["max_drawdown"]
                )
            else:
                metrics["calmar_ratio"] = 0

            # Win rate
            positive_days = (returns > 0).sum()
            total_days = len(returns)
            metrics["win_rate"] = (
                float(positive_days / total_days) if total_days > 0 else 0
            )

            # Profit/Loss ratio
            gains = returns[returns > 0]
            losses = returns[returns < 0]
            avg_gain = gains.mean() if len(gains) > 0 else 0
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 0
            metrics["profit_loss_ratio"] = (
                float(avg_gain / avg_loss) if avg_loss > 0 else 0
            )

            self.logger.info(f"Risk metrics calculated: {metrics}")
            return metrics

        except Exception as e:
            self.logger.error(f"Failed to calculate risk metrics: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {}

    def _generate_backtest_charts(
        self, report_df: pd.DataFrame, benchmark: str
    ) -> Dict[str, Any]:
        """
        Generate chart data for backtest visualization.

        Charts:
        - Cumulative returns curve (strategy vs benchmark)
        - Daily returns distribution
        - Drawdown curve

        Args:
            report_df: Backtest report DataFrame
            benchmark: Benchmark symbol

        Returns:
            Dictionary of chart data
        """
        try:
            charts = {}

            # 1. Cumulative Returns Chart
            if "return" in report_df.columns:
                cumulative = (1 + report_df["return"]).cumprod() - 1
                cumulative_data = []
                for date, value in cumulative.items():
                    cumulative_data.append(
                        {
                            "date": str(date)[:10],
                            "strategy": float(value),
                        }
                    )

                # Add benchmark if available
                if "bench" in report_df.columns:
                    bench_cumulative = (1 + report_df["bench"]).cumprod() - 1
                    for i, (date, value) in enumerate(bench_cumulative.items()):
                        if i < len(cumulative_data):
                            cumulative_data[i]["benchmark"] = float(value)

                charts["cumulative_returns"] = cumulative_data

            # 2. Daily Returns Distribution
            if "return" in report_df.columns:
                returns = report_df["return"].dropna()
                # Create histogram bins
                import numpy as np

                hist, bin_edges = np.histogram(returns, bins=30)
                distribution_data = []
                for i in range(len(hist)):
                    distribution_data.append(
                        {
                            "bin_start": float(bin_edges[i]),
                            "bin_end": float(bin_edges[i + 1]),
                            "bin_center": float((bin_edges[i] + bin_edges[i + 1]) / 2),
                            "count": int(hist[i]),
                        }
                    )
                charts["return_distribution"] = distribution_data

            # 3. Max Drawdown Analysis (for annotation on cumulative returns chart)
            if "return" in report_df.columns:
                cumulative = (
                    1 + report_df["return"]
                ).cumprod() - 1  # Convert to percentage
                running_max = (1 + report_df["return"]).cumprod().cummax()
                drawdown = (
                    (1 + report_df["return"]).cumprod() - running_max
                ) / running_max

                # Find max drawdown point (trough)
                max_dd_idx = drawdown.idxmin()
                max_dd_value = float(drawdown.min())

                # Find the peak before max drawdown (start of drawdown period)
                dd_before_max = drawdown.loc[:max_dd_idx]
                peak_candidates = dd_before_max[dd_before_max == 0]
                if len(peak_candidates) > 0:
                    peak_date = peak_candidates.index[-1]
                else:
                    peak_date = drawdown.index[0]

                # Get cumulative return values at peak and trough for annotation
                peak_value = (
                    float(cumulative.loc[peak_date])
                    if peak_date in cumulative.index
                    else 0
                )
                trough_value = float(cumulative.loc[max_dd_idx])

                # Find recovery date (when cumulative returns exceed peak value again)
                after_trough = cumulative.loc[max_dd_idx:]
                recovery_candidates = after_trough[after_trough >= peak_value]
                recovery_date = (
                    str(recovery_candidates.index[0])[:10]
                    if len(recovery_candidates) > 0
                    else None
                )

                # Calculate drawdown duration
                drawdown_days = (
                    (max_dd_idx - peak_date).days
                    if hasattr(max_dd_idx - peak_date, "days")
                    else 0
                )

                charts["max_drawdown_info"] = {
                    "max_drawdown": max_dd_value,
                    "max_drawdown_date": str(max_dd_idx)[:10],
                    "peak_date": str(peak_date)[:10],
                    "peak_value": peak_value,
                    "trough_value": trough_value,
                    "recovery_date": recovery_date,
                    "drawdown_days": drawdown_days,
                }

            # 4. Daily Returns Time Series
            if "return" in report_df.columns:
                daily_returns = []
                for date, value in report_df["return"].items():
                    daily_returns.append(
                        {
                            "date": str(date)[:10],
                            "return": float(value),
                        }
                    )
                charts["daily_returns"] = daily_returns

            self.logger.info(f"Generated {len(charts)} chart datasets for backtest")
            return charts

        except Exception as e:
            self.logger.error(f"Failed to generate backtest charts: {e}")
            return {}

    def _execute_topk_backtest(
        self,
        signals: pd.DataFrame,
        benchmark: Optional[str] = None,
        account: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute backtest using Qlib's TopkDropoutStrategy with intelligent rebalancing.

        Args:
            signals: Prediction signals from Online Serving
            benchmark: Benchmark symbol (default: 000300.SH)
            account: Initial account value

        Returns:
            Dictionary with backtest results
        """
        try:
            from qlib.contrib.strategy import TopkDropoutStrategy
            from qlib.contrib.evaluate import backtest_daily
            from app.config.qlib import qlib_config

            # Get TopK Dropout strategy configuration
            topk_config = qlib_config._config.get("topk_dropout_strategy", {})

            topk = topk_config.get("topk", 10)
            n_drop = topk_config.get("n_drop", 10)

            # Get backtest configuration
            backtest_config = qlib_config.backtest_config.get("backtest", {})
            if account is None:
                account = backtest_config.get("account", 1000000)

            # Set benchmark from config or auto-detect from index_config.yaml
            if benchmark is None:
                benchmark_setting = backtest_config.get("benchmark", "auto")
                if benchmark_setting == "auto":
                    try:
                        import yaml
                        from pathlib import Path

                        config_path = (
                            Path(__file__).parent.parent
                            / "config"
                            / "index_config.yaml"
                        )
                        with open(config_path, "r", encoding="utf-8") as f:
                            index_cfg = yaml.safe_load(f)
                        active_index = index_cfg.get("active_index", "etf_universe")
                        active_cfg = index_cfg.get("indexes", {}).get(active_index, {})
                        benchmark = active_cfg.get("etf_code", "SH510300")
                        self.logger.info(
                            f"Auto-detected benchmark from index_config: {benchmark}"
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to auto-detect benchmark, using SH510300: {e}"
                        )
                        benchmark = "SH510300"
                else:
                    benchmark = benchmark_setting

            self.logger.info(
                f"TopK Dropout Strategy config: topk={topk}, n_drop={n_drop}, account={account}"
            )

            # Create TopkDropoutStrategy with intelligent rebalancing
            strategy = TopkDropoutStrategy(topk=topk, n_drop=n_drop, signal=signals)

            # Get date range from signals
            signal_dates = signals.index.get_level_values(0).unique().sort_values()
            start_time = str(signal_dates[0].date())
            # Use second-to-last date to avoid Qlib calendar boundary IndexError
            # (Qlib needs calendar[index+1] which doesn't exist on the last date)
            end_time = (
                str(signal_dates[-2].date())
                if len(signal_dates) > 1
                else str(signal_dates[-1].date())
            )

            self.logger.info(f"Backtest period: {start_time} to {end_time}")

            # Execute backtest using Qlib's standard framework
            backtest_result = backtest_daily(
                start_time=start_time,
                end_time=end_time,
                strategy=strategy,
                account=account,
                benchmark=benchmark,
                exchange_kwargs={
                    "limit_threshold": 0.095,
                    "deal_price": "close",
                    "open_cost": 0.0001,
                    "close_cost": 0.0001,
                    "min_cost": 0,
                },
            )

            # backtest_daily returns (report_normal, positions_normal) tuple
            report_df, positions = backtest_result

            if report_df is None or report_df.empty:
                return {"status": "error", "error": "Backtest returned empty results"}

            # Calculate metrics using Qlib's risk analysis
            from qlib.contrib.evaluate import risk_analysis

            returns = (
                report_df["return"] if "return" in report_df.columns else pd.Series()
            )
            analysis_df = risk_analysis(returns, freq="day")

            # Extract key metrics
            annual_return = _safe_float(analysis_df.loc["annualized_return", "risk"])
            max_drawdown = _safe_float(analysis_df.loc["max_drawdown", "risk"])
            sharpe_ratio = _safe_float(analysis_df.loc["information_ratio", "risk"])
            volatility = _safe_float(analysis_df.loc["std", "risk"])

            # Calculate cumulative return from daily returns
            total_return = _safe_float(
                ((1 + returns).cumprod().iloc[-1] - 1) if len(returns) > 0 else 0
            )
            trading_days = len(report_df)

            # Calculate cost from report_df
            total_cost_pct = _safe_float(
                report_df["cost"].sum() if "cost" in report_df.columns else 0
            )
            total_cost_money = _safe_float(total_cost_pct * account)
            # Qlib's report_df["return"] is already net of costs,
            # so total_return IS the net return. Do NOT subtract cost again.
            net_return = total_return

            # Calculate net CAGR
            if trading_days > 0:
                years = trading_days / 252.0
                net_cagr = _safe_float((1 + net_return) ** (1 / years) - 1)
            else:
                net_cagr = 0.0

            # Calmar ratio = annualized_return / |max_drawdown|
            calmar_ratio = _safe_float(
                annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
            )

            # Win rate = days with positive return / total days
            win_rate = _safe_float(
                (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
            )

            # Profit/Loss ratio = avg(positive returns) / |avg(negative returns)|
            pos_returns = returns[returns > 0]
            neg_returns = returns[returns < 0]
            profit_loss_ratio = _safe_float(
                pos_returns.mean() / abs(neg_returns.mean())
                if len(neg_returns) > 0 and neg_returns.mean() != 0
                else 0
            )

            # Cost ratio = total cost / initial account
            cost_ratio = _safe_float(total_cost_pct)

            # Cost to profit ratio = total cost / total profit
            total_profit_money = total_return * account
            cost_to_profit = _safe_float(
                total_cost_money / total_profit_money if total_profit_money > 0 else 0
            )

            # Average daily turnover rate from report_df
            # (each row is daily turnover as fraction of portfolio, e.g. 1.76 = 176%)
            turnover_rate = _safe_float(
                report_df["turnover"].mean() if "turnover" in report_df.columns else 0
            )

            # Alpha and Beta (CAPM-based)
            # Beta = Cov(Rp, Rm) / Var(Rm)
            # Alpha = (Rp - Rf) - Beta * (Rm - Rf), annualized
            import numpy as np

            alpha = 0.0
            beta = 0.0
            if "bench" in report_df.columns and len(returns) > 1:
                bench_returns = report_df["bench"].dropna()
                if len(bench_returns) == len(returns):
                    rf_daily = 0.02 / 252  # ~2% annual risk-free rate
                    excess_p = returns.values - rf_daily
                    excess_m = bench_returns.values - rf_daily
                    var_m = np.var(excess_m, ddof=1)
                    if var_m > 0:
                        beta = _safe_float(np.cov(excess_p, excess_m)[0][1] / var_m)
                    # Annualized alpha
                    alpha = _safe_float(
                        (
                            returns.mean()
                            - rf_daily
                            - beta * (bench_returns.mean() - rf_daily)
                        )
                        * 252
                    )

            # Generate confidence history from backtest signals
            self._generate_confidence_history_from_signals(signals, topk)

            # Build API result
            api_result = {
                "status": "success",
                "start_time": start_time,
                "end_time": end_time,
                "data_start_time": start_time,
                "data_end_time": end_time,
                "freq": "day",
                "trading_days": trading_days,
                "rebalance_days": trading_days,
                "rebalance_period": 1,
                "signal_count": len(signals),
                "total_return": total_return,
                "total_cost": total_cost_money,
                "net_return": net_return,
                "final_account": account * (1 + total_return),
                "benchmark": benchmark,
                "strategy": "topk_dropout_intelligent",
                "risk_metrics": {
                    "annualized_return": annual_return,
                    "max_drawdown": max_drawdown,
                    "sharpe_ratio": sharpe_ratio,
                    "volatility": volatility,
                    "cagr": annual_return,
                    "net_cagr": net_cagr,
                    "calmar_ratio": calmar_ratio,
                    "win_rate": win_rate,
                    "profit_loss_ratio": profit_loss_ratio,
                    "cost_ratio": cost_ratio,
                    "cost_to_profit_ratio": cost_to_profit,
                    "turnover_rate": turnover_rate,
                    "alpha": alpha,
                    "beta": beta,
                },
                "charts": self._generate_topk_backtest_charts(report_df),
            }

            # Ensure max_drawdown is consistent between risk_metrics and charts
            chart_dd = api_result.get("charts", {}).get("max_drawdown_info", {})
            if chart_dd and chart_dd.get("max_drawdown") is not None:
                api_result["risk_metrics"]["max_drawdown"] = chart_dd["max_drawdown"]
                # Recalculate calmar ratio with consistent max_drawdown
                consistent_dd = abs(chart_dd["max_drawdown"])
                if consistent_dd > 0:
                    api_result["risk_metrics"]["calmar_ratio"] = _safe_float(
                        annual_return / consistent_dd
                    )

            return api_result

        except Exception as e:
            self.logger.error(f"TopK backtest execution failed: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {"status": "error", "error": str(e)}

    def _generate_topk_backtest_charts(self, report_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate chart data from TopK backtest results.
        """
        try:
            if report_df.empty:
                return {}

            import numpy as np

            charts: Dict[str, Any] = {}

            # 1. Cumulative returns chart
            cumulative_returns = []
            strategy_cum = 1.0
            bench_cum = 1.0
            for date, row in report_df.iterrows():
                strategy_cum *= 1 + float(row.get("return", 0))
                bench_cum *= 1 + float(row.get("bench", 0))
                cumulative_returns.append(
                    {
                        "date": (
                            str(date.date()) if hasattr(date, "date") else str(date)
                        ),
                        "strategy": round(strategy_cum - 1, 6),
                        "benchmark": round(bench_cum - 1, 6),
                    }
                )
            charts["cumulative_returns"] = cumulative_returns

            # 2. Daily returns distribution
            if "return" in report_df.columns:
                returns = report_df["return"].dropna()
                hist, bin_edges = np.histogram(returns, bins=30)
                distribution_data = []
                for i in range(len(hist)):
                    distribution_data.append(
                        {
                            "bin_start": float(bin_edges[i]),
                            "bin_end": float(bin_edges[i + 1]),
                            "bin_center": float((bin_edges[i] + bin_edges[i + 1]) / 2),
                            "count": int(hist[i]),
                        }
                    )
                charts["return_distribution"] = distribution_data

            # 3. Max drawdown analysis
            if "return" in report_df.columns:
                cumulative = (1 + report_df["return"]).cumprod() - 1
                running_max = (1 + report_df["return"]).cumprod().cummax()
                drawdown = (
                    (1 + report_df["return"]).cumprod() - running_max
                ) / running_max

                max_dd_idx = drawdown.idxmin()
                max_dd_value = float(drawdown.min())

                dd_before_max = drawdown.loc[:max_dd_idx]
                peak_candidates = dd_before_max[dd_before_max == 0]
                if len(peak_candidates) > 0:
                    peak_date = peak_candidates.index[-1]
                else:
                    peak_date = drawdown.index[0]

                peak_value = (
                    float(cumulative.loc[peak_date])
                    if peak_date in cumulative.index
                    else 0
                )
                trough_value = float(cumulative.loc[max_dd_idx])

                after_trough = cumulative.loc[max_dd_idx:]
                recovery_candidates = after_trough[after_trough >= peak_value]
                recovery_date = (
                    str(recovery_candidates.index[0])[:10]
                    if len(recovery_candidates) > 0
                    else None
                )

                drawdown_days = (
                    (max_dd_idx - peak_date).days
                    if hasattr(max_dd_idx - peak_date, "days")
                    else 0
                )

                charts["max_drawdown_info"] = {
                    "max_drawdown": max_dd_value,
                    "max_drawdown_date": str(max_dd_idx)[:10],
                    "peak_date": str(peak_date)[:10],
                    "peak_value": peak_value,
                    "trough_value": trough_value,
                    "recovery_date": recovery_date,
                    "drawdown_days": drawdown_days,
                }

            # 4. Daily returns time series
            if "return" in report_df.columns:
                daily_returns = []
                for date, value in report_df["return"].items():
                    daily_returns.append(
                        {
                            "date": str(date)[:10],
                            "return": float(value),
                        }
                    )
                charts["daily_returns"] = daily_returns

            # 5. Yearly returns
            if "return" in report_df.columns and "bench" in report_df.columns:
                yearly_returns = []
                report_copy = report_df.copy()
                report_copy["year"] = report_copy.index.map(
                    lambda x: x.year if hasattr(x, "year") else int(str(x)[:4])
                )
                for year, group in report_copy.groupby("year"):
                    strategy_ret = float((1 + group["return"]).cumprod().iloc[-1] - 1)
                    benchmark_ret = float((1 + group["bench"]).cumprod().iloc[-1] - 1)
                    yearly_returns.append(
                        {
                            "period": str(year),
                            "strategy_return": strategy_ret,
                            "benchmark_return": benchmark_ret,
                            "excess_return": strategy_ret - benchmark_ret,
                            "trading_days": len(group),
                        }
                    )
                charts["yearly_returns"] = yearly_returns

            # 6. Monthly returns
            if "return" in report_df.columns and "bench" in report_df.columns:
                monthly_returns = []
                report_copy = report_df.copy()
                report_copy["month"] = report_copy.index.map(
                    lambda x: (
                        f"{x.year}-{x.month:02d}" if hasattr(x, "year") else str(x)[:7]
                    )
                )
                for month, group in report_copy.groupby("month"):
                    strategy_ret = float((1 + group["return"]).cumprod().iloc[-1] - 1)
                    benchmark_ret = float((1 + group["bench"]).cumprod().iloc[-1] - 1)
                    monthly_returns.append(
                        {
                            "period": str(month),
                            "strategy_return": strategy_ret,
                            "benchmark_return": benchmark_ret,
                            "excess_return": strategy_ret - benchmark_ret,
                        }
                    )
                charts["monthly_returns"] = monthly_returns

            charts["portfolio_values"] = []

            self.logger.info(f"Generated TopK chart datasets: {list(charts.keys())}")
            return charts

        except Exception as e:
            self.logger.error(f"Failed to generate TopK charts: {e}")
            return {}

    def reset(self) -> Dict[str, Any]:
        """
        Reset Online Serving state (for debugging).

        This clears all state and allows re-initialization.

        Returns:
            Reset result dictionary
        """
        self._online_manager = None
        self._is_initialized = False
        self._last_routine_time = None
        self._initialization_error = None

        self.logger.info("Online Serving state reset")

        return {
            "success": True,
            "message": "Online Serving state reset successfully",
        }


# Singleton instance
_online_serving_service: Optional[OnlineServingService] = None


def get_online_serving_service() -> OnlineServingService:
    """
    Get the singleton OnlineServingService instance.

    Returns:
        OnlineServingService instance
    """
    global _online_serving_service
    if _online_serving_service is None:
        _online_serving_service = OnlineServingService()
    return _online_serving_service
