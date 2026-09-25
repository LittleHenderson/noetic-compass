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
    assert bound["expected_cost_usd"] == "13.76"
    # The expected cost is the delivered R17 job's own measured seconds per update, projected over 20 passes.
    assert bound["projected_instance_seconds"] == "17536.03231641743"
    assert float(bound["projected_instance_seconds"]) / 3600 * 2.52 + 1.48 == pytest.approx(13.7552, abs=1e-4)
    assert bound["receipt_of_the_basis"] == "records/typed_pointer_001/receipt_analogy_on_20260917"


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
    assert required["count"] == 126 and len(required["pass_output_names_required"]) == 20
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


def test_the_writer_has_not_run_and_its_targets_are_free(writer):
    assert not writer.SEED_OUTPUT.exists() and not writer.PARTIAL_OUTPUT.exists()
    assert writer.RECEIPT_DIR.name == "receipt_cm2x_20260918"
    assert not writer.RECEIPT_DIR.exists()
    assert writer.SEED == 20260918 and writer.package_dir("a" * 40).name == "package_aaaaaaaa"


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


def test_quoted_status_paths_are_read_back_as_paths_with_spaces(writer):
    """`git status --porcelain` quotes this tree's paths, because they contain spaces."""
    assert writer.porcelain_path(' "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/x"') == \
        "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/x"
    assert writer.porcelain_path(' "quote\\"inside"') == 'quote"inside'
    assert writer.porcelain_path(" plain/path") == "plain/path"
    # Git writes forward slashes and reports paths from the REPOSITORY ROOT; pathlib on Windows writes
    # backslashes and the writer's paths start at the CNCM folder. Both are reconciled, so the writer's own
    # declared outputs compare equal to what git actually reports in this worktree.
    package = writer.repo_path(writer.PACKAGE_PARENT)
    assert package == ("cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
                       "research/CAS_META_2_COMPOSITION/records/typed_pointer_001")
    line = '?? "%s/"' % package
    path = writer.git_path(writer.porcelain_path(line[3:]))
    assert path == package + "/" and path.startswith(package + "/")
    # The seed outputs are a DIFFERENT prefix and must not be tolerated by the package rule.
    assert not path.startswith(writer.repo_path(writer.SEED_OUTPUT) + "/")


def test_the_r18_admission_record_is_byte_identical_to_its_frozen_digest():
    raw = R18_REQUEST.read_bytes()
    assert sha256(raw).hexdigest() == R18_REQUEST_SHA256
    record = json.loads(raw)
    assert record["launch_authorized"] is False
    assert record["source_sha"] == "3df31d965bb2eabb168ae7efbf03300a1a1144d7"
    # R18's own 10-pass package identity, still the one it was frozen with.
    assert record["archive_sha256"] == "0020c28080c2c9432ff5b627e14db5c3fbe433b0b1397d454d4ee0637ba23377"
