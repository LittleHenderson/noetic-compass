"""C5 bridge to the source-pinned CAS interface; it owns no native state writer."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

from .contracts import HarnessConfig, ParentIdentity, digest, execution_config, public_observation

ROOT = Path(__file__).resolve().parents[2]
CAS = ROOT / "research/cas_closed_loop_1"
RUNTIME = CAS / "_runtime"
HOST_STEP_LIMIT = 32


def verify_source(expected_manifest_sha256=None):
    raw = (ROOT / "PUBLIC_SOURCE_MANIFEST.json").read_bytes()
    manifest_sha = hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise ValueError("SOURCE_MANIFEST_CHANGED")
    manifest = json.loads(raw)
    for row in manifest["files"]:
        rel = Path(row["path"])
        target = ROOT / rel
        if rel.is_absolute() or ".." in rel.parts or target.is_symlink() or not target.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("SOURCE_PATH_ESCAPE")
        data = target.read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("PINNED_CAS_SOURCE_CHANGED:" + row["path"])
    return manifest, manifest_sha


def parent_identity(branch="codex/helm-si-three-lead-20260927"):
    manifest, manifest_sha = verify_source()
    return ParentIdentity(manifest["source_commit"], manifest["runtime_commit"], branch, manifest_sha)


def _runtime(parent):
    manifest, _ = verify_source(parent.source_manifest_sha256)
    if manifest["source_commit"] != parent.source_sha or manifest["runtime_commit"] != parent.runtime_sha:
        raise ValueError("RUNTIME_SOURCE_MISMATCH")
    if parent.checkpoint_sha256 is not None:
        raise ValueError("NEURAL_CHECKPOINT_NOT_SUPPORTED")
    # Trusted, verified host code only. A candidate cannot select import locations.
    sys.dont_write_bytecode = True
    if str(RUNTIME) not in sys.path:
        sys.path.insert(0, str(RUNTIME))
    from cncm.compound_engine import CompoundMachine
    from cncm.compound_profile import load_compound_profile
    from research.cas_closed_loop_1 import run_closed_loop as native
    from research.cas_closed_loop_1.native_step_adapter import admission_for
    return CompoundMachine, load_compound_profile, native, admission_for


def run_branch(parent, config, *, destination=None):
    if type(config) is not HarnessConfig:
        raise ValueError("TYPED_CONFIGURATION_REQUIRED")
    CompoundMachine, load_profile, native, admission = _runtime(parent)
    genesis = native.public_problem()
    machine = CompoundMachine(load_profile(), trusted_ingress=())
    machine.start(genesis)
    admitted = admission(machine)
    if destination is not None:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
    started = time.monotonic_ns()
    try:
        rows = native.run_episode(machine, allow_acquisition=config.allow_acquisition,
                                  actuator_enabled=True, limit=HOST_STEP_LIMIT)
    except Exception as error:
        if destination is not None:
            failure = {"status": "FAILED_NOT_RETRIED", "error_type": type(error).__name__,
                       "error": str(error), "config_consumed": asdict(config),
                       "wall_ns": time.monotonic_ns() - started,
                       "native_fault_receipt": getattr(error, "receipt", None),
                       "work_refunded": False, "partial_state_verified": False}
            (destination / "failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
            try:
                (destination / "partial_journal.json").write_text(
                    json.dumps(machine.journal(), indent=2) + "\n", encoding="utf-8")
            except Exception as capture_error:
                (destination / "journal_capture_error.txt").write_text(
                    type(capture_error).__name__ + ": " + str(capture_error), encoding="utf-8")
        raise
    wall_ns = time.monotonic_ns() - started
    journal = machine.journal()
    checked = native.effect_check(machine)
    prediction = machine.result().output
    result = {"input_sha256": digest(genesis.to_dict()), "trace_sha256": digest(journal),
              "original_prediction": prediction, "checked_effect": checked,
              "feedback": "CHECKED" if checked else "BLOCKED"}
    operations = [row["board_binding"]["operation"] for row in rows]
    summary = {**result, "config_consumed": asdict(config), "operations": operations,
               "host_entries": sum(row["I_executed"] for row in rows),
               "host_step_limit": HOST_STEP_LIMIT, "wall_ns": wall_ns,
               "state_hash": machine.state.state_hash,
               "primitive_work": {key: sum(row["actual_primitive_work"]["measured_totals"][key]
                                           for row in rows)
                                  for key in ("primitive_instructions", "original_checks", "linear_checks")},
               "model_calls": 0, "neural_prediction": "NOT_RUN"}
    if destination is not None:
        # The existing native replay schema and verifier remain authoritative.
        body = {"schema": "cas.closed-loop.replay-bundle/0.1", "admission": admitted,
                "trusted_genesis": genesis.to_dict(), "trusted_ingress": [],
                "journal_digest": journal["journal_digest"], "receipts_digest": native.digest(rows)}
        bundle = {**body, "bundle_digest": native.digest(body)}
        for name, value in (("bundle.json", bundle), ("journal.json", journal), ("summary.json", summary)):
            (destination / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        with (destination / "events.jsonl").open("x", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
        summary["bundle_digest"] = bundle["bundle_digest"]
        summary["native_replay"] = native.replay(destination, bundle["bundle_digest"], export_atlas=True) if checked else None
    return summary, public_observation(parent, result)


def execute_candidate(description, observation, candidate, *, mode, destination=None):
    config = execution_config(description, observation, candidate, mode)
    return run_branch(description.parent, config, destination=destination)


def replay_native(parent, directory, expected_bundle_digest):
    _, _, native, _ = _runtime(parent)
    return native.replay(directory, expected_bundle_digest)
