"""Synthetic component fixtures only; never a full native-success evidence set.

The in-memory packet deliberately has non-native placeholder bodies. Passing a
header/process/call component test is not a successful full semantic audit.
No checkpoint, tensor, native runtime, provider, or reserved task is opened.
"""
from copy import deepcopy
from hashlib import sha256
import ast
import json
from pathlib import Path
import sys

import pytest

from tools import audit_native_demo as audit


pytestmark = pytest.mark.not_gpu
JOB = "synthetic_component_fixture"
SOURCE = {"fixture_only": "NOT REAL NATIVE OR PROVIDER EVIDENCE"}
ROOTS = {"demo": "/synthetic-only/demo", "native": "/synthetic-only/native"}


def fake_hash(label):
    return sha256(("SYNTHETIC COMPONENT ONLY:" + label).encode()).hexdigest()


def stamp(second):
    return f"2026-01-01T00:00:{second:02d}+00:00"


class SyntheticPacket:
    """Only enough byte-bound methods for individual component checks."""
    def __init__(self):
        self.members = {}
        self.inventory = {}
        self.receipt = {"synthetic_component_only": True}
        self.index = {"roots": deepcopy(ROOTS), "entries": []}
        self.sidecar_hashes = {"memory_demo_receipt.json": fake_hash("header-sidecar"),
                               "file_index.json": fake_hash("index-sidecar")}

    def put(self, name, value):
        raw = value if isinstance(value, bytes) else audit.canonical(value) + b"\n"
        self.members[name] = raw
        checksum = sha256(raw).hexdigest()
        root, relative = name.split("/", 1)
        self.inventory[name] = {"root": root, "path": relative, "bytes": len(raw), "sha256": checksum}
        return checksum

    def raw(self, name):
        assert name in self.members, "SYNTHETIC_FIXTURE_MEMBER_MISSING:" + name
        raw = self.members[name]
        audit.require(sha256(raw).hexdigest() == self.inventory[name]["sha256"], "SYNTHETIC_MEMBER_HASH_CHANGED")
        return raw

    def json(self, name):
        return json.loads(self.raw(name))

    def same_hash(self, name, expected):
        audit.require(name in self.inventory and self.inventory[name]["sha256"] == expected,
                      "SEALED_MEMBER_HASH_MISMATCH:" + name)

    def mutate(self, name, change):
        value = self.json(name)
        change(value)
        return self.put(name, value)


def header_fixture():
    packet = SyntheticPacket()
    packet.put("demo/task.json", audit.expected_task())
    for name in ("trusted_compatibility.json", "writer_process.json", "reader_process.json"):
        packet.put("demo/" + name, {"synthetic_placeholder_not_valid_component": name})
    packet.put("native/mock-only.bin", b"SYNTHETIC, NOT A NATIVE DATABASE")
    packet.index.update(schema="cas-meta3-file-index/0.1", entries=list(packet.inventory.values()))
    packet.index["entries_sha256"] = audit.digest(packet.index["entries"])
    # This header exists only in memory and is not a full-run receipt or packet.
    packet.receipt.update(schema="cas-meta3-native-reuse/0.1", status="CAS_META_3_NATIVE_REUSE_DEMONSTRATED",
        completed=True, job=JOB, qualification_status="UNQUALIFIED", learning_performed=False,
        automatic_retries=0, reference_native_runs=3, candidate_native_runs=3, identity_probe_native_ticks=0,
        max_wall_seconds=600, wall_seconds=10, output=ROOTS["demo"], native_output=ROOTS["native"])
    for name, field in (("task.json", "independent_task_sha256"),
                        ("trusted_compatibility.json", "trusted_compatibility_sha256"),
                        ("writer_process.json", "writer_process_sha256"), ("reader_process.json", "reader_process_sha256")):
        packet.receipt[field] = packet.inventory["demo/" + name]["sha256"]
    return packet


def check_header(packet, job=JOB, **overrides):
    return audit.checked_header(packet, job=job,
        demo_receipt_sha256=overrides.get("demo_sha", packet.sidecar_hashes["memory_demo_receipt.json"]),
        file_index_sha256=overrides.get("index_sha", packet.sidecar_hashes["file_index.json"]))


