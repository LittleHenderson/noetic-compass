"""Read one registered saved-repair packet using JSON, ZIP and byte hashes only.

This does not open SQLite, import neural packages, contact a provider, retry a
run, restore an outer caller, or independently execute the semantic decoder.
"""
from __future__ import annotations

import argparse
from base64 import b64decode, b64encode
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import time
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = "e85d224842c50b2be202c8a15181df0526fa26cc"
REGISTRATION_COMMIT = "8af76a090e9f0659a0c84e26c731eb54c3aa285d"
JOB = "cas-meta2-20260906165606-cbc41523"
REGISTRATION_HASH = "e61afa66c8d556389f97ffe8d8d7dcff837ade34f49ad699a9b02e81beb442c4"
REQUEST_HASH = "925629d418561f38453cb9fe9dce7c9fdd9e1035775e9cc0a1ba784ab81f10a9"
DB_HASH = "41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2"
DB_BYTES = 1523712
REPAIR_ID = "repair-3295d0e50cc47ac2f23bb183"
SUBGOAL_ID = "cause-6887f4b6a53020e465d7f15d"
PARENT_ID = "cause-0dc915a7acdf9ebf4fc0ae0b"
FRAME_HASH = "671bae98960f0791852a2cff43f8e06fd90f0d1060624ba06b9adf3a3f925609"
PRESTATE_HASH = "2cff5bb7a71995288d9f2aae3d8377a60361bf49da64833951ef62765a1db4c9"
MODEL_HASH = "76a9bcbce5ffdec4c2dbc9d8ea9958a268dcebf3775f53dd6058a72086709528"
HEAD = {"state_digest": "096674a1225dfd1b50acfa26422076cf215f5f3f21cd098d8290f0ab9fe54b17",
        "state_version": 6, "trace_digest": "66df9c33794e6ba201da151dd5416d046d095f5aa7f5fa9cd9ec231bfd929eeb",
        "model_digest": MODEL_HASH, "commit_receipt_id": "commit-7e24d42d525d62cfcc94b9a5"}
TRACE_HASHES = ["53e12850182ddfd4b53f3fe08e46b976579ca5168e3cd242ec30610863548414",
    "2831d9be59dfc6f6ecd4779416a95e5f3ac13316203f55bcd638ec23e6107d59",
    "dfb2581ebcb03588b274ecc8a68a3be31ae1ccc78778a07edf4c1acbcfc06fb4",
    "72630141311548428622144b1a037f778941cb892b6f9466056348f2c956eb62",
    "f4ac1561bdff893a78cf4be660bc984ab8f20d09626a09a1c37186905fbadf2f", HEAD["trace_digest"]]
PLAN_FIELDS = ("route_quanta", "reasoning_step_quanta", "branch_quanta",
               "memory_read_quanta", "diagnostic_probe_quanta")
FORBIDDEN = {"sqlite3", "_sqlite3", "torch", "numpy", "casformer", "cas_cjt",
             "cas_meta", "cas_meta1", "cas_meta2", "boto3", "botocore", "tensorflow", "jax"}


def require(condition, code):
    if not condition:
        raise ValueError(code)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        require(fullname.split(".")[0] not in FORBIDDEN, "FORBIDDEN_IMPORT:" + fullname)


def restrict_runtime():
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_PRELOADED_MODULE")
    sys.meta_path.insert(0, Guard())
    def audit(event, args):
        require(not event.startswith("socket.") and event not in
                {"sqlite3.connect", "subprocess.Popen", "os.system", "os.posix_spawn"},
                "FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def hashed(raw):
    return sha256(raw).hexdigest()


def document_hash(value, field):
    return type(value) is dict and value.get(field) == hashed(canonical(
        {key: item for key, item in value.items() if key != field}))


def decode(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, "NONFINITE_JSON"))


def safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or
        getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)), "UNSAFE_PATH")
    return path


