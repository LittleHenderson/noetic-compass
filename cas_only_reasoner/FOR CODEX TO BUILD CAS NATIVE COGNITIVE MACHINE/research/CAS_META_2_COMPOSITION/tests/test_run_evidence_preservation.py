"""RUN_EVIDENCE_PRESERVATION_001: permanent failure-injection tests, packaged path.

Every case below drives the real shared machinery - the contract, the writer, the
stager/uploader (the rendered worker's own transport), the collector, the two
verifiers, the receiver receipt and the cleanup boundary - with the neural workload
and the cloud replaced by fixtures. No AWS, no torch, no model, no reservation.

The key regression is the failure that actually happened: all four checkpoints are
delivered while ``measurements.json`` is omitted. It must reject experimental
completeness, retain the available evidence, deny deletion, and still shut down the
compute.

What these tests do NOT claim: a stubbed storage test does not verify the real cloud
configuration. The archive's retention policy and access separation are proposed for
approval and must be confirmed during the next authorised job's preflight.
"""
import ast
import hashlib
import json
import sys
import textwrap
from pathlib import Path

import pytest

from aws import graph_training_curriculum_launch as curriculum
from aws import run_evidence as re_

JOB = "cas-meta2-graph6read-20260911144249-35a06773"
CONDITIONS = ("cfc_stable_cues", "cfc_neutral_cue")


# --------------------------------------------------------------------------
# a panel, a contract, and a dummy experiment that writes real files
# --------------------------------------------------------------------------

def _panel():
    items = []
    for number in range(192):
        items.append({"item_id": "item-%03d" % number,
                      "layer": ("role_application" if number % 2
                                else "role_recognition"),
                      "face": (number % 6) + 1, "kind": "primary"})
    for number in range(24):
        items.append({"item_id": "diag-%02d" % number, "layer": "targeted_check",
                      "face": (number % 6) + 1, "kind": "renamed"})
    return items


def _contract():
    return re_.contract("cfc_loop_face_cue_pilot",
                        re_.face_condition_requirements(CONDITIONS,
                                                        re_.panel_facts(_panel())),
                        job=JOB)


def _rows(condition, phase):
    rows = []
    for item in _panel():
        rows.append({"item_id": item["item_id"], "layer": item["layer"],
                     "face": item["face"], "phase": phase,
                     "expected_answer": "b", "selected_answer": "b",
                     "is_correct": True, "scores": [0.5, 0.3, 0.2], "loss": 0.4})
    return rows


