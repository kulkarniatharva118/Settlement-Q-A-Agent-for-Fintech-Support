from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.repository import get_transaction_records


app = FastAPI(title="PS-8 Settlement Q&A Agent API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/transactions/{transaction_id}")
def read_transaction(transaction_id: str, db: Session = Depends(get_db)) -> dict:
    records = get_transaction_records(db, transaction_id)
    if records is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return records