def raw_file(path, maximum=4 * 1024**2):
    path = safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum, "FILE_BOUND")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "FILE_CHANGED_DURING_READ")
    return raw


def integer_sum(value):
    if type(value) is int:
        require(value >= 0, "NEGATIVE_POLICY_UNIT")
        return value
    require(type(value) is list, "NONINTEGER_POLICY_UNIT")
    return sum(integer_sum(item) for item in value)


def plan_units(plan):
    return sum(integer_sum(plan[key]) for key in PLAN_FIELDS)


def proposal_evidence(observation):
    """Verify bytes and reference integrity; never turn observation into a commit."""
    require(type(observation) is dict and "observation_error" not in observation, "PROPOSAL_BYTES_UNAVAILABLE")
    payload = b64decode(observation["payload_base64"], validate=True)
    require(b64encode(payload).decode("ascii") == observation["payload_base64"], "NONCANONICAL_BASE64")
    ref, metadata = observation["reference"], observation["metadata"]
    header = {"encoding": observation["encoding"], "kind": observation["kind"],
              "media_type": observation["media_type"], "metadata": metadata,
              "payload_byte_length": len(payload)}
    bound = hashed(canonical(header) + b"\n" + payload)
    require(hashed(payload) == observation["payload_sha256"], "PROPOSAL_RAW_HASH")
    require(bound == observation["artifact_sha256"] == ref["sha256"]
            and ref["artifact_id"] == "artifact-" + bound[:24], "PROPOSAL_BOUND_HASH")
    require(ref["encoding"] == observation["encoding"] == "raw-contiguous-v1"
            and ref["byte_length"] == len(payload) and metadata["dtype"] == ref["dtype"]
            and metadata["shape"] == ref["shape"], "PROPOSAL_REFERENCE_METADATA")
    sizes = {"bool": 1, "uint8": 1, "int8": 1, "int16": 2, "int32": 4,
             "int64": 8, "float16": 2, "bfloat16": 2, "float32": 4, "float64": 8}
    count = 1
    for size in ref["shape"]:
        require(type(size) is int and size > 0, "PROPOSAL_SHAPE")
        count *= size
    require(0 < count <= 256 and count == metadata["numel"]
            and len(payload) == count * sizes[ref["dtype"]], "PROPOSAL_BYTE_LENGTH")
    require(observation["kind"] == "diagnostic-uncommitted-proposal"
            and observation["media_type"] == "application/vnd.cas.tensor"
            and observation["not_a_commit_receipt"] is True
            and observation["additional_neural_forward"] is False, "PROPOSAL_BOUNDARY")
    return {"byte_integrity_verified": True, "payload_sha256": hashed(payload),
            "artifact_sha256": bound, "payload_bytes": len(payload),
            "reported_decoded_content": observation["decoded_content"],
            "semantic_decoder_reexecuted_locally": False, "proves_commit_or_acceptance": False}


