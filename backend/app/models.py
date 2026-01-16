import uuid
from datetime import datetime

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
    """Enumeration of supported data source type"""

    YAHOO_FINANCE = "yahoo_finance"
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    LOCAL_FILE = "local_file"
    CUSTOM_API = "custom_api"


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


# Shared properties for Factor
class FactorBase(SQLModel):
    name: str = Field(max_length=100, description="Factor name")
    expression: str = Field(description="Factor expression in Qlib format")
    description: str | None = Field(
        default=None, max_length=500, description="Factor description"
    )
    category: FactorCategory = Field(description="Factor category")
    status: FactorStatus = Field(
        default=FactorStatus.ACTIVE, description="Factor status"
    )


# Properties to receive via API on creation
class FactorCreate(FactorBase):
    pass


# Properties to receive via API on update
class FactorUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    expression: str | None = Field(default=None)
    description: str | None = Field(default=None, max_length=500)
    category: FactorCategory | None = Field(default=None)
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
    factor_ids: str = Field(
        default="[]",
        description="JSON array of factors IDs to use (e.g., ['uuid1', 'uuid2'])",
    )
    # Training/validation time split
    train_start_time: str = Field(
        max_length=50, description="Training start date (e.g., 2008-01-01)"
    )
    train_end_time: str = Field(
        max_length=50, description="Training end date (e.g., 2014-12-31)"
    )
    valid_start_time: str = Field(
        max_length=50, description="Validation start date (e.g., 2015-01-01)"
    )
    valid_end_time: str = Field(
        max_length=50, description="Validation end date (e.g., 2016-12-31)"
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
        max_length=50, description="Benchmark symbol (e.g., SH000300 for CSI300)"
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
