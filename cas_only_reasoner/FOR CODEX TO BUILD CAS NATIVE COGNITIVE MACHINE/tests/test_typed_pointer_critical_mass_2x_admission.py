"""Focused regressions for the critical-mass 2x PROSPECTIVE admission writer.

WHAT THIS FILE IS FOR. `records/typed_pointer_001/admission_cm2x_001/prepare_cm2x_study.py` freezes the job
record for the 20-pass registered full run. Two of its steps cannot run before the source commit exists --
`check_source` requires HEAD to BE the source commit, and the authority binds the committed input inventory --
so this file tests every part that is decidable locally, and pins the two facts that must be true when the
freeze does run:

  * the cost bound is the ledger's own arithmetic and the whole thing fits the $20.00 all-services cap;
  * the study record names BOTH evaluated durations, the pass 11-20 required artifacts, and the one-machine /
    no-retry / cleanup safeguards, and it supersedes R18 for this version without touching R18's records;
  * the writer's target paths are still free, and R18's own frozen request record is byte-identical to the
    digest its own study record pinned when it was frozen.

Pure: no torch, no network, no AWS call, no ledger write, no git write.
"""
import builtins
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _extra in (ROOT, ROOT / "research/CAS_META_2_COMPOSITION"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

WRITER_PATH = ROOT / "records/typed_pointer_001/admission_cm2x_001/prepare_cm2x_study.py"
R18_REQUEST = ROOT / "records/typed_pointer_001/admission_analogy_on_001/seeds/20260918/request.json"
# The digest the frozen R18 study record (`admission_analogy_on_001/seeds/study.json`) pinned for that file.
R18_REQUEST_SHA256 = "c3f16fe669b0f9623e581759e2d82730477b89bae56e43a97895fa701b484591"


@pytest.fixture(autouse=True)
def public_only(monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer"}:
            raise AssertionError("NUMERIC_PROVIDER_IMPORT:" + name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture(scope="module")
def writer():
    spec = importlib.util.spec_from_file_location("prepare_cm2x_study", WRITER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_cost_bound_is_the_ledgers_own_arithmetic_and_fits_the_usd_20_cap(writer):
    bound = writer.cost_bound()
    assert bound["instance_seconds_max"] == 25200
    assert bound["compute_and_ancillary_bound_usd"] == "19.12"
    assert bound["reservation_usd"] == "19.20"
    assert bound["reservation_plus_allowance_usd"] == "19.30"
    assert bound["all_services_cap_usd"] == "20.00"
    assert bound["headroom_to_cap_usd"] == "0.70"
    assert bound["ledger_rule_verdict"] == "PASS"
    assert bound["expected_cost_usd"] == "13.94"
    # The expected cost is the delivered R17 job's own measured seconds per update, projected over 20 passes.
    assert bound["projected_instance_seconds"] == "17795.126661911716"
    assert float(bound["projected_instance_seconds"]) / 3600 * 2.52 + 1.48 == pytest.approx(13.9366, abs=1e-4)
    assert bound["receipt_of_the_basis"] == "records/typed_pointer_001/receipt_analogy_on_20260917"


def test_the_writer_hashes_canonical_record_bytes_without_recanonicalising_them(writer):
    raw = writer.canonical({"record": "bytes"})
    assert writer.digest(raw) == sha256(raw).hexdigest()


def test_the_study_record_names_both_durations_and_the_pass_11_to_20_artifacts(writer):
    study = writer.study_record("a" * 40, {"packaged_version": writer.VERSION, "packaged_passes": 20},
                                {"inputs_sha256": "b" * 64, "design_sha256": "c" * 64,
                                 "evidence_contract_sha256": "d" * 64}, "cas-meta2-tpntr-20260924120000-aaaaaaaa-m-20260918",
                                owner_question=None)
    assert study["schema"] == "cncm.typed-pointer-critical-mass-2x-study-admission/0.1"
    assert study["status"] == "FROZEN_BEFORE_FIRST_RUN"
    assert study["experiment_version"] == writer.VERSION == "cncm.typed-pointer-critical-mass-2x/1"
    assert study["pass_multiplier_over_r18"] == 2
    duration = study["training_duration"]
    assert duration["passes"] == 20 and duration["both_durations_evaluated"] == [10, 20]
    assert 10 in duration["checkpoints_evaluated"] and 20 in duration["checkpoints_evaluated"]
    assert duration["registered_full_run_is_the_20_pass_plan"] is True
    assert study["best_checkpoint_selection"] is False
    required = study["required_artifacts"]
    assert required["covers_passes_11_to_20"] is True
    assert required["count"] == 128 and len(required["pass_output_names_required"]) == 20
    assert "pass_11_batches.jsonl" in required["pass_output_names_required"]
    assert "pass_20_updates.jsonl" in required["pass_output_names_required"]
    assert required["pass_10_evaluations"] == ["course_p10", "development_p10"]
    assert required["pass_20_evaluations"] == ["course_p20", "development_p20"]
    assert study["one_machine_at_a_time"] is True
    assert study["automatic_retries"] == 0
    assert study["cleanup_required"] is True and "cleanup" in study["cleanup_owner"]
    assert study["numeric_runs_completed"] == 0
    assert "R18" in study["supersedes"] and "not modified" in study["supersedes"]
    assert study["cost_bound"]["reservation_plus_allowance_usd"] == "19.30"


def test_the_records_carry_the_version_and_the_new_bounds(writer):
    plan = writer.launch.reservation_plan_for(writer.launch.DESIGN)
    assert plan["frozen_budget"]["experiment_version"] == writer.VERSION
    assert plan["frozen_budget"]["passes"] == 20
    assert plan["frozen_budget"]["evaluated_at_both_durations"] is True
    assert plan["frozen_budget"]["best_checkpoint_selection"] is False
    assert writer.launch.BOUNDS["jobs"] == 1 and writer.launch.BOUNDS["automatic_retries"] == 0
    assert writer.launch.BOUNDS["reservation_usd"] == "19.20"
    assert writer.launch.BOUNDS["instance_seconds_max"] == 25200
    assert writer.launch.BOUNDS["max_wall_seconds"] == 23400
    assert writer.launch.BOUNDS["optimizer_updates_max"] == 2958


def test_the_original_writer_has_run_once_and_its_historical_targets_are_frozen(writer):
    assert writer.SEED_OUTPUT.is_dir() and not writer.PARTIAL_OUTPUT.exists()
    assert not writer.OWNER_PROBE.exists()
    assert writer.RECEIPT_DIR.name == "receipt_cm2x_20260918"
    assert writer.RECEIPT_DIR.is_dir()
    request = json.loads((writer.SEED_OUTPUT / "20260918/request.json").read_bytes())
    assert request["job"] == "cas-meta2-tpntr-20260925151836-b981625f-m-20260918"
    assert writer.SEED == 20260918 and writer.package_dir("a" * 40).name == "package_aaaaaaaa"


def test_the_owner_probe_is_removed_even_when_the_launcher_refuses_the_record(writer):
    """A refused owner record must leave no probe file behind for the next run to trip over."""
    authority = {"job": "cas-meta2-tpntr-20260924120000-aaaaaaaa-m-20260918",
                 "owner_authorization_sha256": "f" * 64, "bounds": writer.launch.BOUNDS}
    with pytest.raises(ValueError) as refusal:
        writer.validate_owner_record(b"{}", authority)
    assert "POINTER_OWNER_FILE_HASH" in str(refusal.value)
    assert not writer.OWNER_PROBE.exists()


def test_failed_exclusive_create_preserves_another_invocations_probe(writer, monkeypatch):
    probe = writer.HERE / "owner_probe_contention_test.json"
    monkeypatch.setattr(writer, "OWNER_PROBE", probe)
    real_open = open

    def lose_exclusive_create(path, mode):
        assert path == probe and mode == "xb"
        with real_open(path, mode) as stream:
            stream.write(b"another invocation")
        raise FileExistsError("another invocation created the probe")

    monkeypatch.setattr(writer, "open", lose_exclusive_create, raising=False)
    try:
        with pytest.raises(FileExistsError):
            writer.validate_owner_record(b"{}", {})
        assert probe.read_bytes() == b"another invocation"
    finally:
        probe.unlink(missing_ok=True)


def test_the_writer_stops_on_a_bad_or_uncommitted_source(writer):
    with pytest.raises(ValueError) as refusal:
        writer.check_source("not-a-sha")
    assert "SOURCE_SHA_FORM" in str(refusal.value)
    with pytest.raises(ValueError) as refusal:
        writer.check_source("a" * 40)
    assert "CM2X_ADMISSION_STOPPED:" in str(refusal.value)
    # No package has been built for that sha either: the writer refuses before writing anything.
    with pytest.raises(ValueError) as refusal:
        writer.verify_package("a" * 40)
    assert "BUILD_THE_PACKAGE_FIRST" in str(refusal.value)


def test_the_tree_check_tolerates_only_the_seed_folder_and_this_source_package(writer):
    """The rule, and the two things that made it fail in a rehearsal, are both exercised here for real."""
    prefix = writer.launch.shared.GIT_PREFIX
    assert writer.tolerated("a" * 40) == (
        prefix + "records/typed_pointer_001/admission_cm2x_001/seeds/",
        prefix + "research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_aaaaaaaa/")
    # `seeds.partial/` is deliberately NOT tolerated (`seeds/` does not prefix it).
    assert not any(hold.endswith("seeds.partial/") for hold in writer.tolerated("a" * 40))
    # AND THE REAL CHECK, on this worktree: it runs `git status` read-only from the CNCM folder, so the
    # coordination folder OUTSIDE that tree cannot appear, and every path that does appear is spelled the way
    # git spells it (forward slashes, repository-root relative). Both were rehearsal failures.
    dirty = writer.dirty_paths(writer.git("rev-parse", "HEAD").strip())
    assert isinstance(dirty, list)
    assert not any("coordination" in entry for entry in dirty)
    # Each entry is a two-character status code, a space, then the repository-root-relative path.
    assert all(entry[2] == " " and entry[3:].startswith(prefix) for entry in dirty)


def test_a_declared_output_is_tolerated_and_a_stray_file_is_not(writer):
    """A real untracked package directory for this source is tolerated; a stray file is reported."""
    package = writer.package_dir("b" * 40)
    stray = writer.ROOT / "records/typed_pointer_001/admission_cm2x_001/stray_probe.txt"
    package.mkdir(parents=True)
    try:
        (package / "probe.txt").write_bytes(b"x")
        stray.write_bytes(b"x")
        dirty = writer.dirty_paths("b" * 40)
        assert not any("package_bbbbbbbb" in entry for entry in dirty), dirty
        assert any("stray_probe.txt" in entry for entry in dirty), dirty
    finally:
        (package / "probe.txt").unlink()
        package.rmdir()
        stray.unlink()


def test_the_r18_admission_record_is_byte_identical_to_its_frozen_digest():
    raw = R18_REQUEST.read_bytes()
    assert sha256(raw).hexdigest() == R18_REQUEST_SHA256
    record = json.loads(raw)
    assert record["launch_authorized"] is False
    assert record["source_sha"] == "3df31d965bb2eabb168ae7efbf03300a1a1144d7"
    # R18's own 10-pass package identity, still the one it was frozen with.
    assert record["archive_sha256"] == "0020c28080c2c9432ff5b627e14db5c3fbe433b0b1397d454d4ee0637ba23377"


def test_owner_directive_is_exact_and_refuses_changed_bytes(writer, monkeypatch):
    assert sha256(writer.OWNER_DIRECTIVE.read_bytes()).hexdigest() == writer.OWNER_DIRECTIVE_SHA256
    assert 'Then launch **2x**.' in writer.owner_directive()
    altered = writer.HERE / 'altered_directive_test.md'
    try:
        altered.write_text('Different authority')
        monkeypatch.setattr(writer, 'OWNER_DIRECTIVE', altered)
        with pytest.raises(ValueError, match='OWNER_DIRECTIVE_BYTES'):
            writer.owner_directive()
    finally:
        altered.unlink(missing_ok=True)
