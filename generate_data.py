from __future__ import annotations

import csv
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path


SEED = 8008
TOTAL_TRANSACTIONS = 1_000
DATA_DIR = Path("data")

GATEWAY_COLUMNS = [
    "transaction_id",
    "payment_id",
    "settlement_id",
    "amount",
    "currency",
    "timestamp",
    "gateway_status",
    "payment_method",
    "merchant_id",
    "gateway_reference",
    "settlement_initiated_at",
]

BANK_COLUMNS = [
    "transaction_id",
    "payment_id",
    "settlement_id",
    "amount",
    "currency",
    "timestamp",
    "bank_status",
    "bank_account_id",
    "utr",
    "cleared_at",
]

LEDGER_COLUMNS = [
    "transaction_id",
    "payment_id",
    "settlement_id",
    "amount",
    "currency",
    "timestamp",
    "ledger_status",
    "ledger_entry_id",
    "posted_at",
    "reconciliation_batch",
]

SCENARIOS = [
    "normal_settlement",
    "bank_delay",
    "missing_bank_record",
    "amount_mismatch",
    "missing_ledger_record",
    "settlement_never_initiated",
    "duplicate_settlement",
    "insufficient_conflicting_evidence",
]

DEMO_SCENARIOS = {
    "TXN-DEMO-001": "normal_settlement",
    "TXN-DEMO-002": "bank_delay",
    "TXN-DEMO-003": "missing_bank_record",
    "TXN-DEMO-004": "amount_mismatch",
    "TXN-DEMO-005": "missing_ledger_record",
    "TXN-DEMO-006": "settlement_never_initiated",
    "TXN-DEMO-007": "duplicate_settlement",
}


@dataclass(frozen=True)
class BaseTransaction:
    transaction_id: str
    payment_id: str
    settlement_id: str
    amount: Decimal
    currency: str
    timestamp: datetime
    settlement_initiated_at: datetime | None
    payment_method: str
    merchant_id: str
    scenario: str


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def iso(dt: datetime | None) -> str:
    return "" if dt is None else dt.replace(microsecond=0).isoformat()


def random_amount(rng: random.Random) -> Decimal:
    cents = rng.randint(199, 249_999)
    return Decimal(cents) / Decimal("100")


def choose_scenario(rng: random.Random) -> str:
    return rng.choices(
        SCENARIOS,
        weights=[680, 95, 40, 55, 40, 35, 35, 20],
        k=1,
    )[0]


def build_base_transaction(
    rng: random.Random,
    index: int,
    scenario: str,
    transaction_id: str | None = None,
) -> BaseTransaction:
    created_at = datetime(2026, 8, 1, 8, 0, 0) + timedelta(
        minutes=rng.randint(0, 44_640),
        seconds=rng.randint(0, 59),
    )
    settlement_id = f"SET-{created_at:%Y%m%d}-{rng.randint(100000, 999999)}"
    settlement_initiated_at = created_at + timedelta(
        minutes=rng.randint(5, 240),
        seconds=rng.randint(0, 59),
    )

    if scenario == "settlement_never_initiated":
        settlement_id = ""
        settlement_initiated_at = None

    txn_id = transaction_id or f"TXN-{index:06d}"

    return BaseTransaction(
        transaction_id=txn_id,
        payment_id=f"PAY-{index:06d}-{rng.randint(100, 999)}",
        settlement_id=settlement_id,
        amount=random_amount(rng),
        currency="INR",
        timestamp=created_at,
        settlement_initiated_at=settlement_initiated_at,
        payment_method=rng.choice(["UPI", "CARD", "NETBANKING", "WALLET"]),
        merchant_id=f"MID-{rng.randint(1001, 1025)}",
        scenario=scenario,
    )


def gateway_row(txn: BaseTransaction, rng: random.Random) -> dict[str, str]:
    status = "CAPTURED"
    if txn.scenario == "settlement_never_initiated":
        status = "CAPTURED_UNSETTLED"
    elif txn.scenario == "insufficient_conflicting_evidence":
        status = rng.choice(["CAPTURED", "SETTLEMENT_PENDING", "CAPTURE_REVERSED"])

    return {
        "transaction_id": txn.transaction_id,
        "payment_id": txn.payment_id,
        "settlement_id": txn.settlement_id,
        "amount": money(txn.amount),
        "currency": txn.currency,
        "timestamp": iso(txn.timestamp),
        "gateway_status": status,
        "payment_method": txn.payment_method,
        "merchant_id": txn.merchant_id,
        "gateway_reference": f"GW-{rng.randint(10_000_000, 99_999_999)}",
        "settlement_initiated_at": iso(txn.settlement_initiated_at),
    }


