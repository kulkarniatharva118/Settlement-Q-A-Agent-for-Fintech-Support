from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.ai_explanation import (
    LLMConfigurationError,
    LLMProviderError,
    LLMTimeoutError,
    generate_explanation,
)
from app.services.investigation import investigate_transaction


def _explanation_for(investigation: dict) -> dict:
    missing_bank = "missing_bank_record" in investigation["discrepancies"]
    missing_ledger = "missing_ledger_record" in investigation["discrepancies"]
    uncertain = investigation["root_cause"] in {"insufficient_evidence", "conflicting_evidence"}
    return {
        "summary": f"Deterministic result: {investigation['root_cause']}.",
        "what_happened": investigation["settlement_status"],
        "why": "The deterministic evidence supports the reported result.",
        "evidence": investigation["evidence"],
        "recommended_action": investigation["recommended_action"],
        "uncertainty": (
            "The available evidence is insufficient or conflicting; the cause cannot be determined."
            if uncertain
            else ("Bank evidence is missing." if missing_bank else "Ledger evidence is missing." if missing_ledger else "No material uncertainty reported.")
        ),
    }


@pytest.mark.parametrize(
    ("transaction_id", "required_text", "forbidden_text"),
    [
        ("TXN-DEMO-001", "normal_settlement", None),
        ("TXN-DEMO-002", "bank_delay", None),
        ("TXN-DEMO-003", "Bank evidence is missing", "rejected"),
        ("TXN-DEMO-004", "amount_mismatch", "fees"),
        ("TXN-DEMO-005", "Ledger evidence is missing", None),
        ("TXN-DEMO-007", "duplicate_settlement", None),
        ("TXN-000020", "cannot be determined", None),
    ],
)
def test_explanation_endpoint_uses_deterministic_investigation(
    client: TestClient,
    transaction_id: str,
    required_text: str,
    forbidden_text: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[dict] = []

    def fake_generate(investigation: dict) -> dict:
        received.append(investigation)
        return _explanation_for(investigation)

    monkeypatch.setattr("app.api.generate_explanation", fake_generate)

    response = client.post(f"/investigations/{transaction_id}/explanation")

    assert response.status_code == 200
    payload = response.json()
    assert received == [payload["investigation"]]
    rendered = json.dumps(payload["explanation"]).lower()
    assert required_text.lower() in rendered
    if forbidden_text:
        assert forbidden_text.lower() not in rendered


def test_explanation_endpoint_returns_404_before_calling_llm(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.generate_explanation", lambda _: pytest.fail("LLM should not be called"))

    response = client.post("/investigations/TXN-DOES-NOT-EXIST/explanation")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (LLMConfigurationError("missing"), 503, "AI explanation service is not configured"),
        (LLMProviderError("provider down"), 502, "AI explanation service is unavailable"),
        (LLMTimeoutError("slow provider"), 504, "AI explanation service timed out"),
    ],
)
def test_explanation_endpoint_hides_provider_error_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    def fail(_: dict) -> dict:
        raise error

    monkeypatch.setattr("app.api.generate_explanation", fail)

    response = client.post("/investigations/TXN-DEMO-001/explanation")

    assert response.status_code == status_code
    assert response.json()["detail"] == detail
    assert "provider down" not in response.text


def test_service_sends_only_structured_investigation_and_parses_json(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    investigation = investigate_transaction("TXN-DEMO-004", db_session)
    response_payload = _explanation_for(investigation)
    calls: list[dict] = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(response_payload)))])

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setattr("app.services.ai_explanation._get_client", lambda *_: fake_client)

    explanation = generate_explanation(investigation)

    assert explanation == response_payload
    assert len(calls) == 1
    prompt_investigation = json.loads(calls[0]["messages"][1]["content"])
    assert prompt_investigation == investigation
    assert "database" not in calls[0]["messages"][1]["content"].lower()
    assert calls[0]["temperature"] == 0


def test_service_requires_an_api_key(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    investigation = investigate_transaction("TXN-DEMO-001", db_session)

    with pytest.raises(LLMConfigurationError):
        generate_explanation(investigation)
