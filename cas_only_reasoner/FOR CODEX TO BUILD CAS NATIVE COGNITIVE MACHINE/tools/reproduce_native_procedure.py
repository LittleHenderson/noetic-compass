"""Retained pure acceptance episode for bounded native procedure acquisition.

Run from the CNCM homebase:
  python -B tools/reproduce_native_procedure.py --output records/native_procedure_001/acceptance_001
The output directory must not already exist. No neural/provider imports or work.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cncm.canonical import canonical_json, digest
from cncm.model import (EntityDecl, InferenceOperation, PredicateDecl, ProblemPacket,
                        Proposition, Provenance, Rule, TerminalStatus)
from cncm.native_engine import NativeMachine
from cncm.native_model import CAPABILITY, CallSpec, NativeProblem, RESULT_PREDICATE
from cncm.native_recovery import replay_native_journal, save_native_journal


def packet(name, inputs):
    call = CallSpec.create(call_id="call-"+name, goal_id="goal-"+name, inputs=inputs)
    checked = Proposition(RESULT_PREDICATE, (call.call_id,))
    query = Proposition("done", (call.call_id,))
    rule = Rule("checked-to-done", InferenceOperation.INFER_MODUS_PONENS,
                (checked,), query, (Provenance("engineering_contract", "current-call-checked"),))
    reasoning = ProblemPacket(schema_version="cncm.problem/0.1",
        problem_id="native-"+name, goal_id=call.goal_id, seed=20260916,
        entities=(EntityDecl(call.call_id, "call"),),
        predicates=(PredicateDecl(RESULT_PREDICATE, ("call",)), PredicateDecl("done", ("call",))),
        facts=(), rules=(rule,), query=query)
    return NativeProblem(reasoning, call)


def write(path, body):
    raw = (canonical_json(body)+"\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
    return {"file": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def forbidden(*args, **kwargs):
    raise AssertionError("new-call acquisition/qualification unexpectedly invoked")


def child(output):
    anchor = json.loads((output / "acquisition_anchor.json").read_bytes())
    genesis = NativeProblem.from_dict(json.loads((output / "genesis.json").read_bytes()))
    machine = replay_native_journal((output / "acquisition_journal.json").read_bytes(),
        trusted_genesis=genesis, expected_journal_digest=anchor["journal_digest"])
    recovered_hash = machine.state.state_hash
    inherited_records = machine.state.native_records
    inherited_artifacts = machine.state.procedural_artifacts
    second = packet("reuse", {"a": "-4", "b": "7", "c": "13"})
    with patch("cncm.native_kernel.select_finite_candidate", forbidden), patch(
            "cncm.native_kernel.qualify_procedure", forbidden):
        result = machine.run(second, allow_acquisition=False)
    assert result.terminal_status is TerminalStatus.CONCLUDED and result.output == "-3/2"
    assert machine.state.procedural_artifacts == inherited_artifacts
    assert machine.state.native_records[:len(inherited_records)] == inherited_records
    assert result.evidence["authorized_native_transitions"]["SELECT_PROCEDURE"] == 0
    assert result.evidence["authorized_native_transitions"]["INSTALL_PROCEDURE"] == 0
    assert result.evidence["conservative_policy_work_reserved"] == {"instructions": 6, "checker_calls": 1}
    write(output / "reuse_result.json", result.to_dict())
    reused_state_hash = machine.state.state_hash
    old_records = machine.state.native_records
    third = packet("after-rollback", {"a": "2", "b": "1", "c": "9"})
    machine.start(third)
    machine.rollback(CAPABILITY)
    assert machine.state.procedure_heads == ()
    assert machine.state.native_records[:len(old_records)] == old_records
    assert machine.state.procedural_artifacts == inherited_artifacts
    rollback_state_hash = machine.state.state_hash
    with patch("cncm.native_kernel.select_finite_candidate", forbidden), patch(
            "cncm.native_kernel.qualify_procedure", forbidden):
        refused = machine.run(allow_acquisition=False)
    assert refused.terminal_status is TerminalStatus.NEEDS_CAPABILITY
    assert refused.output is None and refused.final_state.commitment_state.conclusion is None
    write(output / "rollback_refusal_result.json", refused.to_dict())
    anchor2 = save_native_journal(machine, output / "final_journal.json")
    write(output / "final_anchor.json", anchor2)
    write(output / "fresh_process_receipt.json", {
        "schema_version": "cncm.native-acceptance-child/0.2",
        "pid": os.getpid(), "python": sys.version,
        "source_profile_digest": machine.profile.profile_digest,
        "recovered_state_hash": recovered_hash, "reuse_state_hash": reused_state_hash,
        "reuse_output": result.output, "reuse_terminal": result.terminal_status.value,
        "new_call_selection_and_qualification_denied_by_test_guard": True,
        "rollback_state_hash": rollback_state_hash, "next_call_terminal": refused.terminal_status.value,
        "next_call_output": refused.output, "immutable_records_preserved": True,
        "artifacts_preserved": True, "final_journal_digest": anchor2["journal_digest"],
        "neural_modules_loaded": any(name == "torch" or name.startswith("torch.") for name in sys.modules),
        "trust_boundary": "Trusted host/genesis and external retained digest; no principal authentication.",
    })


def parent(output):
    output.mkdir(parents=True, exist_ok=False)
    genesis = packet("acquire", {"a": "3", "b": "5", "c": "26"})
    write(output / "genesis.json", genesis.to_dict())
    machine = NativeMachine()
    machine.start(genesis)
    checkpoints = []
    for index in range(6):
        machine.advance()
        state = machine.state
        call = state.native_calls[0]
        checkpoints.append({
            "tick": state.logical_tick, "call": call.to_dict(), "active_goal_id": state.active_goal_id,
            "state_hash": state.state_hash, "budget": state.native_budget.to_dict(),
            "rpm_stack": [frame.to_dict() for frame in state.rpm_stack],
            "branch_digest": digest(state.branch_table[0].to_dict()),
            "procedure_heads": [list(item) for item in state.procedure_heads],
        })
    assert checkpoints[1]["call"]["status"] == "SUSPENDED"
    assert checkpoints[1]["call"]["output"] is None
    assert checkpoints[4]["call"]["status"] == "READY" and not checkpoints[4]["rpm_stack"]
    assert checkpoints[4]["active_goal_id"] == genesis.call.goal_id
    assert checkpoints[1]["branch_digest"] == checkpoints[4]["branch_digest"]
    assert machine.state.native_calls[0].output == "7"
    result = machine.run()
    assert result.terminal_status is TerminalStatus.CONCLUDED
    assert result.evidence["conservative_policy_work_reserved"] == {"instructions": 210, "checker_calls": 35}
    write(output / "acquisition_checkpoints.json", checkpoints)
    write(output / "acquisition_result.json", result.to_dict())
    anchor = save_native_journal(machine, output / "acquisition_journal.json")
    write(output / "acquisition_anchor.json", anchor)
    run = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
        "--output", str(output), "--child"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    write(output / "subprocess_exit.json", {
        "exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
        "parent_pid": os.getpid(), "python_executable": sys.executable,
    })
    if run.returncode:
        raise RuntimeError("fresh process failed: "+run.stderr)
    child_receipt = json.loads((output / "fresh_process_receipt.json").read_bytes())
    assert child_receipt["pid"] != os.getpid()
    assert child_receipt["recovered_state_hash"] == result.final_state.state_hash
    assert child_receipt["neural_modules_loaded"] is False
    final_anchor = json.loads((output / "final_anchor.json").read_bytes())
    rebuilt = replay_native_journal((output / "final_journal.json").read_bytes(),
        trusted_genesis=genesis, expected_journal_digest=final_anchor["journal_digest"])
    assert rebuilt.state.halt_status is TerminalStatus.NEEDS_CAPABILITY
    assert not rebuilt.state.procedure_heads
    sources = machine.profile.to_dict()
    write(output / "source_profile.json", sources)
    files = [{"file": path.name, "bytes": path.stat().st_size,
              "sha256": sha256(path.read_bytes()).hexdigest()}
             for path in sorted(output.iterdir()) if path.is_file()]
    receipt = {
        "schema_version": "cncm.native-acceptance/0.2",
        "status": "BOUNDED_NATIVE_ACQUISITION_REUSE_ROLLBACK_PASSED",
        "source_profile_digest": machine.profile.profile_digest,
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "acquire_output": result.output, "acquire_ticks": result.final_state.logical_tick,
        "acquire_policy_work": result.evidence["conservative_policy_work_reserved"],
        "reused_output": child_receipt["reuse_output"], "fresh_process": True,
        "final_journal_replayed_by_parent": True,
        "final_journal_digest": final_anchor["journal_digest"],
        "files": files,
        "limits": ["One exact-rational capability; twelve authored candidate forms.",
                   "Public fixed engineering panels; not neural learning or secret evaluation.",
                   "Trusted host and integrity anchors; no authenticated external custody.",
                   "No full-machine, general reasoning, CAS-Ohm, or production claim."],
    }
    write(output / "receipt.json", receipt)
    print(canonical_json({key: value for key, value in receipt.items() if key != "files"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    destination = args.output.resolve()
    if not destination.is_relative_to(ROOT / "records"):
        raise SystemExit("acceptance output must remain in this homebase's records directory")
    child(destination) if args.child else parent(destination)

