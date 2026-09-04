from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("transaction_id", "settlement_status", "root_cause", "expected_discrepancy"),
    [
        ("TXN-DEMO-001", "settlement_complete", "normal_settlement", None),
        ("TXN-DEMO-002", "settlement_delayed", "bank_delay", None),
        ("TXN-DEMO-003", "bank_record_missing", "missing_bank_record", "missing_bank_record"),
        ("TXN-DEMO-004", "reconciliation_required", "amount_mismatch", "amount_mismatch"),
        ("TXN-DEMO-005", "ledger_record_missing", "missing_ledger_record", "missing_ledger_record"),
        ("TXN-DEMO-006", "settlement_not_initiated", "settlement_never_initiated", "missing_bank_record"),
        ("TXN-DEMO-007", "duplicate_settlement_evidence", "duplicate_settlement", "duplicate_bank_record"),
    ],
)
def test_investigation_endpoint_for_demo_transactions(
    client: TestClient,
    transaction_id: str,
    settlement_status: str,
    root_cause: str,
    expected_discrepancy: str | None,
) -> None:
    response = client.get(f"/investigations/{transaction_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["transaction_id"] == transaction_id
    assert payload["settlement_status"] == settlement_status
    assert payload["root_cause"] == root_cause
    assert isinstance(payload["confidence"], float)
    assert 0 <= payload["confidence"] <= 1
    assert isinstance(payload["gateway_status"], list)
    assert isinstance(payload["bank_status"], list)
    assert isinstance(payload["ledger_status"], list)
    assert isinstance(payload["discrepancies"], list)
    assert isinstance(payload["evidence"], list)
    assert payload["recommended_action"]
    if expected_discrepancy:
        assert expected_discrepancy in payload["discrepancies"]


def test_investigation_endpoint_returns_404_for_unknown_transaction(client: TestClient) -> None:
    response = client.get("/investigations/TXN-DOES-NOT-EXIST")

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction TXN-DOES-NOT-EXIST not found"


def test_investigation_endpoint_hides_unexpected_error_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_investigation(transaction_id, db):
        raise RuntimeError("database password leaked here")

    monkeypatch.setattr("app.api.investigate_transaction", broken_investigation)

    response = client.get("/investigations/TXN-DEMO-001")

    assert response.status_code == 500
    assert response.json()["detail"] == "Unexpected investigation error"
