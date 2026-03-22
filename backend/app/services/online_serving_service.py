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

    def _get_data_frequency(self) -> str:
        """
        Get data frequency for stock selection system.

        Note: Only day-level data is supported in this stock selection system.
        Minute-level data should be handled by a separate timing/execution system.

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
        - Data frequency (day/1min)
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

            # Fail fast if data update failed - do not continue with stale data
            if not data_update_success:
                error_msg = data_update_result.get("error", "Unknown error")
                self.logger.error(f"Data update failed: {error_msg}")
                result["success"] = False
                result["error"] = f"Data update failed: {error_msg}"
                return result

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

            # Step 5: Calculate model metrics
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

            # Step 6: Enhanced Indexing Strategy - Calculate target portfolio
            step_start = time.time()
            enhanced_indexing_result = self._calculate_enhanced_indexing(
                signals, effective_cur_time
            )
            step_duration = time.time() - step_start
            result["steps"].append(
                {
                    "step": "Portfolio Optimization",
                    "success": enhanced_indexing_result.get("success", False),
                    "duration_seconds": round(step_duration, 2),
                    "details": {
                        "description": "Generate target portfolio weights using enhanced indexing strategy",
                        **enhanced_indexing_result.get("summary", {}),
                    },
                }
            )

            # Add target portfolio to result
            if enhanced_indexing_result.get("success"):
                result["target_portfolio"] = enhanced_indexing_result.get(
                    "target_portfolio", []
                )
                # Normalize summary format for frontend compatibility
                raw_summary = enhanced_indexing_result.get("summary", {})
                strategy = enhanced_indexing_result.get("strategy", "enhanced_indexing")

                # Add strategy to top-level result for frontend detection
                result["strategy"] = strategy

                if strategy == "etf_enhanced_indexing":
                    # Add all top-level fields from ETF Enhanced Indexing result
                    result["generated_at"] = enhanced_indexing_result.get(
                        "generated_at", datetime.now().isoformat()
                    )
                    result["trade_date"] = enhanced_indexing_result.get(
                        "trade_date", ""
                    )
                    result["signal_for_date"] = enhanced_indexing_result.get(
                        "signal_for_date", ""
                    )
                    result["total_value"] = enhanced_indexing_result.get(
                        "total_value", 1000000
                    )
                    result["region"] = enhanced_indexing_result.get("region", "cn")
                    result["lot_size"] = enhanced_indexing_result.get("lot_size", 100)
                    result["weights"] = enhanced_indexing_result.get("weights", {})

                    # Convert ETF Enhanced Indexing summary to frontend format
                    result["portfolio_summary"] = {
                        "total_positions": raw_summary.get("total_positions", 10),
                        "etf_positions": raw_summary.get("etf_positions", 1),
                        "stock_positions": raw_summary.get("stock_positions", 9),
                        "buy_count": raw_summary.get("buy_count", 0),
                        "sell_count": raw_summary.get("sell_count", 0),
                        "hold_count": raw_summary.get("hold_count", 0),
                    }
                else:
                    # Legacy Enhanced Indexing format
                    result["portfolio_summary"] = raw_summary

            # Step 7: Export Trading Signals (only if Portfolio Optimization succeeded)
            step_start = time.time()
            signal_export_result = self._export_trading_signals(
                enhanced_indexing_result, effective_cur_time
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

        Supports two strategies:
        1. ETFEnhancedIndexingService (default): 1 ETF + 9 alpha stocks
        2. EnhancedIndexingService (legacy): Full index replication with weight adjustments

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
                self.logger.info(
                    "Calculating target portfolio using ETF Enhanced Indexing strategy..."
                )

                # Calculate target portfolio with ETF + top stocks
                portfolio_data = etf_service.calculate_target_portfolio(
                    signals=signals,
                    trade_date=cur_time,
                )

                # Save portfolio to file
                if portfolio_data.get("positions"):
                    date_str = (
                        cur_time if cur_time else datetime.now().strftime("%Y-%m-%d")
                    )
                    saved_path = etf_service.save_portfolio(portfolio_data, date_str)
                    self.logger.info(f"ETF enhanced portfolio saved to {saved_path}")

                position_count = len(portfolio_data.get("positions", []))
                self.logger.info(
                    f"ETF Enhanced Indexing completed: {position_count} positions "
                    f"(ETF weight: {portfolio_data.get('weights', {}).get('etf_weight', 0):.1%})"
                )

                # Send email notification if enabled
                self._send_etf_portfolio_email(portfolio_data)

                return {
                    "success": True,
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
                    f"Incremental update completed successfully: {result.message}"
                )
                return {
                    "success": True,
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
        Execute backtest using ETFEnhancedIndexingService strategy.

        This method uses the signals from Online Serving (generated by Routine)
        to perform a historical backtest using the ETF Enhanced Indexing strategy.

        The backtest:
        1. Uses signals already generated by Online Serving
        2. For each trading day, uses ETFEnhancedIndexingService to calculate target portfolio
        3. Simulates trading based on portfolio changes
        4. Calculates returns and metrics

        Args:
            benchmark: Benchmark symbol (not used in ETF strategy, kept for API compatibility)
            account: Initial account value (default from config)

        Returns:
            Dictionary with backtest results including daily returns, metrics
        """
        try:
            self.logger.info("Starting ETF Enhanced Indexing backtest...")

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

            # Execute backtest using the signals
            result = self._execute_signal_based_backtest(signals, account)

            if result.get("status") == "error":
                return result

            # Convert result format for API compatibility
            # Qlib metrics + custom metrics
            risk_metrics = {
                # Qlib risk_analysis metrics
                "annualized_return": result.get("annual_return"),
                "max_drawdown": result.get("max_drawdown"),
                "sharpe_ratio": result.get("sharpe_ratio"),
                "volatility": result.get("volatility"),
                # Custom additional metrics
                "calmar_ratio": result.get("calmar_ratio"),
                "win_rate": result.get("win_rate"),
                "profit_loss_ratio": result.get("profit_loss_ratio"),
            }

            # Generate chart data from daily returns
            # Pass Qlib's max_drawdown to ensure consistency
            chart_data = self._generate_etf_backtest_charts(
                result.get("daily_returns", []),
                qlib_max_drawdown=result.get("max_drawdown"),
            )

            api_result = {
                "status": "success",
                "start_time": result.get("start_time"),
                "end_time": result.get("end_time"),
                "data_start_time": result.get("start_time"),
                "data_end_time": result.get("end_time"),
                "freq": "day",
                "trading_days": result.get("trading_days"),
                "signal_count": result.get("trading_days"),  # One signal per day
                "total_return": result.get("total_return"),
                "total_cost": result.get("total_cost"),
                "net_return": result.get("total_return"),  # Cost already deducted
                "final_account": result.get("final_account"),
                "benchmark": benchmark or "ETF",
                "strategy": "etf_enhanced_indexing",
                "risk_metrics": risk_metrics,
                "charts": chart_data,
            }

            self.logger.info(
                f"ETF Backtest completed: {api_result['trading_days']} trading days, "
                f"return={api_result['total_return']:.4f}"
            )
            return api_result

        except Exception as e:
            self.logger.error(f"ETF Backtest failed: {e}")
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
            # Add benchmark index (CSI300) for chart comparison
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

        # Run backtest day by day
        prev_portfolio_value = account

        for i, date in enumerate(
            unique_dates[:-1]
        ):  # Skip last day (no next day return)
            next_date = unique_dates[i + 1]

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

            # Calculate target portfolio using ETF service logic
            try:
                etf_weight, alpha_weight, _ = etf_service.calculate_dynamic_weights(
                    signal_dict
                )

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

            except Exception as e:
                self.logger.warning(f"Failed to calculate weights for {date}: {e}")
                continue

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
                    # Fallback to small positive bias if index not available
                    daily_return += etf_weight * 0.0001

            except Exception as e:
                self.logger.warning(f"Error calculating return for {date}: {e}")

            # Apply trading costs (simplified)
            day_cost = (
                portfolio_value * (open_cost + close_cost) * 0.1
            )  # Assume 10% turnover
            total_cost += day_cost

            # Update portfolio value
            portfolio_value = portfolio_value * (1 + daily_return) - day_cost

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
                    "daily_return": daily_return,
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
        total_return = (portfolio_value - account) / account
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
            annual_return = (1 + total_return) ** annual_factor - 1
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

        # Log metrics for debugging
        self.logger.info(
            f"Backtest metrics: total_return={total_return:.4f}, "
            f"annual_return={annual_return:.4f}, volatility={volatility:.4f}, "
            f"sharpe={sharpe_ratio:.4f}, max_dd={max_drawdown:.4f}, "
            f"calmar={calmar_ratio:.4f}, win_rate={win_rate:.4f}, pl_ratio={profit_loss_ratio:.4f}"
        )

        return {
            "status": "success",
            "start_time": str(unique_dates[0].date()),
            "end_time": str(unique_dates[-1].date()),
            "trading_days": trading_days,
            "total_return": float(total_return),
            "total_cost": float(total_cost),
            "final_account": float(portfolio_value),
            # Qlib risk_analysis metrics
            "annual_return": float(annual_return),
            "volatility": float(volatility),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            # Custom additional metrics
            "calmar_ratio": float(calmar_ratio),
            "win_rate": float(win_rate),
            "profit_loss_ratio": float(profit_loss_ratio),
            "daily_returns": daily_returns,
        }

    def _generate_etf_backtest_charts(
        self, daily_returns: list, qlib_max_drawdown: float = None
    ) -> Dict[str, Any]:
        """Generate chart data from ETF backtest daily returns.

        Args:
            daily_returns: List of daily return records
            qlib_max_drawdown: Max drawdown from Qlib's risk_analysis (for consistency)
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

            for row in daily_returns:
                daily_ret = row.get("daily_return", 0)
                benchmark_ret = row.get("benchmark_return", 0)
                cum_return *= 1 + daily_ret
                cum_benchmark *= 1 + benchmark_ret
                cum_return_pct = float(cum_return - 1)  # Convert to percentage
                cum_benchmark_pct = float(cum_benchmark - 1)

                # Track current peak
                if cum_return > max_cum_return:
                    max_cum_return = cum_return
                    current_peak_date = row.get("date")
                    current_peak_value = cum_return_pct

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
                    "strategy": cum_return_pct,  # Frontend expects "strategy" key
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

            self.logger.info(
                f"Generated chart data: {len(cumulative_returns)} points, "
                f"max_drawdown={max_drawdown:.4f}"
            )

            return {
                "cumulative_returns": cumulative_returns,
                "portfolio_values": portfolio_values,
                "max_drawdown_info": max_drawdown_info,
            }
        except Exception as e:
            self.logger.error(f"Failed to generate chart data: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return {}

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