def process_fixture():
    packet = SyntheticPacket()
    package_hash = packet.put("demo/package.json", {"synthetic_placeholder": "not a package"})
    trusted_hash = packet.put("demo/trusted_compatibility.json", {"synthetic_placeholder": "not trusted identity"})
    registry_hash = packet.put("demo/registry.db", b"SYNTHETIC BYTES, NOT SQLITE")
    child_hashes = {name: packet.put("demo/" + name, {"synthetic_placeholder": name}) for name in (
        "rejection_receipt.json", "link_receipt.json", "identity_probe_receipt.json", "candidate_result.json",
        "candidate_verdict.json", "call_mapping_receipt.json")}
    package_digest = fake_hash("package-digest")
    packet.receipt.update(package_digest=package_digest, registry_sha256_before=registry_hash,
                          registry_sha256_after=registry_hash)
    common = {"schema": "cas-meta3-process-request/0.1", "job": JOB, "output": ROOTS["demo"],
        "native_output": ROOTS["native"], "source": deepcopy(SOURCE), "trusted_sha256": trusted_hash,
        "package_file_sha256": package_hash, "package_digest": package_digest}
    for number, stage in enumerate(("writer", "reader")):
        offset, pid, nonce = number * 4, 101 + number, str(number + 1) * 32
        request = {**deepcopy(common), "stage": stage, "created_utc": stamp(offset)}
        if stage == "reader":
            request.update(writer_process_sha256=packet.inventory["demo/writer_process.json"]["sha256"],
                           writer_receipt_sha256=packet.inventory["demo/writer_receipt.json"]["sha256"])
        request_hash = packet.put("demo/" + stage + "_request.json", request)
        process = {"schema": "cas-meta3-process-exit/0.1", "stage": stage, "pid": pid, "parent_pid": 100,
            "returncode": 0, "timed_out_or_interrupted": False, "automatic_retries": 0,
            "started_utc": stamp(offset + 1), "finished_utc": stamp(offset + 3), "request_sha256": request_hash,
            "command": ["/synthetic/python", "-B", "-m", "cas_meta3.native_demo", "--stage", stage, "--request",
                        ROOTS["demo"] + "/" + stage + "_request.json", "--request-sha256", request_hash]}
        receipt = {"schema": "cas-meta3-" + stage + "/0.1", "job": JOB, "source": deepcopy(SOURCE),
            "pid": pid, "process_nonce": nonce, "utc": stamp(offset + 2), "request_sha256": request_hash,
            "package_digest": package_digest, "qualification_status": "UNQUALIFIED", "learning_performed": False}
        if stage == "writer":
            receipt.update(registry_closed=True, native_execution_performed=False, registry_sha256=registry_hash)
        else:
            receipt.update(fresh_process=True, writer_pid=101, writer_process_nonce="1" * 32,
                writer_process_sha256=request["writer_process_sha256"], writer_receipt_sha256=request["writer_receipt_sha256"],
                receipt_sha256=child_hashes, registry_sha256_before=registry_hash, registry_sha256_after=registry_hash,
                package_file_sha256_before=package_hash, package_file_sha256_after=package_hash)
        packet.put("demo/" + stage + "_process.json", process)
        packet.put("demo/" + stage + "_receipt.json", receipt)
        packet.put("demo/" + stage + ".stdout.log", b"SYNTHETIC STDOUT ONLY")
        packet.put("demo/" + stage + ".stderr.log", b"")
    return packet


