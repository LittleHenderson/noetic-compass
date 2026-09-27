"""Host-only bridge to the pinned CAS coordinator; no alternate state writer."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

from .admission import ROOT, OBSERVATION_FIELDS, TrustedHost, write_new
from .contracts import HarnessConfig, digest, execution_config, public_observation

CAS = ROOT / "research/cas_closed_loop_1"
RUNTIME = CAS / "_runtime"
HOST_STEP_LIMIT = 32
PARITY_FIELDS = ("input_sha256", "trace_sha256", "journal_digest", "original_prediction",
                 "checked_effect", "feedback", "config_consumed", "operations", "host_entries",
                 "host_step_limit", "state_hash", "primitive_work", "model_calls", "neural_prediction")


def _runtime(host):
    if type(host) is not TrustedHost:
        raise ValueError("TRUSTED_HOST_ADMISSION_REQUIRED")
    host.validate_parent(host.parent)
    sys.dont_write_bytecode = True
    if str(RUNTIME) not in sys.path:
        sys.path.insert(0, str(RUNTIME))
    from cncm.compound_engine import CompoundMachine
    from cncm.compound_profile import load_compound_profile
    from research.cas_closed_loop_1 import run_closed_loop as native
    from research.cas_closed_loop_1.native_step_adapter import admission_for
    for name in ("cncm.compound_engine", "cncm.compound_profile"):
        if not Path(sys.modules[name].__file__).resolve().is_relative_to(RUNTIME.resolve()):
            raise ValueError("FOREIGN_IMPORTED_RUNTIME")
    if not Path(native.__file__).resolve().is_relative_to(CAS.resolve()):
        raise ValueError("FOREIGN_IMPORTED_ADAPTER")
    return CompoundMachine, load_compound_profile, native, admission_for


def _semantic(machine, journal, rows, genesis, config, native):
    checked = native.effect_check(machine)
    return {"input_sha256": digest(genesis.to_dict()), "trace_sha256": digest(journal),
            "journal_digest": journal["journal_digest"], "original_prediction": machine.result().output,
            "checked_effect": checked, "feedback": "CHECKED" if checked else "BLOCKED",
            "config_consumed": asdict(config), "operations": [r["board_binding"]["operation"] for r in rows],
            "host_entries": sum(r["I_executed"] for r in rows), "host_step_limit": HOST_STEP_LIMIT,
            "state_hash": machine.state.state_hash,
            "primitive_work": {k: sum(r["actual_primitive_work"]["measured_totals"][k] for r in rows)
                               for k in ("primitive_instructions", "original_checks", "linear_checks")},
            "model_calls": 0, "neural_prediction": "NOT_RUN"}


def _run_branch(host, config, *, mode, candidate_id=None, validation_ns=0):
    before = time.monotonic_ns()
    CompoundMachine, load_profile, native, admission = _runtime(host)
    if type(config) is not HarnessConfig:
        raise ValueError("TYPED_CONFIGURATION_REQUIRED")
    run_id, destination = host.begin_run(config, mode, candidate_id)
    genesis = native.public_problem()
    machine = CompoundMachine(load_profile(), trusted_ingress=())
    machine.start(genesis)
    admitted = admission(machine)
    setup_ns = time.monotonic_ns() - before
    started = time.monotonic_ns()
    try:
        rows = native.run_episode(machine, allow_acquisition=config.allow_acquisition,
                                  actuator_enabled=True, limit=HOST_STEP_LIMIT)
    except Exception as error:
        failure = {"status": "FAILED_NOT_RETRIED", "error_type": type(error).__name__,
                   "error": str(error), "mode": mode, "config_consumed": asdict(config),
                   "wall_ns": time.monotonic_ns() - started, "native_fault_receipt": getattr(error, "receipt", None),
                   "work_refunded": False, "partial_state_verified": False}
        write_new(destination / "failure.json", failure)
        host.append("RUN_FAILED", {"run_id": run_id, "failure": failure})
        try:
            write_new(destination / "partial_journal.json", machine.journal())
        except Exception as journal_error:
            write_new(destination / "partial_journal_failure.json",
                      {"error_type": type(journal_error).__name__, "error": str(journal_error)})
        raise
    runtime_ns = time.monotonic_ns() - started
    post_started = time.monotonic_ns()
    journal = machine.journal()
    summary = _semantic(machine, journal, rows, genesis, config, native)
    body = {"schema": "cas.closed-loop.replay-bundle/0.1", "admission": admitted,
            "trusted_genesis": genesis.to_dict(), "trusted_ingress": [],
            "journal_digest": journal["journal_digest"], "receipts_digest": native.digest(rows)}
    bundle = {**body, "bundle_digest": native.digest(body)}
    write_new(destination / "bundle.json", bundle)
    write_new(destination / "journal.json", journal)
    with (destination / "events.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    replay = native.replay(destination, bundle["bundle_digest"], export_atlas=True) if summary["checked_effect"] else None
    summary.update({"bundle_digest": bundle["bundle_digest"], "native_replay": replay, "mode": mode,
                    "candidate_id": candidate_id, "runtime_wall_ns": runtime_ns,
                    "host_setup_ns": setup_ns, "mode_validation_ns": validation_ns,
                    "verification_and_persistence_ns": time.monotonic_ns() - post_started,
                    "overhead_definition": "Host setup + mode validation + verification/persistence; excludes final summary and host-ledger write.",
                    "receipt_identity_includes_wall_fields": True,
                    "deterministic_parity": {k: summary[k] for k in PARITY_FIELDS}})
    # Persist only after bundle/replay/overhead fields are final. Returned value equals saved JSON.
    summary = host.finish_run(run_id, summary)
    return summary, public_observation(host.parent, {k: summary[k] for k in OBSERVATION_FIELDS})


def run_baseline(host):
    return _run_branch(host, host.baseline_config, mode="baseline")


def execute_candidate(host, description, observation, candidate, *, mode):
    started = time.monotonic_ns()
    config = execution_config(host, description, observation, candidate, mode)
    return _run_branch(host, config, mode=mode,
                       candidate_id=candidate.candidate_id if mode != "disabled" and candidate else None,
                       validation_ns=time.monotonic_ns() - started)


def verify_run_semantics(host, summary, directory):
    _, load_profile, native, admission = _runtime(host)
    trusted = host.verified_run(summary["run_id"])
    if summary != trusted or json.loads((directory / "summary.json").read_bytes()) != summary:
        raise ValueError("PERSISTED_SUMMARY_DIFFERS_FROM_HOST_RUN")
    bundle = json.loads((directory / "bundle.json").read_bytes())
    journal = json.loads((directory / "journal.json").read_bytes())
    rows = [json.loads(line) for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if (bundle["bundle_digest"] != summary["bundle_digest"] or
            native.digest({k: v for k, v in bundle.items() if k != "bundle_digest"}) != bundle["bundle_digest"] or
            native.digest(rows) != bundle["receipts_digest"] or not all(native.verify_receipt(r) for r in rows)):
        raise ValueError("RUN_RECEIPTS_CHANGED")
    genesis = native.CompoundProblem.from_dict(bundle["trusted_genesis"])
    if genesis.to_dict() != native.public_problem().to_dict() or bundle["trusted_ingress"] != []:
        raise ValueError("RUN_INPUT_NOT_PUBLIC_FIXTURE")
    machine = native.recover_compound_journal(journal, trusted_genesis=genesis, trusted_ingress=(),
        expected_journal_digest=bundle["journal_digest"], profile=load_profile())
    if admission(machine) != bundle["admission"] or machine.journal() != journal:
        raise ValueError("RUN_NATIVE_REPLAY_MISMATCH")
    semantic = _semantic(machine, journal, rows, genesis, HarnessConfig(**summary["config_consumed"]), native)
    if any(summary[k] != semantic[k] for k in PARITY_FIELDS) or summary["deterministic_parity"] != semantic:
        raise ValueError("RUN_SEMANTIC_SUMMARY_MISMATCH")
    replay = native.replay(directory, summary["bundle_digest"]) if summary["checked_effect"] else None
    if replay != summary["native_replay"]:
        raise ValueError("RUN_REPLAY_REPORT_MISMATCH")
    return replay
