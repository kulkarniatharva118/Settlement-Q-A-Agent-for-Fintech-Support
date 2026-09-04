from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankRecord, GatewayRecord, LedgerRecord


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _record_to_dict(record: Any) -> dict[str, Any]:
    columns = record.__mapper__.columns.keys()
    return {column: _json_value(getattr(record, column)) for column in columns}


def get_transaction_records(db: Session, transaction_id: str) -> dict[str, Any] | None:
    gateway = db.scalars(
        select(GatewayRecord)
        .where(GatewayRecord.transaction_id == transaction_id)
        .order_by(GatewayRecord.id)
    ).all()
    bank = db.scalars(
        select(BankRecord).where(BankRecord.transaction_id == transaction_id).order_by(BankRecord.id)
    ).all()
    ledger = db.scalars(
        select(LedgerRecord)
        .where(LedgerRecord.transaction_id == transaction_id)
        .order_by(LedgerRecord.id)
    ).all()

    if not gateway and not bank and not ledger:
        return None

    return {
        "transaction_id": transaction_id,
        "gateway": [_record_to_dict(record) for record in gateway],
        "bank": [_record_to_dict(record) for record in bank],
        "ledger": [_record_to_dict(record) for record in ledger],
    }
