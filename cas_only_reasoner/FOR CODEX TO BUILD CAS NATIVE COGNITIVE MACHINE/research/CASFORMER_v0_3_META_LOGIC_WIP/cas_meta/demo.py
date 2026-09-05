"""Reproduce fixed-weight equivalence with an actual process restart."""

from dataclasses import asdict
from hashlib import sha256
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from cas_cjt import validate_contract

from .compiler import compile_program
from .executor import Executor, MetaRuntimeError, digest
from .fixture import create_native, initial_input, open_native, run_reference


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_PATH = ROOT / "programs" / "fixed_chain.json"


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def semantic_projection(runtime):
    """Common native meaning, not meta-event or whole-trace byte identity."""
    projected = []
    for trace in runtime.store.trace_events():
        validate_contract(trace)
        receipt_id = trace["commit_receipt_id"]
        projected.append({
            "tick": trace["tick"],
            "pre_state": runtime.store.load_state(trace["pre_state_digest"]),
            "post_state": runtime.store.load_state(trace["post_state_digest"]),
            "compute_plan": trace["compute_plan"],
            "compute_observations": trace["compute_observations"],
            **{table: runtime.store.documents_for_receipt(table, receipt_id)
               for table in ("causes", "candidate_effects", "verifier_receipts",
                             "published_effects", "repair_frames", "repair_outcomes",
                             "state_intents", "model_intents", "memory_intents")},
        })
    return projected


def resume(output, expected_digest):
    output = Path(output).resolve()
    # A checkpoint is not a database backup. Reject missing prerequisites
    # before opening SQLite; never create or substitute a replacement store.
    for name in ("checkpoint.json", "compiled.db"):
        if not (output / name).is_file():
            raise MetaRuntimeError("MISSING_CHECKPOINT_DEPENDENCY:" + name)
    native = open_native(output / "compiled.db")
    try:
        program = compile_program(PROGRAM_PATH.read_text(encoding="utf-8"))
        executor = Executor.restore(native, program, output / "checkpoint.json",
                                    expected_digest=expected_digest, chain_id="fixed-chain")
        if len(native.store.trace_events()) != 4 or len(executor.frames) != 3:
            raise AssertionError("restart did not restore the suspended repair caller")
        before_frames = list(executor.frames)
        before_head = asdict(native.store.head)
        before_projection = semantic_projection(native)
        before_events = executor.events
        before_spent = executor.spent
        before_model = native.state.model_digest
        executor.run()
        if (semantic_projection(native)[:4] != before_projection
                or executor.events[:len(before_events)] != before_events
                or len(native.store.trace_events()) != 5
                or before_spent != 288 or executor.spent != 360
                or native.state.model_digest != before_model
                or native.state.by_cjt_id["C"].rpm.open_repair_ids):
            raise AssertionError("resume did not preserve the declared continuation")
        final_checkpoint = executor.checkpoint(output / "final_checkpoint.json")
        write_json(output / "meta_trace.json", executor.events)
        write_json(output / "worker_result.json", {
            "done": executor.done, "spent": executor.spent,
            "result_effect_id": executor.result_effect_id,
            "final_checkpoint_digest": final_checkpoint,
            "meta_event_count": len(executor.events),
            "restored_frames": before_frames,
            "native_head_before": before_head,
            "native_head_after": asdict(native.store.head),
            "native_trace_count_before": 4,
            "native_trace_count_after": 5,
            "spent_before": before_spent,
            "remaining_before": executor.limits.budget - before_spent,
            "remaining_after": executor.limits.budget - executor.spent,
            "model_digest_before": before_model,
            "model_digest_after": native.state.model_digest,
            "prior_native_projection_unchanged": True,
            "prior_meta_events_unchanged": True,
            "repair_closed": True,
        })
        print(json.dumps({"restart_resumed": True, "done": executor.done, "spent": executor.spent}))
    finally:
        native.close()


def prepare_demo(output: Path):
    """Create a matching paused database/checkpoint and exit before resume.

    The native writer is closed before any database copy or hash is taken.
    This is a clean-boundary snapshot, not cross-store crash recovery.
    """
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    program = compile_program(PROGRAM_PATH.read_text(encoding="utf-8"))
    native = create_native(output / "compiled.db")
    try:
        initial_model = native.state.model_digest
        cause, artifact = initial_input(native)
        executor = Executor(native, program, cause, artifacts=(artifact,))
        while len(native.store.trace_events()) < 4:
            executor.step()
        paused_frames = executor.frames
        if [frame["procedure"] for frame in paused_frames] != ["main", "worker", "repair_c"]:
            raise AssertionError("repair did not execute on its own nested frame")
        paused_head = asdict(native.store.head)
        checkpoint_digest = executor.checkpoint(output / "checkpoint.json")
    finally:
        native.close()
    prepared = {
        "status": "CAS_META_CHECKPOINT_PREPARED",
        "checkpoint_digest": checkpoint_digest,
        "program_digest": program.digest,
        "model_digest": initial_model,
        "native_head": paused_head,
        "frames": list(paused_frames),
        "spent": executor.spent,
        "remaining": executor.limits.budget - executor.spent,
        "native_trace_count": 4,
        "database_sha256": sha256((output / "compiled.db").read_bytes()).hexdigest(),
        "required_files": ["checkpoint.json", "compiled.db"],
    }
    write_json(output / "creation_receipt.json", prepared)
    # Keep a closed, matching pair even after the live copy is consumed.
    # Auditors copy this directory to a new location before resuming it.
    paused = output / "paused"
    paused.mkdir()
    for name in ("checkpoint.json", "compiled.db", "creation_receipt.json"):
        shutil.copyfile(output / name, paused / name)
    return prepared