def call_fixture():
    packet = SyntheticPacket()
    def effect(identifier, producer):
        return {"kind": "effect", "effect_id": identifier, "producer_cjt_id": producer,
                "payload_sha256": fake_hash("same-B-bytes" if producer == "B" else "A-bytes")}
    a, first, last = effect("fixture-A", "A"), effect("fixture-first-B", "B"), effect("fixture-last-B", "B")
    events = [{"kind": "ENTER", "run_id": "fixture-run", "address": "entry"},
              {"kind": "NATIVE", "run_id": "fixture-run", "cjt_id": "A", "output_reference": a}]
    rows = []
    for index, reference in enumerate((first, last), 1):
        call_id = f"fixture-run:entry/{index}"
        events.extend([{"kind": "ENTER", "run_id": "fixture-run", "address": f"entry/{index}",
                        "call_id": call_id, "procedure": "p0", "input_reference": a},
                       {"kind": "NATIVE", "run_id": "fixture-run", "address": f"entry/{index}/0", "call_id": call_id,
                        "cjt_id": "B", "input_reference": a, "output_reference": reference}])
        rows.append({"caller": "main", "pc": index, "functional_address": f"entry:main/steps/{index}",
            "runtime_address": f"entry/{index}", "call_id": call_id, "input_effect_id": a["effect_id"],
            "output_effect_id": reference["effect_id"]})
    events.append({"kind": "RETURN", "run_id": "fixture-run", "address": "entry", "reference": first})
    link = {"cognitive_address": "package:" + fake_hash("package") + "/stored_b"}
    mapping = {"schema": "cas-meta3-native-call-mapping/0.1", "package_address": link["cognitive_address"],
        "run_id": "fixture-run", "calls": rows, "final_effect_id": first["effect_id"], "return_node": 1,
        "expected_native_edges": [{"cjt_id": "A", "input_node": -1}, {"cjt_id": "B", "input_node": 0},
                                   {"cjt_id": "B", "input_node": 0}],
        "package_address_is_not_call_id": True, "first_B_identity_returned": True}
    packet.put("native/candidate/composition_events.json", events)
    packet.put("demo/call_mapping_receipt.json", mapping)
    return packet, {"final_reference": first}, link


def test_expected_task_is_independently_authored_and_matches_demo_once():
    from cas_meta3.native_demo import fixed_task
    assert audit.expected_task() == fixed_task()
    tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "expected_task")
    assert not any(isinstance(item, ast.Name) and item.id in ("fixed_task", "link_demonstration", "retrieve_and_link")
                   for item in ast.walk(node))
    assert "torch" not in sys.modules


def test_synthetic_header_component_passes_without_full_native_claim():
    packet = header_fixture()
    assert check_header(packet) is packet.receipt
    assert packet.receipt["synthetic_component_only"] is True
    assert not hasattr(packet, "completed")


@pytest.mark.parametrize("field,value", [("schema", "wrong"), ("status", "CAS_META_3_NATIVE_REUSE_BLOCKED"),
    ("completed", False), ("job", "other-job"), ("qualification_status", "QUALIFIED"), ("learning_performed", True),
    ("automatic_retries", True), ("candidate_native_runs", True), ("reference_native_runs", 2),
    ("identity_probe_native_ticks", 1), ("max_wall_seconds", 1201), ("wall_seconds", float("nan")),
    ("wall_seconds", 600), ("output", "/changed/demo")])
def test_header_status_scope_counts_time_and_roots_tampering_rejects(field, value):
    packet = header_fixture()
    packet.receipt[field] = value
    with pytest.raises(audit.AuditError):
        check_header(packet)


@pytest.mark.parametrize("mutation", ["demo-sidecar", "index-sidecar", "entries-digest", "entries-body", "member-binding", "expected-task", "job-format"])
def test_header_external_hashes_index_and_authored_task_are_not_trusted(mutation):
    packet = header_fixture()
    kwargs = {}
    if mutation == "demo-sidecar":
        kwargs["demo_sha"] = "0" * 64
    elif mutation == "index-sidecar":
        kwargs["index_sha"] = "0" * 64
    elif mutation == "entries-digest":
        packet.index["entries_sha256"] = "0" * 64
    elif mutation == "entries-body":
        packet.index["entries"][0]["bytes"] += 1
    elif mutation == "member-binding":
        packet.receipt["writer_process_sha256"] = "0" * 64
    elif mutation == "expected-task":
        task = packet.json("demo/task.json")
        task["target"]["program"]["procedures"]["main"]["return"] = "v2"
        packet.receipt["independent_task_sha256"] = packet.put("demo/task.json", task)
    else:
        kwargs["job"] = "../escape"
    with pytest.raises(audit.AuditError):
        check_header(packet, **kwargs)


