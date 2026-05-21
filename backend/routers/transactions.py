"""Transaction recording endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Transaction
from schemas import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=List[TransactionResponse])
def list_transactions(symbol: str = None, db: Session = Depends(get_db)):
    """List all transactions, optionally filtered by symbol."""
    query = db.query(Transaction)

    if symbol:
        query = query.filter(Transaction.symbol == symbol.upper())

    return query.order_by(Transaction.date.desc()).all()


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Record a new transaction."""
    db_transaction = Transaction(
        symbol=transaction.symbol.upper(),
        shares=transaction.shares,
        price=transaction.price,
        date=transaction.date,
        transaction_type=transaction.transaction_type.value
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return db_transaction
