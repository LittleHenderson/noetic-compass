"""Run the CAS broker-funding HTTP contract against a loopback sandbox."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.account_ledger import stable_ledger_id
from cas_forex.money_movement import MovementKind, STATUS_PENDING, STATUS_SETTLED
from cas_forex.payment_providers import BrokerFundingWebhookProvider
from cas_forex.time_utils import utc_now


LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8775")
    parser.add_argument("--account-id", default="cas-sandbox-broker-account")
    parser.add_argument("--destination-id", default="cas-sandbox-destination")
    parser.add_argument("--amount-usd", type=float, default=25.0)
    parser.add_argument(
        "--api-key",
        default=os.environ.get(
            "CAS_BROKER_FUNDING_SANDBOX_API_KEY",
            "cas-local-sandbox-api-key",
        ),
    )
    parser.add_argument(
        "--admin-key",
        default=os.environ.get(
            "CAS_BROKER_FUNDING_SANDBOX_ADMIN_KEY",
            "cas-local-sandbox-admin-key",
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "evidence_runs" / "broker_funding_conformance"),
    )
    return parser


def run(args: argparse.Namespace) -> dict:
    parsed = urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        raise ValueError(
            "Conformance runner is sandbox-only and accepts loopback HTTP URLs only."
        )
    amount = round(float(args.amount_usd), 2)
    if amount <= 0:
        raise ValueError("amount_usd must be positive")
    generated_at = utc_now()
    idempotency_key = stable_ledger_id(
        "broker-funding-conformance",
        generated_at.isoformat(),
        args.account_id,
        amount,
    )
    provider = BrokerFundingWebhookProvider(
        base_url=args.base_url,
        api_key=args.api_key,
        account_id=args.account_id,
        is_real=False,
    )
    health_before = requests.get(f"{args.base_url}/health", timeout=10).json()
    before = float(health_before["account"]["balance_usd"])
    first = provider.withdraw(
        amount,
        destination_id=args.destination_id,
        kind=MovementKind.PAYOUT,
        idempotency_key=idempotency_key,
    )
    replay = provider.withdraw(
        amount,
        destination_id=args.destination_id,
        kind=MovementKind.PAYOUT,
        idempotency_key=idempotency_key,
    )
    lookup = provider.reconcile_idempotency_key(
        idempotency_key,
        kind=MovementKind.PAYOUT,
    )
    transition = requests.post(
        f"{args.base_url}/v1/sandbox/movements/{first.reference}/transition",
        json={"status": "paid", "detail": "Loopback conformance settlement."},
        headers={"Authorization": f"Bearer {args.admin_key}"},
        timeout=10,
    )
    transition.raise_for_status()
    settled = provider.reconcile(first.reference, kind=MovementKind.PAYOUT)
    settled_replay = provider.withdraw(
        amount,
        destination_id=args.destination_id,
        kind=MovementKind.PAYOUT,
        idempotency_key=idempotency_key,
    )
    health_after = requests.get(f"{args.base_url}/health", timeout=10).json()
    after = float(health_after["account"]["balance_usd"])

    checks = [
        _check("sandbox_identity", health_before.get("sandbox_only") is True),
        _check("pending_first", first.status == STATUS_PENDING),
        _check("same_key_same_reference", first.reference == replay.reference),
        _check(
            "idempotency_lookup",
            lookup is not None and lookup.reference == first.reference,
        ),
        _check("settled_after_transition", settled is not None and settled.status == STATUS_SETTLED),
        _check(
            "concrete_balance_evidence",
            settled is not None
            and settled.before_balance_usd == before
            and settled.after_balance_usd == round(before - amount, 2)
            and bool(settled.balance_snapshot_reference),
        ),
        _check("settled_replay_same_reference", settled_replay.reference == first.reference),
        _check("exactly_one_balance_delta", after == round(before - amount, 2)),
    ]
    passed = all(item["passed"] for item in checks)
    report = {
        "report_kind": "cas_forex_broker_funding_conformance",
        "generated_at": generated_at.isoformat(),
        "status": "ACCEPT" if passed else "FLAG_FOR_HUMAN_REVIEW",
        "sandbox_only": True,
        "base_url": args.base_url,
        "account_id": args.account_id,
        "idempotency_key": idempotency_key,
        "provider_reference": first.reference,
        "amount_usd": amount,
        "before_balance_usd": before,
        "after_balance_usd": after,
        "balance_snapshot_reference": (
            settled.balance_snapshot_reference if settled is not None else None
        ),
        "checks": checks,
        "claim_boundary": (
            "ACCEPT proves the loopback sandbox contract only. It is not evidence "
            "that Hugo's Way exposes a funding API or that external money moved."
        ),
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"broker-funding-conformance-{generated_at.strftime('%Y%m%d%H%M%S')}.json"
    )
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report["artifact_path"] = str(output_path)
    return report


def _check(check_id: str, passed: bool) -> dict[str, object]:
    return {"check_id": check_id, "passed": bool(passed)}


def main() -> int:
    report = run(build_parser().parse_args())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
