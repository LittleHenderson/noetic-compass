"""Offline preparation tests; real frozen artifacts and canonical budget required.

Use --basetemp under this package's records directory. The source ZIP alone
does not supply the external development bundle or canonical budget evidence.
No provider, reservation, checkpoint loading or worker execution is permitted.
"""
from copy import deepcopy
import io
from pathlib import Path
import stat
import sys
from zipfile import ZipFile, ZipInfo

import pytest

from aws import prefix_diagnostic_launch_v8 as p

ARTIFACTS = p.ROOT / "records/child_call_v8_diagnostic_001"
SOURCE = ARTIFACTS / "source_001/source.zip"
DEVELOPMENT = ARTIFACTS / "bundle_001"
DEVELOPMENT_ZIP = ARTIFACTS / "development_bundle.zip"


@pytest.fixture(scope="module")
def source():
    return p.inspect_source_archive(SOURCE)


@pytest.fixture(scope="module")
def development(source):
    return p.inspect_development(DEVELOPMENT, DEVELOPMENT_ZIP, source)


def test_real_frozen_source_has_complete_identity(source):
    assert source["source_sha"] == "13f424981d7434b1a92815d1ad5759d543bbd3be"
    assert source["sha256"] == p.SOURCE_ARCHIVE_SHA
    assert source["bytes"] == 7952045
    assert source["member_count"] == 616
    assert len(source["files_sha256"]) == 615
    assert source["files_sha256"][p.PILOT + "aws/budget.py"] == p.BUDGET_SOURCE_SHA
    assert len(source["package_layout"]["wheel_paths"]) == 2
    assert source["prefix_manifest_member"] == "prefix_source_manifest.json"


def test_development_archive_matches_directory_without_model_load(development):
    assert development["archive_bytes"] == 6570836
    assert development["archive_member_count"] == 16
    assert development["archive_root_prefix"] == "bundle_001/"
    assert len(development["file_identities"]) == 16
    assert development["cohort_counts"] == {"train_probe": 24, "validation": 96}
    assert development["limits"]["selected_role_opportunities_per_checkpoint"] == 2272
    assert development["checkpoints_deserialized"] is False
    assert development["final_task_files_included"] is False


def test_canonical_budget_observation_changes_no_file_or_reservation():
    module = p._budget_module()
    before = p._budget_files(module)
    result = p.observe_budget()
    assert result["checked_file_sha256"] == before == p._budget_files(module)
    assert result["history_chain_validated"] is True
    assert result["contents_unchanged"] is True
    assert result["new_reservation"] is False
    assert result["campaign_cap_usd"] == "400.00"
    assert not module.paths(module.CANONICAL_LEDGER)[1].exists()


def test_cost_is_only_a_bounded_proposal_not_a_quote():
    proposal = p.resource_proposal()
    assert proposal["resource_plan"] == {
        "instance_count": 1, "instance_type": "g7.2xlarge", "account_id": "807562639912",
        "region": "us-west-2", "runtime_seconds_max": 3600, "automatic_retries": 0,
        "on_demand_hourly_usd_max": "2.52", "ancillary_reserved_usd": "1.00"}
    assert proposal["worker_seconds_max"] == 1800
    assert proposal["arithmetic_cost_bound_usd"] == "3.52"
    assert proposal["proposed_reservation_usd"] == "4.00"
    assert proposal["price_checked"] is False
    assert proposal["ancillary_allowance_completeness_verified"] is False
    assert proposal["full_provisioning_plan_completed"] is False
    assert proposal["provider_cap_enforced"] is False


def test_draft_cannot_be_passed_as_an_enabled_worker_plan(source, development):
    from cas_meta2.diagnostic_v8 import gpu
    draft = p.worker_plan_draft(source, development, p.resource_proposal())
    assert draft["launch_enabled"] is False
    assert draft["source_sha"] == p.WORKER_SOURCE_SHA
    assert draft["job"] is None and draft["instance_id"] is None
    assert draft["reservation_receipt"] is None and draft["ledger_snapshot"] is None
    assert draft["source_manifest"]["path"] is None
    assert draft["source_archive"]["path"] is None
    with pytest.raises(ValueError):
        gpu.plan_bounds(draft, "cas-meta2-20260906000000-deadbeef", p.BUNDLE_MANIFEST_SHA)