def bank_rows(txn: BaseTransaction, rng: random.Random) -> list[dict[str, str]]:
    if txn.scenario in {"missing_bank_record", "settlement_never_initiated"}:
        return []

    amount = txn.amount
    bank_status = "SETTLED"
    timestamp = (txn.settlement_initiated_at or txn.timestamp) + timedelta(
        hours=rng.randint(1, 8),
        minutes=rng.randint(0, 59),
    )
    cleared_at = timestamp + timedelta(minutes=rng.randint(5, 90))
    settlement_id = txn.settlement_id

    if txn.scenario == "bank_delay":
        bank_status = "PENDING"
        timestamp = txn.timestamp + timedelta(days=rng.randint(2, 5), minutes=rng.randint(1, 240))
        cleared_at = None
    elif txn.scenario == "amount_mismatch":
        delta = Decimal(rng.choice(["1.00", "2.50", "5.00", "10.00", "-1.00", "-2.50"]))
        amount = max(Decimal("1.00"), txn.amount + delta)
    elif txn.scenario == "insufficient_conflicting_evidence":
        bank_status = rng.choice(["RETURNED", "PENDING", "SETTLED"])
        if rng.random() < 0.5:
            settlement_id = f"SET-{txn.timestamp:%Y%m%d}-{rng.randint(100000, 999999)}"

    row = {
        "transaction_id": txn.transaction_id,
        "payment_id": txn.payment_id,
        "settlement_id": settlement_id,
        "amount": money(amount),
        "currency": txn.currency,
        "timestamp": iso(timestamp),
        "bank_status": bank_status,
        "bank_account_id": f"BA-{rng.randint(3001, 3010)}",
        "utr": f"UTR{rng.randint(10**11, 10**12 - 1)}",
        "cleared_at": iso(cleared_at),
    }

    rows = [row]
    if txn.scenario == "duplicate_settlement":
        duplicate = row.copy()
        duplicate["utr"] = f"UTR{rng.randint(10**11, 10**12 - 1)}"
        duplicate["timestamp"] = iso(timestamp + timedelta(minutes=rng.randint(3, 45)))
        duplicate["cleared_at"] = iso(cleared_at + timedelta(minutes=rng.randint(3, 45)))
        rows.append(duplicate)

    return rows


def ledger_rows(txn: BaseTransaction, rng: random.Random) -> list[dict[str, str]]:
    if txn.scenario in {"missing_ledger_record", "settlement_never_initiated"}:
        return []

    amount = txn.amount
    ledger_status = "POSTED"
    posted_at = (txn.settlement_initiated_at or txn.timestamp) + timedelta(
        hours=rng.randint(2, 12),
        minutes=rng.randint(0, 59),
    )
    settlement_id = txn.settlement_id

    if txn.scenario == "amount_mismatch":
        amount = txn.amount
    elif txn.scenario == "bank_delay":
        ledger_status = "ACCRUED"
        posted_at = txn.timestamp + timedelta(hours=rng.randint(6, 24))
    elif txn.scenario == "insufficient_conflicting_evidence":
        ledger_status = rng.choice(["POSTED", "SUSPENSE", "REVERSAL_POSTED"])
        amount = txn.amount + Decimal(rng.choice(["0.00", "3.00", "-3.00"]))
        if rng.random() < 0.5:
            settlement_id = f"SET-{txn.timestamp:%Y%m%d}-{rng.randint(100000, 999999)}"

    row = {
        "transaction_id": txn.transaction_id,
        "payment_id": txn.payment_id,
        "settlement_id": settlement_id,
        "amount": money(amount),
        "currency": txn.currency,
        "timestamp": iso(txn.timestamp),
        "ledger_status": ledger_status,
        "ledger_entry_id": f"LED-{rng.randint(10_000_000, 99_999_999)}",
        "posted_at": iso(posted_at),
        "reconciliation_batch": f"RB-{posted_at:%Y%m%d}",
    }

    rows = [row]
    if txn.scenario == "duplicate_settlement":
        reversal = row.copy()
        reversal["ledger_status"] = "DUPLICATE_HOLD"
        reversal["ledger_entry_id"] = f"LED-{rng.randint(10_000_000, 99_999_999)}"
        reversal["posted_at"] = iso(posted_at + timedelta(minutes=rng.randint(5, 60)))
        rows.append(reversal)

    return rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def generate() -> tuple[Counter[str], dict[str, int], set[str]]:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(exist_ok=True)

    gateway_records: list[dict[str, str]] = []
    bank_records: list[dict[str, str]] = []
    ledger_records: list[dict[str, str]] = []
    scenario_counts: Counter[str] = Counter()
    duplicate_settlement_ids: set[str] = set()

    demo_offset = TOTAL_TRANSACTIONS - len(DEMO_SCENARIOS)
    demo_ids = set(DEMO_SCENARIOS)

    for index in range(1, TOTAL_TRANSACTIONS + 1):
        if index > demo_offset:
            demo_position = index - demo_offset
            transaction_id = f"TXN-DEMO-{demo_position:03d}"
            scenario = DEMO_SCENARIOS[transaction_id]
        else:
            transaction_id = None
            scenario = choose_scenario(rng)

        txn = build_base_transaction(rng, index, scenario, transaction_id)
        if txn.transaction_id in demo_ids and txn.scenario != DEMO_SCENARIOS[txn.transaction_id]:
            raise RuntimeError(f"Demo scenario mismatch for {txn.transaction_id}")
        if scenario == "duplicate_settlement":
            duplicate_settlement_ids.add(txn.transaction_id)

        scenario_counts[scenario] += 1
        gateway_records.append(gateway_row(txn, rng))
        bank_records.extend(bank_rows(txn, rng))
        ledger_records.extend(ledger_rows(txn, rng))

    write_csv(DATA_DIR / "gateway.csv", GATEWAY_COLUMNS, gateway_records)
    write_csv(DATA_DIR / "bank.csv", BANK_COLUMNS, bank_records)
    write_csv(DATA_DIR / "ledger.csv", LEDGER_COLUMNS, ledger_records)

    record_counts = {
        "gateway.csv": len(gateway_records),
        "bank.csv": len(bank_records),
        "ledger.csv": len(ledger_records),
    }
    return scenario_counts, record_counts, duplicate_settlement_ids


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_columns(rows: list[dict[str, str]], expected_columns: list[str], filename: str) -> None:
    if not rows:
        return
    actual_columns = list(rows[0].keys())
    if actual_columns != expected_columns:
        raise AssertionError(f"{filename} has columns {actual_columns}, expected {expected_columns}")


