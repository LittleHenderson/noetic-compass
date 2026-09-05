"""Reproduce fixed-weight equivalence with an actual process restart."""

from dataclasses import asdict
from hashlib import sha256
import argparse
import json
from pathlib import Path
import subprocess
import sys

from cas_cjt import validate_contract

from .compiler import compile_program
from .executor import Executor, digest
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
    native = open_native(output / "compiled.db")
    try:
        program = compile_program(PROGRAM_PATH.read_text(encoding="utf-8"))
        executor = Executor.restore(native, program, output / "checkpoint.json",
                                    expected_digest=expected_digest, chain_id="fixed-chain")
        if len(native.store.trace_events()) != 4 or len(executor.frames) != 3:
            raise AssertionError("restart did not restore the suspended repair caller")
        executor.run()
        final_checkpoint = executor.checkpoint(output / "final_checkpoint.json")
        write_json(output / "meta_trace.json", executor.events)
        write_json(output / "worker_result.json", {
            "done": executor.done, "spent": executor.spent,
            "result_effect_id": executor.result_effect_id,
            "final_checkpoint_digest": final_checkpoint,
            "meta_event_count": len(executor.events),
        })
        print(json.dumps({"restart_resumed": True, "done": executor.done, "spent": executor.spent}))
    finally:
        native.close()


def run_demo(output: Path):
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
    group.add_argument("--resume", type=Path)
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    if args.resume:
        if args.expected_digest is None:
            parser.error("--resume requires --expected-digest")
        resume(args.resume, args.expected_digest)
    else:
        print(json.dumps(run_demo(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