def test_command_is_a_non_executable_template_with_required_worker_layout(source, development):
    result = p.command_template(source, development)
    assert result["kind"] == "NON_EXECUTABLE_TYPED_ARGUMENT_TEMPLATE"
    assert result["argv"][:4] == ["python", "-B", "-m", "cas_meta2.diagnostic_v8.gpu"]
    assert sum(type(arg) is dict for arg in result["argv"]) == 5
    assert result["shell_command_generated"] is False
    assert result["local_execution_permitted"] is False
    assert "Nonexistent child" in result["path_constraints"]["new_worker_output_directory"]
    assert "not the ZIP" in result["path_constraints"]["remote_bundle_directory"]
    assert "extracted package root" in result["path_constraints"]["source_manifest"]
    assert "final source_closure" in result["path_constraints"]["source_archive"]
    assert len(result["path_constraints"]["python_package_roots"]) == 3
    for name in ("source_manifest", "source_archive", "reservation_receipt", "ledger_snapshot"):
        assert "Linux absolute path" in result["path_constraints"][name]
    assert result["installs_required_later"]["python_allowed_versions"] == ["3.11", "3.12"]


def test_prepare_is_pure_disabled_and_preserves_all_inputs(tmp_path, monkeypatch):
    module = p._budget_module()
    before = p._budget_files(module)
    original_loader = p._budget_module
    calls = []
    def checked_loader():
        checked = original_loader()
        def forbidden(*args, **kwargs):
            raise AssertionError("Budget reservation is forbidden in preparation")
        checked.reserve_budget = forbidden
        original_reader = checked.read_ledger
        def reader(*args, **kwargs):
            calls.append("read_ledger")
            return original_reader(*args, **kwargs)
        checked.read_ledger = reader
        return checked
    class ImportGuard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"torch", "numpy", "casformer", "cas_cjt",
                                         "tensorflow", "jax", "boto3", "botocore"}:
                raise AssertionError("Unexpected non-pure import: " + fullname)
    monkeypatch.setattr(p, "_budget_module", checked_loader)
    monkeypatch.setattr(sys, "meta_path", [ImportGuard(), *sys.meta_path])
    original = {str(path): p.digest(p.read(path)) for path in
                [SOURCE, DEVELOPMENT_ZIP, DEVELOPMENT / "manifest.json"]}
    output = tmp_path / "preparation"
    result = p.prepare(SOURCE, DEVELOPMENT, DEVELOPMENT_ZIP, output)
    report = p.decode((output / "preparation.json").read_bytes())
    assert calls == ["read_ledger"]
    assert set(path.name for path in output.iterdir()) == {
        "preparation.json", "worker_plan_draft.json", "command_template.json"}
    assert result["status"] == report["status"] == "PREPARATION_ONLY_NO_PAID_LAUNCH"
    assert result["launch_enabled"] is False and result["new_reservation"] is False
    assert report["execution_ready"] is False
    assert report["boundary"]["paid_parent_orchestration_implemented"] is False
    assert report["boundary"]["provider_calls"] is False
    assert report["boundary"]["neural_imports_or_execution"] is False
    assert report["boundary"]["native_execution"] is False
    assert report["boundary"]["job_created"] is False
    assert report["boundary"]["budget_observation_not_launch_authority"] is True
    assert set(report["missing_gates"]) == set(p.MISSING_GATES)
    assert "REAL_UNIQUE_JOB_AND_CANONICAL_BUDGET_RESERVATION" in report["missing_gates"]
    assert report["worker_source_sha"] == p.WORKER_SOURCE_SHA
    assert before == p._budget_files(module)
    assert original == {path: p.digest(p.read(path)) for path in original}
    for name, record in result["files"].items():
        raw = (output / name).read_bytes()
        assert record == {"bytes": len(raw), "sha256": p.digest(raw)}
    assert p.decode((output / "worker_plan_draft.json").read_bytes()) == report["worker_plan_draft"]
    assert p.decode((output / "command_template.json").read_bytes()) == report["command_template"]


@pytest.mark.parametrize("field,value", [("expected_sha256", "0" * 64),
                                         ("expected_source_sha", "a1abe578" + "0" * 32)])
def test_new_parent_commit_or_substitute_source_is_not_accepted(field, value):
    with pytest.raises(p.PreparationRefused, match="FROZEN_DIAGNOSTIC_SOURCE_REQUIRED"):
        p.inspect_source_archive(SOURCE, **{field: value})


@pytest.mark.parametrize("field", ["expected_manifest_sha256", "expected_archive_sha256"])
def test_substitute_development_identity_is_not_accepted(source, field):
    with pytest.raises(p.PreparationRefused, match="FROZEN_DEVELOPMENT_PANEL_REQUIRED"):
        p.inspect_development(DEVELOPMENT, DEVELOPMENT_ZIP, source, **{field: "0" * 64})


