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
class ModelStatus(str, Enum):
    """Enumeration of model status"""

    TRAINED = "trained"  # Model is trained with latest data
    OUTDATED = "outdated"  # Model file exists but data has been updated
    UNTRAINED = "untrained"  # Model has never been trained


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
        description="Model configuration (JSON string, e.g., hyperparameters)",
    )
    model_file_path: str | None = Field(
        default=None, max_length=500, description="Path to trained model file"
    )
    status: ModelStatus = Field(
        default=ModelStatus.UNTRAINED, description="Model training status"
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
    model_file_path: str | None = Field(default=None, max_length=500)
    status: ModelStatus | None = Field(default=None)


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
