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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.config.qlib import qlib_config
from app.services.qlib_init_service import get_qlib_init_service
from app.services.enhanced_indexing_service import get_enhanced_indexing_service

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

    def __init__(self):
        """Initialize the Online Serving service."""
        self._online_manager = None
        self._is_initialized: bool = False
        self._freq: str = "day"
        self._last_routine_time: Optional[datetime] = None
        self._initialization_error: Optional[str] = None
        self._experiment_name: str = qlib_config.experiment_name
        self.logger = logger

    @property
    def is_initialized(self) -> bool:
        """Check if OnlineManager is initialized."""
        return self._is_initialized and self._online_manager is not None

    def _detect_data_frequency(self) -> str:
        """
        Detect data frequency based on available bin data.

        Returns:
            "day" or "1min" based on available data
        """
        # Use frequency from configuration
        freq = qlib_config.freq
        self.logger.info(f"Using frequency from config: freq='{freq}'")
        return freq

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
        - Data frequency (day/1min)
        - Time range (from actual data)
        - Instruments (all available stocks)

        Returns:
            Task template dictionary
        """
        # Detect frequency
        self._freq = self._detect_data_frequency()

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

    def routine(self, cur_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute daily routine (main entry point).

        This method:
        1. Auto-initializes if not yet initialized
        2. Updates data incrementally
        3. Calls OnlineManager.routine() - checks training, updates models, generates signals
        4. Returns execution result with step timing

        Args:
            cur_time: Current time string (YYYY-MM-DD), None for latest

        Returns:
            Execution result dictionary with step timing
        """
        import time

        routine_start = time.time()
        result = {
            "success": False,
            "cur_time": cur_time,
            "executed_at": datetime.now().isoformat(),
            "steps": [],
            "total_duration_seconds": 0,
        }

        try:
            # Step 1: Auto-initialize if needed
            if not self.is_initialized:
                step_start = time.time()
                self.logger.info("Online Serving not initialized, auto-initializing...")
                init_result = self._auto_init()
                step_duration = time.time() - step_start
                result["steps"].append(
                    {
                        "step": "initialization",
                        "success": True,
                        "duration_seconds": round(step_duration, 2),
                        "details": init_result,
                    }
                )

            # Step 2: Update data incrementally
            step_start = time.time()
            self.logger.info("Updating data incrementally...")
            data_update_result = self._update_data_incrementally()
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "data_update",
                    "success": data_update_result.get("success", False),
                    "duration_seconds": round(step_duration, 2),
                    "details": data_update_result,
                }
            )

            # Step 3: Execute OnlineManager routine
            step_start = time.time()

            # Use latest data date if cur_time is None or invalid
            effective_cur_time = cur_time
            if effective_cur_time is None:
                # Get latest date from data
                effective_cur_time = self._get_latest_data_date()
                self.logger.info(
                    f"cur_time not provided, using latest data date: {effective_cur_time}"
                )
            else:
                # Validate cur_time - if it's earlier than data range, use latest data date
                latest_data_date = self._get_latest_data_date()
                if latest_data_date and effective_cur_time < latest_data_date:
                    self.logger.warning(
                        f"Provided cur_time {effective_cur_time} is earlier than latest data date {latest_data_date}, "
                        f"using latest data date instead"
                    )
                    effective_cur_time = latest_data_date

            self.logger.info(
                f"Executing OnlineManager routine with cur_time={effective_cur_time}..."
            )
            self._online_manager.routine(cur_time=effective_cur_time)

            # Re-prepare signals with online-only filter to fix the issue where
            # offline recorders' predictions override online recorders' predictions
            self._prepare_signals_with_online_filter()

            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "online_manager_routine",
                    "success": True,
                    "duration_seconds": round(step_duration, 2),
                    "details": {"message": "OnlineManager routine completed"},
                }
            )

            # Step 4: Get signals (for logging/verification)
            step_start = time.time()
            signals = self._online_manager.get_signals()
            signal_count = len(signals) if signals is not None else 0
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "signal_generation",
                    "success": True,
                    "duration_seconds": round(step_duration, 2),
                    "details": {"signal_count": signal_count},
                }
            )

            # Step 5: Calculate model metrics
            step_start = time.time()
            metrics_result = self._calculate_model_metrics(signals)
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "model_metrics_calculation",
                    "success": metrics_result.get("success", False),
                    "duration_seconds": round(step_duration, 2),
                    "details": metrics_result,
                }
            )

            # Step 6: Enhanced Indexing Strategy - Calculate target portfolio
            step_start = time.time()
            enhanced_indexing_result = self._calculate_enhanced_indexing(
                signals, effective_cur_time
            )
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "enhanced_indexing",
                    "success": enhanced_indexing_result.get("success", False),
                    "duration_seconds": round(step_duration, 2),
                    "details": enhanced_indexing_result.get("summary", {}),
                }
            )

            # Add target portfolio to result
            if enhanced_indexing_result.get("success"):
                result["target_portfolio"] = enhanced_indexing_result.get(
                    "target_portfolio", []
                )
                result["portfolio_summary"] = enhanced_indexing_result.get(
                    "summary", {}
                )

            self._last_routine_time = datetime.now()
            result["success"] = True
            result["message"] = "Routine completed successfully"
            result["total_duration_seconds"] = round(time.time() - routine_start, 2)

            self.logger.info(
                f"Routine completed successfully, generated {signal_count} signals"
            )

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["total_duration_seconds"] = round(time.time() - routine_start, 2)
            self.logger.error(f"Routine failed: {e}")

        return result

    def _calculate_enhanced_indexing(
        self, signals: pd.DataFrame, cur_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate target portfolio using enhanced indexing strategy.

        Args:
            signals: Model prediction signals DataFrame
            cur_time: Current time string for date reference

        Returns:
            Dict containing target_portfolio, summary, and success status
        """
        try:
            enhanced_indexing_service = get_enhanced_indexing_service()

            # Check if enhanced indexing is enabled
            if not enhanced_indexing_service.enabled:
                self.logger.info("Enhanced indexing is disabled, skipping")
                return {
                    "success": True,
                    "target_portfolio": [],
                    "summary": {
                        "enabled": False,
                        "message": "Enhanced indexing is disabled",
                    },
                }

            # Calculate target portfolio
            self.logger.info(
                "Calculating target portfolio using enhanced indexing strategy..."
            )
            portfolio_data = enhanced_indexing_service.calculate_target_portfolio(
                signals=signals,
                date=cur_time,
            )

            # Save portfolio to file
            if portfolio_data.get("target_portfolio"):
                date_str = cur_time if cur_time else datetime.now().strftime("%Y-%m-%d")
                saved_path = enhanced_indexing_service.save_portfolio(
                    portfolio_data, date_str
                )
                self.logger.info(f"Target portfolio saved to {saved_path}")

            portfolio_count = len(portfolio_data.get("target_portfolio", []))
            self.logger.info(
                f"Enhanced indexing completed: {portfolio_count} positions"
            )

            return {
                "success": True,
                "target_portfolio": portfolio_data.get("target_portfolio", []),
                "summary": portfolio_data.get("summary", {}),
            }

        except Exception as e:
            self.logger.error(f"Enhanced indexing calculation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "target_portfolio": [],
                "summary": {},
            }

    def _update_data_incrementally(self) -> Dict[str, Any]:
        """
        Update data incrementally or download default data if none exists.

        Logic:
        1. If bin data exists: perform incremental update on existing data
        2. If no data exists: download CSI300 daily data (past 1 year) as default

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

            # Get interval based on freq
            interval = "1d" if qlib_config.freq == "day" else "1m"

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

            if result.status == "started":
                self.logger.info(f"Data download started successfully")
                return {
                    "success": True,
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
                    "error": f"Download failed: {result.message}",
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
            interval = "1d" if qlib_config.freq == "day" else "1m"

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

            return {
                "success": True,
                "message": "Incremental update completed",
                "task_id": result.task_id,
                "stock_pool": stock_pool,
                "freq": qlib_config.freq,
                "interval": interval,
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
        topk: Optional[int] = None,
        n_drop: Optional[int] = None,
        account: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute backtest using signals from OnlineManager.

        This method:
        1. Auto-initializes OnlineManager if not initialized (loads models from MongoDB)
        2. Gets signals from OnlineManager (ensemble of all rolling-trained models)
        3. Executes backtest using the signals with TopkDropout strategy

        The signals are generated by multiple rolling-trained models, each responsible
        for a specific time window. OnlineManager handles the ensemble logic.

        Args:
            benchmark: Benchmark symbol for comparison (default: SH000300)
            topk: Number of stocks to hold (default: 50)
            n_drop: Number of stocks to drop each day (default: 5)
            account: Initial account value (default: 100000000)

        Returns:
            Dictionary with backtest results
        """
        import pandas as pd
        from qlib.contrib.strategy import TopkDropoutStrategy
        from qlib.backtest import backtest as backtest_func
        from qlib.backtest.executor import SimulatorExecutor
        from qlib.utils.time import Freq

        # Default values
        benchmark = benchmark or "SH000300"
        topk = topk or 50
        n_drop = n_drop or 5
        account = account or 100000000

        try:
            # Ensure Qlib is initialized
            if not self._ensure_qlib_initialized():
                return {
                    "status": "error",
                    "error": "Failed to initialize Qlib",
                }

            # Detect frequency
            freq = self._detect_data_frequency()
            self.logger.info(f"Backtest using freq: {freq}")

            # Step 1: Auto-initialize OnlineManager if not initialized
            # This loads trained models from MongoDB
            if not self.is_initialized:
                self.logger.info("Auto-initializing OnlineManager for backtest...")
                init_result = self._auto_init()
                if not init_result.get("success"):
                    return {
                        "status": "error",
                        "error": f"Failed to initialize OnlineManager: {init_result.get('error', 'Unknown error')}",
                    }

            # Step 2: Get signals from OnlineManager
            # OnlineManager handles multi-model ensemble and generates signals for all time periods
            pred = self._online_manager.get_signals()
            if pred is None or len(pred) == 0:
                return {
                    "status": "error",
                    "error": "No signals available. OnlineManager may not have trained models.",
                }

            self.logger.info(
                f"Using {len(pred)} signals from OnlineManager for backtest"
            )

            # Step 3: Get time range from predictions
            dt_values = pred.index.get_level_values("datetime")
            signal_start = dt_values.min()
            signal_end = dt_values.max()

            self.logger.info(
                f"Signal date range: {signal_start} to {signal_end}, "
                f"unique dates: {len(dt_values.unique())}"
            )

            bt_start_time = str(signal_start)[:10]
            # Shift back by 1 day because backtest needs next day's return
            if freq == "day":
                bt_end_time = str(signal_end - pd.Timedelta(days=1))[:10]
            else:
                bt_end_time = str(signal_end - pd.Timedelta(minutes=1))

            self.logger.info(f"Backtest period: {bt_start_time} to {bt_end_time}")

            # Step 4: Create strategy with predictions as signals
            strategy = TopkDropoutStrategy(
                signal=pred,
                topk=topk,
                n_drop=n_drop,
            )

            # Exchange configuration
            exchange_kwargs = {
                "freq": freq,
                "limit_threshold": 0.095,
                "deal_price": "close",
                "open_cost": 0.0003,
                "close_cost": 0.0013,
                "min_cost": 5,
            }

            # Create executor
            executor_config = {
                "time_per_step": freq,
                "generate_portfolio_metrics": True,
            }
            executor = SimulatorExecutor(**executor_config)

            # Step 7: Execute backtest
            portfolio_metric_dict, indicator_dict = backtest_func(
                start_time=bt_start_time,
                end_time=bt_end_time,
                strategy=strategy,
                executor=executor,
                account=account,
                benchmark=benchmark,
                exchange_kwargs=exchange_kwargs,
            )

            # Extract report
            analysis_freq = "{0}{1}".format(*Freq.parse(freq))
            report_df, positions = portfolio_metric_dict.get(analysis_freq)

            # Calculate basic metrics
            total_return = (
                report_df["return"].sum() if "return" in report_df.columns else 0
            )
            total_cost = report_df["cost"].sum() if "cost" in report_df.columns else 0

            # Calculate risk metrics using Qlib's risk_analysis
            risk_metrics = self._calculate_risk_metrics(report_df, freq)

            # Generate chart data
            chart_data = self._generate_backtest_charts(report_df, benchmark)

            result = {
                "status": "success",
                "start_time": bt_start_time,
                "end_time": bt_end_time,
                "freq": freq,
                "trading_days": len(report_df),
                "signal_count": len(pred),
                "total_return": float(total_return),
                "total_cost": float(total_cost),
                "net_return": float(total_return - total_cost),
                "final_account": (
                    float(report_df["account"].iloc[-1])
                    if "account" in report_df.columns
                    else account
                ),
                "topk": topk,
                "n_drop": n_drop,
                "benchmark": benchmark,
                # Risk metrics
                "risk_metrics": risk_metrics,
                # Chart data
                "charts": chart_data,
            }

            self.logger.info(
                f"Backtest completed: {result['trading_days']} trading days, "
                f"return={result['total_return']:.4f}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

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
                status["signal_count"] = len(signals) if signals is not None else 0
            except Exception as e:
                status["signal_count"] = 0

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

                return {"start_date": start_str, "end_date": end_str}
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
            freq: Data frequency ('day' or '1min')

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