def test_changed_source_bytes_refused_before_zip_read(tmp_path):
    path = tmp_path / "changed.zip"
    path.write_bytes(b"changed")
    with pytest.raises(p.PreparationRefused, match="SOURCE_ARCHIVE_CHANGED"):
        p.inspect_source_archive(path)


def test_changed_development_zip_refused(source, tmp_path):
    path = tmp_path / "changed.zip"
    path.write_bytes(b"changed")
    with pytest.raises(p.PreparationRefused, match="DEVELOPMENT_ARCHIVE_CHANGED"):
        p.inspect_development(DEVELOPMENT, path, source)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}',
                                b'{"a":-Infinity}', b'{"a":1e999}', b'{'])
def test_untrusted_json_duplicate_nonfinite_or_malformed_values_refused(raw):
    with pytest.raises(p.PreparationRefused):
        p.decode(raw)


@pytest.mark.parametrize("name", ["/absolute", "../escape", "a/../escape", "a//b", "./a",
                                 "C:/file", "a\\b", "a/", ""])
def test_unsafe_archive_member_name_is_refused(name):
    with pytest.raises(p.PreparationRefused, match="UNSAFE_ARCHIVE_PATH"):
        p.safe_name(name)


def zip_bytes(entries):
    result = io.BytesIO()
    with ZipFile(result, "w") as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return result.getvalue()


def test_case_colliding_archive_paths_refused():
    raw = zip_bytes([("a", b"a"), ("A", b"b")])
    with pytest.raises(p.PreparationRefused, match="ARCHIVE_COVERAGE"):
        p._zip_payloads(raw, 2)


def test_archive_symlink_refused():
    info = ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    raw = zip_bytes([(info, b"target")])
    with pytest.raises(p.PreparationRefused, match="ARCHIVE_LINK_DIRECTORY_OR_ENCRYPTION"):
        p._zip_payloads(raw, 1)


def test_archive_expansion_bound_refused(monkeypatch):
    monkeypatch.setattr(p, "MAX_EXPANDED_BYTES", 1)
    with pytest.raises(p.PreparationRefused, match="EXPANDED_ARCHIVE_BOUND"):
        p._zip_payloads(zip_bytes([("a", b"ab")]), 1)


def test_existing_output_is_not_overwritten(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    keep = output / "keep.txt"
    keep.write_bytes(b"user bytes")
    with pytest.raises(p.PreparationRefused, match="NEW_IN_SCOPE_PREPARATION_OUTPUT_REQUIRED"):
        p.prepare(SOURCE, DEVELOPMENT, DEVELOPMENT_ZIP, output)
    assert keep.read_bytes() == b"user bytes"


def test_output_outside_records_is_refused():
    output = p.ROOT / "this-must-never-be-created"
    with pytest.raises(p.PreparationRefused, match="NEW_IN_SCOPE_PREPARATION_OUTPUT_REQUIRED"):
        p.prepare(SOURCE, DEVELOPMENT, DEVELOPMENT_ZIP, output)
    assert not output.exists()


def test_budget_changed_during_observation_is_refused(monkeypatch):
    module = p._budget_module()
    before = p._budget_files(module)
    after = deepcopy(before)
    after[str(module.CANONICAL_LEDGER)] = "0" * 64
    observations = iter([before, after])
    monkeypatch.setattr(p, "_budget_files", lambda _: next(observations))
    with pytest.raises(p.PreparationRefused, match="BUDGET_CHANGED_DURING_OBSERVATION"):
        p.observe_budget()


def test_budget_helper_source_change_is_refused(monkeypatch):
    original = p.read
    monkeypatch.setattr(p, "read", lambda path, *args: b"changed" if
                        Path(path) == p.ROOT / "aws/budget.py" else original(path, *args))
    with pytest.raises(p.PreparationRefused, match="CANONICAL_BUDGET_HELPER_CHANGED"):
        p.observe_budget()


def test_budget_capacity_shortfall_writes_nothing(tmp_path, monkeypatch):
    state = p.observe_budget()
    state["remaining_unreserved_usd"] = "3.99"
    monkeypatch.setattr(p, "observe_budget", lambda: state)
    output = tmp_path / "no-budget"
    with pytest.raises(p.PreparationRefused, match="CAPACITY_BELOW_PROPOSED_RESERVATION"):
        p.prepare(SOURCE, DEVELOPMENT, DEVELOPMENT_ZIP, output)
    assert not output.exists()


def test_cli_has_no_launch_or_reservation_option():
    with pytest.raises(SystemExit) as result:
        p.main(["--launch"])
    assert result.value.code == 2
