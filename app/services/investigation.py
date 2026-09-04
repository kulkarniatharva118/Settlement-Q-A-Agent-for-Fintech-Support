from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.repository import get_transaction_records


class TransactionNotFoundError(ValueError):
    pass


COMPLETED_GATEWAY_STATUSES = {"CAPTURED"}
DELAYED_GATEWAY_STATUSES = {"SETTLEMENT_PENDING"}
UNSETTLED_GATEWAY_STATUSES = {"CAPTURED_UNSETTLED"}
REVERSED_GATEWAY_STATUSES = {"CAPTURE_REVERSED"}
COMPLETED_BANK_STATUSES = {"SETTLED"}
DELAYED_BANK_STATUSES = {"PENDING"}
COMPLETED_LEDGER_STATUSES = {"POSTED"}
INTERMEDIATE_LEDGER_STATUSES = {"ACCRUED"}
DUPLICATE_LEDGER_STATUSES = {"DUPLICATE_HOLD"}
CONFLICT_LEDGER_STATUSES = {"SUSPENSE", "REVERSAL_POSTED"}


def investigate_transaction(transaction_id: str, db: Session) -> dict[str, Any]:
    records = get_transaction_records(db, transaction_id)
    if records is None:
        raise TransactionNotFoundError(f"Transaction not found: {transaction_id}")

    gateway = records["gateway"]
    bank = records["bank"]
    ledger = records["ledger"]

    gateway_statuses = _unique_values(gateway, "gateway_status")
    bank_statuses = _unique_values(bank, "bank_status")
    ledger_statuses = _unique_values(ledger, "ledger_status")

    discrepancies = _detect_discrepancies(gateway, bank, ledger)
    evidence = _build_evidence(gateway, bank, ledger)
    settlement_status, root_cause, recommended_action, confidence = _classify(
        gateway_statuses=gateway_statuses,
        bank_statuses=bank_statuses,
        ledger_statuses=ledger_statuses,
        discrepancies=discrepancies,
    )

    return {
        "transaction_id": transaction_id,
        "gateway_status": gateway_statuses or ["missing"],
        "bank_status": bank_statuses or ["missing"],
        "ledger_status": ledger_statuses or ["missing"],
        "settlement_status": settlement_status,
        "root_cause": root_cause,
        "confidence": confidence,
        "discrepancies": discrepancies,
        "evidence": evidence,
        "recommended_action": recommended_action,
    }


def _unique_values(records: list[dict[str, Any]], key: str) -> list[str]:
    values = sorted({str(record[key]) for record in records if record.get(key)})
    return values


def _amounts(records: list[dict[str, Any]]) -> set[Decimal]:
    return {Decimal(str(record["amount"])) for record in records if record.get("amount") is not None}


def _values(records: list[dict[str, Any]], key: str) -> set[str]:
    return {str(record[key]) for record in records if record.get(key)}


def _detect_discrepancies(
    gateway: list[dict[str, Any]],
    bank: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
) -> list[str]:
    discrepancies: list[str] = []

    if not gateway:
        discrepancies.append("missing_gateway_record")
    if not bank:
        discrepancies.append("missing_bank_record")
    if not ledger:
        discrepancies.append("missing_ledger_record")
    if len(gateway) > 1:
        discrepancies.append("duplicate_gateway_record")
    if len(bank) > 1:
        discrepancies.append("duplicate_bank_record")
    if len(ledger) > 1:
        discrepancies.append("duplicate_ledger_record")

    amount_sets = [_amounts(records) for records in (gateway, bank, ledger) if records]
    all_amounts = set().union(*amount_sets) if amount_sets else set()
    if len(all_amounts) > 1:
        discrepancies.append("amount_mismatch")

    payment_ids = set().union(*[_values(records, "payment_id") for records in (gateway, bank, ledger)])
    if len(payment_ids) > 1:
        discrepancies.append("payment_id_mismatch")

    settlement_ids = set().union(*[_values(records, "settlement_id") for records in (gateway, bank, ledger)])
    if len(settlement_ids) > 1:
        discrepancies.append("settlement_id_mismatch")

    gateway_statuses = set(_unique_values(gateway, "gateway_status"))
    bank_statuses = set(_unique_values(bank, "bank_status"))
    ledger_statuses = set(_unique_values(ledger, "ledger_status"))
    if _has_status_conflict(gateway_statuses, bank_statuses, ledger_statuses):
        discrepancies.append("status_conflict")
    if _is_conflicting_evidence(discrepancies, gateway_statuses, bank_statuses, ledger_statuses):
        discrepancies.append("conflicting_evidence")

    return discrepancies