def run_demo(output: Path):
    output = Path(output).resolve()
    prepared = prepare_demo(output)
    checkpoint_digest = prepared["checkpoint_digest"]
    initial_model = prepared["model_digest"]
    paused_head = prepared["native_head"]
    paused_frames = prepared["frames"]
    program = compile_program(PROGRAM_PATH.read_text(encoding="utf-8"))
    # Passing a separately held checkpoint digest binds the fresh process to
    # these exact saved bytes. It is not a signature or protection against a
    # hostile caller replacing both the file and its trusted receipt.
    command = [sys.executable, "-m", "cas_meta.demo", "--resume", str(output),
               "--expected-digest", checkpoint_digest]
    worker = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    (output / "resume.stdout.txt").write_text(worker.stdout, encoding="utf-8")
    (output / "resume.stderr.txt").write_text(worker.stderr, encoding="utf-8")
    write_json(output / "resume_command.json", {"argv": command, "returncode": worker.returncode})
    if worker.returncode:
        raise RuntimeError("fresh-process resume failed: " + worker.stderr)
    reference = create_native(output / "reference.db")
    native = open_native(output / "compiled.db")
    try:
        reference_results = run_reference(reference)
        actual, expected = semantic_projection(native), semantic_projection(reference)
        if actual != expected:
            raise AssertionError("compiled execution differs from fixed-weight reference")
        if native.state != reference.state:
            raise AssertionError("committed native states differ")
        worker_result = json.loads((output / "worker_result.json").read_text(encoding="utf-8"))
        traces = native.store.trace_events()
        write_json(output / "compiled_native_trace.json", traces)
        write_json(output / "reference_native_trace.json", reference.store.trace_events())
        write_json(output / "semantic_projection.json", actual)
        result = {
            "status": "CAS_META_0_FIXED_WEIGHT_COMPOSITION_TEST_PASSED",
            "release_status": "WIP_UNREVIEWED_NOT_PART_OF_V0_2",
            "program_digest": program.digest,
            "chain": [item.cjt_id for item in reference_results],
            "candidate_symbols": [item.candidate_effect.content["symbol"] for item in reference_results],
            "accepted_effects": sum(len(t["published_effect_ids"]) for t in traces),
            "native_trace_count": len(traces),
            "native_schema_validated_count": len(traces),
            "meta_event_count": worker_result["meta_event_count"],
            "semantic_projection_equal": True,
            "semantic_projection_digest": digest(actual),
            "committed_state_equal": True,
            "repair_closed": not native.state.by_cjt_id["C"].rpm.open_repair_ids,
            "model_digest_before": initial_model,
            "model_digest_after": native.state.model_digest,
            "fixed_weights": initial_model == native.state.model_digest,
            "budget_reserved_policy_units": worker_result["spent"],
            "budget_ceiling": 512,
            "paused_native_tick": 4,
            "paused_call_ids": [frame["call_id"] for frame in paused_frames],
            "paused_procedures": [frame["procedure"] for frame in paused_frames],
            "paused_head": paused_head,
            "checkpoint_digest": checkpoint_digest,
            "fresh_process_restart": worker.returncode == 0,
            "integrity": native.store.verify_integrity() and reference.store.verify_integrity(),
            "claim_boundary": "Fixed-weight, authored-oracle composition only. Not learning equivalence, learned recursion, CAS advantage, or crash-atomic recovery.",
        }
        if not all(result[key] for key in ("fixed_weights", "repair_closed", "integrity")):
            raise AssertionError("demo acceptance gate failed")
    finally:
        native.close()
        reference.close()
    write_json(output / "result.json", result)
    hashes = {file.name: sha256(file.read_bytes()).hexdigest()
              for file in sorted(output.iterdir()) if file.is_file()}
    write_json(output / "sha256.json", hashes)
    return result


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--prepare", type=Path,
                       help="create a paused bundle and exit without resuming it")
    group.add_argument("--resume", type=Path)
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    if args.resume:
        if args.expected_digest is None:
            parser.error("--resume requires --expected-digest")
        resume(args.resume, args.expected_digest)
    elif args.expected_digest is not None:
        parser.error("--expected-digest is only valid with --resume")
    elif args.prepare:
        print(json.dumps(prepare_demo(args.prepare), indent=2, sort_keys=True))
    else:
        print(json.dumps(run_demo(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
