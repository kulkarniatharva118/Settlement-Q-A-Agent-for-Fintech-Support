from __future__ import annotations

from pydantic import BaseModel, Field


class InvestigationResult(BaseModel):
    transaction_id: str
    gateway_status: list[str]
    bank_status: list[str]
    ledger_status: list[str]
    settlement_status: str
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    discrepancies: list[str]
    evidence: list[str]
    recommended_action: str
