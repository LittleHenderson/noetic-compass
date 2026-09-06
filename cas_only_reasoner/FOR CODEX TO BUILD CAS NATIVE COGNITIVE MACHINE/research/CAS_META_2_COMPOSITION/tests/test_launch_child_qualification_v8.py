"""Pure parent contracts. All provider/ledger/native evidence below is SIMULATED.

The three old fake definitions are byte-pinned and AST-selected. This never
imports an old launcher or invokes an old coordinator, SDK, or native runtime.
"""
import ast
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
from types import SimpleNamespace
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from aws import launch_child_qualification_v8 as p

SIMULATED = "SYNTHETIC_PARENT_CONTRACT_TEST_NOT_NATIVE_EVIDENCE"
CELLS = ("B_C", "B_CR", "R_C", "R_CR")


def request():
    return {"schema": "cas-meta2-child-qualification-launch-request/8", "experiment": p.EXPERIMENT,
        "job": "cas-meta2-20260906000000-deadbeef", "parent_source_sha": "a" * 40,
        "parent_file_sha256": {n: "b" * 64 for n in (*p.PARENT_FILES, *p.FROZEN_PINS)},
        "worker_source_sha": "c" * 40, "source_archive_sha256": "d" * 64,
        "source_manifest_sha256": "e" * 64, "source_archive": "synthetic-source.zip",
        "source_archive_bytes": 17, "resource_plan": p.resource_plan(),
        "qualification_scope": p.qualification_scope(), "subnet_id": "subnet-12345678",
        "standing_authority_registration_required": True, "launch_authorized": False}


def fake_definitions():
    path = Path(__file__).with_name("test_launch_br_construction_v8.py")
    raw = path.read_bytes()
    assert p.digest(raw) == "b26f5a4b94bf2e03f430f6a263fa627ddea06c24a4c455cb50596f25db6ebfcd"
    wanted = {"MissingObject", "FakeS3", "fake_run"}
    nodes = [n for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in wanted]
    assert {n.name for n in nodes} == wanted
    namespace = {"p": p, "request": request, "pytest": pytest, "SimpleNamespace": SimpleNamespace,
                 "datetime": datetime, "timezone": timezone, "io": io}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def test_default_is_pure_unpaid_and_is_not_a_prior_job(capsys, monkeypatch):
    monkeypatch.setattr(p, "helpers", lambda *a: pytest.fail("default imported launch helper"))
    assert p.main([]) == 0
    report = p.decoded(capsys.readouterr().out)
    assert report["provider_calls"] is report["new_reservation"] is False
    assert report["resource_plan"]["worker_seconds_max"] == 1800
    assert report["resource_plan"]["runtime_seconds_max"] == 3600
    assert report["qualification_scope"]["planned_complete_executions"] == 20
    assert report["qualification_scope"]["planned_native_ticks"] == 110
    assert report["experiment"] == {"profile": "one_child_full_task_qualification_v8",
                                    "entrypoint": "cas_meta2.child_qualification_gpu_v8"}
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(sys.modules)


@pytest.mark.parametrize("field,value", [("worker_seconds_max", 1801), ("worker_seconds_max", 600),
    ("runtime_seconds_max", 3601), ("per_launch_reserved_cap_usd", "5.00"), ("instance_count", True),
    ("automatic_retries", 1), ("training", True), ("instance_type", "g4dn.xlarge"), ("ebs_iops", 9000)])
def test_resource_plan_changes_are_refused(field, value):
    current = request()
    current["resource_plan"][field] = value
    with pytest.raises(p.LaunchRefused, match="CHQ_EXACT_SCOPE"):
        p.validate_request(current)


@pytest.mark.parametrize("field,value", [("max_seconds", 600), ("max_cost_usd", "8.00"),
    ("task_count", 3), ("candidates_per_task", 3), ("planned_complete_executions", 19),
    ("planned_native_ticks", 100), ("binding", False), ("binding", 1), ("seed", 8),
    ("training", True), ("return_child_result", False)])
def test_qualification_plan_cannot_silently_change(field, value):
    current = request()
    current["qualification_scope"][field] = value
    with pytest.raises(p.LaunchRefused, match="CHQ_EXACT_SCOPE"):
        p.validate_request(current)