def duplicate_transaction_ids(rows: list[dict[str, str]]) -> set[str]:
    counts = Counter(row["transaction_id"] for row in rows)
    return {transaction_id for transaction_id, count in counts.items() if count > 1}


def verify_outputs(scenario_counts: Counter[str], duplicate_settlement_ids: set[str]) -> None:
    paths = {
        "gateway.csv": DATA_DIR / "gateway.csv",
        "bank.csv": DATA_DIR / "bank.csv",
        "ledger.csv": DATA_DIR / "ledger.csv",
    }

    missing_files = [filename for filename, path in paths.items() if not path.exists()]
    if missing_files:
        raise AssertionError(f"Missing generated CSV files: {', '.join(missing_files)}")

    gateway = read_csv(paths["gateway.csv"])
    bank = read_csv(paths["bank.csv"])
    ledger = read_csv(paths["ledger.csv"])

    assert_columns(gateway, GATEWAY_COLUMNS, "gateway.csv")
    assert_columns(bank, BANK_COLUMNS, "bank.csv")
    assert_columns(ledger, LEDGER_COLUMNS, "ledger.csv")

    gateway_ids = {row["transaction_id"] for row in gateway}
    missing_demo_ids = [transaction_id for transaction_id in DEMO_SCENARIOS if transaction_id not in gateway_ids]
    if missing_demo_ids:
        raise AssertionError(f"Missing demo transactions: {', '.join(missing_demo_ids)}")

    missing_scenarios = [scenario for scenario in SCENARIOS if scenario_counts[scenario] < 1]
    if missing_scenarios:
        raise AssertionError(f"No generated examples for scenarios: {', '.join(missing_scenarios)}")

    gateway_duplicates = duplicate_transaction_ids(gateway)
    if gateway_duplicates:
        raise AssertionError(f"gateway.csv has accidental duplicate transaction IDs: {gateway_duplicates}")

    bank_duplicates = duplicate_transaction_ids(bank)
    ledger_duplicates = duplicate_transaction_ids(ledger)
    unexpected_bank_duplicates = bank_duplicates - duplicate_settlement_ids
    unexpected_ledger_duplicates = ledger_duplicates - duplicate_settlement_ids
    if unexpected_bank_duplicates:
        raise AssertionError(f"bank.csv has unexpected duplicate transaction IDs: {unexpected_bank_duplicates}")
    if unexpected_ledger_duplicates:
        raise AssertionError(f"ledger.csv has unexpected duplicate transaction IDs: {unexpected_ledger_duplicates}")

    print("Verification passed:")
    print("  all three CSVs exist")
    print("  demo transactions TXN-DEMO-001 through TXN-DEMO-007 exist")
    print("  every scenario has at least one example")
    print("  CSV columns match expected schemas")
    print("  duplicate transaction IDs are limited to duplicate settlement examples")


def print_summary(scenario_counts: Counter[str], record_counts: dict[str, int]) -> None:
    print(f"Generated {TOTAL_TRANSACTIONS} transactions with seed {SEED}.")
    print("Records written:")
    for filename, count in record_counts.items():
        print(f"  {filename}: {count}")

    print("Scenario counts:")
    for scenario in SCENARIOS:
        print(f"  {scenario}: {scenario_counts[scenario]}")

    print("Demo transactions:")
    for transaction_id, scenario in DEMO_SCENARIOS.items():
        print(f"  {transaction_id}: {scenario}")


if __name__ == "__main__":
    counts, records, duplicate_ids = generate()
    print_summary(counts, records)
    verify_outputs(counts, duplicate_ids)
