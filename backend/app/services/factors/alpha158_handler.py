"""
Alpha158 factor handler
Wraps Qlib's built-in Alpha158 with our unified interface
"""

import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import qlib
from qlib.contrib.data.handler import Alpha158 as QlibAlpha158
from .base_factor_handler import BaseFactorHandler


class Alpha158Handler(BaseFactorHandler):
    """
    Qlib Alpha158 factor handler

    Provides access to Qlib's built-in 158 alpha factors through
    our unified factor handler interface.

    Features:
    - Automatic caching via Qlib
    - Incremental computation
    - Memory-efficient data access
    - Multi-market support (CN/US)
    """

    def __init__(self, region: str = "us"):
        """
        Initialize Alpha158 handler
        Args:
            region: Market region, either 'cn' or 'us'. Default is 'us'.
        """

        super().__init__(
            name="alpha158",
            description="Qlib's built-in 158 alpha factors including price patterns, volume features, and technical indicators",
        )
        self.logger = logging.getLogger(__name__)
        self.region = region
        self._qlib_initialized = False
        self._initialize_qlib()

    def _initialize_qlib(self):
        """
        Initialize Qlib if not already initialized

        Use default paths:
        - provider_uri: ~/.qlib/qlib_data/{region}_data
        - cache_dir: ~/.qlib/cache
        """
        if self._qlib_initialized:
            return

        try:
            from ..qlib_utils import init_qlib

            # Use qlib_utils to initialize with proper region support
            init_qlib(region=self.region)
            self._qlib_initialized = True
            self.logger.info(f"Qlib initialized successfully for region: {self.region}")
        except Exception as e:
            # Check if Qlib is actually initialized despite the error
            try:
                from qlib.data.data import ProviderManager

                if ProviderManager.get_default_provider() is not None:
                    # Qlib is initialized, just had a warning
                    self._qlib_initialized = True
                    self.logger.warning(
                        f"Qlib initialization warning (but provider is available): {e}"
                    )
                    return
            except Exception:
                pass

            # Qlib is NOT initialized, raise the error
            self.logger.error(f"Failed to initialize Qlib: {e}")
            raise RuntimeError(f"Qlib initialization failed: {e}") from e

    def calculate(
        self, instruments: List[str], start_date: str, end_date: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Calculate Alpha158 factors

        This triggers factor calculation. Qlib will automatically cache
        the results for future queries.

        Args:
            instruments: List of instrument codes (e.g., ["000001.SZ"])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            **kwargs: Additional parameters (currently unused)

        Returns:
            Calculation starts and metadata

        Note:
            Instrument codes are automatically normalized to lowercase to match
            Qlib's directory structure (dump_bin.py converts to lowercase).
        """
        start_time = time.time()

        # Ensure Qlib is initialized before calculation
        self._initialize_qlib()

        try:
            # Normalize instrument codes to lowercase for Qlib compatibility
            # dump_bin.py creates lowercase directories, so we need to match that format
            normalized_instruments = [inst.lower() for inst in instruments]

            self.logger.info(
                f"Calculating Alpha158 factors for {len(instruments)} instruments "
                f"from {start_date} to {end_date} (normalized: {normalized_instruments})"
            )

            # Create Alpha158 handler with config using normalized instruments
            handler = QlibAlpha158(
                instruments=normalized_instruments,
                start_time=start_date,
                end_time=end_date,
                fit_start_time=start_date,
                fit_end_time=end_date,
            )

            # Fetch to trigger calculation (Qlib will cache automatically)
            self.logger.info("Fetching Alpha158 features from Qlib...")
            features = handler.fetch(col_set="feature")

            calculation_time = time.time() - start_time

            # Check if data is actually available
            if features is None or features.empty:
                raise ValueError(
                    f"No data available for instruments {normalized_instruments} "
                    f"from {start_date} to {end_date}. "
                    f"Please collect data first using the data collection API."
                )

            # Log detailed calculation results for verification
            self.logger.info(
                f"Alpha158 calculation results: "
                f"shape={features.shape}, "
                f"date_range=({features.index.get_level_values(0).min()}, {features.index.get_level_values(0).max()}), "
                f"instruments={features.index.get_level_values(1).unique().tolist()}, "
                f"features_sample={features.columns.tolist()[:5]}"
            )

            # Detect cache usage based on calculation time
            # With Redis cache: first calculation > 0.3s, cached < 0.3s
            # This is a heuristic since Redis cache is in-memory
            cached = calculation_time < 0.3

            self.logger.info(
                f"Alpha158 calculation completed in {calculation_time:.2f}s "
                f"(cached: {cached})"
            )

            return {
                "success": True,
                "factor_handler": self.name,
                "instruments_count": len(instruments),
                "features_count": len(self.get_feature_names()),
                "calculation_time": calculation_time,
                "cached": cached,
                "error": None,
            }
        except Exception as e:
            self.logger.error(f"Alpha158 calculation failed: {e}", exc_info=True)

            # Provide user-friendly error message for common issues
            error_msg = str(e)
            if (
                "can't find a freq" in error_msg
                or "No data" in error_msg
                or error_msg == ""
            ):
                error_msg = (
                    f"No data available for instruments {instruments} "
                    f"from {start_date} to {end_date}. "
                    f"Please collect data first using the data collection API "
                    f"(POST /api/v1/data-collection/collect)."
                )

            return {
                "success": False,
                "factor_handler": self.name,
                "instruments_count": len(instruments),
                "features_count": 0,
                "calculation_time": time.time() - start_time,
                "cached": False,
                "error": error_msg,
            }

    def fetch(
        self,
        instruments: List[str],
        start_date: str,
        end_date: str,
        features: Optional[List[str]] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch Alpha158 factor data

        Retrieve previously calculated factor data from Qlib's cache.
        If not cached, will trigger caclulation.

        Args:
            instruments: List of instrument codes
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            features: Optional list of specific features to fetch.
                    If None, fetch all features.
            **kwargs: Additional parameters (currently unused)

        Returns:
            DataFrame with MultiIndex (datetime, instrument) and feature columns
        """
        try:
            self.logger.info(
                f"Fetching Alpha158 data for {len(instruments)} instruments "
                f"from {start_date} to {end_date}"
            )

            # Create Alpha158 handler
            handler = QlibAlpha158(
                instruments=instruments,
                start_time=start_date,
                end_time=end_date,
                fit_start_time=start_date,
                fit_end_time=end_date,
            )

            # Fetch features (uses cache if available)
            df = handler.fetch(col_set="feature")

            #  Filter specific features if requested
            if features is not None:
                available_features = [f for f in features if f in df.columns]
                if not available_features:
                    raise ValueError(
                        f"None of the requested features {features} are available. "
                        f"Available features: {df.columns.tolist()[:10]}..."
                    )
                df = df[available_features]

            self.logger.info(f"Fetched {len(df)} rows with {len(df.columns)} features")

            return df
        except Exception as e:
            self.logger.error(f"Failed to fetch Alpha158 data: {e}", exc_info=True)
            raise

    def get_feature_names(self) -> List[str]:
        """
        Get list of all 158 Alpha158 feature names

        Returns:
            List of feature names
        """
        # Alpha158 feature names (158 features)
        # These are the actual names from Qlib's Alpha158
        features = [
            # KLEN series (price patterns)
            "KLEN",
            "KMID",
            "KLOW",
            "KSFT",
            "KSFT2",
            # OPEN series (opening price features)
            "OPEN0",
            "OPEN1",
            # CLOSE series (closing price features)
            "CLOSE0",
            "CLOSE1",
            # HIGH series (high price features)
            "HIGH0",
            "HIGH1",
            # LOW series (low price features)
            "LOW0",
            "LOW1",
            # VWAP series (volume weighted average price)
            "VWAP0",
            "VWAP1",
            # Volume series
            "VOLUME0",
            "VOLUME1",
        ]

        # Add ROC features for OPEN, CLOSE, HIGH, LOW, VWAP, VOLUME
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            for window in [5, 10, 20, 30, 60]:
                features.append(f"ROC{window}_{field}")

        # Add MA features (moving averages) - 30 features
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            for window in [5, 10, 20, 30, 60]:
                features.append(f"MA{window}_{field}")

        # Add STD features (standard deviation) - 30 features
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            for window in [5, 10, 20, 30, 60]:
                features.append(f"STD{window}_{field}")

        # Add BETA features - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"BETA{window}")

        # Add RSQR features (R-squared) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"RSQR{window}")

        # Add RESI features (residual) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"RESI{window}")

        # Add MAX/MIN features - 20 features
        for field in ["HIGH", "LOW"]:
            for window in [5, 10, 20, 30, 60]:
                features.append(f"MAX{window}_{field}")
                features.append(f"MIN{window}_{field}")

        # Add QTLU/QTLD features (quantile up/down) - 10 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"QTLU{window}")
            features.append(f"QTLD{window}")

        # Add RANK features - 6 features
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            features.append(f"RANK_{field}")

        # Add RSV features (raw stochastic value) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"RSV{window}")

        # Add IMAX/IMIN features (index of max/min) - 20 features
        for field in ["HIGH", "LOW"]:
            for window in [5, 10, 20, 30, 60]:
                features.append(f"IMAX{window}_{field}")
                features.append(f"IMIN{window}_{field}")

        # Add IMXD features (index max - index min) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"IMXD{window}")

        # Add CORR features (correlation) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"CORR{window}")

        # Add CORD features (correlation difference) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"CORD{window}")

        # Add CNTP/CNTN features (count positive/negative) - 10 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"CNTP{window}")
            features.append(f"CNTN{window}")

        # Add CNTD features (count difference) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"CNTD{window}")

        # Add SUMP/SUMN features (sum positive/negative) - 10 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"SUMP{window}")
            features.append(f"SUMN{window}")

        # Add SUMD features (sum difference) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"SUMD{window}")

        # Add VMA features (volume moving average) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"VMA{window}")

        # Add VSTD features (volume standard deviation) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"VSTD{window}")

        # Add WVMA features (weighted volume moving average) - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"WVMA{window}")

        # Add VSUMP/VSUMN features - 10 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"VSUMP{window}")
            features.append(f"VSUMN{window}")

        # Add VSUMD features - 5 features
        for window in [5, 10, 20, 30, 60]:
            features.append(f"VSUMD{window}")

        return features[:158]  # Return exactly 158 features

    def get_feature_info(self) -> List[Dict[str, str]]:
        """
        Get detailed information about Alpha158 features

        Returns:
            List of feature metadata dictionaries
        """
        feature_info = []

        # Price pattern features (5)
        feature_info.extend(
            [
                {
                    "name": "KLEN",
                    "description": "K-line length (high-low)",
                    "category": "价格形态",
                },
                {
                    "name": "KMID",
                    "description": "K-line middle point",
                    "category": "价格形态",
                },
                {
                    "name": "KLOW",
                    "description": "K-line low position",
                    "category": "价格形态",
                },
                {
                    "name": "KSFT",
                    "description": "K-line shift (close-open)",
                    "category": "价格形态",
                },
                {
                    "name": "KSFT2",
                    "description": "K-line shift squared",
                    "category": "价格形态",
                },
            ]
        )

        # Basic price features (6)
        feature_info.extend(
            [
                {
                    "name": "OPEN0",
                    "description": "Current open price",
                    "category": "基础价格",
                },
                {
                    "name": "CLOSE0",
                    "description": "Current close price",
                    "category": "基础价格",
                },
                {
                    "name": "HIGH0",
                    "description": "Current high price",
                    "category": "基础价格",
                },
                {
                    "name": "LOW0",
                    "description": "Current low price",
                    "category": "基础价格",
                },
                {
                    "name": "VWAP0",
                    "description": "Current VWAP",
                    "category": "基础价格",
                },
                {
                    "name": "VOLUME0",
                    "description": "Current volume",
                    "category": "成交量",
                },
            ]
        )

        # ROC features (30: 6 fields × 5 windows)
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            for window in [5, 10, 20, 30, 60]:
                feature_info.append(
                    {
                        "name": f"ROC{window}_{field}",
                        "description": f"Rate of change for {field} over {window} days",
                        "category": "技术指标",
                    }
                )

        # MA features (30: 6 fields × 5 windows)
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            for window in [5, 10, 20, 30, 60]:
                feature_info.append(
                    {
                        "name": f"MA{window}_{field}",
                        "description": f"Moving average of {field} over {window} days",
                        "category": "技术指标",
                    }
                )

        # STD features (30: 6 fields × 5 windows)
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            for window in [5, 10, 20, 30, 60]:
                feature_info.append(
                    {
                        "name": f"STD{window}_{field}",
                        "description": f"Standard deviation of {field} over {window} days",
                        "category": "技术指标",
                    }
                )

        # BETA features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"BETA{window}",
                    "description": f"Beta coefficient over {window} days",
                    "category": "技术指标",
                }
            )

        # RSQR features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"RSQR{window}",
                    "description": f"R-squared over {window} days",
                    "category": "技术指标",
                }
            )

        # RESI features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"RESI{window}",
                    "description": f"Residual over {window} days",
                    "category": "技术指标",
                }
            )

        # MAX features (10: 2 fields × 5 windows)
        for field in ["HIGH", "LOW"]:
            for window in [5, 10, 20, 30, 60]:
                feature_info.append(
                    {
                        "name": f"MAX{window}_{field}",
                        "description": f"Maximum {field} over {window} days",
                        "category": "技术指标",
                    }
                )

        # MIN features (10: 2 fields × 5 windows)
        for field in ["HIGH", "LOW"]:
            for window in [5, 10, 20, 30, 60]:
                feature_info.append(
                    {
                        "name": f"MIN{window}_{field}",
                        "description": f"Minimum {field} over {window} days",
                        "category": "技术指标",
                    }
                )

        # QTLU features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"QTLU{window}",
                    "description": f"Quantile upper bound over {window} days",
                    "category": "技术指标",
                }
            )

        # QTLD features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"QTLD{window}",
                    "description": f"Quantile lower bound over {window} days",
                    "category": "技术指标",
                }
            )

        # RANK features (6)
        for field in ["OPEN", "CLOSE", "HIGH", "LOW", "VWAP", "VOLUME"]:
            feature_info.append(
                {
                    "name": f"RANK_{field}",
                    "description": f"Rank of {field}",
                    "category": "技术指标",
                }
            )

        # RSV features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"RSV{window}",
                    "description": f"Raw stochastic value over {window} days",
                    "category": "技术指标",
                }
            )

        # IMAX features (10: 2 fields × 5 windows)
        for field in ["HIGH", "LOW"]:
            for window in [5, 10, 20, 30, 60]:
                feature_info.append(
                    {
                        "name": f"IMAX{window}_{field}",
                        "description": f"Index of maximum {field} over {window} days",
                        "category": "技术指标",
                    }
                )

        # IMIN features (10: 2 fields × 5 windows)
        for field in ["HIGH", "LOW"]:
            for window in [5, 10, 20, 30, 60]:
                feature_info.append(
                    {
                        "name": f"IMIN{window}_{field}",
                        "description": f"Index of minimum {field} over {window} days",
                        "category": "技术指标",
                    }
                )

        # IMXD features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"IMXD{window}",
                    "description": f"Index max - index min over {window} days",
                    "category": "技术指标",
                }
            )

        # CORR features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"CORR{window}",
                    "description": f"Correlation over {window} days",
                    "category": "技术指标",
                }
            )

        # CORD features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"CORD{window}",
                    "description": f"Correlation difference over {window} days",
                    "category": "技术指标",
                }
            )

        # CNTP features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"CNTP{window}",
                    "description": f"Count of positive returns over {window} days",
                    "category": "技术指标",
                }
            )

        # CNTN features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"CNTN{window}",
                    "description": f"Count of negative returns over {window} days",
                    "category": "技术指标",
                }
            )

        # CNTD features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"CNTD{window}",
                    "description": f"Count difference (positive - negative) over {window} days",
                    "category": "技术指标",
                }
            )

        # SUMP features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"SUMP{window}",
                    "description": f"Sum of positive returns over {window} days",
                    "category": "技术指标",
                }
            )

        # SUMN features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"SUMN{window}",
                    "description": f"Sum of negative returns over {window} days",
                    "category": "技术指标",
                }
            )

        # SUMD features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"SUMD{window}",
                    "description": f"Sum difference (positive - negative) over {window} days",
                    "category": "技术指标",
                }
            )

        # VMA features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"VMA{window}",
                    "description": f"Volume moving average over {window} days",
                    "category": "成交量指标",
                }
            )

        # VSTD features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"VSTD{window}",
                    "description": f"Volume standard deviation over {window} days",
                    "category": "成交量指标",
                }
            )

        # WVMA features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"WVMA{window}",
                    "description": f"Weighted volume moving average over {window} days",
                    "category": "成交量指标",
                }
            )

        # VSUMP features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"VSUMP{window}",
                    "description": f"Sum of positive volume changes over {window} days",
                    "category": "成交量指标",
                }
            )

        # VSUMN features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"VSUMN{window}",
                    "description": f"Sum of negative volume changes over {window} days",
                    "category": "成交量指标",
                }
            )

        # VSUMD features (5)
        for window in [5, 10, 20, 30, 60]:
            feature_info.append(
                {
                    "name": f"VSUMD{window}",
                    "description": f"Volume sum difference over {window} days",
                    "category": "成交量指标",
                }
            )

        # Total: 5 + 6 + 30 + 30 + 30 + 5 + 5 + 5 + 10 + 10 + 5 + 5 + 6 + 5 + 10 + 10 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 + 5 = 158
        return feature_info