@pytest.mark.parametrize("schema", ["cas-meta2-br-launch-request/8", "cas-meta2-prefix-launch-request/8"])
def test_old_request_schemas_are_not_qualification(schema):
    current = request()
    current["schema"] = schema
    with pytest.raises(p.LaunchRefused, match="CHQ_DEDICATED_REQUEST"):
        p.validate_request(current)


def authority_fixture(tmp_path, monkeypatch):
    current = request()
    campaign, message = tmp_path / "SIMULATED-campaign.txt", tmp_path / "SIMULATED-message.txt"
    campaign.write_bytes(SIMULATED.encode())
    message.write_bytes((SIMULATED + " standing message").encode())
    monkeypatch.setattr(p, "STANDING_MESSAGE_SHA256", p.digest(message.read_bytes()))
    ledger = {"approval": {"path": str(campaign), "sha256": p.digest(campaign.read_bytes())},
              "owner_task_cap_usd": "400.00", "no_automatic_refund": True}
    request_hash = p.digest(p.encoded(current))
    authority = {"schema": "cas-meta2-child-qualification-standing-authority/8", "standing_campaign_authorization": True,
        "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00", "experiment": p.EXPERIMENT,
        "training": False, "native_execution": True, "launch_request_sha256": request_hash,
        **{k: current[k] for k in ("job", "parent_source_sha", "worker_source_sha", "source_archive_sha256", "source_manifest_sha256")},
        "campaign_approval": ledger["approval"], "standing_user_message": {"path": str(message), "sha256": p.STANDING_MESSAGE_SHA256}}
    path = tmp_path / "SIMULATED-authority.json"
    path.write_bytes(p.encoded(authority))
    return current, request_hash, authority, path, ledger


def test_authority_binds_full_current_message_campaign_and_distinct_sources(tmp_path, monkeypatch):
    assert p.STANDING_MESSAGE_SHA256 == "d0b640ec3059ea73d677b632a4bc2f3188bbcd87b231e4362914e219459fc5bb"
    current, request_hash, _, path, ledger = authority_fixture(tmp_path, monkeypatch)
    actual = p.validate_authority(path, p.digest(path.read_bytes()), current, request_hash, ledger)
    assert actual["max_job_cost_usd"] == "4.00" and actual["campaign_cap_usd"] == "400.00"
    assert actual["worker_source_sha"] != actual["parent_source_sha"]


@pytest.mark.parametrize("field,value", [("job", "other"), ("worker_source_sha", "f" * 40),
    ("launch_request_sha256", "f" * 64), ("training", True), ("max_job_cost_usd", "5.00"),
    ("standing_campaign_authorization", 1), ("schema", "cas-meta2-br-standing-authority/8")])
def test_authority_cannot_be_reused_or_expanded(tmp_path, monkeypatch, field, value):
    current, request_hash, authority, path, ledger = authority_fixture(tmp_path, monkeypatch)
    authority[field] = value
    path.write_bytes(p.encoded(authority))
    with pytest.raises(p.LaunchRefused, match="CHQ_STANDING_AUTHORITY_SCOPE"):
        p.validate_authority(path, p.digest(path.read_bytes()), current, request_hash, ledger)


@pytest.mark.parametrize("kind", ["message", "campaign", "wrong_campaign", "refund", "cap"])
def test_authority_actual_bytes_and_canonical_campaign_cannot_change(tmp_path, monkeypatch, kind):
    current, request_hash, authority, path, ledger = authority_fixture(tmp_path, monkeypatch)
    if kind in ("message", "campaign"):
        key = "standing_user_message" if kind == "message" else "campaign_approval"
        Path(authority[key]["path"]).write_bytes(b"changed")
    elif kind == "wrong_campaign":
        ledger["approval"] = {**ledger["approval"], "sha256": "0" * 64}
    elif kind == "refund":
        ledger["no_automatic_refund"] = False
    else:
        ledger["owner_task_cap_usd"] = "500.00"
    with pytest.raises(p.LaunchRefused):
        p.validate_authority(path, p.digest(path.read_bytes()), current, request_hash, ledger)