def inspect_core(core, files):
    checks, stages = [], []
    def check(ok, name):
        checks.append({"check": name, "ok": ok is True})
        return ok is True
    def record(name):
        key = "repair/repair/" + name
        require(key in files, "MISSING_RECORD:" + name)
        return decode(files[key])
    check(core["schema"] == "cas-meta2-saved-repair/8", "core_schema")
    before, after = core["before"], core["after"]
    check(before == record("before.json") and after == record("after.json"), "snapshot_record_copies")
    old, traces = before["traces"], after["traces"]
    check(before["head"] == HEAD and len(old) == 6
          and [t["trace_digest"] for t in old] == TRACE_HASHES
          and [t["tick"] for t in old] == list(range(1, 7)), "pinned_original_six_traces")
    check(traces[:6] == old, "original_six_traces_retained_exactly")
    check(all(document_hash(t, "trace_digest") for t in traces), "trace_document_hashes")
    check(all(traces[i]["previous_trace_digest"] == traces[i - 1]["trace_digest"]
              for i in range(1, len(traces))), "trace_digest_chain")
    check(all(document_hash(s["state"], "state_digest")
              and s["state"]["state_digest"] == s["head"]["state_digest"]
              and s["head"]["trace_digest"] == s["traces"][-1]["trace_digest"]
              for s in (before, after)), "snapshot_state_head_binding")
    check(before["integrity"] is True and after["integrity"] is True, "worker_reported_store_integrity")
    reconstruction = record("reconstruction.json")
    frame = reconstruction["frame"]
    check(frame["repair_id"] == REPAIR_ID and frame["frame_digest"] == FRAME_HASH
          and document_hash(frame, "frame_digest") and frame["status"] == "OPEN"
          and old[5]["repair_frames"] == [frame], "original_immutable_open_frame")
    check(reconstruction["pre_state_digest"] == PRESTATE_HASH
          and old[5]["pre_state_digest"] == PRESTATE_HASH
          and reconstruction["pre_bias_version"] == 1
          and [b for b in old[5]["state_before"]["biases"] if b["cjt_id"] == "R"][0]["version"] == 1
          and reconstruction["subgoal"]["cause_id"] == SUBGOAL_ID
          and reconstruction["subgoal"]["tick"] == 7
          and frame["subgoal_cause_id"] == SUBGOAL_ID
          and reconstruction["original_parent_cause"]["cause_id"] == PARENT_ID
          and reconstruction["full_frame_match"] is True, "exact_prestate_R_v1_subgoal_reconstruction")
    check(before["identity"] == after["identity"]
          and before["identity"]["model"]["model_digest"] == MODEL_HASH
          and after["head"]["model_digest"] == MODEL_HASH, "model_and_runtime_identity_unchanged")
    final = core["postchecks"]
    check(final["model_before"] == final["model_after"] == before["identity"]["model"]
          and all(final[k] is True for k in ("weights_unchanged", "sources_unchanged", "protected_identities_unchanged"))
          and final["errors"] == [], "frozen_postchecks")
    check(core["original_database_unchanged"] is True
          and len(files["repair/original_native.db"]) == DB_BYTES
          and hashed(files["repair/original_native.db"]) == DB_HASH, "original_database_bytes_unchanged")
    attempts = core["attempts"]
    check(type(attempts) is list and len(attempts) <= 2
          and [(a["cjt_id"], a["tick"]) for a in attempts] == [("C", 7), ("R", 8)][:len(attempts)], "bounded_attempt_sequence")
    check([t["tick"] for t in traces[6:]] == list(range(7, 7 + len(traces[6:])))
          and len(traces[6:]) <= len(attempts) and after["head"]["state_version"] == len(traces), "committed_tick_sequence")
    returned = accepted = attempted_units = committed_units = 0
    results = {}
    for cjt, tick, target in (("C", 7, "L2"), ("R", 8, "L1")):
        attempted = next((a for a in attempts if a["tick"] == tick), None)
        trace = next((t for t in traces[6:] if t["tick"] == tick), None)
        result_key = "repair/repair/result_%02d.json" % tick
        result = decode(files[result_key]) if result_key in files else None
        row = {"cjt_id": cjt, "tick": tick, "expected_symbol": target,
               "attempted": attempted is not None, "returned": False,
               "committed": trace is not None, "accepted": False,
               "published_effect_ids": [], "proposal_observation": None}
        if attempted is not None:
            row["returned"] = attempted["returned"] is True
            returned += row["returned"]
            check(attempted == record("attempt_%02d_finished.json" % tick), "attempt_finished_copy_%d" % tick)
            check(attempted["expected_symbol"] == target and attempted["resume_repair_id"] ==
                  (REPAIR_ID if cjt == "R" else None), "frozen_target_and_resume_%d" % tick)
            plan = attempted["plan"]
            units = plan_units(plan["compute_plan"])
            attempted_units += units
            check(units == plan["policy_units"] and 0 < units <= 8192
                  and plan["plan_digest"] == hashed(canonical(plan["compute_plan"])), "attempt_plan_%d" % tick)
            check(not row["returned"] or result is not None, "returned_result_retained_%d" % tick)
            observation = attempted.get("proposal_observation")
            if observation and "observation_error" not in observation:
                row["proposal_observation"] = proposal_evidence(observation)
                check(observation["tick"] == tick and observation["cjt_id"] == cjt, "proposal_call_identity_%d" % tick)
            elif observation:
                row["proposal_observation"] = {"byte_integrity_verified": False, "observation_error": observation["observation_error"],
                                              "proves_commit_or_acceptance": False}
            row["error"] = attempted["error"]
            row["gpu_module_entries_delta"] = attempted["gpu_forward_calls_after"] - attempted["gpu_forward_calls_before"]
            check(not row["returned"] or row["gpu_module_entries_delta"] > 0, "returned_call_gpu_observation_%d" % tick)
        if trace is not None:
            candidate, verifier = trace["candidate_effects"][0], trace["verifier_receipts"][0]
            row["published_effect_ids"] = trace["published_effect_ids"]
            row["actual_symbol"] = candidate["content"]["symbol"]
            row["verifier_disposition"] = verifier["disposition"]
            row["accepted"] = (len(trace["candidate_effects"]) == len(trace["verifier_receipts"]) == 1
                and verifier["disposition"] == "ACCEPT" and verifier["semantic_outcome"] == "INTENDED"
                and verifier["repair_required"] is False and len(trace["published_effect_ids"]) == 1
                and candidate["producer_cjt_id"] == cjt and candidate["content"]["symbol"] == target)
            accepted += row["accepted"]
            committed_units += plan_units(trace["compute_plan"])
            check(attempted is not None and trace["compute_plan"] == attempted["plan"]["compute_plan"], "committed_plan_%d" % tick)
            check(document_hash(candidate, "candidate_digest") and document_hash(verifier, "receipt_digest")
                  and verifier["candidate_effect_id"] == candidate["candidate_effect_id"]
                  and verifier["candidate_effect_digest"] == candidate["candidate_digest"]
                  and verifier["tick"] == candidate["tick"] == tick
                  and verifier["cause_id"] == candidate["parent_cause_id"] == trace["cause"]["cause_id"],
                  "committed_candidate_verifier_%d" % tick)
        if result is not None:
            results[cjt] = result
            check(result["tick"] == tick and result["cjt_id"] == cjt and trace is not None
                  and result["trace"] == trace and result["candidate_effect"] == trace["candidate_effects"][0]
                  and result["verifier_receipt"] == trace["verifier_receipts"][0], "returned_stored_result_%d" % tick)
            effect = result["published_effect"]
            check(effect is not None and document_hash(effect, "publication_digest")
                  and effect["published_effect_id"] in trace["published_effect_ids"]
                  and effect["producer_cjt_id"] == cjt and effect["tick"] == tick
                  and effect["content"] == result["candidate_effect"]["content"]
                  and effect["candidate_effect_id"] == result["candidate_effect"]["candidate_effect_id"]
                  and effect["content_ref"] == result["candidate_effect"]["content_ref"]
                  and result["commit_receipt"]["published_effect_ids"] == [effect["published_effect_id"]]
                  and effect["commit_receipt_id"] == result["commit_receipt"]["receipt_id"]
                  and trace["commit_receipt_id"] == result["commit_receipt"]["receipt_id"], "published_effect_link_%d" % tick)
            if cjt == "C":
                check(result["cause"] == reconstruction["subgoal"], "C_uses_exact_reconstructed_subgoal")
            else:
                original_parent = reconstruction["original_parent_cause"]
                check("C" in results and result["cause"]["parent_effect_id"] == results["C"]["published_effect"]["published_effect_id"]
                      and result["cause"]["candidate_operation_ids"] == original_parent["candidate_operation_ids"]
                      and result["cause"]["goal_context"] == original_parent["goal_context"], "R_resumes_exact_child_effect_and_original_context")
        stages.append(row)
    counts = {"native_call_attempts": len(attempts), "returned_native_calls": returned,
              "completed_new_ticks": len(traces[6:]), "accepted_new_ticks": accepted,
              "attempted_policy_units": attempted_units, "committed_policy_units": committed_units}
    check(all(type(core.get(k)) is int and core[k] == v for k, v in counts.items())
          and attempted_units <= 16384, "independent_counts_match_receipt")
    closure_verified = False
    closure = core.get("closure")
    if closure is not None and set(results) == {"C", "R"}:
        child, resumed = results["C"], results["R"]
        outcome, effect = closure["outcome"], child["published_effect"]
        rpm = [b for b in after["state"]["biases"] if b["cjt_id"] == "R"][0]["rpm"]
        expected = {"repair_id": REPAIR_ID, "tick": 8, "frame_digest": FRAME_HASH,
            "result_effect_id": effect["published_effect_id"], "result_effect_digest": effect["publication_digest"],
            "result_effect_commit_receipt_id": effect["commit_receipt_id"],
            "resumed_cause_id": resumed["cause"]["cause_id"],
            "resumed_candidate_effect_id": resumed["candidate_effect"]["candidate_effect_id"],
            "verifier_receipt_id": resumed["verifier_receipt"]["receipt_id"],
            "target_bias_id": "bias:R", "target_bias_version": 2,
            "target_bias_digest": resumed["bias_before"]["state_digest"]}
        closure_verified = check(closure == record("closure.json") and document_hash(outcome, "outcome_digest")
            and outcome == resumed["repair_outcome"] and outcome["status"] == "RETURNED"
            and all(outcome[k] == v for k, v in expected.items())
            and outcome["outcome_id"] == "repair-outcome-" + hashed(canonical(expected))[:24]
            and resumed["trace"]["repair_outcomes"] == [outcome]
            and rpm == closure["R_rpm"] and rpm["open_repair_ids"] == []
            and rpm["suspended_parent_cause_id"] is None and rpm["return_addresses"] == []
            and REPAIR_ID in rpm["repair_history"] and closure["frame_unchanged"] is True,
            "separate_returned_outcome_and_cleared_R_rpm")
    check(core["training"] is False and all(core["claim_boundary"].get(k) is False for k in
          ("outer_caller_stack_restored", "full_task_return_proven", "qualification_passed",
           "learning_proven", "universal_R_expected_L1_claimed", "training")), "claim_boundary")
    facts_succeed = all(c["ok"] for c in checks) and closure_verified and all(
        row[k] is True for row in stages for k in ("attempted", "returned", "committed", "accepted"))
    return {"checks": checks, "stages": stages, "independent_counts": counts,
            "repair_closure_verified": closure_verified, "repair_facts_succeed": facts_succeed,
            "reported_core_status": core["status"], "reported_repaired": core["repaired"],
            "core_failures": core["failures"], "gpu_forward_audit": core["gpu_forward_audit"],
            "R_rpm_after": [b for b in after["state"]["biases"] if b["cjt_id"] == "R"][0]["rpm"]}


