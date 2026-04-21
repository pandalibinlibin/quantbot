import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)

    # Relationship to DataSource
    data_sources: list["DataSource"] = Relationship(back_populates="creator")

    # Relationship to Factor
    factors: list["Factor"] = Relationship(back_populates="creator")

    # Relationship to Model
    models: list["MLModel"] = Relationship(back_populates="creator")

    # Relationship to Strategy
    strategies: list["Strategy"] = Relationship(back_populates="creator")

    # Relationship to ModelTraining
    model_trainings: list["ModelTraining"] = Relationship(back_populates="creator")

    # Relationship to Backtest
    backtests: list["Backtest"] = Relationship(back_populates="creator")


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# ===============================================================
# Quantitative Finance Models
# ===============================================================

from enum import Enum


class DataSourceType(str, Enum):
    """Enumeration of supported data source types.

    - TUSHARE: A-share (China) market data
    - EOD: US stock market data (EOD Historical Data)
    - LOCAL_FILE: Local file data source
    """

    TUSHARE = "tushare"
    EOD = "eod"
    LOCAL_FILE = "local_file"


class DataSourceStatus(str, Enum):
    """Enumeration of data source status"""

    ACTIVE = "active"
    INACTIVE = "inactive"


# Shared properties for DataSource
class DataSourceBase(SQLModel):
    name: str = Field(max_length=100, description="Data source name")
    data_source_type: DataSourceType = Field(description="Type of data source")
    description: str | None = Field(
        default=None, max_length=500, description="Data source description"
    )
    config: str = Field(
        default="{}", description="Data source configuration (JSON string)"
    )
    status: DataSourceStatus = Field(
        default=DataSourceStatus.ACTIVE, description="Data source status"
    )
    last_update: datetime | None = Field(
        default=None, description="Last successful data update time"
    )


# Properties to receive via API on creation
class DataSourceCreate(DataSourceBase):
    pass


# Properties to receive via API on update
class DataSourceUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    config: str | None = Field(default=None)
    status: DataSourceStatus | None = Field(default=None)


# Database model for DataSource
class DataSource(DataSourceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: uuid.UUID = Field(foreign_key="user.id")

    # Relationship back to User
    creator: "User" = Relationship(back_populates="data_sources")


# Properties to return via API
class DataSourcePublic(DataSourceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID


# ====================================================================
# Factor Model
# ====================================================================
class FactorCategory(str, Enum):
    """Enumeration of factor categories"""

    TECHNICAL = "technical"
    PRICE_VOLUME = "price_volume"
    FUNDAMENTAL = "fundamental"
    CUSTOM = "custom"


class FactorStatus(str, Enum):
    """Enumeration of factor status"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class FactorType(str, Enum):
    """Enumeration of factor types - distinguishes features from labels"""

    FEATURE = "feature"  # Used as model input (X)
    LABEL = "label"  # Used as prediction target (Y)


class ComputationStatus(str, Enum):
    """Enumeration of factor computation status"""

    PENDING = "pending"
    COMPUTING = "computing"
    COMPLETED = "completed"
    FAILED = "failed"


# Shared properties for Factor
class FactorBase(SQLModel):
    name: str = Field(max_length=100, description="Factor name")
    expression: str = Field(description="Factor expression in Qlib format")
    description: str | None = Field(
        default=None, max_length=500, description="Factor description"
    )
    factor_type: FactorType = Field(
        default=FactorType.FEATURE, description="Factor type: feature (X) or label (Y)"
    )
    status: FactorStatus = Field(
        default=FactorStatus.ACTIVE, description="Factor status"
    )

    # IC analysis fields
    last_ic_value: float | None = Field(default=None, description="Latest IC value")
    last_ic_date: datetime | None = Field(
        default=None, description="Latest IC calculation date"
    )
    avg_ic_value: float | None = Field(default=None, description="Average IC value")
    ic_ir_ratio: float | None = Field(default=None, description="IC Information Ratio")

    # Computation status fields
    last_computed_at: datetime | None = Field(
        default=None, description="Last computation time"
    )
    computation_status: ComputationStatus | None = Field(
        default=None, description="Factor computation status"
    )
    data_points_count: int | None = Field(
        default=None, description="Number of data points computed"
    )


# Properties to receive via API on creation
class FactorCreate(FactorBase):
    pass


# Properties to receive via API on update
class FactorUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    expression: str | None = Field(default=None)
    description: str | None = Field(default=None, max_length=500)
    factor_type: FactorType | None = Field(default=None)
    status: FactorStatus | None = Field(default=None)


# Database model for Factor
class Factor(FactorBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: uuid.UUID = Field(foreign_key="user.id")
    # Relationship back to User
    creator: "User" = Relationship(back_populates="factors")


# Properties to return via API
class FactorPublic(FactorBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID


# ==========================================================
# Factor Analysis Module
# ==========================================================


class FactorAnalysis(SQLModel, table=True):
    """Factor analysis results storage"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    factor_id: uuid.UUID = Field(
        foreign_key="factor.id", description="Related factor ID"
    )
    analysis_date: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis execution date"
    )

    # IC analysis results
    ic_value: float | None = Field(
        default=None, description="Information Coefficient value"
    )
    ic_pvalue: float | None = Field(default=None, description="IC statistical p-value")
    rank_ic_value: float | None = Field(default=None, description="Rank IC value")
    rank_ic_pvalue: float | None = Field(default=None, description="Rank IC p-value")

    # Correlation analysis results
    correlation_matrix: str | None = Field(
        default=None, description="Correlation matrix in JSON format"
    )

    # Statistical metrics
    mean_value: float | None = Field(default=None, description="Factor mean value")
    std_value: float | None = Field(
        default=None, description="Factor standard deviation"
    )
    sharpe_ratio: float | None = Field(default=None, description="Factor Sharpe ratio")

    # Metadata
    analysis_period_start: datetime | None = Field(
        default=None, description="Analysis period start date"
    )
    analysis_period_end: datetime | None = Field(
        default=None, description="Analysis period end date"
    )
    sample_count: int | None = Field(
        default=None, description="Number of samples analyzed"
    )