def test_permit_binds_1800_second_qualification_and_new_linux_paths():
    current, reservation, ledger = request(), {"SIMULATED": "reservation"}, {"SIMULATED": "ledger"}
    permit = p.worker_permit(current, {}, reservation, ledger, "i-1234567890abcdef0", datetime.now(timezone.utc))
    plan = permit["worker_plan"]
    assert plan["schema"] == "cas-meta2-child-qualification-plan/8"
    assert plan["max_seconds"] == 1800 and plan["max_cost_usd"] == "4.00"
    assert plan["source_sha"] == current["worker_source_sha"]
    assert plan["source_manifest"]["path"] == "/opt/cas-meta2-child-qualification/package/child_qualification_source_manifest.json"
    assert plan["source_archive"]["path"] == "/opt/cas-meta2-child-qualification/source.zip"
    assert plan["reservation_receipt"]["sha256"] == p.digest(p.encoded(reservation))
    assert plan["ledger_snapshot"]["sha256"] == p.digest(p.encoded(ledger))
    assert permit["worker_plan_sha256"] == p.digest(p.encoded(plan))
    assert plan["training"] is False and plan["native_execution"] is True


def test_fake_lifecycle_reserves_once_then_schedules_permits_collects_and_cleans(tmp_path, monkeypatch):
    result, events, ec2, s3 = fake_definitions()["fake_run"](tmp_path, monkeypatch)
    assert result["status"] == "AWS_CHILD_QUALIFICATION_FINISHED"
    assert events.count("reserve") == events.count("run_instances") == 1
    assert events.index("reserve") < events.index("run_instances") < events.index("verify_schedule") < events.index("put:input/permit.json")
    assert events.index("verify_packet") < events.index("terminate:True") < events.index("cleanup")
    assert result["termination_confirmed"] and result["artifact_verified"]
    assert ec2.run["BlockDeviceMappings"][0]["Ebs"] == {"VolumeSize": 75, "VolumeType": "gp3", "Iops": 3000,
                                                        "Throughput": 125, "Encrypted": True, "DeleteOnTermination": True}
    assert p.decoded(s3.objects["input/permit.json"])["worker_plan"]["max_seconds"] == 1800
    assert set(s3.objects).isdisjoint({"input/development.zip", "input/checkpoint.pt"})


@pytest.mark.parametrize("flag", ["schedule_bad", "uncertain", "ledger_bad", "failed"])
def test_fake_failures_preserve_receipts_and_never_retry(tmp_path, monkeypatch, flag):
    result, events, _, _ = fake_definitions()["fake_run"](tmp_path, monkeypatch, **{flag: True})
    assert events.count("reserve") == 1 and events.count("run_instances") <= 1
    assert result["status"] != "AWS_CHILD_QUALIFICATION_FINISHED"
    if flag == "ledger_bad":
        assert events == ["reserve"]
        assert result["budget_reservation_state"] == "RESERVED_NO_AUTOMATIC_REFUND"
        saved = p.decoded((tmp_path / "fake_run/launch_receipt.json").read_bytes())
        assert saved["task_budget_reservation"] == result["task_budget_reservation"]
    elif flag == "failed":
        assert result["artifact_verified"] and "terminate:True" in events
    else:
        assert "put:input/permit.json" not in events and "terminate:False" in events


def test_remaining_time_gate_is_1800_plus_240_and_refuses_before_permit(tmp_path, monkeypatch):
    seen = []
    def changed_delta(*args, **kwargs):
        if kwargs.get("seconds") == 2040:
            seen.append(2040)
            return timedelta(seconds=4000)  # Force late setup in this simulated clock gate.
        return timedelta(*args, **kwargs)
    monkeypatch.setattr(p, "timedelta", changed_delta)
    result, events, _, _ = fake_definitions()["fake_run"](tmp_path, monkeypatch)
    assert seen == [2040]
    assert "put:input/permit.json" not in events and "terminate:False" in events
    assert any("INSUFFICIENT_INSTANCE_TIME" in row.get("message", "") for row in result["events"])


@pytest.mark.parametrize("response", [{"Errors": [{"Key": "input/source.zip", "Code": "AccessDenied"}]},
                                     {"Deleted": [{"Key": "input/source.zip"}]}])
def test_s3_delete_errors_never_become_claimed_cleanup(tmp_path, monkeypatch, response):
    fake = fake_definitions()
    monkeypatch.setattr(fake["FakeS3"], "delete_objects", lambda self, **kwargs: response)
    result, _, _, _ = fake["fake_run"](tmp_path, monkeypatch)
    assert result["status"] == "CLEANUP_REQUIRES_ATTENTION"
    assert result["input_delete_response"] == response
    assert not any(row["event"] == "OWNED_INPUTS_REMOVED_AFTER_VERIFIED_DOWNLOAD" for row in result["events"])


