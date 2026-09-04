from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal
from app.models import BankRecord, GatewayRecord, LedgerRecord


DATA_DIR = Path("data")


def parse_datetime(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def optional_string(value: str) -> str | None:
    return value if value else None


def load_gateway(row: dict[str, str]) -> GatewayRecord:
    return GatewayRecord(
        transaction_id=row["transaction_id"],
        payment_id=row["payment_id"],
        settlement_id=optional_string(row["settlement_id"]),
        amount=Decimal(row["amount"]),
        currency=row["currency"],
        timestamp=parse_datetime(row["timestamp"]),
        gateway_status=row["gateway_status"],
        payment_method=row["payment_method"],
        merchant_id=row["merchant_id"],
        gateway_reference=row["gateway_reference"],
        settlement_initiated_at=parse_datetime(row["settlement_initiated_at"]),
    )


def load_bank(row: dict[str, str]) -> BankRecord:
    return BankRecord(
        transaction_id=row["transaction_id"],
        payment_id=row["payment_id"],
        settlement_id=optional_string(row["settlement_id"]),
        amount=Decimal(row["amount"]),
        currency=row["currency"],
        timestamp=parse_datetime(row["timestamp"]),
        bank_status=row["bank_status"],
        bank_account_id=row["bank_account_id"],
        utr=row["utr"],
        cleared_at=parse_datetime(row["cleared_at"]),
    )


def load_ledger(row: dict[str, str]) -> LedgerRecord:
    return LedgerRecord(
        transaction_id=row["transaction_id"],
        payment_id=row["payment_id"],
        settlement_id=optional_string(row["settlement_id"]),
        amount=Decimal(row["amount"]),
        currency=row["currency"],
        timestamp=parse_datetime(row["timestamp"]),
        ledger_status=row["ledger_status"],
        ledger_entry_id=row["ledger_entry_id"],
        posted_at=parse_datetime(row["posted_at"]),
        reconciliation_batch=row["reconciliation_batch"],
    )


def read_records(path: Path, loader) -> list:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return [loader(row) for row in csv.DictReader(handle)]


def import_csvs(db: Session, replace: bool = True) -> dict[str, int]:
    Base.metadata.create_all(bind=db.get_bind())

    if replace:
        db.execute(delete(GatewayRecord))
        db.execute(delete(BankRecord))
        db.execute(delete(LedgerRecord))
        db.flush()

    gateway = read_records(DATA_DIR / "gateway.csv", load_gateway)
    bank = read_records(DATA_DIR / "bank.csv", load_bank)
    ledger = read_records(DATA_DIR / "ledger.csv", load_ledger)

    db.add_all(gateway)
    db.add_all(bank)
    db.add_all(ledger)
    db.commit()

    return count_records(db)


def count_records(db: Session) -> dict[str, int]:
    return {
        "gateway_records": db.scalar(select(func.count()).select_from(GatewayRecord)) or 0,
        "bank_records": db.scalar(select(func.count()).select_from(BankRecord)) or 0,
        "ledger_records": db.scalar(select(func.count()).select_from(LedgerRecord)) or 0,
    }


if __name__ == "__main__":
    with SessionLocal() as session:
        counts = import_csvs(session)
    print("Imported CSV data into PostgreSQL:")
    for table, count in counts.items():
        print(f"  {table}: {count}")
