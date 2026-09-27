#!/usr/bin/env python3
"""Offline planning helpers. No cloud SDKs, credentials, network, or submission code.

The fixture reference is classical test machinery, not a quantum oracle or HELM.
A successful planning-policy check is not an execution authorization.
"""
from __future__ import annotations
import argparse
import itertools
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]


def positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def nonnegative_decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite nonnegative decimal")
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a decimal") from exc
    if not d.is_finite() or d < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return d


def estimate_qpu(snapshot: dict[str, Any], device: str, tasks: int, shots: int) -> dict[str, Any]:
    positive_int(tasks, "tasks")
    positive_int(shots, "shots")
    if device not in snapshot["rates"]:
        raise ValueError(f"Unknown device: {device}")
    rate = snapshot["rates"][device]
    task_rate = nonnegative_decimal(rate["task"], "task rate")
    shot_rate = nonnegative_decimal(rate["shot"], "shot rate")
    per_task = task_rate + shot_rate * shots
    return {
        "status": "ILLUSTRATIVE_OFFLINE_ESTIMATE_NOT_A_LIVE_QUOTE",
        "price_observed_on": snapshot["observed_on"],
        "device": device, "tasks": tasks, "shots_per_task": shots,
        "qpu_only_per_task_usd": format(per_task, "f"),
        "qpu_only_total_usd": format(per_task * tasks, "f"),
        "excluded": snapshot["excluded"],
        "cloud_submission_authorized": False,
    }


def budget_fits(*, cap: str, spent: str, reserved: str, proposed: str) -> bool:
    """Pure arithmetic only. Production code also needs atomic trusted storage."""
    values = {k: nonnegative_decimal(v, k) for k, v in
              {"cap": cap, "spent": spent, "reserved": reserved, "proposed": proposed}.items()}
    return values["spent"] + values["reserved"] + values["proposed"] <= values["cap"]


def validate_offline_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("schema") != "helm-q1-planning-policy/1.0":
        raise ValueError("Unsupported policy schema")
    if policy.get("mode") != "offline":
        raise ValueError("This helper validates offline planning only")
    if policy.get("quantum_feature_default") != "disabled":
        raise ValueError("The supplied planning policy must default to disabled")
    for key in ("cloud_submission_enabled", "paid_fallback_enabled", "training_changes_enabled", "authoritative_write_enabled"):
        if policy.get(key) is not False:
            raise ValueError(f"{key} must explicitly be false")
    if nonnegative_decimal(policy.get("cloud_budget_usd"), "cloud_budget_usd") != 0:
        raise ValueError("This planning package has no authorized cloud spend")
    if policy.get("trusted_execution_grant") is not None:
        raise ValueError("A supplied field cannot substitute for trusted host authorization")
    return {"status": "VALID_OFFLINE_PLANNING_POLICY", "cloud_submission_authorized": False,
            "warning": "This check is not a production authority or budget controller."}


def run_program(program: Sequence[int], x: int) -> int:
    if isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < 4:
        raise ValueError("x must be an integer in [0,3]")
    for op in program:
        if isinstance(op, bool) or not isinstance(op, int) or op not in range(4):
            raise ValueError("Each operation code must be an integer in [0,3]")
        if op == 1:
            x = (x + 1) % 4
        elif op == 2:
            x = (x + 3) % 4
        elif op == 3:
            x = 3 - x
    return x


def fixture_reference(length: int = 3) -> dict[str, Any]:
    positive_int(length, "length")
    if length > 7:
        raise ValueError("Reference helper is bounded to length <= 7")
    positive = negative = 0
    for program in itertools.product(range(4), repeat=length):
        outputs = [run_program(program, x) for x in range(4)]
        positive += outputs == [(x + 2) % 4 for x in range(4)]
        negative += outputs == [x % 2 for x in range(4)]
    return {"status": "CLASSICAL_REFERENCE_ONLY_NOT_QUANTUM_OR_HELM",
            "program_length": length, "candidates_checked": 4 ** length,
            "inputs_per_candidate": 4, "add2_valid_program_count": positive,
            "nonbijective_target_valid_program_count": negative,
            "answer_program_ids_exported": False,
            "warning": "Do not use evaluator counts or solved IDs to construct/tune the quantum search."}


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    quote = commands.add_parser("quote", help="Calculate a dated illustrative QPU-only price")
    quote.add_argument("--device", choices=["rigetti_cepheus", "iqm_garnet", "ionq_forte"], required=True)
    quote.add_argument("--tasks", type=int, default=1)
    quote.add_argument("--shots", type=int, default=1000)
    quote.add_argument("--snapshot", type=Path, default=ROOT / "sources/price_snapshot.json")
    check = commands.add_parser("check-policy", help="Validate the default offline-only planning policy")
    check.add_argument("--path", type=Path, default=ROOT / "config/policy.json")
    fixture = commands.add_parser("fixture-reference", help="Evaluate the finite classical test fixture")
    fixture.add_argument("--length", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        if args.command == "quote":
            result = estimate_qpu(read_json(args.snapshot), args.device, args.tasks, args.shots)
        elif args.command == "check-policy":
            result = validate_offline_policy(read_json(args.path))
        else:
            result = fixture_reference(args.length)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