def _has_status_conflict(
    gateway_statuses: set[str],
    bank_statuses: set[str],
    ledger_statuses: set[str],
) -> bool:
    if gateway_statuses & REVERSED_GATEWAY_STATUSES and (
        bank_statuses & COMPLETED_BANK_STATUSES or ledger_statuses & COMPLETED_LEDGER_STATUSES
    ):
        return True
    if gateway_statuses & DELAYED_GATEWAY_STATUSES and ledger_statuses & COMPLETED_LEDGER_STATUSES:
        return True
    if bank_statuses & DELAYED_BANK_STATUSES and ledger_statuses & COMPLETED_LEDGER_STATUSES:
        return True
    if ledger_statuses & CONFLICT_LEDGER_STATUSES:
        return True
    return False


def _is_conflicting_evidence(
    discrepancies: list[str],
    gateway_statuses: set[str],
    bank_statuses: set[str],
    ledger_statuses: set[str],
) -> bool:
    if "status_conflict" in discrepancies:
        return True
    if "settlement_id_mismatch" in discrepancies or "payment_id_mismatch" in discrepancies:
        return True
    if gateway_statuses & REVERSED_GATEWAY_STATUSES and not bank_statuses and not ledger_statuses:
        return True
    return False


def _build_evidence(
    gateway: list[dict[str, Any]],
    bank: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
) -> list[str]:
    evidence: list[str] = []
    evidence.extend(_system_evidence("Gateway", gateway, "gateway_status", "gateway_reference"))
    evidence.extend(_system_evidence("Bank", bank, "bank_status", "utr"))
    evidence.extend(_system_evidence("Ledger", ledger, "ledger_status", "ledger_entry_id"))
    return evidence


def _system_evidence(
    label: str,
    records: list[dict[str, Any]],
    status_key: str,
    reference_key: str,
) -> list[str]:
    if not records:
        return [f"No {label.lower()} record was found."]

    statuses = ", ".join(_unique_values(records, status_key))
    amounts = ", ".join(str(amount) for amount in sorted(_amounts(records)))
    settlement_ids = ", ".join(sorted(_values(records, "settlement_id"))) or "missing"
    references = ", ".join(sorted(_values(records, reference_key)))
    return [
        f"{label} record count is {len(records)}.",
        f"{label} status is {statuses}.",
        f"{label} amount is {amounts}.",
        f"{label} settlement_id is {settlement_ids}.",
        f"{label} reference is {references}.",
    ]


def _classify(
    gateway_statuses: list[str],
    bank_statuses: list[str],
    ledger_statuses: list[str],
    discrepancies: list[str],
) -> tuple[str, str, str, float]:
    gateway_set = set(gateway_statuses)
    bank_set = set(bank_statuses)
    ledger_set = set(ledger_statuses)

    if "conflicting_evidence" in discrepancies:
        return (
            "conflicting_evidence",
            "conflicting_evidence",
            "Escalate for manual investigation.",
            0.35,
        )

    if gateway_set & UNSETTLED_GATEWAY_STATUSES and "missing_bank_record" in discrepancies and "missing_ledger_record" in discrepancies:
        return (
            "settlement_not_initiated",
            "settlement_never_initiated",
            "Verify whether settlement initiation was triggered for this payment.",
            0.9,
        )

    if "duplicate_bank_record" in discrepancies or "duplicate_ledger_record" in discrepancies:
        return (
            "duplicate_settlement_evidence",
            "duplicate_settlement",
            "Review duplicate settlement records before taking further action.",
            0.85,
        )

    if "amount_mismatch" in discrepancies:
        return (
            "reconciliation_required",
            "amount_mismatch",
            "Escalate for financial reconciliation due to amount mismatch.",
            0.9,
        )

    if "missing_bank_record" in discrepancies:
        return (
            "bank_record_missing",
            "missing_bank_record",
            "Check bank settlement processing and reconciliation logs.",
            0.75,
        )

    if "missing_ledger_record" in discrepancies:
        return (
            "ledger_record_missing",
            "missing_ledger_record",
            "Verify ledger posting/reconciliation.",
            0.8,
        )

    if bank_set & DELAYED_BANK_STATUSES or ledger_set & INTERMEDIATE_LEDGER_STATUSES or gateway_set & DELAYED_GATEWAY_STATUSES:
        return (
            "settlement_delayed",
            "bank_delay",
            "Verify bank-side settlement processing/status.",
            0.8,
        )

    if (
        gateway_set <= COMPLETED_GATEWAY_STATUSES
        and bank_set <= COMPLETED_BANK_STATUSES
        and ledger_set <= COMPLETED_LEDGER_STATUSES
        and gateway_set
        and bank_set
        and ledger_set
        and not discrepancies
    ):
        return (
            "settlement_complete",
            "normal_settlement",
            "Settlement appears complete; no further action required.",
            0.95,
        )

    return (
        "insufficient_evidence",
        "insufficient_evidence",
        "Escalate for manual investigation.",
        0.4,
    )