def test_synthetic_process_component_proves_only_its_record_relationships():
    packet = process_fixture()
    assert audit.check_processes(packet, SOURCE, job=JOB) == {"writer_pid": 101, "reader_pid": 102,
        "distinct_processes": True, "successful_writer_exit_precedes_reader_request": True, "registry_bytes_unchanged": True}
    assert packet.raw("demo/registry.db") == b"SYNTHETIC BYTES, NOT SQLITE"


@pytest.mark.parametrize("name,field,value", [
    ("writer_request", "source", {"changed": True}), ("reader_receipt", "job", "other-job"),
    ("reader_request", "native_output", "/other/native"), ("writer_process", "returncode", 1),
    ("writer_process", "returncode", False), ("reader_process", "timed_out_or_interrupted", True),
    ("reader_process", "automatic_retries", 1), ("writer_process", "pid", True),
    ("reader_receipt", "pid", 999), ("reader_receipt", "process_nonce", "bad"),
    ("reader_receipt", "process_nonce", "1" * 32), ("reader_process", "parent_pid", 999),
    ("reader_receipt", "writer_pid", 777), ("reader_receipt", "writer_process_nonce", "3" * 32),
    ("writer_receipt", "registry_closed", False), ("writer_receipt", "native_execution_performed", True),
    ("reader_receipt", "fresh_process", False), ("reader_receipt", "qualification_status", "QUALIFIED"),
    ("writer_receipt", "learning_performed", True), ("reader_receipt", "registry_sha256_after", "0" * 64),
    ("reader_receipt", "package_file_sha256_after", "0" * 64),
    ("reader_receipt", "writer_receipt_sha256", "0" * 64),
    ("reader_receipt", "receipt_sha256", {}), ("writer_request", "package_digest", "0" * 64)])
def test_process_source_job_scope_pid_nonce_and_binding_tampering_rejects(name, field, value):
    packet = process_fixture()
    packet.mutate("demo/" + name + ".json", lambda record: record.__setitem__(field, value))
    with pytest.raises(audit.AuditError):
        audit.check_processes(packet, SOURCE, job=JOB)


@pytest.mark.parametrize("name,field,value", [
    ("writer_process", "started_utc", stamp(3)),
    ("writer_receipt", "utc", stamp(0)),
    ("writer_process", "finished_utc", stamp(1)),
    ("reader_request", "created_utc", stamp(2)),
    ("reader_receipt", "utc", "2026-01-01T00:00:06"),
    ("reader_receipt", "utc", "2026-01-01T00:00:06+01:00")])
def test_process_timestamp_tampering_is_rejected(name, field, value):
    packet = process_fixture()
    packet.mutate("demo/" + name + ".json", lambda record: record.__setitem__(field, value))
    with pytest.raises(audit.AuditError):
        audit.check_processes(packet, SOURCE, job=JOB)


def test_reader_before_writer_exit_rejects_even_with_consistently_rebound_request_hashes():
    packet = process_fixture()
    changed_hash = packet.mutate("demo/reader_request.json", lambda row: row.__setitem__("created_utc", stamp(2)))
    def bind_process(row):
        row["request_sha256"] = changed_hash
        row["command"][9] = changed_hash
    packet.mutate("demo/reader_process.json", bind_process)
    packet.mutate("demo/reader_receipt.json", lambda row: row.__setitem__("request_sha256", changed_hash))
    with pytest.raises(audit.AuditError, match="FRESH_READER_AFTER_WRITER_EXIT_NOT_PROVEN"):
        audit.check_processes(packet, SOURCE, job=JOB)


