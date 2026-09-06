"""AWS-only execution gate for stored learned-program reuse on new inputs.

This module is pure on import. It performs no training or learned retrieval.
The launcher must bind the explicit job flags to actual AWS identity and budget.
The CLI must run as a fresh child after the candidate writer exits; this module
records its process identity but does not itself attest to that parent action.
"""
import argparse
from copy import deepcopy
import os
from pathlib import Path
import signal
import struct
import time
from uuid import uuid4

from . import native_demo as native_support
from . import learned_package as packages
from . import learning_evidence as evidence
from .learned_linker import retrieve_for_reuse
from .learned_store import LearnedCandidateStore

ROOT = Path(__file__).resolve().parents[1]
MAX_WALL_SECONDS = 1200
MAX_TOTAL_NATIVE_RUNS = 96
SOURCE_FILES = ("__init__.py", "learned_package.py", "learning_evidence.py",
                "learned_handoff.py", "learned_store.py", "learned_linker.py", "learned_reuse.py")


class ReuseError(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise ReuseError(code)


def source_identity():
    return {"native": native_support.source_identity(), "learned_dependency": packages.dependency_receipt(),
        "learned_files_sha256": {name: native_support.file_hash(ROOT / "cas_meta3" / name) for name in SOURCE_FILES}}


def check_public_cases(source_public, public_cases, binding, source_public_sha256):
    require(type(public_cases) is list and 1 <= len(public_cases) <= 4, "BOUNDED_REUSE_CASES_REQUIRED")
    require(type(binding) is int and binding in (0, 1, 2), "REUSE_BINDING_INVALID")
    with packages._pure_dependencies() as (_, codec, _topology):
        codec.validate_public(source_public)
        require(evidence.digest(source_public) == source_public_sha256, "SOURCE_PUBLIC_NOT_BOUND_TO_LEARNING")
        source_values = next(row["values"] for row in source_public["observations"] if row["slot"] == binding)
        require(all(-1 <= value <= 1 for row in source_public["observations"] for value in row["values"]), "REUSE_INPUT_DOMAIN_EXCEEDED")
        seen = {struct.pack("<8f", *source_values)}
        for public in public_cases:
            codec.validate_public(public)
            values = next(row["values"] for row in public["observations"] if row["slot"] == binding)
            require(all(-1 <= value <= 1 for row in public["observations"] for value in row["values"]), "REUSE_INPUT_DOMAIN_EXCEEDED")
            input_bytes = struct.pack("<8f", *values)
            require(input_bytes not in seen, "REUSE_REQUIRES_NEW_SELECTED_INPUT_VALUES")
            seen.add(input_bytes)


def reference_compatibility(reference, source):
    result = native_support.compatibility_from_reference(reference, source["native"])
    result["meta2_source_sha"] = packages.META2_SOURCE_SHA
    result["decoder_contracts"] = {name: reference["runtime_identity"]["decoders"][name] for name in packages.CJT_IDS}
    return result


def check_root_calls(result, events, link):
    count = link["call_count"]
    addresses = ["entry/" + str(index) for index in range(count)]
    calls = [row for row in events if row["kind"] == "ENTER" and row["address"] in addresses]
    returns = [row for row in events if row["kind"] == "RETURN" and row["address"] in addresses]
    roots = [row for row in events if row["kind"] == "RETURN" and row["address"] == "entry"]
    require([row["address"] for row in calls] == addresses and [row["address"] for row in returns] == addresses,
            "REUSE_ROOT_CALL_COVERAGE_MISMATCH")
    require(len({row["call_id"] for row in calls}) == count
            and all(row["input_reference"] == calls[0]["input_reference"] for row in calls),
            "REUSE_CALL_ID_OR_INPUT_MISMATCH")
    require(len({row["reference"]["effect_id"] for row in returns}) == count, "REUSE_DISTINCT_EFFECT_IDS_REQUIRED")
    selected = returns[link["return_call"]]["reference"]
    require(len(roots) == 1 and roots[0]["reference"] == selected and result["final_reference"] == selected,
            "REUSE_SELECTED_EFFECT_IDENTITY_MISMATCH")
    return {"call_ids": [row["call_id"] for row in calls], "runtime_addresses": addresses,
        "returned_effect_ids": [row["reference"]["effect_id"] for row in returns],
        "selected_effect_id": selected["effect_id"], "return_call": link["return_call"],
        "functional_addresses": [row["functional_address"] for row in link["call_sites"]]}


def run_reuse_suite(*, job, store_path, expected_digest, trust_inputs, source_public,
                    public_cases, output, native_output, call_count=2, return_call=0):
    # This must precede path reads, construction and any neural import.
    native_support.aws_guard(job)
    require(os.name == "posix" and hasattr(signal, "SIGALRM"), "AWS_LINUX_DEADLINE_REQUIRED")
    require(type(trust_inputs) is dict, "EXTERNAL_TRUST_OBJECT_REQUIRED")
    source = source_identity()
    output, native_output = native_support.checked_paths(output, native_output, job, new=True)
    store_path = Path(store_path).absolute()
    require(any(store_path.is_relative_to(ROOT / name) for name in ("records", "runs")), "REUSE_STORE_ROOT_REQUIRED")
    store = LearnedCandidateStore(store_path)
    store_hash = native_support.file_hash(store_path)
    retrieved = store.retrieve(expected_digest, **trust_inputs)
    linked = retrieve_for_reuse(store_path, expected_digest=expected_digest,
        call_count=call_count, return_call=return_call, **trust_inputs)
    proof = retrieved["handoff"]["learning_evidence"]
    check_public_cases(source_public, public_cases, retrieved["package"]["binding"], proof["public_sha256"])
    per_case = linked["link_receipt"]["derived_bounds"]["expanded_run_count"]
    require(2 * per_case * len(public_cases) <= MAX_TOTAL_NATIVE_RUNS, "REUSE_TOTAL_NATIVE_RUN_CEILING")
    require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), "EXISTING_DEADLINE_MUST_NOT_BE_REPLACED")
    output.mkdir(parents=True, exist_ok=False)
    native_output.mkdir(parents=True, exist_ok=False)
    native_support.save(output / "source_identity.json", source)
    native_support.save(output / "link_receipt.json", linked["link_receipt"])
    started = time.monotonic()
    previous_handler = signal.getsignal(signal.SIGALRM)
    def expired(*_):
        raise ReuseError("REUSE_WALL_DEADLINE")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(MAX_WALL_SECONDS)
    try:
        native, device, environment = native_support.cuda_runtime(job)
        results = []
        for index, public in enumerate(public_cases):
            # The frozen direct interpreter is the execution oracle. This is
            # reuse of a known learned program, not new problem-to-program inference.
            task = {"task_id": "learned-reuse-" + str(index), "public": deepcopy(public),
                    "target": deepcopy(linked["action"])}
            case_dir = native_output / ("case_" + str(index))
            case_dir.mkdir()
            reference = native.reference_task(task, case_dir / "reference", device=device)
            reference_verdict = native.verify_reference_task(task, reference)
            require(reference_verdict["task_correct"] is True, "REUSE_REFERENCE_FAILED")
            require(reference_compatibility(reference, source) == trust_inputs["trusted_compatibility"],
                    "FRESH_REUSE_RUNTIME_COMPATIBILITY_MISMATCH")
            candidate = native.execute_task(public, linked["action"], case_dir / "candidate", device=device)
            verdict = native.verify_task(task, candidate, reference)
            require(verdict["task_correct"] is True and verdict["native_runs"] == per_case
                    and verdict["stored_call_tree_verified"] is True, "REUSE_NATIVE_OUTPUT_VERIFICATION_FAILED")
            events = native_support.read(case_dir / "candidate/composition_events.json")
            mapping = check_root_calls(candidate, events, linked["link_receipt"])
            row = {"case_index": index, "task": task, "reference": reference,
                "reference_verdict": reference_verdict, "candidate": candidate, "verdict": verdict,
                "call_mapping": mapping}
            native_support.save(output / ("case_" + str(index) + ".json"), row)
            require(sum(p.stat().st_size for p in native_output.rglob("*") if p.is_file())
                    <= native_support.MAX_OUTPUT_BYTES, "REUSE_NATIVE_OUTPUT_BYTE_CEILING")
            results.append({"case_index": index, "task_correct": True, "candidate_native_runs": per_case,
                "reference_native_runs": per_case, "result_sha256": native_support.file_hash(output / ("case_" + str(index) + ".json"))})
        require(source_identity() == source and native_support.file_hash(store_path) == store_hash,
                "REUSE_SOURCE_OR_STORE_CHANGED")
        receipt = {"schema": "cas-meta3-learned-native-reuse/0.1", "status": "NATIVE_REUSE_EXECUTED",
            "job": job, "pid": os.getpid(), "process_nonce": uuid4().hex, "environment": environment,
            "package_sha256": expected_digest, "store_sha256": store_hash,
            "source_identity_sha256": native_support.file_hash(output / "source_identity.json"),
            "link_receipt_sha256": native_support.file_hash(output / "link_receipt.json"),
            "source_handoff_sha256": retrieved["handoff"]["receipt_sha256"],
            "source_learning_arm": proof["arm"], "source_learning_gain": proof["observed_correct_gain"],
            "cases": results, "native_runs": 2 * per_case * len(results),
            "wall_seconds": time.monotonic() - started, "qualification_status": "UNQUALIFIED",
            "promotion_granted": False, "learning_performed": False, "learned_retrieval_performed": False,
            "writer_exit_independently_verified": False, "retention_tested": False, "rollback_tested": False,
            "boundary": "Known learned-program reuse on new numeric inputs through a new deterministic parent. Separate process-exit, packet/schema audit, retention and rollback gates remain required."}
        native_support.save(output / "reuse_receipt.json", receipt)
        return receipt
    except Exception as error:
        native_support.save(output / "reuse_failure.json", {"schema": "cas-meta3-learned-reuse-failure/0.1",
            "job": job, "package_sha256": expected_digest, "error_type": type(error).__name__,
            "reason": str(error), "wall_seconds": time.monotonic() - started,
            "qualification_status": "UNQUALIFIED", "promotion_granted": False})
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def main():
    native_support.aws_guard()
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--request-sha256", required=True)
    args = parser.parse_args()
    request = native_support.read(args.request, args.request_sha256)
    run_reuse_suite(**request)


if __name__ == "__main__":
    main()