@pytest.mark.parametrize("reason", ["authority", "preflight", "lock"])
def test_refused_preflight_has_receipt_and_never_reserves(tmp_path, monkeypatch, reason):
    current, path = request(), tmp_path / "SIMULATED-request.json"
    path.write_bytes(p.encoded(current))
    calls = []
    def fail(label):
        calls.append(label)
        raise ValueError("SIMULATED " + label)
    old = SimpleNamespace(campaign_execution_lock=lambda: fail("lock") if reason == "lock" else nullcontext(),
        budget=SimpleNamespace(read_ledger=lambda: {"remaining_unreserved_usd": "314.00"},
                               reserve_budget=lambda *a: pytest.fail("reserved during refused preflight")))
    plumbing = SimpleNamespace(client_factory=lambda *a: calls.append("clients") or {},
        provider_preflight=lambda *a: fail("preflight"))
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setattr(p, "helpers", lambda *a: {"old": old, "plumbing": plumbing, "package": None,
        "identity": current["parent_file_sha256"]})
    monkeypatch.setattr(p, "source_for", lambda *a: {})
    monkeypatch.setattr(p, "validate_authority", lambda *a: fail("authority") if reason == "authority" else {"SIMULATED": True})
    output = tmp_path / "records/refused"
    result = p.execute(path, p.digest(path.read_bytes()), "SIMULATED", "f" * 64, output)
    assert result["status"] == "CHQ_LAUNCH_PREFLIGHT_REFUSED"
    assert not result["new_reservation"] and not result["provider_resources_created"]
    assert p.decoded((output / "launch_receipt.json").read_bytes()) == result
    if reason != "preflight":
        assert "clients" not in calls


def test_execute_cli_returns_zero_only_for_new_success_status(capsys, monkeypatch):
    monkeypatch.setattr(p, "execute", lambda *a: {"status": "AWS_CHILD_QUALIFICATION_FINISHED", "evidence_kind": SIMULATED})
    argv = ["--execute", "--request", "SIMULATED", "--request-sha256", "a" * 64,
            "--authority", "SIMULATED", "--authority-sha256", "b" * 64, "--receipt-dir", "SIMULATED"]
    assert p.main(argv) == 0
    assert p.decoded(capsys.readouterr().out)["evidence_kind"] == SIMULATED
    monkeypatch.setattr(p, "execute", lambda *a: {"status": "AWS_CHQ_CONSTRUCTION_FINISHED"})
    assert p.main(argv) == 1