@pytest.mark.parametrize("mutation", ["command", "request-checksum", "request-body", "missing-log", "result-checksum"])
def test_process_commands_requests_logs_and_child_result_bindings_reject(mutation):
    packet = process_fixture()
    if mutation == "command":
        packet.mutate("demo/reader_process.json", lambda row: row["command"].__setitem__(3, "untrusted.module"))
    elif mutation == "request-checksum":
        packet.mutate("demo/reader_process.json", lambda row: row.__setitem__("request_sha256", "0" * 64))
    elif mutation == "request-body":
        packet.mutate("demo/reader_request.json", lambda row: row.__setitem__("created_utc", stamp(5)))
    elif mutation == "missing-log":
        del packet.members["demo/reader.stderr.log"]
    else:
        packet.mutate("demo/reader_receipt.json", lambda row: row["receipt_sha256"].__setitem__("candidate_verdict.json", "0" * 64))
    with pytest.raises((audit.AuditError, AssertionError)):
        audit.check_processes(packet, SOURCE, job=JOB)


def test_synthetic_call_component_keeps_package_address_and_first_effect_distinct():
    packet, result, link = call_fixture()
    derived = audit.check_call_identity(packet, result, link)
    assert derived["calls"][0]["functional_address"] == "entry:main/steps/1"
    assert derived["calls"][0]["runtime_address"] == "entry/1"
    assert derived["calls"][0]["call_id"] != derived["calls"][1]["call_id"]
    assert derived["final_effect_id"] == "fixture-first-B"
    assert link["cognitive_address"] not in [row["call_id"] for row in derived["calls"]]


@pytest.mark.parametrize("mutation", ["second-equal-bytes", "same-effect-id", "same-call-id", "wrong-input",
                                    "mixed-run", "wrong-address", "wrong-procedure", "wrong-producer", "missing-call"])
def test_call_ids_dependencies_and_first_return_are_checked_beyond_output_bytes(mutation):
    packet, result, link = call_fixture()
    events = packet.json("native/candidate/composition_events.json")
    first_b, last_b = events[3]["output_reference"], events[5]["output_reference"]
    assert first_b["payload_sha256"] == last_b["payload_sha256"] and first_b["effect_id"] != last_b["effect_id"]
    if mutation == "second-equal-bytes":
        result["final_reference"] = last_b
        events[-1]["reference"] = last_b
        packet.mutate("demo/call_mapping_receipt.json", lambda row: row.__setitem__("final_effect_id", last_b["effect_id"]))
    elif mutation == "same-effect-id":
        last_b["effect_id"] = first_b["effect_id"]
    elif mutation == "same-call-id":
        events[4]["call_id"] = events[2]["call_id"]
        events[5]["call_id"] = events[2]["call_id"]
    elif mutation == "wrong-input":
        events[4]["input_reference"] = first_b
        events[5]["input_reference"] = first_b
    elif mutation == "mixed-run":
        events[5]["run_id"] = "different-run"
    elif mutation == "wrong-address":
        events[5]["address"] = "entry/1/0"
    elif mutation == "wrong-procedure":
        events[4]["procedure"] = "p1"
    elif mutation == "wrong-producer":
        first_b["producer_cjt_id"] = "A"
    else:
        del events[4]
    packet.put("native/candidate/composition_events.json", events)
    with pytest.raises(audit.AuditError):
        audit.check_call_identity(packet, result, link)


@pytest.mark.parametrize("field,value", [("package_address", "wrong-package"), ("return_node", 2),
                                       ("package_address_is_not_call_id", False), ("first_B_identity_returned", False)])
def test_saved_mapping_is_recomputed_from_events(field, value):
    packet, result, link = call_fixture()
    packet.mutate("demo/call_mapping_receipt.json", lambda row: row.__setitem__(field, value))
    with pytest.raises(audit.AuditError, match="SAVED_CALL_MAPPING_DIFFERS_FROM_EVENTS"):
        audit.check_call_identity(packet, result, link)


def test_claimed_native_dependency_rows_are_recomputed():
    packet, result, link = call_fixture()
    packet.mutate("demo/call_mapping_receipt.json", lambda row: row["expected_native_edges"][2].__setitem__("input_node", 1))
    with pytest.raises(audit.AuditError, match="SAVED_CALL_MAPPING_DIFFERS_FROM_EVENTS"):
        audit.check_call_identity(packet, result, link)


def test_no_neural_import_or_full_native_audit_was_used():
    assert not any(name in sys.modules for name in ("torch", "tensorflow", "jax", "casformer"))
    assert not hasattr(SyntheticPacket(), "completed")