def dummy_experiment(root, contract, *, omit=(), corrupt=(), drop_face=None,
                     drop_phase=None):
    """A dummy experiment writing exactly the registered evidence directory.

    It replaces the neural workload only. The files, names, rows and phases are the
    real shape, so the collector, the verifiers and the cleanup boundary under test
    are the ones that run in the field.
    """
    root = Path(root)
    evidence = root / "results" / "evidence"
    artifacts = root / "results" / "artifacts"
    evidence.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    def write(relative, raw):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    envelope = {"schema": "cas.cube-face-readout-result/1", "job": JOB,
                "status": "READOUT_COMPLETE", "failure": None,
                "artifacts": [], "reproduction": {"reproduced": True}}
    raw = (json.dumps(envelope, sort_keys=True, indent=2) + "\n").encode("utf-8")
    write("results/result.json", raw)
    write("results/result.json.sha256",
          (hashlib.sha256(raw).hexdigest() + "\n").encode("utf-8"))
    measurements_payload = json.dumps({"schema": "cas.cube-face-readout/0.1",
                                       "job": JOB}).encode()
    readout_payload = json.dumps({"job": JOB}).encode()
    write("results/artifacts/measurements.json", measurements_payload)
    write("results/artifacts/readout.json", readout_payload)
    write("results/evidence/panel.json", json.dumps({"items": len(_panel())}).encode())
    write("results/evidence/frozen_inputs.json", b'{"encoder": "frozen"}')
    write("results/evidence/encoder_identity.json", b'{"encoder": "frozen"}')
    write("results/evidence/containment.json", b'{"contained": true}')
    write("results/evidence/worker.log", b"dummy worker log\n")
    # a declared summary, keyed per condition so it can be compared with the rows
    write("results/evidence/panel_analysis.json", json.dumps(
        {"layers": {"role_application": {"correct": 96, "questions": 96}},
         "by_condition": {condition:
                          {"role_application": {"correct": 96, "questions": 96},
                           "role_recognition": {"correct": 96, "questions": 96}}
                          for condition in CONDITIONS}}).encode())
    write("results/artifacts/checkpoint_initial.pt", b"initial-state")
    for condition in CONDITIONS:
        write("results/artifacts/checkpoint_%s.pt" % condition,
              ("weights:" + condition).encode())
        rows = []
        for phase in ("before", "after"):
            if drop_phase == phase:
                continue
            rows.extend(_rows(condition, phase))
        if drop_face is not None:
            rows = [row for row in rows if int(row["face"]) != int(drop_face)]
        body = b"".join(re_.canonical(row) for row in rows)
        write("results/evidence/rows_%s.jsonl" % condition, body)
        write("results/evidence/updates_%s.jsonl" % condition,
              re_.canonical({"update_index": 0, "batch_index": 0}))
    # last, so it declares every artifact the experiment actually wrote, with
    # digests: this is what lets the collector catch a corrupted download
    declared = []
    for path in sorted(artifacts.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            raw_bytes = path.read_bytes()
            declared.append({"name": path.name, "bytes": len(raw_bytes),
                             "sha256": hashlib.sha256(raw_bytes).hexdigest()})
    write("results/artifacts/manifest.json", json.dumps(
        {"schema": "cas.cube-face-artifact-manifest/1", "job": JOB,
         "artifacts": declared}).encode())
    for relative in omit:
        target = root / relative
        if target.is_file():
            target.unlink()
    for relative in corrupt:
        target = root / relative
        if target.is_file():
            body = bytearray(target.read_bytes())
            body[0] = body[0] ^ 0xFF
            target.write_bytes(bytes(body))
    return root


# --------------------------------------------------------------------------
# the cloud, as a recorder that can also fail
# --------------------------------------------------------------------------

class FakeS3:
    """S3 enough for the collector, and a list of every call it received."""

    def __init__(self, objects=None, *, fail_on=(), corrupt_reads=(),
                 precondition=True):
        self.objects = dict(objects or {})
        self.calls = []
        self.fail_on = set(fail_on)
        self.corrupt_reads = set(corrupt_reads)
        self.precondition = precondition

    def list_objects_v2(self, Bucket=None, Prefix=""):
        self.calls.append(("list_objects_v2", Prefix))
        keys = sorted(key for key in self.objects if key.startswith(Prefix))
        return {"Contents": [{"Key": key, "Size": len(self.objects[key]),
                              "ETag": '"' + hashlib.md5(self.objects[key]).hexdigest() + '"',
                              "VersionId": "v-" + hashlib.sha256(
                                  key.encode()).hexdigest()[:12]}
                             for key in keys]}

    def get_object(self, Bucket=None, Key=None):
        self.calls.append(("get_object", Key))
        if Key not in self.objects:
            raise curriculum._DefaultClientError("NoSuchKey", Key)
        body = self.objects[Key]
        if Key in self.corrupt_reads:
            body = body[:-1] + bytes([body[-1] ^ 0xFF])
        return {"Body": _Body(body),
                "VersionId": "v-" + hashlib.sha256(Key.encode()).hexdigest()[:12]}

    def put_object(self, Bucket=None, Key=None, Body=None, **kwargs):
        self.calls.append(("put_object", Key, kwargs.get("IfNoneMatch")))
        if Key in self.fail_on:
            raise curriculum._DefaultClientError("AccessDenied", Key)
        if Key in self.objects and kwargs.get("IfNoneMatch") == "*" \
                and self.precondition:
            raise curriculum._DefaultClientError("PreconditionFailed", Key)
        self.objects[Key] = Body
        return {}

    def delete_object(self, **kwargs):
        self.calls.append(("delete_object", kwargs.get("Key")))
        raise AssertionError("routine cleanup must never delete evidence")

    def delete_objects(self, **kwargs):
        self.calls.append(("delete_objects", None))
        raise AssertionError("routine cleanup must never delete evidence")

    def delete_bucket(self, **kwargs):
        self.calls.append(("delete_bucket", None))
        raise AssertionError("routine cleanup must never delete evidence")

    def destructive_calls(self):
        return [call for call in self.calls
                if call[0] in ("delete_object", "delete_objects", "delete_bucket",
                               "delete_object_version", "put_bucket_lifecycle")]


class _Body:
    """A streaming body, like the real one: it advances and ends."""

    def __init__(self, raw):
        self._raw = raw
        self._offset = 0

    def read(self, size=None):
        if size is None:
            chunk = self._raw[self._offset:]
            self._offset = len(self._raw)
            return chunk
        chunk = self._raw[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk


class StubClientError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.response = {"Error": {"Code": code, "Message": message}}


class FakeEC2:
    """Compute cleanup, recorded. Termination only; no evidence operations exist."""

    def __init__(self):
        self.calls = []

    def describe_instances(self, InstanceIds=None):
        self.calls.append(("describe_instances", tuple(InstanceIds or ())))
        return {"Reservations": [{"Instances": [
            {"InstanceId": instance_id, "State": {"Name": "terminated"}}
            for instance_id in (InstanceIds or ())]}]}

    def terminate_instances(self, InstanceIds=None):
        self.calls.append(("terminate_instances", tuple(InstanceIds or ())))
        return {}

    def describe_security_groups(self, Filters=None):
        self.calls.append(("describe_security_groups", None))
        return {"SecurityGroups": []}


class FakeIAM:
    def __init__(self):
        self.calls = []

    def _record(self, name):
        self.calls.append(name)

    def remove_role_from_instance_profile(self, **kwargs):
        self._record("remove_role_from_instance_profile")
        raise StubClientError("NoSuchEntity")

    def delete_role_policy(self, **kwargs):
        self._record("delete_role_policy")
        raise StubClientError("NoSuchEntity")

    def get_role(self, **kwargs):
        self._record("get_role")
        raise StubClientError("NoSuchEntity")

    def delete_role(self, **kwargs):
        self._record("delete_role")
        raise StubClientError("NoSuchEntity")

    def get_instance_profile(self, **kwargs):
        self._record("get_instance_profile")
        raise StubClientError("NoSuchEntity")

    def delete_instance_profile(self, **kwargs):
        self._record("delete_instance_profile")
        raise StubClientError("NoSuchEntity")


def _provider(s3, receipt_dir, contract):
    provider = curriculum.CurriculumProvider(
        job=JOB, source_sha="a" * 40, archive_sha256="b" * 64,
        manifest_sha256="c" * 64, ledger_path="ledger.json",
        clients={"s3": s3, "ec2": FakeEC2(), "iam": FakeIAM(), "scheduler": None},
        client_error=StubClientError)
    provider._instance_id = "i-0123456789abcdef0"
    provider._instance_ids = ["i-0123456789abcdef0"]
    provider._resources["bucket"] = "bucket"
    provider._result = {"status": "READOUT_COMPLETE", "artifacts": []}
    provider._result_raw = b'{"status": "READOUT_COMPLETE"}'
    receipt_dir.mkdir(parents=True)
    provider.configure_evidence(receipt_dir, contract)
    return provider


def _uploaded(root):
    """The instance's own results tree, as the objects the worker published."""
    root = Path(root)
    objects = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            objects[path.relative_to(root).as_posix()] = path.read_bytes()
    return objects


def _collect(s3, contract, tmp_path):
    provider = _provider(s3, tmp_path / "receipt", contract)
    # the provider holds the marker bytes it read while waiting, exactly as in a
    # real run; the sidecar check compares against those
    provider._result_raw = s3.objects.get("results/result.json",
                                          b'{"status": "READOUT_COMPLETE"}')
    return provider, provider.collect(JOB)


# --------------------------------------------------------------------------
# THE KEY REGRESSION
# --------------------------------------------------------------------------

def test_four_checkpoints_delivered_and_measurements_omitted_is_rejected(tmp_path):
    """The exact failure: every declared file arrives, the measurement does not.

    Before this directive the collector checked the worker's own list, so this run
    reported a complete delivery, and routine cleanup then deleted the bucket.
    """
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract,
                            omit=("results/artifacts/measurements.json",))
    s3 = FakeS3(_uploaded(root))
    provider, collected = _collect(s3, contract, tmp_path)

    # the checkpoints arrived, byte for byte
    assert collected["byte_integrity"]["state"] == "INCOMPLETE"
    assert not [key for key in collected["byte_integrity"]["missing"]
                if key.endswith(".pt")], "the checkpoints were expected to arrive"
    assert "results/artifacts/measurements.json" in \
        collected["byte_integrity"]["missing"]

    # completeness fails on the missing measurement, not on a count
    assert collected["measurement_completeness"]["state"] == "INCOMPLETE"
    codes = {failure["code"]
             for failure in collected["measurement_completeness"]["failures"]}
    assert codes & {"RECORDS_NOT_COLLECTED", "MEASUREMENT_OBJECT_MISSING"}, codes

    receipt = collected["receiver_receipt"]
    assert receipt["collection"] == "INCOMPLETE"
    assert receipt["issued_by"] == "receiver"

    stages = re_.stage_states(
        execution="FINISHED", byte_verdict=collected["byte_integrity"],
        completeness_verdict=collected["measurement_completeness"],
        compute={"state": "COMPLETE"},
        measurement_keys=("results/artifacts/measurements.json",),
        document=contract)
    assert stages["checkpoint_collection"] == "COMPLETE_VERIFIED"
    assert stages["measurement_collection"] == "INCOMPLETE"
    assert stages["measurement_completeness"] == "INCOMPLETE"
    assert stages["evidence_archive"] in ("RETAINED_PENDING_COLLECTION",
                                          "DELETION_DENIED")
    assert stages["evidence_retention"] == "ACTIVE"
    assert stages["only_surviving_copy"] == "RETAINED"
    assert re_.completed_deliverable(
        execution="FINISHED", byte_verdict=collected["byte_integrity"],
        completeness_verdict=collected["measurement_completeness"], receipt=receipt,
        compute={"state": "COMPLETE"}, document=contract) is False

    # and the compute still shuts down, with no erasure anywhere
    cleanup = provider.cleanup(JOB, collection_verified=False)
    assert cleanup["complete"] is True, cleanup["failures"]
    assert cleanup["evidence_deleted"] is False
    assert cleanup["bucket_deleted"] is False
    assert cleanup["deletion_decision"]["decision"] == re_.DENY
    assert s3.destructive_calls() == []
    assert cleanup["instances"]["i-0123456789abcdef0"] == "CONFIRMED_TERMINATED"

    # the measurement is still preserved on the cloud side for a later recovery
    assert "results/artifacts/measurements.json" not in s3.objects  # omitted by the worker
    assert any(key.endswith(".pt") for key in s3.objects)


def test_a_complete_run_is_a_completed_deliverable_and_still_not_deleted(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    s3 = FakeS3(_uploaded(root))
    provider, collected = _collect(s3, contract, tmp_path)
    assert collected["byte_integrity"]["state"] == "COMPLETE_VERIFIED"
    assert collected["measurement_completeness"]["state"] == "COMPLETE"
    assert collected["receiver_receipt"]["collection"] == "COMPLETE_VERIFIED"
    assert re_.completed_deliverable(
        execution="FINISHED", byte_verdict=collected["byte_integrity"],
        completeness_verdict=collected["measurement_completeness"],
        receipt=collected["receiver_receipt"], compute={"state": "COMPLETE"},
        document=contract) is True
    # a complete collection still does not authorise deletion
    cleanup = provider.cleanup(JOB, collection_verified=True)
    assert cleanup["bucket_deleted"] is False
    assert cleanup["deletion_decision"]["decision"] == re_.DENY
    assert "NO_APPROVED_RETENTION_POLICY" in \
        cleanup["deletion_decision"]["reasons"]
    assert s3.destructive_calls() == []


# --------------------------------------------------------------------------
# content coverage, not counts
# --------------------------------------------------------------------------

def test_one_face_missing_fails_completeness_even_though_every_byte_matched(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract, drop_face=4)
    s3 = FakeS3(_uploaded(root))
    _, collected = _collect(s3, contract, tmp_path)
    # every required file exists and hashed correctly
    assert collected["byte_integrity"]["state"] == "COMPLETE_VERIFIED"
    # and the science is still rejected
    assert collected["measurement_completeness"]["state"] == "INCOMPLETE"
    codes = {failure["code"]
             for failure in collected["measurement_completeness"]["failures"]}
    assert "EXACT_ITEM_IDS_MISSING" in codes
    assert "PER_FACE_ITEM_COUNT" in codes
    failures = collected["measurement_completeness"]["failures"]
    face_failure = [entry for entry in failures if entry["code"] == "PER_FACE_ITEM_COUNT"]
    assert face_failure and face_failure[0]["face"] == "4"
    assert collected["receiver_receipt"]["collection"] == "INCOMPLETE"


def test_a_missing_phase_fails_completeness(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract, drop_phase="before")
    s3 = FakeS3(_uploaded(root))
    _, collected = _collect(s3, contract, tmp_path)
    assert collected["measurement_completeness"]["state"] == "INCOMPLETE"
    codes = {failure["code"]
             for failure in collected["measurement_completeness"]["failures"]}
    assert "PHASE_COVERAGE_MISSING" in codes


def test_duplicate_rows_cannot_substitute_for_missing_questions(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    path = root / ("results/evidence/rows_%s.jsonl" % CONDITIONS[0])
    rows = re_.read_records(path)
    rows[-1] = dict(rows[0])                      # a duplicate standing in for a row
    path.write_bytes(b"".join(re_.canonical(row) for row in rows))
    s3 = FakeS3(_uploaded(root))
    _, collected = _collect(s3, contract, tmp_path)
    codes = {failure["code"]
             for failure in collected["measurement_completeness"]["failures"]}
    assert "DUPLICATE_ROWS_SUBSTITUTING" in codes
    assert "EXACT_ITEM_IDS_MISSING" in codes


def test_a_missing_score_is_refused_rather_than_read_as_zero(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    path = root / ("results/evidence/rows_%s.jsonl" % CONDITIONS[0])
    rows = re_.read_records(path)
    rows[0] = {key: value for key, value in rows[0].items()
               if key not in ("scores", "loss")}
    path.write_bytes(b"".join(re_.canonical(row) for row in rows))
    s3 = FakeS3(_uploaded(root))
    _, collected = _collect(s3, contract, tmp_path)
    failures = collected["measurement_completeness"]["failures"]
    score_failure = [entry for entry in failures
                     if entry["code"] == "SCORE_FIELDS_MISSING"]
    assert score_failure, failures
    assert "never as zero" in score_failure[0]["note"]
    assert collected["measurement_completeness"]["state"] == "INCOMPLETE"

    # and an explicit unavailability with a reason is accepted, not invented
    rows[0]["scores_unavailable"] = {"reason": "SCORES_UNAVAILABLE_ON_INSTANCE"}
    path.write_bytes(b"".join(re_.canonical(row) for row in rows))
    s3 = FakeS3(_uploaded(root))
    _, second = _collect(s3, contract, tmp_path / "again")
    assert not [entry for entry in second["measurement_completeness"]["failures"]
                if entry["code"] == "SCORE_FIELDS_MISSING"]


def test_an_unlisted_safe_output_is_reconciled_and_retained(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    (root / "results/evidence/extra_notes.jsonl").write_bytes(
        re_.canonical({"note": "produced by the worker, never declared"}))
    (root / "results/notes.txt").write_bytes(b"plain text log\n")
    s3 = FakeS3(_uploaded(root))
    _, collected = _collect(s3, contract, tmp_path)
    assert "results/evidence/extra_notes.jsonl" in collected["inventory"]["unlisted"]
    assert "results/notes.txt" in collected["inventory"]["unlisted"]
    assert collected["inventory"]["unlisted_retained"] is True
    assert "results/notes.txt" in collected["inventory"]["unlisted"]
    # retained, not discarded, and not counted as a completeness failure
    assert collected["measurement_completeness"]["state"] == "COMPLETE"


# --------------------------------------------------------------------------
# transport failures
# --------------------------------------------------------------------------

def test_a_corrupt_download_fails_byte_integrity_and_keeps_the_cloud_copy(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    s3 = FakeS3(_uploaded(root),
                corrupt_reads=("results/artifacts/checkpoint_%s.pt" % CONDITIONS[0],))
    provider, collected = _collect(s3, contract, tmp_path)
    assert collected["byte_integrity"]["state"] == "INCOMPLETE"
    mismatched = collected["byte_integrity"]["mismatched"]
    assert [entry for entry in mismatched
            if entry["key"].endswith(CONDITIONS[0] + ".pt")]
    receipt = collected["receiver_receipt"]
    assert receipt["collection"] == "INCOMPLETE"
    cleanup = provider.cleanup(JOB, collection_verified=False)
    assert cleanup["deletion_decision"]["decision"] == re_.DENY
    assert s3.destructive_calls() == []
    assert "results/artifacts/checkpoint_%s.pt" % CONDITIONS[0] in s3.objects


def test_an_unreadable_object_is_named_and_does_not_stop_the_rest(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    objects = _uploaded(root)
    s3 = FakeS3(objects)
    s3.objects.pop("results/evidence/worker.log")
    provider, collected = _collect(s3, contract, tmp_path)
    assert collected["byte_integrity"]["state"] == "INCOMPLETE"
    assert "results/evidence/worker.log" in collected["byte_integrity"]["missing"]
    # everything else still arrived
    assert len(collected["byte_integrity"]["verified"]) >= 10


def test_a_disk_failure_during_collection_leaves_no_success_receipt(tmp_path,
                                                                   monkeypatch):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    s3 = FakeS3(_uploaded(root))
    provider = _provider(s3, tmp_path / "receipt", contract)
    provider._result_raw = s3.objects["results/result.json"]
    calls = {"count": 0}
    original = curriculum.write_evidence

    def failing(path, raw):
        calls["count"] += 1
        if calls["count"] > 3:
            raise OSError(28, "No space left on device")
        return original(path, raw)

    monkeypatch.setattr(curriculum, "write_evidence", failing)
    with pytest.raises(OSError):
        provider.collect(JOB)
    assert not (tmp_path / "receipt" / "receiver_receipt.json").is_file()
    cleanup = provider.cleanup(JOB, collection_verified=False)
    assert cleanup["deletion_decision"]["decision"] == re_.DENY
    assert s3.destructive_calls() == []


def test_stale_or_wrong_job_receipts_never_authorise_deletion(tmp_path):
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    s3 = FakeS3(_uploaded(root))
    _, collected = _collect(s3, contract, tmp_path)
    receipt = collected["receiver_receipt"]
    files = [{"relative_path": key, "bytes": len(body),
              "sha256": re_.digest(body)} for key, body in sorted(s3.objects.items())]

    valid, why = re_.receipt_is_valid_for(receipt, job=JOB, document=contract,
                                          collected_inventory=files)
    assert valid is True, why

    for stale, expected in (
            (dict(receipt, job="cas-meta2-graph6read-other"), "RECEIPT_JOB_MISMATCH"),
            (dict(receipt, contract_sha256="d" * 64), "RECEIPT_CONTRACT_MISMATCH"),
            (dict(receipt, inventory_sha256="e" * 64),
             "RECEIPT_INVENTORY_MISMATCH"),
            (dict(receipt, receipt_sha256="f" * 64), "RECEIPT_DIGEST_MISMATCH"),
            ("forged", "RECEIPT_SCHEMA")):
        ok, reason = re_.receipt_is_valid_for(
            stale, job=JOB, document=contract, collected_inventory=files)
        assert ok is False and reason == expected, (reason, expected)

    decision = re_.deletion_decision(
        receipt=dict(receipt, job="cas-meta2-graph6read-other"),
        contract_document=contract,
        retention={"approved_by_owner": True, "minimum_protection_days": 7,
                   "elapsed_days": 90},
        backup={"state": "VERIFIED"}, policy={"approved_cleanup_policy": True})
    assert decision["decision"] == re_.DENY
    assert any("RECEIPT" in reason for reason in decision["reasons"])


def test_an_old_cleanup_path_that_asks_to_delete_is_denied_by_the_boundary(tmp_path):
    """Even a caller that insists collection was verified cannot erase evidence."""
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    s3 = FakeS3(_uploaded(root))
    provider, _ = _collect(s3, contract, tmp_path)
    first = provider.cleanup(JOB, collection_verified=True)
    assert first["deletion_decision"]["decision"] == re_.DENY
    second = provider.cleanup(JOB, collection_verified=True)
    assert second["deletion_decision"]["decision"] == re_.DENY
    assert "A_PREVIOUS_DENIAL_IS_STICKY" in second["deletion_decision"]["reasons"]
    assert s3.destructive_calls() == []


def test_deletion_is_allowed_only_with_a_policy_an_elapsed_period_and_a_backup():
    contract = _contract()
    files = [{"relative_path": "results/artifacts/manifest.json", "bytes": 3,
              "sha256": re_.digest(b"abc")}]
    byte = {"state": "COMPLETE_VERIFIED", "verified": [], "missing": [],
            "mismatched": [], "unavailable": [], "verified_count": 1,
            "required_count": 1}
    complete = {"state": "COMPLETE", "failures": [], "conditions": ["a"],
                "conditions_omitted": []}
    receipt = re_.collection_receipt(
        job=JOB, profile=contract["profile"], document=contract,
        collected_inventory=files, byte_verdict=byte, completeness_verdict=complete,
        destination="/tmp/receipt")
    assert receipt["collection"] == "COMPLETE_VERIFIED"
    allowed = re_.deletion_decision(
        receipt=receipt, contract_document=contract, inventory_digest_check=True,
        retention={"approved_by_owner": True, "minimum_protection_days": 7,
                   "elapsed_days": 8},
        backup={"state": "VERIFIED"}, policy={"approved_cleanup_policy": True})
    assert allowed["decision"] == re_.ALLOW
    for missing in ("retention", "backup", "policy"):
        arguments = {"receipt": receipt, "contract_document": contract,
                     "inventory_digest_check": True,
                     "retention": {"approved_by_owner": True,
                                   "minimum_protection_days": 7, "elapsed_days": 8},
                     "backup": {"state": "VERIFIED"},
                     "policy": {"approved_cleanup_policy": True}}
        arguments[missing] = None
        assert re_.deletion_decision(**arguments)["decision"] == re_.DENY
    # seven days is a minimum, not a timer: day six is still denied
    early = re_.deletion_decision(
        receipt=receipt, contract_document=contract, inventory_digest_check=True,
        retention={"approved_by_owner": True, "minimum_protection_days": 7,
                   "elapsed_days": 6},
        backup={"state": "VERIFIED"}, policy={"approved_cleanup_policy": True})
    assert early["decision"] == re_.DENY
    assert "RETENTION_PERIOD_NOT_ELAPSED" in early["reasons"]


# --------------------------------------------------------------------------
# the rendered stager and uploader
# --------------------------------------------------------------------------

def _transport(root):
    """The worker's own transport functions, compiled from the rendered source."""
    namespace = {"hashlib": hashlib}
    source = "\n".join(re_.render_transport())
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef):
            exec(textwrap.dedent(ast.get_source_segment(source, node)), namespace)
    return namespace


def test_the_shared_stager_uploads_every_extension_not_only_checkpoints(tmp_path):
    root = tmp_path / "run"
    (root / "results" / "artifacts").mkdir(parents=True)
    (root / "results" / "evidence").mkdir(parents=True)
    (root / "results" / "artifacts" / "checkpoint_a.pt").write_bytes(b"weights")
    (root / "results" / "artifacts" / "measurements.json").write_bytes(b'{"m": 1}')
    (root / "results" / "evidence" / "rows_a.jsonl").write_bytes(b'{"row": 1}\n')
    (root / "results" / "evidence" / "worker.log").write_bytes(b"log line\n")
    (root / "results" / "artifacts" / "manifest.json").write_bytes(b'{"artifacts": []}')
    (root / "results" / "result.json").write_bytes(b'{"status": "DONE"}')
    (root / "results" / "result.json.sha256").write_bytes(b"0" * 64)
    namespace = _transport(root)
    s3 = FakeS3()
    namespace["upload_results"](s3, "bucket", root)
    keys = sorted(key for key in s3.objects)
    assert "results/artifacts/measurements.json" in keys
    assert "results/evidence/rows_a.jsonl" in keys
    assert "results/evidence/worker.log" in keys
    assert "results/artifacts/checkpoint_a.pt" in keys
    # and the transport marker is last among the calls made
    assert s3.calls[-1][1] == "results/result.json"
    assert [call[1] for call in s3.calls][-3:] == [
        "results/artifacts/manifest.json", "results/result.json.sha256",
        "results/result.json"]
    upload = namespace["upload_results"](s3, "bucket", root)
    assert upload["marker"] is True
    assert "neither collection completeness nor evidence deletion" in \
        upload["marker_meaning"]
    assert namespace["publish_once"](s3, "bucket", root, {})["unuploaded_tail"] == []


def test_incremental_publishing_reports_the_unuploaded_tail(tmp_path):
    """What is remotely verified, and what is still only local."""
    root = tmp_path / "run"
    (root / "results" / "evidence").mkdir(parents=True)
    namespace = _transport(root)
    s3 = FakeS3()
    published = {}
    for number in range(3):
        (root / "results" / "evidence" / ("rows_chunk_%02d.jsonl" % number)
         ).write_bytes(re_.canonical({"chunk": number}))
        report = namespace["publish_once"](s3, "bucket", root, published)
        assert len(report["uploaded"]) == 1
    (root / "results" / "evidence" / "rows_chunk_03.jsonl").write_bytes(
        re_.canonical({"chunk": 3}))
    report = namespace["publish_once"](s3, "bucket", root, published)
    assert report["unuploaded_tail"] == []
    assert report["published_sequence"] == 4
    # a chunk that fails to upload stays visible as an unuploaded tail
    (root / "results" / "evidence" / "rows_chunk_04.jsonl").write_bytes(
        re_.canonical({"chunk": 4}))
    s3b = FakeS3(fail_on=("results/evidence/rows_chunk_04.jsonl",))
    with pytest.raises(curriculum._DefaultClientError):
        namespace["publish_once"](s3b, "bucket", root, published)
    assert any("rows_chunk_04" in key for key in
               namespace["publish_once"](s3, "bucket", root,
                                         published)["unuploaded_tail"]) is False


def test_a_conflicting_digest_at_an_existing_key_is_an_integrity_error(tmp_path):
    root = tmp_path / "run"
    (root / "results" / "evidence").mkdir(parents=True)
    path = root / "results" / "evidence" / "rows_a.jsonl"
    path.write_bytes(b"first version\n")
    namespace = _transport(root)
    s3 = FakeS3({"results/evidence/rows_a.jsonl": b"a different version\n"})
    with pytest.raises(SystemExit) as error:
        namespace["publish_once"](s3, "bucket", root, {})
    assert "EVIDENCE_DIGEST_CONFLICT" in str(error.value)
    assert s3.objects["results/evidence/rows_a.jsonl"] == b"a different version\n"


def test_an_identical_existing_key_is_recognised_rather_than_rewritten(tmp_path):
    root = tmp_path / "run"
    (root / "results" / "evidence").mkdir(parents=True)
    body = b"identical bytes\n"
    (root / "results" / "evidence" / "rows_a.jsonl").write_bytes(body)
    namespace = _transport(root)
    s3 = FakeS3({"results/evidence/rows_a.jsonl": body})
    report = namespace["publish_once"](s3, "bucket", root, {})
    assert report["uploaded"] == []
    assert report["published_sequence"] == 1


# --------------------------------------------------------------------------
# the writer itself
# --------------------------------------------------------------------------

def test_the_writer_never_overwrites_and_never_publishes_a_partial_file(tmp_path):
    path = tmp_path / "measurements.json"
    first = re_.write_atomic(path, b"first")
    assert first["sha256"] == re_.digest(b"first")
    with pytest.raises(ValueError) as error:
        re_.write_atomic(path, b"second")
    assert "EVIDENCE_OBJECT_ALREADY_EXISTS" in str(error.value)
    assert path.read_bytes() == b"first"
    unique = re_.write_atomic(path, b"third", unique=True)
    assert Path(unique["path"]).read_bytes() == b"third"
    assert path.read_bytes() == b"first"
    assert not list(tmp_path.glob("*.partial"))


def test_a_failure_record_never_replaces_a_completed_measurement(tmp_path):
    run = tmp_path / "run"
    contract = _contract()
    dummy_experiment(run, contract)
    measurements = run / "results/artifacts/measurements.json"
    before = measurements.read_bytes()
    failure = run / "results/failure.json"
    re_.write_document(failure, {"type": "UploadError", "message": "after evaluation"})
    assert measurements.read_bytes() == before
    assert json.loads(failure.read_bytes())["type"] == "UploadError"
    # a second failure is a new object, not an overwrite
    with pytest.raises(ValueError):
        re_.write_document(failure, {"type": "Second"})
    numbered = run / "results/failures/failure-0001.json"
    re_.write_document(numbered, {"type": "UploadError", "sequence": 1})
    re_.write_document(run / "results/failures/failure-0002.json",
                       {"type": "UploadError", "sequence": 2})
    assert json.loads(numbered.read_bytes())["sequence"] == 1


def test_the_journal_records_a_prediction_before_its_update_and_bounds_the_tail(
        tmp_path):
    journal = re_.Journal(tmp_path / "evidence", prefix="cfc_stable_cues",
                          now=lambda: 1.0)
    journal.record_prediction({"item_id": "item-001", "batch_index": 0,
                               "update_batch_expected": True, "scores": [1, 0, 0]})
    journal.log("condition cfc_stable_cues started")
    assert journal.pending_updates() == ["item-001"]
    journal.record_update({"update_index": 0, "batch_index": 0,
                           "committed_exposure": 8})
    assert journal.pending_updates() == []
    journal.record_prediction({"item_id": "item-002", "batch_index": 1,
                               "update_batch_expected": True, "scores": [0, 1, 0]})
    chunk = journal.close_chunk("condition_complete", condition="cfc_stable_cues",
                                phase="after")
    rows = re_.read_records(chunk["path"])
    assert [row["item_id"] for row in rows] == ["item-001", "item-002"]
    assert rows[1]["update_committed"] is None, \
        "a crash between prediction and update must stay explicitly incomplete"
    assert journal.updates_seen == [{"update_index": 0, "batch_index": 0,
                                     "committed_exposure": 8}]
    assert (tmp_path / "evidence" / "updates_cfc_stable_cues.jsonl").is_file()
    assert (tmp_path / "evidence" / "worker.log").is_file()
    # the chunk is immutable
    with pytest.raises(ValueError):
        re_.write_atomic(Path(chunk["path"]), b"replacement")


def test_the_contract_cannot_be_narrowed_by_the_worker(tmp_path):
    contract = _contract()
    keys = set(re_.contract_keys(contract))
    assert "results/artifacts/measurements.json" in keys
    assert contract["cannot_shrink_after_a_failure"] is True
    assert contract["worker_may_not_amend_required"] is True
    produced = re_.produced_manifest(tmp_path, contract, job=JOB,
                                     errors=["UPLOAD_FAILED:one.pdf"])
    assert set(produced["required_keys_still_required"]) == keys
    assert produced["cannot_shrink_required"] is True
    assert produced["errors"] == ["UPLOAD_FAILED:one.pdf"]
    assert re_.contract_digest(contract) == re_.contract_digest(_contract())


def test_the_wall_clock_ceiling_shuts_down_compute_with_evidence_retained(tmp_path):
    """A hard timeout during collection: GPU stops, durable archive stays."""
    contract = _contract()
    root = dummy_experiment(tmp_path / "run", contract)
    s3 = FakeS3(_uploaded(root))
    provider = _provider(s3, tmp_path / "receipt", contract)
    provider._instance_ids = []
    cleanup = provider.cleanup(JOB, collection_verified=False)
    assert cleanup["complete"] is True
    assert cleanup["evidence_archive"] in ("RETAINED_PENDING_COLLECTION",
                                           "DELETION_DENIED")
    assert cleanup["retained_bucket"] == "bucket"
    assert cleanup["archive_object_prefix"] == "results/"
    assert s3.destructive_calls() == []
    # the cleanup boundary touches no evidence object at all
    assert s3.calls == []


def test_no_lifecycle_or_version_deletion_call_exists_in_the_boundary():
    """The cleanup path has no erasure call to flip on later."""
    source = Path(curriculum.__file__).read_text(encoding="utf-8")
    body = source[source.index("    def cleanup("):]
    body = body[:body.index("\ndef ", body.index("        return status"))]
    for forbidden in ("delete_objects(", "delete_bucket(", "delete_object(",
                      "delete_object_version", "put_bucket_lifecycle",
                      "delete_bucket_lifecycle", "put_object_retention",
                      "put_object_legal_hold"):
        assert forbidden not in body, forbidden
    assert "evidence_deleted" in body and "deletion_decision" in body
