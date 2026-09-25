"""Bounded engineering demo and caller-anchored replay; no model/AWS calls."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE / "_runtime"))

from cncm.canonical import digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundProblem, create_problem
from cncm.compound_profile import load_compound_profile
from cncm.compound_recovery import recover_compound_journal
from cncm.model import TerminalStatus
from cncm.rpa_compound_adapter import compound_atlas_from_journal
from research.cas_closed_loop_1.control import controlled_step
from research.cas_closed_loop_1.native_step_adapter import admission_for, verify_receipt, primitive_work_for_events


def public_problem(**options):
    # Original public inputs only. The solver receives no expected answer.
    return create_problem({"a": "2", "b": "3", "c": "5", "d": "7", "e": "35"}, **options)


def run_episode(machine, *, allow_acquisition=True, actuator_enabled=True, limit=32):
    receipts = []
    for _ in range(limit):
        if machine.state.halt_status is not TerminalStatus.RUNNING:
            break
        row = controlled_step(machine, allow_acquisition=allow_acquisition, actuator_enabled=actuator_enabled)
        receipts.append(row)
        if not row["I_executed"]:
            break
    if machine.state.halt_status is TerminalStatus.RUNNING and actuator_enabled:
        raise RuntimeError("BOUNDED_HOST_STEP_LIMIT_REACHED")
    return receipts


def effect_check(machine):
    result = machine.result()
    if result.output is None:
        return False
    values = dict(machine.problem.parameters)
    if (any(type(value) is not str for value in values.values())
            or dict(machine.state.compound_call.inputs) != values):
        return False  # This direct-literal profile does not attest external MemoryRef resolution.
    a, b, c, d, e = (Fraction(values[key]) for key in "abcde")
    return (result.terminal_status is TerminalStatus.CONCLUDED
            and machine.state.commitment_state.decision_status == "COMMITTED"
            and a * (b * Fraction(result.output) + c) + d == e)


def demo(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    profile, genesis = load_compound_profile(), public_problem()
    machine = CompoundMachine(profile, trusted_ingress=())
    machine.start(genesis)
    admitted = admission_for(machine)
    started = time.monotonic_ns()
    receipts = run_episode(machine)
    execution_ns = time.monotonic_ns() - started
    if not effect_check(machine):
        raise RuntimeError("ENGINEERING_EFFECT_NOT_CHECKED")
    journal = machine.journal()
    body = {"schema": "cas.closed-loop.replay-bundle/0.1", "admission": admitted,
            "trusted_genesis": genesis.to_dict(), "trusted_ingress": [],
            "journal_digest": journal["journal_digest"], "receipts_digest": digest(receipts)}
    bundle = {**body, "bundle_digest": digest(body)}
    # Immutable after creation. Replay requires caller-held bundle_digest.
    for name, value in (("bundle.json", bundle), ("journal.json", journal)):
        (destination / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    with (destination / "events.jsonl").open("x", encoding="utf-8") as stream:
        for row in receipts:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    report = replay(destination, bundle["bundle_digest"], export_atlas=True)
    totals = {key: sum(row["actual_primitive_work"]["measured_totals"][key] for row in receipts)
              for key in ("primitive_instructions", "original_checks", "linear_checks")}
    result = {"schema": "cas.closed-loop.demo-result/0.1", "engineering_demo": "CHECKED",
              "output": machine.result().output, "effect_checked_by_original_substitution": True,
              "native_events": len(machine.coordinator.trace.events), "host_entries": sum(r["I_executed"] for r in receipts),
              "measured_native_work": totals, "complete_compute": None,
              "unmeasured_records": sorted({v for r in receipts for v in r["actual_primitive_work"]["unmeasured_records"]}),
              "execution_and_observation_ns": execution_ns, "replay": report,
              "model_prediction": "NOT_RUN", "input_use": "ORIGINAL_PUBLIC_PARAMETERS_ONLY",
              "task_benefit": "KNOWN_ENGINEERING_ACQUISITION_WITNESS_NOT_STATISTICAL_ESTIMATE",
              "cas_specific_advantage": "UNMEASURED", "ASOM": "UNASSESSED", "new_paid_jobs": 0,
              "bundle_digest": bundle["bundle_digest"]}
    (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def replay(directory, expected_bundle_digest, *, export_atlas=False):
    directory = Path(directory)
    bundle = json.loads((directory / "bundle.json").read_text(encoding="utf-8"))
    if (bundle["bundle_digest"] != expected_bundle_digest
            or digest({k: v for k, v in bundle.items() if k != "bundle_digest"}) != expected_bundle_digest):
        raise ValueError("UNTRUSTED_REPLAY_BUNDLE")
    journal = json.loads((directory / "journal.json").read_text(encoding="utf-8"))
    receipts = [json.loads(line) for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if digest(receipts) != bundle["receipts_digest"] or not all(verify_receipt(row) for row in receipts):
        raise ValueError("STEP_RECEIPTS_ALTERED_OR_TRUNCATED")
    genesis = CompoundProblem.from_dict(bundle["trusted_genesis"])
    profile = load_compound_profile()
    machine = recover_compound_journal(journal, trusted_genesis=genesis,
        trusted_ingress=tuple(bundle["trusted_ingress"]), expected_journal_digest=bundle["journal_digest"], profile=profile)
    if admission_for(machine) != bundle["admission"]:
        raise ValueError("REPLAY_ADMISSION_MISMATCH")
    if machine.journal() != journal or not effect_check(machine):
        raise ValueError("REPLAY_PARITY_OR_EFFECT_FAILED")
    actual_refs = [(e.event_id, e.event_hash) for e in machine.coordinator.trace.events]
    observed_refs = [(r["event_id"], r["event_hash"]) for row in receipts for r in row["native_event_refs"]]
    if observed_refs != actual_refs:
        raise ValueError("OBSERVATION_EVENT_COVERAGE_MISMATCH")
    by_ref = {(event.event_id, event.event_hash): event for event in machine.coordinator.trace.events}
    previous_state = journal["episodes"][0]["initial_state_hash"]
    for row in receipts:
        events = [by_ref[(ref["event_id"], ref["event_hash"])] for ref in row["native_event_refs"]]
        expected_after = events[-1].post_state_hash if events else previous_state
        if row["before"]["state_hash"] != previous_state or row["after"]["state_hash"] != expected_after:
            raise ValueError("OBSERVATION_WINDOW_BINDING_MISMATCH")
        reconstructed = primitive_work_for_events(machine, events)
        for key in ("measured_totals", "unmeasured_records", "events"):
            if row["actual_primitive_work"][key] != reconstructed[key]:
                raise ValueError("OBSERVED_WORK_DIFFERS_FROM_NATIVE_REPLAY")
        previous_state = expected_after
    if export_atlas:
        atlas = compound_atlas_from_journal(journal, trusted_genesis=genesis,
            trusted_ingress=tuple(bundle["trusted_ingress"]), expected_journal_digest=bundle["journal_digest"], profile=profile)
        (directory / "atlas.json").write_text(json.dumps(atlas, indent=2) + "\n", encoding="utf-8")
    return {"status": "EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT", "final_state_hash": machine.state.state_hash,
            "journal_digest": machine.journal()["journal_digest"], "events": len(actual_refs)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    run = sub.add_parser("demo")
    run.add_argument("--output", required=True)
    again = sub.add_parser("replay")
    again.add_argument("--directory", required=True)
    again.add_argument("--expected-bundle-digest", required=True)
    sub.add_parser("pilot")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = demo(args.output)
        elif args.command == "replay":
            result = replay(args.directory, args.expected_bundle_digest)
        elif args.command == "pilot":
            raise ValueError("MODEL_PILOT_NOT_AUTHORIZED_IN_RECOVERY_TASK")
        else:
            machine = CompoundMachine(load_compound_profile(), trusted_ingress=())
            machine.start(public_problem())
            result = {"status": "SOURCE_ADMITTED", **admission_for(machine)}
        print(json.dumps(result))
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__, "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
