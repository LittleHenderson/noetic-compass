"""Public, non-numeric checks for the distinct corrected HELM 2x rerun admission."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "records/typed_pointer_001/admission_cm2x_rerun_001/prepare_cm2x_rerun.py"


def load_writer():
    spec = importlib.util.spec_from_file_location("prepare_cm2x_rerun", WRITER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rerun_has_new_paths_and_preserves_the_failed_attempt_identity():
    writer = load_writer()
    assert writer.RERUN_ADMISSION_VERSION == 2
    assert writer.SEED_OUTPUT.parent.name == "admission_cm2x_rerun_001"
    assert writer.RECEIPT_DIR.name == "receipt_cm2x_rerun_20260918"
    assert not writer.SEED_OUTPUT.exists() and not writer.PARTIAL_OUTPUT.exists()
    assert not writer.RECEIPT_DIR.exists()
    prior = writer.historical_attempt_snapshot()
    assert prior["job"] == "cas-meta2-tpntr-20260925151836-b981625f-m-20260918"
    assert prior["recorded_downloaded_objects"] == 538
    assert prior["recorded_hash_mismatches"] == []
    assert len(prior["public_closeout_sha256"]) == 64
    assert prior["admission_path"] != str(writer.SEED_OUTPUT)
    assert prior["receipt_path"] != str(writer.RECEIPT_DIR)


def test_rerun_keeps_the_science_and_finite_resource_bounds():
    writer = load_writer()
    assert writer.VERSION == "cncm.typed-pointer-critical-mass-2x/1"
    assert writer.SEED == 20260918
    assert writer.contract.PASSES == 20
    assert writer.contract.PASS_CHECKPOINTS[-2:] == (10, 20)
    assert writer.contract.DESIGN["optimizer_config"]["learning_rate"] == 0.003
    assert writer.contract.DESIGN["best_checkpoint_selection"] is False
    assert writer.launch.BOUNDS["jobs"] == 1
    assert writer.launch.BOUNDS["automatic_retries"] == 0
    assert writer.launch.BOUNDS["instance_type"] == "g7.2xlarge"
    bound = writer.cost_bound()
    assert bound["reservation_plus_allowance_usd"] == "19.30"
    assert bound["all_services_cap_usd"] == "21.50"
    assert bound["all_services_prospective_total_usd"] == "20.60"
    assert bound["headroom_to_cap_usd"] == "0.90"


def test_rerun_directive_is_byte_bound_and_names_the_no_reuse_rule():
    writer = load_writer()
    raw = writer.OWNER_DIRECTIVE.read_bytes()
    assert sha256(raw).hexdigest() == writer.OWNER_DIRECTIVE_SHA256
    text = raw.decode("utf-8")
    assert "automatic_retries=0" in text
    assert "mandatory pass-10 checkpoint evidence" in text
    assert writer.PRIOR_JOB in text


def test_rerun_study_marks_attempt_two_without_changing_experiment_version():
    writer = load_writer()
    study = writer.study_record(
        "a" * 40,
        {"packaged_version": writer.VERSION, "packaged_passes": 20},
        {"inputs_sha256": "b" * 64, "design_sha256": "c" * 64,
         "evidence_contract_sha256": "d" * 64},
        "cas-meta2-tpntr-20260925170000-aaaaaaaa-m-20260918",
        owner_question=None,
    )
    assert study["attempt"] == 2 and study["rerun_admission_version"] == 2
    assert study["scientific_experiment_version_unchanged"] == writer.VERSION
    assert study["automatic_retry_of_prior_attempt"] is False
    assert study["prior_failed_attempt_untouched"] is True
    assert study["required_artifacts"]["pass_10_evaluations"] == ["course_p10", "development_p10"]
    assert study["required_artifacts"]["pass_20_evaluations"] == ["course_p20", "development_p20"]


def test_public_partial_checkout_metadata_query_covers_exact_inventory(monkeypatch, tmp_path):
    launch = load_writer().launch
    bodies = {"cncm/public.py": b"public\n", "research/public.py": b"metadata\n"}
    rows = [{"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
            for name, raw in sorted(bodies.items())]
    monkeypatch.setattr(launch.contract, "input_inventory", lambda root: rows)
    def git(args, repository):
        if args[2] == "show":
            name = args[3].split(":", 1)[1].removeprefix(launch.shared.GIT_PREFIX)
            return bodies[name]
        assert args[:7] == ["-c", "core.autocrlf=false", "ls-tree", "-r", "-l", "-z", "a" * 40]
        assert args[7:] == ["--"] + [launch.shared.GIT_PREFIX + name for name in sorted(bodies)]
        return b"".join(("100644 blob %s %d\t%s%s\0" % (launch._git_object_id(raw), len(raw),
                         launch.shared.GIT_PREFIX, name)).encode() for name, raw in sorted(bodies.items()))
    monkeypatch.setattr(launch.shared, "_run_git", git)
    assert launch._committed_rows("a" * 40, tmp_path, repository=tmp_path) == rows


def test_public_partial_checkout_still_refuses_incorrect_blob_size(monkeypatch, tmp_path):
    launch = load_writer().launch
    raw = b"public\n"
    row = {"path": "cncm/public.py", "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    monkeypatch.setattr(launch.contract, "input_inventory", lambda root: [row])
    def git(args, repository):
        if args[2] == "show":
            return raw
        return ("100644 blob %s 999\t%scncm/public.py\0" % (launch._git_object_id(raw), launch.shared.GIT_PREFIX)).encode()
    monkeypatch.setattr(launch.shared, "_run_git", git)
    with pytest.raises(ValueError, match="POINTER_INVENTORY_WORKING_TREE_DIVERGED"):
        launch._committed_rows("a" * 40, tmp_path, repository=tmp_path)
