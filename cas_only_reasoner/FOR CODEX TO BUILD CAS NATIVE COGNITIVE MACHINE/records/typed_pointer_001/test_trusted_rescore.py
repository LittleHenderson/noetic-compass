"""T01 tamper suite for trusted_rescore.py (written for 0.2, kept current for 0.4) -- every rejection must FIRE, on a
real receipt, with a real edit. The 0.4 historical-compatibility mode has its own suite: test_historical_compatibility.py.

Two groups.

FAST (always run, a few seconds in total). These exercise everything the tool decides by READING FILES
ONLY: anchor and study identity, the seed set, the frozen grader's hash, the hash of every checker source
file, prediction-file identity, duplicate / missing ids, non-finite numbers, duplicate JSON keys. They
also prove the ordering rule: when an identity does not match, the checker code is NOT imported and the
checks that need it are recorded NOT_RUN -- a substituted evaluator is never executed.

SLOW (run only with HELM_RUN_SLOW_TESTS=1; about 25 minutes of one CPU core -- run them on the cloud
machine, not on the owner's laptop). These need the frozen course loaded (minutes) and re-check all 1,128
predictions of the sandbox seed per run: the clean copy through the command line, altered scores with and
without a rewritten manifest, an absent scoring file, a malformed answer, profile / course / population
identity, agreement and disagreement with a frozen grader reading, and executed-but-not-anchored code.

The sandbox is a copy of the certified Helm 1.0 seed 20260918's four files with a one-seed study.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trusted_rescore as T  # noqa: E402

RESCORE = HERE / "trusted_rescore.py"
CERTIFIED_SEED = "20260918"
SOURCE_RECEIPT = HERE / ("receipt_helm1_certified_%s" % CERTIFIED_SEED) / "collected/results/artifacts"
FILES = ["course_p00_predictions.json", "course_p00_scoring.json", "course_p10_predictions.json", "course_p10_scoring.json"]
HISTORICAL_ANCHOR = HERE / "trust_anchor_helm1_certified.json"
slow = pytest.mark.skipif(os.environ.get("HELM_RUN_SLOW_TESTS") != "1",
                          reason="needs the frozen course loaded (minutes) and ~25 min of CPU; set HELM_RUN_SLOW_TESTS=1 (cloud machine)")


# --- sandbox -------------------------------------------------------------------------------------
def _make_sandbox():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="trusted_rescore_"))
    target = tmp / "receipt" / "collected/results/artifacts"
    target.mkdir(parents=True)
    for name in FILES:
        shutil.copy(SOURCE_RECEIPT / name, target / name)
    study = json.loads((HERE / "study_helm1_certified.json").read_text(encoding="utf-8"))
    study["jobs"] = [dict(j, receipt_dir=str(tmp / "receipt_as_recorded_elsewhere")) for j in study["jobs"] if str(j["model_seed"]) == CERTIFIED_SEED]
    (tmp / "study.json").write_text(json.dumps(study), encoding="utf-8")
    return tmp


def override(tmp):
    return {CERTIFIED_SEED: str(tmp / "receipt")}


def _course_part_without_loading():
    """The parts of an anchor that need the course loaded, taken from committed records instead (fast tests only)."""
    old = json.loads(HISTORICAL_ANCHOR.read_text(encoding="utf-8"))
    ids = sorted(p["record_id"] for p in json.loads((SOURCE_RECEIPT / "course_p10_predictions.json").read_text(encoding="utf-8"))["predictions"])
    return {"course_digest": old["course_digest"], "population": old["population"], "profile_digest": old["checker"]["profile_digest"],
            "expected_record_ids": ids, "expected_record_count": len(ids)}


@pytest.fixture()
def fast():
    tmp = _make_sandbox()
    anchor = T.safe_anchor_part(tmp / "study.json", override(tmp))
    part = _course_part_without_loading()
    anchor["checker"]["profile_digest"] = part.pop("profile_digest")
    anchor.update(part)
    (tmp / "anchor.json").write_text(json.dumps(anchor), encoding="utf-8")
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def run(tmp, **kw):
    out = tmp / "reading.json"
    code = T.rescore(tmp / "study.json", tmp / "anchor.json", override(tmp), out, **kw)
    return code, json.loads(out.read_text(encoding="utf-8"))


def codes(reading):
    return [r.split(":")[0] for r in reading["reject_reasons"]]


def art(tmp, name):
    return tmp / "receipt/collected/results/artifacts" / name


def edit_anchor(tmp, change):
    a = json.loads((tmp / "anchor.json").read_text(encoding="utf-8"))
    change(a)
    (tmp / "anchor.json").write_text(json.dumps(a), encoding="utf-8")


def _edit_predictions(tmp, change):
    path = art(tmp, "course_p10_predictions.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    change(d)
    path.write_text(json.dumps(d), encoding="utf-8")


def assert_checker_never_ran(reading):
    assert reading["imported_checker_code"] is False and reading["label_rederived"] in ("VOID_REJECTED", "NOT_DERIVED")
    assert all(reading["checks"][name]["status"] == "NOT_RUN" for name in T.CHECKER_CHECKS)


# =================================== FAST ===================================
def test_clean_files_pass_every_file_check_and_safe_only_is_never_ok(fast):
    code, r = run(fast, safe_only=True)
    assert r["reject_reasons"] == [] and all(r["checks"][n]["status"] == "PASS" for n in T.SAFE_CHECKS if n != "HISTORICAL_EVIDENCE")
    assert r["checks"]["HISTORICAL_EVIDENCE"]["status"] == "NOT_REQUESTED" and r["mode"]["name"] == "TRUSTED"   # 0.4: default mode
    assert r["verdict"] == "RESCORE_INCOMPLETE" and code == 3           # NOT_RUN is not PASS
    assert_checker_never_ran(r)
    assert r["custody"].startswith("EVALUATION_NOT_INDEPENDENT")


def test_evaluator_substitution_is_rejected_and_the_checker_is_not_run(fast):
    edit_anchor(fast, lambda a: a["grader"]["pin"].update(sha256_lf="0" * 64))
    code, r = run(fast)                                                   # NOT safe_only: the gate itself must stop the import
    assert code == 2 and r["verdict"] == "REJECT" and "EVALUATOR_IDENTITY" in codes(r)
    assert_checker_never_ran(r)


def test_checker_code_substitution_is_rejected_before_any_import(fast):
    focal = T._TT + "focal.py"                                            # the file the 0.1 anchor did not cover
    edit_anchor(fast, lambda a: a["checker"]["code_closure"][focal].update(sha256_lf="1" * 64))
    code, r = run(fast)
    assert code == 2 and "CHECKER_CODE_IDENTITY" in codes(r) and "focal.py" in " ".join(r["reject_reasons"])
    assert_checker_never_ran(r)


def test_checker_code_substitution_through_the_command_line_does_not_import_the_checker(fast):
    edit_anchor(fast, lambda a: a["checker"]["code_closure"][T._TT + "checker.py"].update(sha256_lf="2" * 64))
    out = fast / "cli.json"
    proc = subprocess.run([sys.executable, str(RESCORE), "--study", str(fast / "study.json"), "--anchor", str(fast / "anchor.json"),
                           "--receipt", "%s=%s" % (CERTIFIED_SEED, fast / "receipt"), "--out", str(out)], capture_output=True, text=True)
    r = json.loads(out.read_text(encoding="utf-8"))
    assert proc.returncode == 2 and "CHECKER_CODE_IDENTITY" in codes(r)
    assert_checker_never_ran(r)                                           # a fresh process: nothing under cas_meta2 was ever imported


def test_a_closure_file_the_anchor_does_not_list_is_rejected(fast):
    edit_anchor(fast, lambda a: a["checker"]["code_closure"].pop(T._TT + "slots.py"))
    code, r = run(fast)
    assert "CHECKER_CODE_IDENTITY" in codes(r) and "not in the anchor" in " ".join(r["reject_reasons"])
    assert_checker_never_ran(r)


def test_study_identity_and_seed_set(fast):
    study = json.loads((fast / "study.json").read_text(encoding="utf-8"))
    study["jobs"][0]["model_seed"] = 20260917                              # a different seed slipped into the study
    (fast / "study.json").write_text(json.dumps(study), encoding="utf-8")
    T.rescore(fast / "study.json", fast / "anchor.json", {"20260917": str(fast / "receipt")}, fast / "reading.json")
    r = json.loads((fast / "reading.json").read_text(encoding="utf-8"))
    assert {"STUDY_IDENTITY", "SEED_SET"} <= set(codes(r))
    assert_checker_never_ran(r)


def test_an_outdated_or_unreadable_anchor_is_a_typed_rejection_with_a_written_reading(fast):
    if json.loads(HISTORICAL_ANCHOR.read_text(encoding="utf-8")).get("schema") != T.ANCHOR_SCHEMA:
        shutil.copy(HISTORICAL_ANCHOR, fast / "anchor.json")              # the committed 0.2 anchor (wrong rule description)
        code, r = run(fast)
        assert code == 2 and codes(r) == ["RULE_DESCRIPTION_MISMATCH", "ANCHOR_SCHEMA_OUTDATED"]   # 0.4: the rule is named first
        assert_checker_never_ran(r)
    (fast / "anchor.json").write_text("{ this is not json", encoding="utf-8")
    code, r = run(fast)
    assert code == 2 and codes(r) == ["ANCHOR_UNREADABLE"]
    assert_checker_never_ran(r)


def test_wrong_phase_file_is_rejected(fast):
    shutil.copy(art(fast, "course_p00_predictions.json"), art(fast, "course_p10_predictions.json"))
    _, r = run(fast, safe_only=True)
    assert r["verdict"] == "REJECT" and codes(r) == ["PREDICTIONS_IDENTITY"]


def test_duplicate_missing_and_absent_predictions_are_rejected(fast):
    _edit_predictions(fast, lambda d: d["predictions"].append(dict(d["predictions"][0])))
    _, r = run(fast, safe_only=True)
    assert "DUPLICATE_IDS" in codes(r) and r["checks"]["ID_SET"]["status"] == "FAIL"
    shutil.copy(SOURCE_RECEIPT / "course_p10_predictions.json", art(fast, "course_p10_predictions.json"))
    _edit_predictions(fast, lambda d: d["predictions"].pop())
    _, r = run(fast, safe_only=True)
    assert "MISSING_OR_EXTRA_PREDICTIONS" in codes(r) and "missing 1, extra 0" in " ".join(r["reject_reasons"])
    art(fast, "course_p10_predictions.json").unlink()
    _, r = run(fast, safe_only=True)
    assert "file absent" in " ".join(r["reject_reasons"])


def test_nonfinite_numbers_and_duplicate_json_keys_are_rejected(fast):
    _edit_predictions(fast, lambda d: d["predictions"][5].update(scores={"typed-slot-x": {"ABSENT": float("nan"), "PRESENT": 0.0}}))
    _, r = run(fast, safe_only=True)
    assert "NONFINITE_NUMBER" in codes(r) and r["checks"]["FINITE_NUMBERS"]["status"] == "FAIL"
    shutil.copy(SOURCE_RECEIPT / "course_p10_predictions.json", art(fast, "course_p10_predictions.json"))
    path = art(fast, "course_p10_predictions.json")
    path.write_text(path.read_text(encoding="utf-8").replace("{", '{"phase": "smuggled", ', 1), encoding="utf-8")
    _, r = run(fast, safe_only=True)
    assert "DUPLICATE_JSON_KEYS" in codes(r)                              # plain json.loads would silently keep the last one


def test_every_safely_checkable_reason_is_collected_not_just_the_first(fast):
    edit_anchor(fast, lambda a: a["grader"]["pin"].update(sha256_lf="0" * 64))
    _edit_predictions(fast, lambda d: (d["predictions"].append(dict(d["predictions"][0])),
                                       d["predictions"][5].update(scores={"s": {"ABSENT": float("inf")}})))
    code, r = run(fast)
    assert {"EVALUATOR_IDENTITY", "PREDICTIONS_IDENTITY", "DUPLICATE_IDS", "NONFINITE_NUMBER"} <= set(codes(r)) and code == 2
    assert_checker_never_ran(r)


def test_rejection_is_irreversible():
    run_ = T._Run()
    run_.fail("ID_SET", "DUPLICATE_IDS", "x")
    run_.passed("ID_SET")
    run_.not_run("ID_SET", "y")
    assert run_.checks["ID_SET"]["status"] == "FAIL" and run_.reasons == ["DUPLICATE_IDS:x"]


def test_hash_policy_compares_text_and_records_raw_bytes(tmp_path):
    (tmp_path / "lf.json").write_bytes(b'{"a": 1,\n "b": 2}\n')
    (tmp_path / "crlf.json").write_bytes(b'{"a": 1,\r\n "b": 2}\r\n')
    lf, crlf = T.file_pin(tmp_path / "lf.json"), T.file_pin(tmp_path / "crlf.json")
    assert lf["sha256_lf"] == crlf["sha256_lf"] and lf["bytes_lf"] == crlf["bytes_lf"] == 18
    assert lf["sha256_raw_observed"] != crlf["sha256_raw_observed"] and crlf["bytes_raw_observed"] == 20
    assert lf["sha256_raw_observed"] == hashlib.sha256(b'{"a": 1,\n "b": 2}\n').hexdigest()
    assert T.HASH_POLICY["policy_id"] == "cncm.hash-policy/1.0"


def test_receipts_resolve_inside_this_package_and_paths_are_portable():
    part = T.safe_anchor_part(HERE / "study_helm1_certified.json", {})
    assert part["seed_set"] == ["20260917", "20260918", "20260919"] and part["study"]["path"] == "records/typed_pointer_001/study_helm1_certified.json"
    for seed, info in part["seeds"].items():
        assert info["receipt_resolved_from"] == "package-relative"          # not the absolute path into another worktree
        assert info["receipt_dir"] == "records/typed_pointer_001/receipt_helm1_certified_%s" % seed
    assert "\\" not in json.dumps(part["seeds"]) and ":" not in part["grader"]["path"]


def test_the_closure_list_names_real_files_and_covers_more_than_the_three_the_first_anchor_did():
    pins = T.code_closure_pins()
    assert len(pins) == 18 and all(pin is not None for pin in pins.values())
    assert {T._TT + "focal.py", "records/typed_practice_001/evaluate_gates.py"} <= set(pins)


@pytest.mark.parametrize("name,expected_label,counts", [
    ("helm1_certified", "LEARNS_NEW_WORLDS", {"20260917": [10, 0], "20260918": [12, 0], "20260919": [11, 0]}),
    ("helm2_experimental", "NO_TRANSFER_TO_NEW_WORLDS", {"20260917": [11, 1], "20260918": [12, 0], "20260919": [7, 1]})])
def test_committed_readings_agree_with_the_frozen_grader(name, expected_label, counts):
    r = json.loads((HERE / ("trusted_rescore_reading_%s.json" % name)).read_text(encoding="utf-8"))
    assert r["verdict"] == "RESCORE_OK" and r["label_rederived"] == expected_label
    c = r["comparison_with_frozen_grader"]
    assert c["labels_agree"] is True and {s: v["rescored_gained_broken"] for s, v in c["per_seed"].items()} == counts
    assert all(v["agree"] for v in c["per_seed"].values())
    assert all(s["phases"][ph]["rescored"] == 564 and s["phases"][ph]["disagreements"] == 0 for s in r["per_seed"].values() for ph in T.PHASES)


# The anchors were written on the cloud machine (2026-09-21, commit 8fab9575, Python 3.14.7) and checked here file by file.
# Whoever rewrites a receipt cannot rewrite an anchor without failing this test.
ANCHOR_SHA256_LF = {
    "trust_anchor_helm1_certified.json": "b1798323f6f7f9c9656b1c30eef724e94104715e180eb6724ad11c6c3b2b49ef",
    "trust_anchor_helm2_experimental_20208c92.json": "f71fa001209eb0bb8a7ab980cae24c1dab394ca3f12ce333a84e985a76a1f834",
}


def test_the_committed_anchors_are_the_pinned_ones_and_every_file_they_pin_is_the_file_on_disk():
    # 0.4: the committed anchors are the 0.2 HISTORICAL anchors. Trusted mode refuses them (wrong rule description);
    # their evidence is checked file by file in the explicit historical-compatibility mode.
    studies = {"trust_anchor_helm1_certified.json": "study_helm1_certified.json", "trust_anchor_helm2_experimental_20208c92.json": "admission_001/study.json"}
    for name, digest in ANCHOR_SHA256_LF.items():
        assert T.file_pin(HERE / name)["sha256_lf"] == digest, "ANCHOR_CHANGED:%s" % name
        anchor = json.loads((HERE / name).read_text(encoding="utf-8"))
        assert anchor["schema"] == T.HISTORICAL_ANCHOR_SCHEMA and anchor["custody"].startswith("EVALUATION_NOT_INDEPENDENT") and len(anchor["checker"]["code_closure"]) == 18
        out = pathlib.Path(tempfile.mkdtemp()) / "safe.json"
        T.rescore(HERE / studies[name], HERE / name, {}, out, safe_only=True, historical_compatibility=True)   # file checks only: seconds
        reading = json.loads(out.read_text(encoding="utf-8"))
        assert reading["reject_reasons"] == [] and all(reading["checks"][c]["status"] == "PASS" for c in T.SAFE_CHECKS)


def test_the_committed_readings_retain_their_historical_tool_identity():
    # Immutable 0.2 readings are historical evidence, not receipts for today's
    # repaired 0.3 tool. New acceptance records live in helm_integrated_repairs.
    for name, anchor in (("helm1_certified", "trust_anchor_helm1_certified.json"), ("helm2_experimental", "trust_anchor_helm2_experimental_20208c92.json")):
        r = json.loads((HERE / ("trusted_rescore_reading_%s.json" % name)).read_text(encoding="utf-8"))
        assert r["schema"] == "cncm.trusted-rescore-reading/0.2" and r["anchor"]["pin"]["sha256_lf"] == ANCHOR_SHA256_LF[anchor]
        assert r["tool"]["pin"]["sha256_lf"] == "8e9a751a15358043b8d1bbc7428fd0e475325174e58fe9e00ec5297cbdd5953a"
        assert all(c["status"] == "PASS" for c in r["checks"].values()) and r["imported_checker_code"] is True
        assert r["bytecode_policy"] == "FRESH_EMPTY_PYCACHE_PREFIX_AND_NO_BYTECODE_WRITTEN" and r["material_supplied_by_caller"] is False
        assert all(s["receipt_resolved_from"] == "package-relative" for s in r["per_seed"].values())


# =================================== SLOW ===================================
@pytest.fixture(scope="module")
def material():
    return T._load_frozen_and_checker()


@pytest.fixture()
def real(material):
    tmp = _make_sandbox()
    assert T.write_anchor(tmp / "study.json", tmp / "anchor.json", override(tmp), material=material) == 0
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@slow
def test_clean_copy_through_the_command_line_reproduces_the_certified_numbers(real):
    out = real / "cli.json"
    proc = subprocess.run([sys.executable, str(RESCORE), "--study", str(real / "study.json"), "--anchor", str(real / "anchor.json"),
                           "--receipt", "%s=%s" % (CERTIFIED_SEED, real / "receipt"), "--no-frozen-reading", "--out", str(out)], capture_output=True, text=True)
    r = json.loads(out.read_text(encoding="utf-8"))
    assert proc.returncode == 0 and r["verdict"] == "RESCORE_OK" and r["label_rederived"] == "LEARNS_NEW_WORLDS", r["reject_reasons"]
    s = r["per_seed"][CERTIFIED_SEED]
    assert (s["gained"], s["broken"]) == (12, 0) and s["frozen_18_after"] == s["frozen_18_before"] + 12
    assert r["imported_checker_code"] is True and r["bytecode_policy"] == "FRESH_EMPTY_PYCACHE_PREFIX_AND_NO_BYTECODE_WRITTEN"
    assert r["checks"]["FROZEN_GRADER_AGREEMENT"]["status"] == "NOT_REQUESTED"
    assert all(r["checks"][k]["status"] == "NOT_REQUESTED" for k in ("HISTORICAL_EVIDENCE", "HISTORICAL_DECISIONS"))   # 0.4 trusted mode
    assert all(v["status"] == "PASS" for k, v in r["checks"].items() if k not in ("FROZEN_GRADER_AGREEMENT", "HISTORICAL_EVIDENCE", "HISTORICAL_DECISIONS"))


def _flip_scores(tmp):
    path = art(tmp, "course_p10_scoring.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    for row in d["rows"][:20]:
        row["correct"] = not row["correct"]
    body = json.dumps(d).encode("utf-8")
    path.write_bytes(body)
    return body


@slow
def test_altered_scores_are_rejected_with_or_without_a_rewritten_manifest(real, material):
    body = _flip_scores(real)
    _, r = run(real, material=material, compare_frozen=False)
    assert r["verdict"] == "REJECT" and codes(r) == ["SCORING_FILE_DISAGREES_WITH_RESCORE"]
    manifest = [{"name": "course_p10_scoring.json", "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}]
    (real / "receipt" / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")   # the forgery that fooled the frozen grader
    _, r = run(real, material=material, compare_frozen=False)
    assert r["verdict"] == "REJECT" and codes(r) == ["SCORING_FILE_DISAGREES_WITH_RESCORE"]


@slow
def test_an_absent_scoring_file_is_not_run_which_is_not_ok(real, material):
    art(real, "course_p10_scoring.json").unlink()
    code, r = run(real, material=material, compare_frozen=False)
    assert r["reject_reasons"] == [] and r["checks"]["SCORING_FILE_AGREEMENT"]["status"] == "NOT_RUN"
    assert r["verdict"] == "RESCORE_INCOMPLETE" and code == 3 and r["label_rederived"] == "LEARNS_NEW_WORLDS"


@slow
def test_a_malformed_answer_is_rejected_and_the_rescore_is_incomplete(real, material):
    _edit_predictions(real, lambda d: d["predictions"][3].update(answer="this is not an answer"))
    _, r = run(real, material=material, compare_frozen=False)
    assert {"PREDICTIONS_IDENTITY", "MALFORMED_PREDICTION", "INCOMPLETE_RESCORE"} <= set(codes(r)) and r["label_rederived"] == "VOID_REJECTED"


@slow
@pytest.mark.parametrize("change,code_", [
    (lambda a: a["checker"].update(profile_digest="3" * 64), "CHECKER_IDENTITY"),
    (lambda a: a.update(course_digest="4" * 64), "COURSE_IDENTITY"),
    (lambda a: a["population"].update(digest="5" * 64), "POPULATION_IDENTITY")])
def test_profile_course_and_population_identity(real, material, change, code_):
    edit_anchor(real, change)
    _, r = run(real, material=material, compare_frozen=False)
    assert r["verdict"] == "REJECT" and code_ in codes(r)


@slow
def test_agreement_and_disagreement_with_a_frozen_grader_reading(real, material):
    def reading(gained):
        g = json.loads((HERE / "admission_helm1_certified/gate_reading.json").read_text(encoding="utf-8"))
        row = dict(g["seeds"][CERTIFIED_SEED]["G_LEARN_population"], wrong_to_right=gained)
        return {"label": "LEARNS_NEW_WORLDS", "seeds": {CERTIFIED_SEED: {"G_LEARN_population": row}}}
    (real / "gate_reading.json").write_text(json.dumps(reading(12)), encoding="utf-8")
    code, r = run(real, material=material)
    assert code == 0 and r["checks"]["FROZEN_GRADER_AGREEMENT"]["status"] == "PASS"
    (real / "gate_reading.json").write_text(json.dumps(reading(13)), encoding="utf-8")
    code, r = run(real, material=material)
    assert code == 2 and codes(r) == ["FROZEN_GRADER_DISAGREES"] and r["label_rederived"] == "VOID_REJECTED"
    (real / "gate_reading.json").unlink()
    code, r = run(real, material=material)
    assert code == 3 and r["checks"]["FROZEN_GRADER_AGREEMENT"]["status"] == "NOT_RUN"      # absent is NOT_RUN, never a silent OK


@slow
def test_code_that_ran_but_is_not_anchored_is_rejected(real, material, monkeypatch):
    focal = T._TT + "focal.py"
    monkeypatch.setattr(T, "CODE_CLOSURE", tuple(rel for rel in T.CODE_CLOSURE if rel != focal))
    edit_anchor(real, lambda a: a["checker"]["code_closure"].pop(focal))
    _, r = run(real, material=material, compare_frozen=False)
    assert "CODE_CLOSURE_INCOMPLETE" in codes(r) and "focal.py" in " ".join(r["reject_reasons"])