def packet(tmp_path, *, failure=False, mutate=None, corrupt_member=None, emergency=False):
    current, plan_hash, files = request(), "f" * 64, {}
    qualified = {"schema": "cas-meta2-one-child-qualification/8", "status": "QUALIFIED", "qualified": True,
        "training": False, "evidence_kind": SIMULATED, "attempted_execution_count": 20,
        "reported_executed_count": 20, "completed_execution_count": 20, "audited_native_ticks": 110,
        "completed_native_ticks": 110, "all_scheduled_executions_completed": True,
        "unattempted_execution_count": 0, "failed_or_unaudited_attempts": 0, "cases": []}
    for index, target_cell in enumerate(CELLS):
        case = {"index": index, "target_combination": target_cell, "status": "QUALIFIED", "comparisons": [], "executions": []}
        reference_hash = p.digest((SIMULATED + target_cell).encode())
        folder = "qualification/cases/case_%02d/" % index
        for number, cell in enumerate((target_cell, *CELLS)):
            slot, is_reference = ("reference" if number == 0 else "candidate_%02d" % (number - 1)), number == 0
            is_target, ticks = cell == target_cell, 6 if cell.endswith("CR") else 5
            output_hash = p.digest((SIMULATED + cell).encode())
            actual = {"status": "EXECUTED", "reference": is_reference, "fixed_weights": True,
                "integrity": True, "native_trace_count": ticks, "reserved_policy_units": ticks * 72, "evidence_kind": SIMULATED}
            audit = {"audit_method": "read-only-sqlite-source-replay/0.1", "stored_call_tree_verified": not is_reference,
                "expected_action_checked": True,
                "trace_count": ticks, "reserved_policy_units": ticks * 72, "final_output_sha256": output_hash}
            verdict = {k: is_target for k in ("task_correct", "procedure_correct", "dependency_correct", "actual_output_correct")}
            verdict.update(binding_correct=True, trace_valid=True, stored_call_tree_verified=not is_reference,
                           native_runs=ticks, reserved_policy_units=ticks * 72)
            if is_reference:
                verdict.update(candidate_task_evaluation=False, verdict_kind="PRIVATE_NATIVE_REFERENCE_CHECK")
            execution = {"slot": slot, "status": "EXECUTED_AND_STORED_AUDITED", "execution_result": actual,
                         "stored_audit": audit, "verification": verdict}
            case["executions"].append(execution)
            files[folder + slot + "_qualification.json"] = p.encoded(execution)
            for name in ("native.db", "native_traces.json", "composition_events.json", "native_kernel_events.json"):
                files[folder + slot + "/" + name] = p.encoded({"evidence_kind": SIMULATED})
            files[folder + slot + "/result.json"] = p.encoded(actual)
            if not is_reference:
                case["comparisons"].append({"combination": cell, "correct_target": is_target, "task_correct": is_target,
                    "final_output_differs_from_reference": not is_target, "final_output_sha256": output_hash,
                    "reference_final_output_sha256": reference_hash})
        qualified["cases"].append(case)
        files[folder + "panel_qualification.json"] = p.encoded(case)
    files["qualification/cases/qualification_receipt.json"] = p.encoded(qualified)
    files["qualification/cases/candidates_sealed.json"] = p.encoded({"evidence_kind": SIMULATED})
    files["qualification/admission.json"] = p.encoded({"evidence_kind": SIMULATED})
    files["lifecycle/worker/stdout.txt"] = SIMULATED.encode()
    files["lifecycle/worker/stderr.txt"] = b""
    files["lifecycle/worker/receipt.json"] = p.encoded({"exit_code": 0, "failure": None, "maximum_seconds": 1800,
        "outputs": {n: {"sha256": p.digest(files["lifecycle/worker/" + n]), "bytes": len(files["lifecycle/worker/" + n])}
                    for n in ("stdout.txt", "stderr.txt")}})
    files["lifecycle/remote_receipt.json"] = p.encoded({"returncode": 0, "worker_process_started": True,
        "worker_qualification_completed": True, "neural_training": False,
        "source_sha": current["worker_source_sha"], "parent_source_sha": current["parent_source_sha"],
        "archive_sha256": current["source_archive_sha256"], "source_manifest_sha256": current["source_manifest_sha256"]})
    worker = {"schema": "cas-meta2-child-qualification-gpu/8", "job": current["job"],
        "status": "CHILD_CURRICULUM_NATIVE_QUALIFIED", "experiment": p.EXPERIMENT,
        "source_sha": current["worker_source_sha"], "source_archive_sha256": current["source_archive_sha256"],
        "source_manifest_sha256": current["source_manifest_sha256"], "plan_sha256": plan_hash,
        "training": False, "native_execution": True, "cleanup_errors": [], "qualification": qualified,
        "postchecks": {"source": {"ok": True}, "reservation": {"ok": True}}, "evidence_kind": SIMULATED}
    if failure:
        worker.update(status="CHILD_QUALIFICATION_REFUSED", failure={"type": "SIMULATED_FAILURE"})
        files = {"qualification/progress.json": p.encoded({"evidence_kind": SIMULATED})}
    if mutate:
        mutate(worker, files)
    worker["files_sha256"] = {n.removeprefix("qualification/"): p.digest(raw) for n, raw in files.items() if n.startswith("qualification/")}
    files["qualification/worker_receipt.json"] = p.encoded(worker)
    collection = {"job": current["job"], "source_sha": current["worker_source_sha"], "parent_source_sha": current["parent_source_sha"],
        "experiment": p.EXPERIMENT, "returncode": 1 if failure else 0, "partial_evidence": False,
        "original_file_count": len(files), "included_full_file_count": len(files), "omitted_full_file_count": 0,
        "files": {n: {"sha256": p.digest(raw), "bytes": len(raw)} for n, raw in files.items()}}
    if emergency:
        files = {}
        collection.update(returncode=1, partial_evidence=True, original_file_count=None, included_full_file_count=0,
            omitted_full_file_count=None, full_file_counts_known=False, collection_failure={"evidence_kind": SIMULATED})
        collection.pop("files")
    if corrupt_member:
        files[corrupt_member] += b"changed after index"
    path = tmp_path / "SIMULATED-packet.zip"
    with ZipFile(path, "x", ZIP_DEFLATED) as zipped:
        for name, raw in files.items():
            zipped.writestr(name, raw)
        zipped.writestr("artifact_collection_receipt.json", p.encoded(collection))
    result = {k: collection[k] for k in ("job", "source_sha", "parent_source_sha", "experiment", "returncode", "partial_evidence", "omitted_full_file_count")}
    result.update(sha256=p.digest(path.read_bytes()), bytes=path.stat().st_size)
    return path, result, current, plan_hash


