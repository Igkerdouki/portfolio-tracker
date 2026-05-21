from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum
from sqlalchemy.sql import func
from database import Base
import enum


class AssetType(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    BOND = "bond"
    CASH = "cash"
    CRYPTO = "crypto"
    OTHER = "other"


class TransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    shares = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=False)  # Total cost basis
    purchase_date = Column(Date, nullable=False)
    asset_type = Column(String, default=AssetType.STOCK.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    shares = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    transaction_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    total_value = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    daily_return = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
