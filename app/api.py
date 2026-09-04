from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.repository import get_transaction_records
from app.schemas import InvestigationResult
from app.services.investigation import TransactionNotFoundError, investigate_transaction


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


@app.get(
    "/investigations/{transaction_id}",
    response_model=InvestigationResult,
    summary="Investigate settlement status for a transaction",
    responses={
        404: {"description": "Transaction was not found in gateway, bank, or ledger records."},
        500: {"description": "Unexpected investigation or database error."},
    },
)
def read_investigation(
    transaction_id: str = Path(description="Transaction ID to investigate, for example TXN-DEMO-001."),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return investigate_transaction(transaction_id, db)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unexpected investigation error") from exc
