from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.repository import get_transaction_records


def test_normal_transaction_has_records_in_all_systems(db_session: Session) -> None:
    records = get_transaction_records(db_session, "TXN-DEMO-001")

    assert records is not None
    assert len(records["gateway"]) == 1
    assert len(records["bank"]) >= 1
    assert len(records["ledger"]) >= 1


def test_missing_bank_record_returns_empty_bank_list(client: TestClient) -> None:
    response = client.get("/transactions/TXN-DEMO-003")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["gateway"]) == 1
    assert payload["bank"] == []
    assert len(payload["ledger"]) >= 1


def test_missing_ledger_record_returns_empty_ledger_list(client: TestClient) -> None:
    response = client.get("/transactions/TXN-DEMO-005")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["gateway"]) == 1
    assert len(payload["bank"]) >= 1
    assert payload["ledger"] == []


def test_duplicate_records_are_returned_as_lists(client: TestClient) -> None:
    response = client.get("/transactions/TXN-DEMO-007")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["gateway"]) == 1
    assert len(payload["bank"]) > 1 or len(payload["ledger"]) > 1


def test_nonexistent_transaction_returns_404(client: TestClient) -> None:
    response = client.get("/transactions/TXN-NOT-REAL")

    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"
