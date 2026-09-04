from __future__ import annotations

from app.database import Base, engine
from app import models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables are ready: gateway_records, bank_records, ledger_records")


if __name__ == "__main__":
    init_db()
