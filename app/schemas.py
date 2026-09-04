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


class AIExplanation(BaseModel):
    summary: str
    what_happened: str
    why: str
    evidence: list[str]
    recommended_action: str
    uncertainty: str


class InvestigationExplanationResponse(BaseModel):
    transaction_id: str
    investigation: InvestigationResult
    explanation: AIExplanation