def success_from_evidence(core_analysis, packet, core, outer):
    return (core_analysis["repair_facts_succeed"] is True and packet["native_success"] is True
            and core["failures"] == [] and core["repaired"] is True and core["status"] == "REPAIR_RESUMED"
            and outer["status"] == "AWS_SAVED_NATIVE_REPAIR_FINISHED" and outer.get("source_postcheck") == {"ok": True})


def analyze():
    registration_raw = raw_file(HERE / "registration_001/registration_receipt.json")
    request_raw = raw_file(HERE / "registration_001/launch_request.json")
    require(hashed(registration_raw) == REGISTRATION_HASH and hashed(request_raw) == REQUEST_HASH, "REGISTRATION_PIN")
    registration, request = decode(registration_raw), decode(request_raw)
    require(registration["job"] == request["job"] == JOB
            and registration["source_sha"] == request["worker_source_sha"] == request["parent_source_sha"] == SOURCE,
            "REGISTERED_SOURCE_JOB")
    for name, pin in request["parent_file_sha256"].items():
        require(hashed(raw_file(ROOT / name)) == pin, "PARENT_SOURCE_CHANGED:" + name)
    lifecycle_path = HERE / "execution_001/lifecycle/launch_receipt.json"
    outer_path = HERE / "execution_001/launch_receipt.json"
    lifecycle_raw, outer_raw = raw_file(lifecycle_path), raw_file(outer_path)
    lifecycle, outer = decode(lifecycle_raw), decode(outer_raw)
    require(lifecycle["job"] == outer["job"] == JOB and lifecycle["source_sha"] == outer["source_sha"] == SOURCE
            and lifecycle["request_sha256"] == outer["request_sha256"] == REQUEST_HASH, "LAUNCH_BINDING")
    artifact = HERE / "execution_001/lifecycle/cloud_artifacts.zip"
    require(artifact.is_file() and "result" in lifecycle, "LOCAL_RESULT_NOT_YET_AVAILABLE")
    plan_raw = raw_file(HERE / "execution_001/lifecycle/worker_plan.json")
    plan = decode(plan_raw)
    require(plan["job"] == JOB and plan["source_sha"] == SOURCE, "WORKER_PLAN_BINDING")
    require([e["worker_plan_sha256"] for e in lifecycle["events"] if e["event"] ==
             "WORKER_PERMIT_PUBLISHED_AFTER_CONFIRMED_SHUTDOWN"] == [hashed(plan_raw)], "WORKER_PLAN_RECEIPT_HASH")
    spec = importlib.util.spec_from_file_location("saved_repair_analysis_parent", ROOT / "aws/launch_saved_repair_v8.py")
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    packet = parent.verify_packet(artifact, lifecycle["result"], request, hashed(plan_raw))
    raw = raw_file(artifact, 268435456)
    with ZipFile(io.BytesIO(raw)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    output = {"schema": "cas-meta2-saved-repair-independent-analysis/8", "job": JOB, "source_sha": SOURCE,
        "registration_commit_supplied_by_parent": REGISTRATION_COMMIT,
        "registration_receipt_sha256": hashed(registration_raw), "request_sha256": hashed(request_raw),
        "worker_plan_sha256": hashed(plan_raw), "artifact_sha256": hashed(raw),
        "lifecycle_receipt_sha256": hashed(lifecycle_raw), "outer_launch_receipt_sha256": hashed(outer_raw),
        "parent_packet_verification": {k: v for k, v in packet.items() if k not in ("worker_receipt", "collection")},
        "reported_launch_status": outer["status"], "reported_lifecycle_status": lifecycle["status"],
        "local_sqlite_opened": False, "local_neural_execution": False, "provider_calls": False,
        "outer_caller_restored": False, "learning_proven": False, "qualification_passed": False,
        "status": "NEGATIVE_OR_INCOMPLETE", "independent_native_repair_success": False}
    worker = packet.get("worker_receipt")
    if worker is None or worker.get("repair") is None:
        output["unavailable"] = "No complete core repair receipt was collected."
        return output
    core = worker["repair"]
    require(decode(files["repair/repair/repair_receipt.json"]) == core, "CORE_RECEIPT_COPY")
    for name, pin in core.get("files_sha256", {}).items():
        key = "repair/repair/" + parent.safe_member(name)
        require(key not in files or hashed(files[key]) == pin, "CORE_RECORD_HASH:" + name)
    try:
        output["core_analysis"] = inspect_core(core, files)
    except (ValueError, KeyError, TypeError, IndexError) as error:
        output["analysis_failure"] = {"type": type(error).__name__, "message": str(error)}
        return output
    success = success_from_evidence(output["core_analysis"], packet, core, outer)
    output["independent_native_repair_success"] = success
    output["status"] = "SAVED_NATIVE_REPAIR_VERIFIED" if success else "NEGATIVE_OR_INCOMPLETE"
    return output


def self_test():
    payload = b"12345678"
    metadata = {"dtype": "float32", "shape": [1, 2], "numel": 2}
    observation = {"payload_base64": b64encode(payload).decode("ascii"), "payload_sha256": hashed(payload),
        "metadata": metadata, "kind": "diagnostic-uncommitted-proposal", "encoding": "raw-contiguous-v1",
        "media_type": "application/vnd.cas.tensor", "decoded_content": {"symbol": "SIMULATED"},
        "not_a_commit_receipt": True, "additional_neural_forward": False}
    bound = hashed(canonical({k: observation[k] for k in ("encoding", "kind", "media_type", "metadata")} |
                              {"payload_byte_length": len(payload)}) + b"\n" + payload)
    observation["artifact_sha256"] = bound
    observation["reference"] = {"artifact_id": "artifact-" + bound[:24], "sha256": bound,
        "dtype": "float32", "shape": [1, 2], "encoding": "raw-contiguous-v1", "byte_length": 8}
    require(proposal_evidence(observation)["proves_commit_or_acceptance"] is False, "SELFTEST_NEGATIVE_BOUNDARY")
    for key, value in (("payload_sha256", "0" * 64), ("artifact_sha256", "0" * 64),
                       ("not_a_commit_receipt", False), ("payload_base64", "!!!!")):
        broken = deepcopy(observation)
        broken[key] = value
        try:
            proposal_evidence(broken)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("SELFTEST_FAILED:" + key)
    simulated_core = {"repaired": True, "status": "REPAIR_RESUMED", "failures": []}
    simulated_outer = {"status": "AWS_SAVED_NATIVE_REPAIR_FINISHED", "source_postcheck": {"ok": True}}
    require(not success_from_evidence({"repair_facts_succeed": False}, {"native_success": True},
                                      simulated_core, simulated_outer), "SELFTEST_REPAIRED_FLAG_IS_NOT_EVIDENCE")
    require(not success_from_evidence({"repair_facts_succeed": True}, {"native_success": False},
                                      simulated_core, simulated_outer), "SELFTEST_NEGATIVE_PACKET_NOT_PROMOTED")
    print(json.dumps({"status": "SELF_TEST_PASSED", "checks": 7,
                      "simulated_bytes_only": True, "native_evidence": False}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(HERE / "analysis_001"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    restrict_runtime()
    if args.self_test:
        self_test()
        return 0
    started, started_utc = time.monotonic(), datetime.now(timezone.utc).isoformat()
    report = analyze()
    output = safe(args.output)
    require(output.parent == HERE and output.name.startswith("analysis_") and not output.exists(), "FRESH_ANALYSIS_DIRECTORY_REQUIRED")
    output.mkdir()
    report_raw = json.dumps(report, sort_keys=True, indent=2, allow_nan=False).encode("ascii") + b"\n"
    with (output / "analysis.json").open("xb") as stream:
        stream.write(report_raw)
    receipt = {"schema": "cas-meta2-saved-repair-analysis-command/8", "command": [sys.executable, *sys.argv],
        "cwd": str(Path.cwd()), "python": sys.version, "analyzer_sha256": hashed(raw_file(__file__)),
        "analysis_sha256": hashed(report_raw), "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic() - started,
        "status": report["status"], "analysis_completed": "analysis_failure" not in report,
        "forbidden_modules_loaded": sorted(FORBIDDEN.intersection(sys.modules)),
        "local_sqlite_opened": False, "local_neural_execution": False, "provider_calls": False}
    with (output / "command_receipt.json").open("xb") as stream:
        stream.write(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False).encode("ascii") + b"\n")
    print(json.dumps({"status": report["status"], "independent_native_repair_success": report["independent_native_repair_success"],
                      "analysis": str(output / "analysis.json"), "analysis_failure": report.get("analysis_failure")}))
    return 0 if "analysis_failure" not in report else 1


if __name__ == "__main__":
    raise SystemExit(main())
