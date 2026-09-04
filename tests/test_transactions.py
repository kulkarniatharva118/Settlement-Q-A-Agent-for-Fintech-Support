from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import app
from app.database import Base, get_db
from app.repository import get_transaction_records
from scripts.import_csv import import_csvs


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestingSessionLocal() as session:
        import_csvs(session)
        yield session


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


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