class FactorDependency(SQLModel, table=True):
    """Factor data field dependencies"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    factor_id: uuid.UUID = Field(
        foreign_key="factor.id", description="Related factor ID"
    )
    field_name: str = Field(
        max_length=50, description="Required data field like $close, $volume"
    )
    is_available: bool = Field(description="Whether field is available in current data")
    description: str | None = Field(
        default=None, max_length=200, description="Field description"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==========================================================
# Model (Machine Learning Model) Module
# ==========================================================
# Note: MLModel stores model definition/template only.
# For trained models and training tasks, see ModelTraining module.


# Shared properties for Model
class ModelBase(SQLModel):
    name: str = Field(max_length=100, description="Model name")
    class_path: str = Field(
        max_length=255,
        description="Model class path (e.g., qlib.contrib.model.gbdt.LGBModel)",
    )
    description: str | None = Field(
        default=None, max_length=500, description="Model description"
    )
    config: str = Field(
        default="{}",
        description="Model configuration (JSON string, e.g., default hyperparameters)",
    )


# Properties to receive via API on creation
class ModelCreate(ModelBase):
    pass


# Properties to receive via API on update
class ModelUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    class_path: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    config: str | None = Field(default=None)


# Database model for Model
class MLModel(ModelBase, table=True):
    __tablename__ = "mlmodel"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: uuid.UUID = Field(foreign_key="user.id")
    # Relationship back to User
    creator: "User" = Relationship(back_populates="models")


# Properties to return via API
class ModelPublic(ModelBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID


# ===============================================================
# ModelTraining Module
# ===============================================================
# Note: ModelTraining stores training tasks and trained  model results.
# Each training task links to a MLModel (model definition) and produces
# a trained model file that can be used for backtesting.
class TrainingStatus(str, Enum):
    """Enumeration of training task status"""

    PENDING = "pending"  # Task created, waiting to start
    RUNNING = "running"  # Training in progress
    COMPLETED = "completed"  # Training completed successfully
    FAILED = "failed"  # Training failed with error


# Shared properties for ModelTraining
class ModelTrainingBase(SQLModel):
    name: str = Field(max_length=100, description="Training task name")
    model_id: uuid.UUID = Field(
        foreign_key="mlmodel.id", description="Model definition to use for training"
    )
    factor_handler: str = Field(
        default="alpha158",
        max_length=100,
        description="Factor handler name (e.g., 'alpha158', 'alpha360', or 'custom:set_name')",
    )
    # Training/validation time split - Auto split mode
    data_start_time: str = Field(
        max_length=50, description="Overall data start date (e.g., 2008-01-01)"
    )
    data_end_time: str = Field(
        max_length=50, description="Overall data end date (e.g., 2020-12-31)"
    )
    train_ratio: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Training data ratio (e.g., 0.7 for 70%). Default is 0.7",
    )
    valid_ratio: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Validation data ratio (e.g., 0.3 for 30%). Default is 0.3",
    )

    # Training configuration
    training_config: str = Field(
        default="{}",
        description="Training configuration (JSON string, e.g., batch_size, epochs)",
    )
    use_gpu: bool = Field(default=False, description="Whether to use GPU for training")
    num_workers: int = Field(default=1, description="Number of parallel workers")

    # Execution status
    status: TrainingStatus = Field(
        default=TrainingStatus.PENDING, description="Training task status"
    )
    progress: int = Field(default=0, description="Training progress (0-100)")
    current_step: str | None = Field(
        default=None, max_length=200, description="Current step description"
    )

    # Results
    model_file_path: str | None = Field(
        default=None, max_length=500, description="Path to trained model file"
    )
    training_metrics: str | None = Field(
        default=None,
        description="Training metrics (JSON string, e.g., loss, IC, Rank IC)",
    )
    error_message: str | None = Field(
        default=None, description="Error message if training failed"
    )


# Properties to receive via API on creation
class ModelTrainingCreate(ModelTrainingBase):
    pass


# Properties to receive via API on update
class ModelTrainingUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    training_config: str | None = Field(default=None)
    use_gpu: bool | None = Field(default=None)
    num_workers: int | None = Field(default=None)
    status: TrainingStatus | None = Field(default=None)
    progress: int | None = Field(default=None)
    current_step: str | None = Field(default=None, max_length=200)
    model_file_path: str | None = Field(default=None, max_length=500)
    training_metrics: str | None = Field(default=None)
    error_message: str | None = Field(default=None)


# Database model for ModelTraining
class ModelTraining(ModelTrainingBase, table=True):
    __tablename__ = "modeltraining"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="user.id")
    # Relationship back to User
    creator: "User" = Relationship(back_populates="model_trainings")


# Properties to return via API
class ModelTrainingPublic(ModelTrainingBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_by: uuid.UUID


# ===============================================================
# Backtest Module
# ===============================================================
# Note: Backtest stores backtest tasks and results.
# Each backtest task uses a trained model (from ModelTraining) for inference only.
# combined with a strategy to generate trading decision and evaluate performance.
class BacktestStatus(str, Enum):
    """Enumeration of backtest task status"""

    PENDING = "pending"  # Task created, waiting to start
    RUNNING = "running"  # Backtest in progress
    COMPLETED = "completed"  # Backtest completed successfully
    FAILED = "failed"  # Backtest failed with error


# Shared properties for Backtest
class BacktestBase(SQLModel):
    name: str = Field(max_length=100, description="Backtest task name")
    model_training_id: uuid.UUID = Field(
        foreign_key="modeltraining.id",
        description="Trained model to use for prediction",
    )
    strategy_id: uuid.UUID = Field(
        foreign_key="strategy.id", description="Strategy to use for trading decisions"
    )
    # Backtest time period
    backtest_start_time: str = Field(
        max_length=50, description="Backtest start date (e.g., 2017-01-01)"
    )
    backtest_end_time: str = Field(
        max_length=50, description="Backtest end date (e.g., 2020-08-01)"
    )
    # Backtest configuration
    benchmark: str = Field(
        max_length=50, description="Benchmark symbol (e.g., 000300.SH)"
    )
    account: float = Field(default=100000000.0, description="Initial account balance")
    exchange_config: str = Field(
        default="{}",
        description="Exchange configuration (JSON string, e.g., commission rates)",
    )

    # Execution status
    status: BacktestStatus = Field(
        default=BacktestStatus.PENDING, description="Backtest task status"
    )
    progress: int = Field(default=0, description="Backtest progress (0-100)")
    current_step: str | None = Field(
        default=None, max_length=200, description="Current step description"
    )

    # Results
    report_path: str | None = Field(
        default=None, max_length=500, description="Path to backtest report file"
    )
    positions_path: str | None = Field(
        default=None, max_length=500, description="Path to positions file"
    )
    performance_metrics: str | None = Field(
        default=None,
        description="Performance metrics (JSON string, e.g., annual return, sharpe ratio, max drawdown)",
    )
    error_message: str | None = Field(
        default=None, description="Error message if backtest failed"
    )


# Properties to receive via API on creation
class BacktestCreate(BacktestBase):
    pass


# Properties to receive via API on update
class BacktestUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    exchange_config: str | None = Field(default=None)
    status: BacktestStatus | None = Field(default=None)
    progress: int | None = Field(default=None)
    current_step: str | None = Field(default=None, max_length=200)
    report_path: str | None = Field(default=None, max_length=500)
    positions_path: str | None = Field(default=None, max_length=500)
    performance_metrics: str | None = Field(default=None)
    error_message: str | None = Field(default=None)


# Database model for Backtest
class Backtest(BacktestBase, table=True):
    __tablename__ = "backtest"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="user.id")
    # Relationship back to User
    creator: "User" = Relationship(back_populates="backtests")


# Properties to return via API
class BacktestPublic(BacktestBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_by: uuid.UUID


# ===============================================================
# Strategy Model
# ===============================================================
class StrategyStatus(str, Enum):
    """Enumeration of strategy status"""

    ACTIVE = "active"
    INACTIVE = "inactive"


# Shared properties for Strategy
class StrategyBase(SQLModel):
    name: str = Field(max_length=100, description="Strategy name")
    class_path: str = Field(
        max_length=255,
        description="Strategy class path (e.g., qlib.contrib.strategy.TopkDropoutStrategy)",
    )
    description: str | None = Field(
        default=None, max_length=500, description="Strategy description"
    )
    config: str = Field(
        default="{}",
        description='Strategy configuration (JSON string, e.g., {"topk": 50, "n_drop": 5})',
    )
    status: StrategyStatus = Field(
        default=StrategyStatus.ACTIVE, description="Strategy status"
    )


# Properties to receive via API on creation
class StrategyCreate(StrategyBase):
    pass


# Properties to receive via API on update
class StrategyUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    class_path: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    config: str | None = Field(default=None)
    status: StrategyStatus | None = Field(default=None)


# Database model for Strategy
class Strategy(StrategyBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: uuid.UUID = Field(foreign_key="user.id")
    # Relationship back to User
    creator: "User" = Relationship(back_populates="strategies")


# Properties to return via API
class StrategyPublic(StrategyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID


# Data Collection Models
class DataCollectionRequest(SQLModel):
    """
    Request model for data collection task.

    Educational Notes:
    - Pydantic model for request validation
    - All fields are validated automatically by FastAPI
    - Type hints ensure type safety
    """

    collector_name: str = Field(
        description="Name of the data collector (e.g., 'tushare', 'eod')"
    )
    instruments: list[str] = Field(
        description="List of instrument codes to collect",
        min_length=1,
    )
    start_date: str = Field(
        description="Start date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    )
    end_date: str = Field(
        description="End date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    )


class DataCollectionResponse(SQLModel):
    """
    Response model for data collection task.

    Educational Notes:
    - Provides detailed information about collection result
    - Includes success status and error information
    - API-friendly format for frontend consumption
    """

    success: bool = Field(description="Whether the collection was successful")
    collector: str = Field(description="Name of the collector used")
    total_instruments: int = Field(description="Total number of instruments requested")
    successful_count: int = Field(
        description="Number of instruments successfully collected"
    )
    csv_dir: str | None = Field(
        default=None, description="Directory where CSV files are saved"
    )
    qlib_dir: str | None = Field(
        default=None, description="Directory where Qlib .bin files are saved"
    )
    errors: list[str] = Field(
        default_factory=list, description="List of error messages if any"
    )
    error: str | None = Field(
        default=None, description="Error message if collection failed"
    )


class CollectorInfo(SQLModel):
    """
    Information about a data collector.

    Educational Notes:
    - Metadata about collector capabilities
    - Includes field coverage information
    - Helps users understand what data is available
    """

    name: str = Field(description="Collector name")
    supported_fields: list[str] = Field(description="List of supported data fields")
    field_coverage: dict = Field(description="Detailed field coverage information")
    config_keys: list[str] = Field(description="Required configuration keys")


class CollectorsInfoResponse(SQLModel):
    """
    Response model for collectors information.

    Educational Notes:
    - Provides overview of all available collectors
    - Useful for API discovery
    - Frontend can use this to build UI
    """

    total_collectors: int = Field(description="Total number of registered collectors")
    collectors: dict[str, CollectorInfo] = Field(
        description="Dictionary of collector information"
    )


# Factor Calculation Models
class FactorCalculationRequest(SQLModel):
    """
    Request model for factor calculation task.

    Educational Notes:
    - Pydantic model for factor calculation request validation
    - Supports multiple factor handlers (alpha158, alpha191, etc.)
    - All fields are validated automatically by FastAPI
    """

    handler_name: str = Field(
        description="Name of the factor handler (e.g., 'alpha158')"
    )
    instruments: list[str] = Field(
        description="List of instrument codes to calculate factors for",
        min_length=1,
    )
    start_date: str = Field(
        description="Start date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    )
    end_date: str = Field(
        description="End date in YYYY-MM-DD format",
        regex=r"^\d{4}-\d{2}-\d{2}$",
    )


class FactorCalculationResponse(SQLModel):
    """
    Response model for factor calculation task.

    Educational Notes:
    - Provides detailed information about calculation result
    - Includes success status, timing, and caching information
    - API-friendly format for frontend consumption
    """

    success: bool = Field(description="Whether the calculation was successful")
    factor_handler: str = Field(description="Name of the factor handler used")
    instruments_count: int = Field(description="Number of instruments processed")
    features_count: int = Field(description="Number of features calculated")
    calculation_time: float = Field(description="Time taken for calculation in seconds")
    cached: bool = Field(description="Whether result was retrieved from cache")
    error: str | None = Field(
        default=None, description="Error message if calculation failed"
    )


class FactorHandlerInfo(SQLModel):
    """
    Information about a factor handler.

    Educational Notes:
    - Metadata about factor handler capabilities
    - Includes feature count and description
    - Helps users understand available factors
    """

    name: str = Field(description="Handler name")
    description: str = Field(description="Handler description")
    features_count: int = Field(
        description="Number of features provided by this handler"
    )


class FactorHandlersInfoResponse(SQLModel):
    """
    Response model for factor handlers information.

    Educational Notes:
    - Provides overview of all available factor handlers
    - Useful for API discovery
    - Frontend can use this to build UI
    """

    total_handlers: int = Field(description="Total number of registered handlers")
    handlers: list[FactorHandlerInfo] = Field(description="List of handler information")


class FactorDataFetchRequest(SQLModel):
    """
    Request model for fetching actual factor data.

    Educational Notes:
    - Returns actual calculated factor values as evidence
    - Allows specifying which features to retrieve
    - Useful for verification and debugging
    """

    handler_name: str = Field(description="Name of the factor handler")
    instruments: list[str] = Field(description="List of instrument codes")
    start_date: str = Field(description="Start date (YYYY-MM-DD)")
    end_date: str = Field(description="End date (YYYY-MM-DD)")
    features: list[str] | None = Field(
        default=None,
        description="Specific features to fetch (if None, fetch first 5 features)",
    )


class FactorDataFetchResponse(SQLModel):
    """
    Response model for factor data fetch.

    Educational Notes:
    - Contains actual calculated factor values
    - Provides evidence of real computation
    - Includes metadata for verification
    """

    success: bool = Field(description="Whether the fetch was successful")
    factor_handler: str = Field(description="Name of the factor handler used")
    instruments: list[str] = Field(description="List of instruments")
    date_range: tuple[str, str] = Field(description="Date range (start, end)")
    features: list[str] = Field(description="List of feature names")
    data_shape: tuple[int, int] = Field(description="Shape of data (rows, columns)")
    sample_data: dict[str, list[float | None]] = Field(
        description="Sample data (first 5 rows) for each feature. None values represent NaN or Inf."
    )
    error: str | None = Field(default=None, description="Error message if fetch failed")


class FeatureInfo(SQLModel):
    """
    Information about a single feature.

    Educational Notes:
    - Metadata about individual factor features
    - Includes name, description, and category
    - Helps users understand what each feature represents
    """

    name: str = Field(description="Feature name")
    description: str = Field(description="Feature description")
    category: str = Field(description="Feature category (e.g., '价格形态', '技术指标')")


# Model Handler Models
class ModelHandlerInfo(SQLModel):
    """
    Information about a model handler.

    Educational Notes:
    - Metadata about model handler capabilities
    - Describes the model type and purpose
    - Helps users understand available models
    """

    name: str = Field(description="Handler name")
    description: str = Field(description="Handler description")


class ModelHandlersInfoResponse(SQLModel):
    """
    Response model for model handlers information.

    Educational Notes:
    - Provides overview of all available model handlers
    - Useful for API discovery
    - Frontend can use this to build UI
    """

    total_handlers: int = Field(description="Total number of registered handlers")
    handlers: List[ModelHandlerInfo] = Field(description="List of handler information")


# ===================================================================
# Training Workflow Models - Based on Qlib Configuration Structure
# ===================================================================
class QlibComponentConfig(SQLModel):
    """
    Base configuration for Qlib components following init_instance_by_config pattern.

    Educational Notes:
    - Qlib uses declarative configuration with class + module_path + kwargs
    - This pattern allows dynamic instantiation by any Qlib component
    - Follows the same structure as Qlib YAML configuration files
    """

    class_name: str = Field(
        description="Class name of the Qlib component (e.g., 'LGBModel', 'Alpha158')",
    )

    module_path: str | None = Field(
        default=None,
        description="Python module path where the class is located (e.g., 'qlib.contrib.model.gbdt'). If not provided, will be automatically filled by backend based on class_name.",
    )

    kwargs: dict = Field(
        default_factory=dict,
        description="Keyword arguments passed to the component's __init__ method",
    )


class ModelConfig(QlibComponentConfig):
    """
    Configuration for Qlib Model (e.g., LGBModel).

    Educational Notes:
    - Model defines the machine learning algorithm for prediction
    - LGBModel is LightGBM implementation optimized for financial data
    - Model kwargs include hyperparameters like learning_rate, num_leaves
    - Inherits all fields from QlibComponentConfig (class, module_path, kwargs)
    """

    pass  # Inherits all fields from QlibComponentConfig


class DataHandlerConfig(QlibComponentConfig):
    """
    Configuration for Qlib Data Handler (e.g., Alpha158)

    Educational Notes:
    - Data Handler processes raw data into features for model training
    - Alpha158 is Qlib's built-in 158 alpha factors
    - Inherits class_name, module_path, kwargs from QlibComponentConfig
    - Handler kwargs include time ranges and instrument selection
    """

    pass  # Inherits all fields from QlibComponentConfig


class DatasetSegments(SQLModel):
    """
    Time-based segments for train/validation/test splits.

    Educational Notes:
    - Qlib uses time-based splitting for financial data
    - Each segment is a tuple of (start_date, end_date)
    - Ensures no look-ahead bias in model training
    """

    train: tuple[str, str] = Field(
        description="Training period as (start_date, end_date) tuple"
    )

    valid: tuple[str, str] = Field(
        description="Validation period as (start_date, end_date) tuple"
    )

    test: tuple[str, str] = Field(
        description="Test period as (start_date, end_date) tuple"
    )


class DatasetKwargs(SQLModel):
    """
    Dataset kwargs containing handler and segments.

    Educational Notes:
    - Dataset kwargs combine data processing (handler) and time splitting (segments)
    - Handler defines how raw data becomes features
    - Segments define how data is split for training/validation/testing
    """

    handler: DataHandlerConfig = Field(
        description="Data handler configuration for feature processing"
    )

    segments: DatasetSegments = Field(
        description="Time-based data segments for train/valid/test splits"
    )


class DatasetConfig(SQLModel):
    """
    Configuration for Qlib Dataset (e.g., DatasetH).

    Educational Notes:
    - Dataset handles data preprocessing and train/valid/test splitting
    - DatasetH is Qlib's hierarchical dataset for time series data
    # Contains handler config and segment definitions
    """

    class_name: str = Field(description="Dataset class name (e.g., 'DatasetH')")

    module_path: str | None = Field(
        default=None,
        description="Module path for dataset (e.g., 'qlib.data.dataset'). If not provided, will be automatically filled by backend based on class_name.",
    )

    kwargs: DatasetKwargs = Field(
        description="Dataset configuration including handler and segments"
    )


class TaskConfig(SQLModel):
    """
    Qlib Task configuration containing model and dataset.

    Educational Notes:
    - Task is the core unit of execution in Qlib workflows
    - Combines model, dataset, and optional record configurations
    - Maps directly to Qlib's task section in YAML configs
    """

    model: ModelConfig = Field(description="Model configuration for training")
    dataset: DatasetConfig = Field(
        description="Dataset configuration for data processing"
    )


class TrainingWorkflowRequest(SQLModel):
    """
    Request model for training workflow API.

    Educational Notes:
    - Follows Qlib's workflow configuration structure exactly
    # Allows users to specify complete training pipeline
    - Experiment name helps organize and track different runs
    """

    experiment_name: str = Field(
        default="default_experiment",
        description="Name for the training experiment (used in MLflow tracking)",
        min_length=1,
        max_length=100,
    )
    task: TaskConfig = Field(
        description="Task configuration containing model and dataset settings"
    )


class TrainingWorkflowResponse(SQLModel):
    """
    Response model for training workflow API.

    Educational Notes:
    - Provides comprehensive feedback on training execution
    - Predictions count indicates model's output on test set
    - Model saved status confirms persistence for future use
    """

    status: str = Field(description="Execution status ('success' or 'error')")
    predictions_count: int = Field(
        description="Number of predictions generated on test set"
    )
    model_saved: bool = Field(
        description="Whether the trained model was successfully saved"
    )
    experiment_name: str = Field(description="Name of the experiment that was executed")
    error_message: str | None = Field(
        default=None, description="Error message if status is 'error'"
    )


# ============================================================================
# Data source Management Models
# ============================================================================
class DataSourceStatus(SQLModel):
    """
    Data source status information.

    Educational Notes:
    - This model represents the current state of the data
    - Used to display information to users
    - Not stored in database, just for API response
    """

    source_name: str = Field(description="Current data source name")
    data_exists: bool = Field(description="Whether data exists in qlib_data directory")
    data_range_start: str | None = Field(
        default=None, description="Start date of available data"
    )
    data_range_end: str | None = Field(
        default=None, description="End date of available data"
    )
    instruments: list[str] | None = Field(
        default=None, description="List of stock codes (first 10 if more than 10)"
    )
    instruments_count: int | None = Field(default=None, description="Number of stocks")
    stock_pool: str | None = Field(
        default=None,
        description="Stock pool name (e.g., 'etf_universe')",
    )
    features: list[str] | None = Field(
        default=None,
        description="List of available features (e.g., ['open', 'close', 'high', 'low', 'volume'])",
    )
    label: str | None = Field(
        default=None,
        description="Active label name for prediction target (e.g., 'return_1d')",
    )
    data_size_mb: float | None = Field(
        default=None, description="Total data size in MB"
    )
    last_updated: str | None = Field(default=None, description="Last update timestamp")


class DownloadDataRequest(SQLModel):
    """
    Request model for downloading data.

    Educational Notes:
    - This defines what parameters users need to provide
    - Validation is automatic through Pydantic
    - Data source is now controlled by configuration, not user input
    """

    stock_pool: str = Field(
        default="etf_universe",
        description="Stock pool to download (e.g., 'etf_universe')",
    )
    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")
    incremental: bool = Field(
        default=False,
        description="Whether to perform incremental update (append new data only)",
    )
    interval: Optional[str] = Field(
        default="1d",
        description="Data interval: '1d' for daily data",
    )


class DownloadTaskResponse(SQLModel):
    """
    Response model for download task creation.

    Educational Notes:
    - Returned immediately when user starts download
    - Contains task_id for tracking progress
    """

    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Initial status: 'started'")
    message: str = Field(description="Human-readable message")


class DownloadTaskStatus(SQLModel):
    """
    Download task status information.

    Educational Notes:
    - Used for progress tracking
    - Frontend polls this endpoint to update progress bar
    """

    task_id: str = Field(description="Task identifier")
    status: str = Field(
        description="Task status: 'downloading', 'converting', 'completed', 'failed'"
    )
    progress: int = Field(description="Progress percentage (0-100)")
    message: str = Field(description="Current operation message")
    error: str | None = Field(default=None, description="Error message if failed")


class ClearDataResponse(SQLModel):
    """
    Response model for data clearing operation.

    Educational Notes:
    - Simple response to confirm operation
    """

    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Result message")
    cleared_size_mb: float | None = Field(
        default=None, description="Size of cleared data in MB"
    )


"""
Simplified pipeline models that work with existing API.

