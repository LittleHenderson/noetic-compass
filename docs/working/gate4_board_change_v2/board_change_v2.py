#!/usr/bin/env python3
"""Offline control plane for the board-change v2 successor.

There is intentionally no provider client or external authority verifier in this runner.
It can validate/freeze a prompt plan, inspect state, seal already admitted evidence, and run
the corrected Claim-2 permutation analysis. ``authorize-full`` intentionally fails closed
until a separately reviewed trust-registry verifier is integrated. A future network adapter
must also be separate and must use this package's guarded admission contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core import (
    AttemptLedger,
    ContractError,
    ExperimentState,
    canonical_json_bytes,
    claim2_refit_permutation,
    complete_generation_if_ready,
    load_json,
    load_jsonl_strict,
    seal_corpus,
    sha256_bytes,
    start_labeling,
    validate_prompt_plan,
    validate_protocol_lock,
    verify_corpus_seal,
)


def _forbidden_hashes(path: str | None) -> list[str]:
    if not path:
        return []
    payload = load_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("seed_sha256s"), list):
        raise ContractError("forbidden seed file must contain a seed_sha256s array")
    return payload["seed_sha256s"]


def _forbidden_normalized_hashes(path: str | None) -> list[str]:
    if not path:
        return []
    payload = load_json(path)
    if not isinstance(payload, dict) or not isinstance(
        payload.get("normalized_seed_sha256s"), list
    ):
        raise ContractError(
            "forbidden seed file must contain a normalized_seed_sha256s array"
        )
    return payload["normalized_seed_sha256s"]


def _plan(path: str, forbidden_path: str | None = None):
    plan = load_json(path)
    validation = validate_prompt_plan(
        plan, forbidden_seed_hashes=_forbidden_hashes(forbidden_path),
        forbidden_normalized_seed_hashes=_forbidden_normalized_hashes(forbidden_path),
    )
    return plan, validation


def _protocol_lock(path: str, source_root: str, plan, forbidden_path: str | None = None):
    lock = load_json(path)
    validation = validate_protocol_lock(
        lock, source_root=source_root, prompt_plan=plan,
        forbidden_seed_hashes=_forbidden_hashes(forbidden_path),
        forbidden_normalized_seed_hashes=_forbidden_normalized_hashes(forbidden_path),
    )
    return lock, validation


def _write_json(path: str | Path, payload) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json_bytes(payload) + b"\n")


def command_validate_plan(args) -> dict:
    _, validation = _plan(args.plan, args.forbidden_seed_hashes)
    return validation


def command_init(args) -> dict:
    _, validation = _plan(args.plan, args.forbidden_seed_hashes)
    plan = load_json(args.plan)
    _, protocol_validation = _protocol_lock(
        args.protocol_lock, args.source_root, plan, args.forbidden_seed_hashes
    )
    state = ExperimentState(args.run_dir)
    return state.initialize(
        run_id=args.run_id,
        protocol_lock_sha256=protocol_validation["protocol_lock_sha256"],
        prompt_plan_sha256=validation["plan_sha256"],
    )


def command_freeze(args) -> dict:
    plan, _ = _plan(args.plan, args.forbidden_seed_hashes)
    protocol_lock, _ = _protocol_lock(
        args.protocol_lock, args.source_root, plan, args.forbidden_seed_hashes
    )
    return ExperimentState(args.run_dir).freeze_protocol(
        prompt_plan=plan,
        protocol_lock=protocol_lock,
        source_root=args.source_root,
        forbidden_seed_hashes=_forbidden_hashes(args.forbidden_seed_hashes),
        forbidden_normalized_seed_hashes=_forbidden_normalized_hashes(
            args.forbidden_seed_hashes
        ),
    )


def command_validate_lock(args) -> dict:
    plan, _ = _plan(args.plan, args.forbidden_seed_hashes)
    _, validation = _protocol_lock(
        args.protocol_lock, args.source_root, plan, args.forbidden_seed_hashes
    )
    return validation


def command_authorize(args) -> dict:
    authorization = load_json(args.authorization)
    # Deliberately no verifier is wired into this offline runner. Shape-correct files are
    # insufficient authority, so this command fails closed until a separately audited
    # external trust-registry verifier is integrated.
    return ExperimentState(args.run_dir).authorize_full(authorization)


def command_start_generation(args) -> dict:
    return ExperimentState(args.run_dir).start_generation(
        authorization_sha256=args.authorization_sha256
    )


def command_complete_generation(args) -> dict:
    state = ExperimentState(args.run_dir)
    return complete_generation_if_ready(state, AttemptLedger.for_run(state))


def command_seal_corpus(args) -> dict:
    rows = load_jsonl_strict(args.corpus)
    state = ExperimentState(args.run_dir)
    return seal_corpus(
        state=state,
        ledger=AttemptLedger.for_run(state),
        corpus_rows=rows,
    )


def command_start_labeling(args) -> dict:
    return start_labeling(ExperimentState(args.run_dir))


def command_status(args) -> dict:
    state = ExperimentState(args.run_dir)
    current = state.current()
    result = {
        "run_id": current["run_id"],
        "phase": current["phase_to"],
        "execution_class": current["execution_class"],
        "production_authorization_status": "NOT_AUTHORIZED",
        "state_event_count": len(state.events()),
        "state_ledger_tip_sha256": current["record_sha256"],
        "network_transport_present": False,
        "provider_calls_possible_from_this_runner": False,
    }
    seal = Path(args.run_dir) / "corpus_seal.json"
    if seal.exists():
        result["corpus_seal"] = verify_corpus_seal(args.run_dir)
    return result


def command_verify_seal(args) -> dict:
    return verify_corpus_seal(args.run_dir)


def command_permutation(args) -> dict:
    rows = load_json(args.input)
    if not isinstance(rows, list):
        raise ContractError("Claim-2 permutation input must be a JSON array")
    result = claim2_refit_permutation(rows)
    _write_json(args.out, result)
    return {key: result[key] for key in (
        "schema_version", "algorithm", "learner_id", "trials", "null_refit_invocations",
        "real_change_f1", "null_mean", "null_p95", "null_p99", "empirical_p",
        "analysis_input_sha256",
    )}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def plan_args(command):
        command.add_argument("--plan", required=True)
        command.add_argument("--forbidden-seed-hashes")

    validate = sub.add_parser("validate-plan")
    plan_args(validate)
    validate.set_defaults(handler=command_validate_plan)

    init = sub.add_parser("init-run")
    plan_args(init)
    init.add_argument("--run-dir", required=True)
    init.add_argument("--run-id", required=True)
    init.add_argument("--protocol-lock", required=True)
    init.add_argument("--source-root", required=True)
    init.set_defaults(handler=command_init)

    freeze = sub.add_parser("freeze-protocol")
    plan_args(freeze)
    freeze.add_argument("--run-dir", required=True)
    freeze.add_argument("--protocol-lock", required=True)
    freeze.add_argument("--source-root", required=True)
    freeze.set_defaults(handler=command_freeze)

    lock = sub.add_parser("validate-lock")
    plan_args(lock)
    lock.add_argument("--protocol-lock", required=True)
    lock.add_argument("--source-root", required=True)
    lock.set_defaults(handler=command_validate_lock)

    authorize = sub.add_parser("authorize-full")
    authorize.add_argument("--run-dir", required=True)
    authorize.add_argument("--authorization", required=True)
    authorize.set_defaults(handler=command_authorize)

    start_generation = sub.add_parser("start-generation")
    start_generation.add_argument("--run-dir", required=True)
    start_generation.add_argument("--authorization-sha256", required=True)
    start_generation.set_defaults(handler=command_start_generation)

    complete_generation = sub.add_parser("complete-generation")
    complete_generation.add_argument("--run-dir", required=True)
    complete_generation.set_defaults(handler=command_complete_generation)

    seal = sub.add_parser("seal-corpus")
    seal.add_argument("--run-dir", required=True)
    seal.add_argument("--corpus", required=True)
    seal.set_defaults(handler=command_seal_corpus)

    labels = sub.add_parser("start-labeling")
    labels.add_argument("--run-dir", required=True)
    labels.set_defaults(handler=command_start_labeling)

    status = sub.add_parser("status")
    status.add_argument("--run-dir", required=True)
    status.set_defaults(handler=command_status)

    verify = sub.add_parser("verify-seal")
    verify.add_argument("--run-dir", required=True)
    verify.set_defaults(handler=command_verify_seal)

    permutation = sub.add_parser("claim2-permutation")
    permutation.add_argument("--input", required=True)
    permutation.add_argument("--out", required=True)
    permutation.set_defaults(handler=command_permutation)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.handler(args)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