def reseal_core(worker, files):
    qualified = worker["qualification"]
    files["qualification/cases/qualification_receipt.json"] = p.encoded(qualified)
    for case in qualified["cases"]:
        folder = "qualification/cases/case_%02d/" % case["index"]
        files[folder + "panel_qualification.json"] = p.encoded(case)
        for execution in case["executions"]:
            files[folder + execution["slot"] + "_qualification.json"] = p.encoded(execution)
            files[folder + execution["slot"] + "/result.json"] = p.encoded(execution["execution_result"])


def test_full_simulated_packet_checks_all_metadata_and_hashes_not_actual_native_execution(tmp_path):
    result = p.verify_packet(*packet(tmp_path))
    assert result["qualification_status"] == "CHILD_CURRICULUM_NATIVE_QUALIFIED"
    assert result["parent_member_hashes_verified"] == result["original_file_count"]
    assert result["not_learning_or_generalization"]


@pytest.mark.parametrize("emergency", [False, True])
def test_failure_packets_are_retained_without_requiring_absent_native_outputs(tmp_path, emergency):
    result = p.verify_packet(*packet(tmp_path, failure=True, emergency=emergency))
    assert not result["native_component_success"]
    assert result["original_member_coverage_verified"] is (not emergency)


@pytest.mark.parametrize("member", ["qualification/cases/case_00/reference/native.db",
    "qualification/cases/case_03/candidate_03/result.json", "lifecycle/worker/stdout.txt"])
def test_archive_reseal_does_not_hide_member_byte_change(tmp_path, member):
    with pytest.raises(p.LaunchRefused, match="CHQ_COLLECTED_MEMBER_HASH"):
        p.verify_packet(*packet(tmp_path, corrupt_member=member))


@pytest.mark.parametrize("key,value", [("source_sha", "0" * 40), ("plan_sha256", "0" * 64),
    ("training", True), ("native_execution", False), ("cleanup_errors", ["unclosed"]), ("postchecks", {})])
def test_resealed_worker_identity_or_success_contradictions_refused(tmp_path, key, value):
    with pytest.raises(p.LaunchRefused):
        p.verify_packet(*packet(tmp_path, mutate=lambda worker, files: worker.update({key: value})))


@pytest.mark.parametrize("fault", ["top_count", "case_copy", "missing_file", "nested_ticks", "verdict", "output_link", "raw_log", "old_remote_key", "sealed_action_audit"])
def test_resealed_packet_cannot_hide_metadata_contradictions(tmp_path, fault):
    def change(worker, files):
        if fault == "top_count":
            worker["qualification"]["audited_native_ticks"] = 109
            reseal_core(worker, files)
        elif fault == "case_copy":
            files["qualification/cases/case_00/panel_qualification.json"] = b"{}"
        elif fault == "missing_file":
            files.pop("qualification/cases/case_00/candidate_00/native.db")
        elif fault in ("nested_ticks", "verdict", "output_link", "sealed_action_audit"):
            execution = worker["qualification"]["cases"][0]["executions"][1]
            if fault == "nested_ticks":
                execution["stored_audit"]["trace_count"] = 1
            elif fault == "verdict":
                execution["verification"]["task_correct"] = False
            elif fault == "sealed_action_audit":
                execution["stored_audit"]["expected_action_checked"] = False
            else:
                execution["stored_audit"]["final_output_sha256"] = "0" * 64
            reseal_core(worker, files)
        elif fault == "raw_log":
            process = p.decoded(files["lifecycle/worker/receipt.json"])
            process["outputs"]["stdout.txt"]["sha256"] = "0" * 64
            files["lifecycle/worker/receipt.json"] = p.encoded(process)
        else:
            remote = p.decoded(files["lifecycle/remote_receipt.json"])
            remote["worker_component_completed"] = remote.pop("worker_qualification_completed")
            files["lifecycle/remote_receipt.json"] = p.encoded(remote)
    with pytest.raises(p.LaunchRefused):
        p.verify_packet(*packet(tmp_path, mutate=change))