Educational Notes:
- Reuses existing DownloadDataRequest and DownloadTaskResponse
- Adds minimal pipeline-specific models for internal use
- Maintains compatibility with current frontend
"""

from enum import Enum
from pathlib import Path
from pydantic import BaseModel
from typing import Optional


class PipelineStage(str, Enum):
    """Internal pipeline stages"""

    COLLECT = "collect"
    NORMALIZE = "normalize"
    DUMP = "dump"


class PipelineWorkspace(BaseModel):
    """Internal workspace configuration"""

    base_dir: Path
    temp_csv_dir: Path
    normalized_dir: Path
    qlib_data_dir: Path

    def create_directories(self):
        """Create workspace directories"""
        for dir_path in [self.temp_csv_dir, self.normalized_dir, self.qlib_data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def cleanup_temp(self):
        """Clean temporary directories"""
        import shutil

        if self.temp_csv_dir.exists():
            shutil.rmtree(self.temp_csv_dir)
        if self.normalized_dir.exists():
            shutil.rmtree(self.normalized_dir)


class PipelineStageResult(BaseModel):
    """Result of a single pipeline stage"""

    stage: PipelineStage
    success: bool
    message: str
    error: Optional[str] = None


# ============================================================================
# Data Health Check Models
# ============================================================================
class MissingDataDetail(SQLModel):
    """Details of missing data for a specific instrument."""

    instrument: str = Field(description="Instrument code")
    open: int = Field(description="Number of missing values in open column")
    high: int = Field(description="Number of missing values in high column")
    low: int = Field(description="Number of missing values in low column")
    close: int = Field(description="Number of missing values in close column")
    volume: int = Field(description="Number of missing values in volume column")


class DataAnomaly(SQLModel):
    """Details of a detected data anomaly (large step change)."""

    instrument: str = Field(description="Instrument code")
    column: str = Field(description="Column with anomaly (e.g., 'close', 'volume')")
    date: str = Field(description="Date of anomaly occurrence")
    pct_change: float = Field(description="Percentage change detected")


class IntegrityChecks(SQLModel):
    """Results of data integrity checks."""

    required_columns: bool = Field(
        description="Whether all required OHLCV columns exist"
    )
    factor_column: bool = Field(description="Whether factor column exists and has data")
    directory_case: bool = Field(
        description="Whether all feature directories are lowercase"
    )


class DataHealthMetrics(SQLModel):
    """
    Comprehensive data health metrics.

    Educational Notes:
    - Provides overview of data quality
    - Includes both summary statistics and detailed lists
    - Used for monitoring and alerting
    """

    data_exists: bool = Field(description="Whether data exists in qlib_data directory")
    completeness_percentage: float = Field(
        description="Percentage of complete data (0-100)"
    )
    missing_data_count: int = Field(
        description="Number of instruments with missing data"
    )
    missing_data_details: List[MissingDataDetail] = Field(
        description="Detailed list of missing data by instrument"
    )
    anomaly_count: int = Field(description="Number of detected anomalies")
    anomalies: List[DataAnomaly] = Field(
        description="Detailed list of anomalies detected"
    )
    integrity_checks: IntegrityChecks = Field(description="Results of integrity checks")
    checked_at: str = Field(description="Timestamp when check was performed")


# ============================================================================
# Model Metrics Models
# ============================================================================


class ICDistributionBin(SQLModel):
    """Single bin for IC distribution histogram."""

    bin_start: float = Field(description="Bin start value")
    bin_end: float = Field(description="Bin end value")
    count: int = Field(description="Count in this bin")
    bin_center: float = Field(description="Bin center value")


class QQPlotPoint(SQLModel):
    """Single point for Q-Q plot."""

    theoretical: float = Field(description="Theoretical quantile")
    sample: float = Field(description="Sample quantile")


class ICDistribution(SQLModel):
    """IC distribution data for histogram and Q-Q plot."""

    histogram: List[ICDistributionBin] = Field(description="Histogram bins")
    qq_plot: List[QQPlotPoint] = Field(description="Q-Q plot data")
    mean: float = Field(description="Mean of IC values")
    std: float = Field(description="Standard deviation of IC values")
    skewness: float = Field(description="Skewness of IC distribution")
    kurtosis: float = Field(description="Kurtosis of IC distribution")


class ICMetrics(SQLModel):
    """
    IC (Information Coefficient) metrics.

    Educational Notes:
    - IC measures correlation between predictions and actual returns
    - Higher IC indicates better predictive power
    - ICIR measures stability of IC (IC Mean / IC Std)
    """

    ic_mean: float = Field(description="Mean IC (Pearson correlation)")
    ic_std: float = Field(description="Standard deviation of IC")
    icir: float = Field(description="IC Information Ratio (IC Mean / IC Std)")
    rank_ic_mean: float = Field(description="Mean Rank IC (Spearman correlation)")
    rank_ic_std: float = Field(description="Standard deviation of Rank IC")
    rank_icir: float = Field(description="Rank IC Information Ratio")

    # Chart data
    monthly_ic: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Monthly IC data for heatmap"
    )
    ic_distribution: Optional[ICDistribution] = Field(
        default=None, description="IC distribution for histogram and Q-Q plot"
    )


class ReturnDistributionBin(SQLModel):
    """Single bin for return distribution histogram."""

    bin_start: float = Field(description="Bin start value")
    bin_end: float = Field(description="Bin end value")
    count: int = Field(description="Count in this bin")
    bin_center: float = Field(description="Bin center value")


class CumulativeReturnPoint(SQLModel):
    """Single point for cumulative returns chart."""

    datetime: str = Field(description="Date")
    cumulative_return: float = Field(description="Cumulative return value")


class LongShortMetrics(SQLModel):
    """
    Long-Short strategy performance metrics.

    Educational Notes:
    - Long-Short: Long top 20% stocks, short bottom 20% stocks
    - Sharpe Ratio: Return per unit of risk (higher is better)
    - Annualized metrics scaled to yearly performance
    """

    long_short_ann_return: float = Field(description="Annualized long-short return")
    long_short_ann_sharpe: float = Field(
        description="Annualized long-short Sharpe ratio"
    )
    long_avg_ann_return: float = Field(description="Annualized long-average return")
    long_avg_ann_sharpe: float = Field(
        description="Annualized long-average Sharpe ratio"
    )

    # Chart data
    cumulative_returns: Optional[List[CumulativeReturnPoint]] = Field(
        default=None, description="Cumulative returns time series"
    )
    return_distribution: Optional[List[ReturnDistributionBin]] = Field(
        default=None, description="Return distribution histogram"
    )


class TurnoverPoint(SQLModel):
    """Single point for turnover time series."""

    datetime: str = Field(description="Date")
    turnover: float = Field(description="Turnover value")


class TurnoverData(SQLModel):
    """Turnover analysis data."""

    top_turnover_series: List[TurnoverPoint] = Field(
        description="Top stocks turnover time series"
    )
    bottom_turnover_series: List[TurnoverPoint] = Field(
        description="Bottom stocks turnover time series"
    )
    avg_top_turnover: float = Field(description="Average top turnover")
    avg_bottom_turnover: float = Field(description="Average bottom turnover")


class QualityMetrics(SQLModel):
    """
    Prediction quality metrics.

    Educational Notes:
    - Precision: Accuracy of predictions (>0.55 is good)
    - Auto Correlation: Prediction stability over time (0.1-0.3 is normal)
    """

    long_precision: float = Field(description="Long prediction precision")
    short_precision: float = Field(description="Short prediction precision")
    auto_correlation: float = Field(description="Auto correlation (lag=1)")

    # Chart data
    turnover: Optional[TurnoverData] = Field(
        default=None, description="Turnover analysis data"
    )


class FeatureImportanceItem(SQLModel):
    """Single feature importance item."""

    feature: str = Field(description="Feature name")
    importance: float = Field(description="Importance value")


class TimeSeriesDataPoint(SQLModel):
    """Single time series data point."""

    datetime: str = Field(description="Date/time as string")
    value: float = Field(description="Value at this time point")


class MonthlyICDataPoint(SQLModel):
    """Monthly IC data point for heatmap."""

    year: int = Field(description="Year")
    month: int = Field(description="Month (1-12)")
    ic: float = Field(description="IC value for this month")


class ModelMetricsResponse(SQLModel):
    """
    Complete model metrics response.

    Educational Notes:
    - Contains all metrics for the active Rolling Ensemble model
    - Metrics are pre-calculated during routine to avoid delays
    - Used for comprehensive model performance analysis
    """

    model_type: str = Field(description="Model type (e.g., 'Rolling Ensemble')")
    calculated_at: str = Field(description="When metrics were calculated")
    frequency: str = Field(description="Data frequency ('day')")

    # Core metrics
    ic_metrics: ICMetrics = Field(description="IC analysis metrics")
    long_short_metrics: LongShortMetrics = Field(
        description="Long-short strategy metrics"
    )
    quality_metrics: QualityMetrics = Field(description="Prediction quality metrics")

    # Feature importance (optional)
    feature_importance: Optional[List[FeatureImportanceItem]] = Field(
        default=None, description="Feature importance from latest model"
    )


class ChartDataResponse(SQLModel):
    """
    Chart data response for various chart types.

    Educational Notes:
    - Different chart types return different data structures
    - All time series data uses string dates for JSON compatibility
    """

    chart_type: str = Field(description="Type of chart data")
    data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        description="Chart data - can be dict or list of dicts"
    )
