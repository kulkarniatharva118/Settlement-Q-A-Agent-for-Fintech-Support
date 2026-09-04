from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db
from app.repository import get_transaction_records
from app.schemas import InvestigationExplanationResponse, InvestigationResult
from app.services.ai_explanation import (
    LLMConfigurationError,
    LLMProviderError,
    LLMTimeoutError,
    generate_explanation,
)
from app.services.investigation import TransactionNotFoundError, investigate_transaction


app = FastAPI(title="PS-8 Settlement Q&A Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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


@app.post(
    "/investigations/{transaction_id}/explanation",
    response_model=InvestigationExplanationResponse,
    summary="Generate a support explanation for a deterministic investigation",
)
def create_investigation_explanation(
    transaction_id: str = Path(description="Transaction ID to investigate and explain."),
    db: Session = Depends(get_db),
) -> dict:
    try:
        investigation = investigate_transaction(transaction_id, db)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unexpected investigation error") from exc

    try:
        explanation = generate_explanation(investigation)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail="AI explanation service is not configured") from exc
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=504, detail="AI explanation service timed out") from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail="AI explanation service is unavailable") from exc

    return {
        "transaction_id": transaction_id,
        "investigation": investigation,
        "explanation": explanation,
    }
