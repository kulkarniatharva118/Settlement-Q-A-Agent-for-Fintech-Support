from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GatewayRecord(Base):
    __tablename__ = "gateway_records"
    __table_args__ = (Index("ix_gateway_records_transaction_id", "transaction_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(60), nullable=False)
    settlement_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    gateway_status: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(40), nullable=False)
    gateway_reference: Mapped[str] = mapped_column(String(60), nullable=False)
    settlement_initiated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BankRecord(Base):
    __tablename__ = "bank_records"
    __table_args__ = (Index("ix_bank_records_transaction_id", "transaction_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(60), nullable=False)
    settlement_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    bank_status: Mapped[str] = mapped_column(String(40), nullable=False)
    bank_account_id: Mapped[str] = mapped_column(String(40), nullable=False)
    utr: Mapped[str] = mapped_column(String(60), nullable=False)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LedgerRecord(Base):
    __tablename__ = "ledger_records"
    __table_args__ = (Index("ix_ledger_records_transaction_id", "transaction_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(60), nullable=False)
    settlement_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ledger_status: Mapped[str] = mapped_column(String(40), nullable=False)
    ledger_entry_id: Mapped[str] = mapped_column(String(60), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconciliation_batch: Mapped[str] = mapped_column(String(40), nullable=False)
