from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.investigation import TransactionNotFoundError, investigate_transaction


def test_demo_001_normal_settlement(db_session: Session) -> None:
    result = investigate_transaction("TXN-DEMO-001", db_session)

    assert result["settlement_status"] == "settlement_complete"
    assert result["root_cause"] == "normal_settlement"
    assert result["confidence"] >= 0.9
    assert "amount_mismatch" not in result["discrepancies"]
    assert "missing_bank_record" not in result["discrepancies"]
    assert "missing_ledger_record" not in result["discrepancies"]


def test_demo_002_bank_delay(db_session: Session) -> None:
    result = investigate_transaction("TXN-DEMO-002", db_session)

    assert result["settlement_status"] == "settlement_delayed"
    assert result["root_cause"] == "bank_delay"
    assert "PENDING" in result["bank_status"]
    assert "ACCRUED" in result["ledger_status"]
    assert result["confidence"] >= 0.7


def test_demo_003_missing_bank(db_session: Session) -> None:
    result = investigate_transaction("TXN-DEMO-003", db_session)

    assert result["settlement_status"] == "bank_record_missing"
    assert result["root_cause"] == "missing_bank_record"
    assert "missing_bank_record" in result["discrepancies"]
    assert result["bank_status"] == ["missing"]


def test_demo_004_amount_mismatch(db_session: Session) -> None:
    result = investigate_transaction("TXN-DEMO-004", db_session)

    assert result["settlement_status"] == "reconciliation_required"
    assert result["root_cause"] == "amount_mismatch"
    assert "amount_mismatch" in result["discrepancies"]
    assert result["confidence"] >= 0.8


def test_demo_005_missing_ledger(db_session: Session) -> None:
    result = investigate_transaction("TXN-DEMO-005", db_session)

    assert result["settlement_status"] == "ledger_record_missing"
    assert result["root_cause"] == "missing_ledger_record"
    assert "missing_ledger_record" in result["discrepancies"]
    assert result["ledger_status"] == ["missing"]


def test_demo_006_settlement_never_initiated(db_session: Session) -> None:
    result = investigate_transaction("TXN-DEMO-006", db_session)

    assert result["settlement_status"] == "settlement_not_initiated"
    assert result["root_cause"] == "settlement_never_initiated"
    assert "CAPTURED_UNSETTLED" in result["gateway_status"]
    assert "missing_bank_record" in result["discrepancies"]
    assert "missing_ledger_record" in result["discrepancies"]


def test_demo_007_duplicate_settlement(db_session: Session) -> None:
    result = investigate_transaction("TXN-DEMO-007", db_session)

    assert result["settlement_status"] == "duplicate_settlement_evidence"
    assert result["root_cause"] == "duplicate_settlement"
    assert "duplicate_bank_record" in result["discrepancies"]
    assert "duplicate_ledger_record" in result["discrepancies"]
    assert result["confidence"] >= 0.8


def test_conflicting_evidence_is_low_confidence(db_session: Session) -> None:
    result = investigate_transaction("TXN-000020", db_session)

    assert result["settlement_status"] == "conflicting_evidence"
    assert result["root_cause"] == "conflicting_evidence"
    assert "conflicting_evidence" in result["discrepancies"]
    assert "status_conflict" in result["discrepancies"]
    assert result["confidence"] < 0.6


def test_nonexistent_transaction_raises_not_found(db_session: Session) -> None:
    try:
        investigate_transaction("TXN-NOT-REAL", db_session)
    except TransactionNotFoundError as exc:
        assert "TXN-NOT-REAL" in str(exc)
    else:
        raise AssertionError("Expected TransactionNotFoundError")


def test_investigation_endpoint_returns_structured_result(client: TestClient) -> None:
    response = client.get("/investigations/TXN-DEMO-001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["transaction_id"] == "TXN-DEMO-001"
    assert payload["settlement_status"] == "settlement_complete"
    assert "evidence" in payload
    assert "recommended_action" in payload


def test_investigation_endpoint_returns_404(client: TestClient) -> None:
    response = client.get("/investigations/TXN-NOT-REAL")

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction TXN-NOT-REAL not found"
