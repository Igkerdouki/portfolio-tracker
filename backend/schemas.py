from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from models import AssetType, TransactionType


class PositionBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    shares: float = Field(..., gt=0)
    cost_basis: float = Field(..., ge=0)
    purchase_date: date
    asset_type: AssetType = AssetType.STOCK


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    symbol: Optional[str] = Field(None, min_length=1, max_length=10)
    shares: Optional[float] = Field(None, gt=0)
    cost_basis: Optional[float] = Field(None, ge=0)
    purchase_date: Optional[date] = None
    asset_type: Optional[AssetType] = None


class PositionResponse(PositionBase):
    id: int
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percent: Optional[float] = None

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    shares: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    date: date
    transaction_type: TransactionType


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: int

    class Config:
        from_attributes = True


class AllocationItem(BaseModel):
    asset_type: str
    value: float
    percentage: float
    symbols: List[str]


class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    total_gain_loss: float
    total_gain_loss_percent: float
    positions_count: int
    allocation: List[AllocationItem]


class PortfolioHistoryItem(BaseModel):
    date: date
    total_value: float
    total_cost: float
    daily_return: float


class PriceResponse(BaseModel):
    symbol: str
    price: float
    currency: str = "USD"
    change: Optional[float] = None
    change_percent: Optional[float] = None
