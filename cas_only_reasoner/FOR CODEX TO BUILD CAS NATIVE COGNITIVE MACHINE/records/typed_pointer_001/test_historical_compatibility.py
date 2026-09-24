"""trusted_rescore 0.4 -- the explicit historical-compatibility mode, and the trusted-mode refusals around it.

Owner direction 2026-09-24 (item 2, RESCORER): use an explicit historical-compatibility mode for the recognised old
grading-description mistake only; require verified original evidence and apply the preserved historical rule; show
the warning and both rule descriptions; never rewrite the original record; reject unknown, altered, incomplete or
incompatible evidence for trusted acceptance; new runs do not receive the historical exception.

FAST (always run; pure Python; no checker import -- a guard makes any import of the checker fail at once). Tampering
is done in a SANDBOX: a copy of the package files one historical study needs, with the tool's paths pointed at it, so
no test can ever touch an original record. SLOW (HELM_RUN_SLOW_TESTS=1, on the cloud machine): the full 564-record
rescore of both historical studies in historical-compatibility mode (about 14 minutes each).
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
import test_trusted_rescore as base  # noqa: E402  (module object only: its tests are not collected twice)

RESCORE = HERE / "trusted_rescore.py"
REAL_PACKAGE = T.PACKAGE
slow = pytest.mark.skipif(os.environ.get("HELM_RUN_SLOW_TESTS") != "1",
                          reason="full 564-record rescore, about 14 minutes per study; set HELM_RUN_SLOW_TESTS=1 (cloud machine)")

# The coordinator's review (RESCORER_REVIEW.json, commit 0d8e8316 on research/helm-integration-20260923): the rule it
# declared, and the six historical decisions it found reproduced (b, c, exact p, passed).
REVIEW_RULE = {"all_seeds_must_pass": True, "alpha": "1/100", "id": "HELM_HISTORICAL_PAIRED_RULE_20260919",
               "min_improved_kinds": 2, "min_improved_worlds": 2, "require_b_greater_than_c": True,
               "test": "exact one-sided Binomial(b+c, 1/2) upper tail at b", "zero_loss_veto": False}
REVIEW_DECISIONS = {
    "helm1_certified": {"20260917": (10, 0, "1/1024", True), "20260918": (12, 0, "1/4096", True), "20260919": (11, 0, "1/2048", True)},
    "helm2_experimental": {"20260917": (11, 1, "13/4096", True), "20260918": (12, 0, "1/4096", True), "20260919": (7, 1, "9/256", False)},
}
READINGS = {name: e["reading"][0] for name, e in T.HISTORICAL_EXCEPTION.items()}
AWS_COPIES = {name: "records/typed_pointer_001/aws_rescore_job/results/" + pathlib.PurePosixPath(rel).name for name, rel in READINGS.items()}


# --- helpers --------------------------------------------------------------------------------------
@pytest.fixture()
def no_checker(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("the checker must not be imported or run in this test")
    monkeypatch.setattr(T, "_load_frozen_and_checker", refuse)


def codes(record):
    return [r.split(":")[0] for r in record["reject_reasons"]]


def raw_digests(paths):
    return {str(p): (hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() if pathlib.Path(p).is_file() else None) for p in paths}


def check(path, tmp, compat=True):
    out = pathlib.Path(tmp) / "check.json"
    code = T.check_reading(path, out, historical_compatibility=compat)
    return code, json.loads(out.read_text(encoding="utf-8"))


def safe(study, anchor, tmp, compat=True, **kw):
    out = pathlib.Path(tmp) / "reading.json"
    code = T.rescore(study, anchor, kw.pop("override", {}), out, safe_only=kw.pop("safe_only", True), historical_compatibility=compat, **kw)
    return code, json.loads(out.read_text(encoding="utf-8"))


def assert_checker_never_ran(record):
    assert record["imported_checker_code"] is False
    assert all(record["checks"][n]["status"] == "NOT_RUN" for n in T.CHECKER_CHECKS)


def study_of(name, package=REAL_PACKAGE):
    anchor = json.loads((package / T.HISTORICAL_EXCEPTION[name]["anchor"][0]).read_text(encoding="utf-8"))
    return package / anchor["study"]["path"]


def _sandbox_rels(name):
    entry = T.HISTORICAL_EXCEPTION[name]
    rels = list(T.CODE_CLOSURE) + ["records/typed_pointer_001/evaluate_gates.py", entry["anchor"][0], entry["reading"][0],
                                    entry["frozen_grader_reading"][0], _rel(study_of(name))]
    for mrel, _ in entry["receipt_manifests"].values():
        rels.append(mrel)
        rels += [mrel.rsplit("/", 1)[0] + "/collected/results/artifacts/" + f for f in T.LABEL_FILES]
    return rels


def _stat(path):
    s = path.stat()
    return s.st_size, s.st_mtime_ns


@pytest.fixture(scope="module")
def sandbox_store():
    """One private copy per historical study for the whole module (copying ~15 MB per test was the slow part)."""
    store = {}
    yield store
    for root, _ in store.values():
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture()
def sandbox(sandbox_store, monkeypatch, no_checker):
    """A private copy of what ONE historical study needs, with the tool pointed at it. Originals are never touched.
    After each test every file is put back exactly (a changed or missing file is re-copied, an extra file removed)."""
    used = []

    def build(name):
        if name not in sandbox_store:
            root = pathlib.Path(tempfile.mkdtemp(prefix="helm_compat_sandbox_"))
            for rel in _sandbox_rels(name):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REAL_PACKAGE / rel, root / rel)
            sandbox_store[name] = (root, {rel: _stat(root / rel) for rel in _sandbox_rels(name)})
        root, stats = sandbox_store[name]
        used.append(name)
        here = root / "records/typed_pointer_001"
        monkeypatch.setattr(T, "PACKAGE", root)
        monkeypatch.setattr(T, "HERE", here)
        monkeypatch.setattr(T, "GRADER", here / "evaluate_gates.py")
        monkeypatch.setattr(T, "CODE_ROOT", root / "research" / "CAS_META_2_COMPOSITION")
        return root
    yield build
    for name in used:
        root, stats = sandbox_store[name]
        for path in [p for p in root.rglob("*") if p.is_file()]:
            if path.relative_to(root).as_posix() not in stats:
                path.unlink()
        for rel, stat in stats.items():
            if not (root / rel).is_file() or _stat(root / rel) != stat:
                shutil.copyfile(REAL_PACKAGE / rel, root / rel)
                stats[rel] = _stat(root / rel)
            assert (root / rel).read_bytes() == (REAL_PACKAGE / rel).read_bytes(), rel


def _rel(path):
    return pathlib.Path(path).resolve().relative_to(REAL_PACKAGE.resolve()).as_posix()


def edit_json(path, change):
    d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    change(d)
    pathlib.Path(path).write_text(json.dumps(d, indent=1, sort_keys=True), encoding="utf-8")


# ================================ FROZEN CONSTANTS ================================
def test_the_frozen_constants_match_their_digests_and_the_reviewed_rule():
    assert T.TOOL_VERSION == "0.4" and T.constants_problems() == []
    assert T.HISTORICAL_RULE == REVIEW_RULE and T.HISTORICAL_RULE["zero_loss_veto"] is False
    canon = lambda v: json.dumps(v, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(canon(REVIEW_RULE)).hexdigest() == T.HISTORICAL_RULE_SHA256
    wrong = T.RECOGNISED_MISTAKE["recorded_description"]
    assert hashlib.sha256(canon(wrong)).hexdigest() == T.RECOGNISED_MISTAKE["recorded_description_sha256"]
    for entry in T.HISTORICAL_EXCEPTION.values():                      # the recognised mistake IS what both anchors record
        assert json.loads((REAL_PACKAGE / entry["anchor"][0]).read_text(encoding="utf-8"))["pass_rule"] == wrong
    assert wrong["broken_must_be"] == 0 and wrong["min_passing_b"] == 7    # the zero-loss veto and the 7-gain minimum


def test_the_frozen_list_is_exactly_two_studies_six_decisions_and_every_pin_matches_the_file_on_disk():
    assert sorted(T.HISTORICAL_EXCEPTION) == ["helm1_certified", "helm2_experimental"]
    for name, entry in T.HISTORICAL_EXCEPTION.items():
        got = {s: (d["gained"], d["broken"], d["p_one_sided"], d["passed"]) for s, d in entry["decisions"].items()}
        assert got == REVIEW_DECISIONS[name]
        pins = [entry["anchor"], entry["reading"], entry["frozen_grader_reading"]] + list(entry["receipt_manifests"].values())
        for rel, digest in pins:
            assert T.file_pin(REAL_PACKAGE / rel)["sha256_lf"] == digest, rel
        gate = json.loads((REAL_PACKAGE / entry["frozen_grader_reading"][0]).read_text(encoding="utf-8"))
        assert gate["label"] == entry["label"]
        for seed, d in entry["decisions"].items():                     # the frozen grader printed exactly these decisions
            g = gate["seeds"][seed]["G_LEARN_population"]
            assert (g["wrong_to_right"], g["right_to_wrong"], g["p_one_sided"], g["passed"]) == (d["gained"], d["broken"], d["p_one_sided"], d["passed"])
            p, passed = T.historical_decision(d["gained"], d["broken"], len(g["improved_kinds"]), len(g["improved_worlds"]))
            assert (str(p), passed) == (d["p_one_sided"], d["passed"])


def test_the_list_cannot_grow_silently(monkeypatch, tmp_path, no_checker):
    grown = json.loads(json.dumps(T.HISTORICAL_EXCEPTION))
    grown["a_new_run"] = dict(grown["helm1_certified"], anchor=["records/x.json", "0" * 64])
    monkeypatch.setattr(T, "HISTORICAL_EXCEPTION", grown)
    code, r = check(REAL_PACKAGE / READINGS["helm1_certified"], tmp_path)
    assert code == 2 and codes(r) == ["TOOL_CONSTANTS_ALTERED"]


def test_the_0_3_tool_is_kept_as_history_byte_identical():
    assert T.file_pin(HERE / "history/trusted_rescore_0_3.py")["sha256_lf"] == "50295072dd662fac1bf51021e8abd8395621ebafc8d35e8f8e4949120e35f8cc"


# ================================ TRUSTED MODE (the default) ================================
@pytest.mark.parametrize("name", sorted(T.HISTORICAL_EXCEPTION))
def test_trusted_mode_refuses_each_historical_anchor_by_name_before_any_import(name, tmp_path, no_checker):
    anchor = REAL_PACKAGE / T.HISTORICAL_EXCEPTION[name]["anchor"][0]
    code, r = safe(study_of(name), anchor, tmp_path, compat=False, safe_only=False)
    assert code == 2 and r["verdict"] == "REJECT" and codes(r) == ["RULE_DESCRIPTION_MISMATCH", "ANCHOR_SCHEMA_OUTDATED"]
    assert "recognised 0.2 grading-description mistake" in r["reject_reasons"][0] and T.HISTORICAL_FLAG in r["reject_reasons"][0]
    assert r["mode"] == {"name": "TRUSTED", "flag": None, "requested_explicitly": False} and r["historical_exception"] is None
    assert r["rule"]["recorded_is_the_recognised_mistake"] is True and r["rule"]["recorded_is_the_applied_rule"] is False
    assert_checker_never_ran(r)


def test_trusted_mode_refusal_through_the_command_line(tmp_path):
    out = tmp_path / "cli.json"
    proc = subprocess.run([sys.executable, str(RESCORE), "--study", str(study_of("helm2_experimental")),
                           "--anchor", str(REAL_PACKAGE / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0]), "--out", str(out)],
                          capture_output=True, text=True, timeout=120)
    r = json.loads(out.read_text(encoding="utf-8"))
    assert proc.returncode == 2 and codes(r)[0] == "RULE_DESCRIPTION_MISMATCH"
    assert_checker_never_ran(r)                                         # a fresh process: nothing under cas_meta2 was imported


@pytest.mark.parametrize("rel", sorted(READINGS.values()) + sorted(AWS_COPIES.values()))
def test_trusted_mode_refuses_each_historical_reading_by_name(rel, tmp_path, no_checker):
    code, r = check(REAL_PACKAGE / rel, tmp_path, compat=False)
    assert code == 2 and codes(r) == ["RULE_DESCRIPTION_MISMATCH", "READING_SCHEMA_OUTDATED"]
    assert r["rule"]["recorded_is_the_recognised_mistake"] is True and r["historical_exception"] is None
    assert r["checks"]["HISTORICAL_EVIDENCE"]["status"] == "NOT_REQUESTED"


def _new_run(tmp):
    """A NEW run (Helm 1.0 seed 20260918 copied into a one-seed study) with a fresh anchor written by 0.4."""
    anchor = T.safe_anchor_part(tmp / "study.json", base.override(tmp))
    part = base._course_part_without_loading()
    anchor["checker"]["profile_digest"] = part.pop("profile_digest")
    anchor.update(part)
    return anchor


@pytest.fixture()
def new_run(no_checker):
    tmp = base._make_sandbox()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_new_anchors_are_written_with_the_preserved_rule(new_run):
    a = _new_run(new_run)
    assert a["schema"] == T.ANCHOR_SCHEMA and a["tool_version"] == "0.4"
    assert a["pass_rule"] == T.HISTORICAL_RULE and a["pass_rule_sha256"] == T.HISTORICAL_RULE_SHA256


def test_an_unrecognised_wrong_description_is_refused_in_both_modes(new_run):
    a = _new_run(new_run)
    a["pass_rule"] = dict(T.HISTORICAL_RULE, alpha="1/20")                # a DIFFERENT wrong description
    a["pass_rule_sha256"] = T.rule_sha(a["pass_rule"])
    (new_run / "anchor.json").write_text(json.dumps(a), encoding="utf-8")
    for compat, expected in ((False, ["RULE_DESCRIPTION_MISMATCH"]), (True, ["HISTORICAL_EXCEPTION_UNKNOWN_ANCHOR", "RULE_DESCRIPTION_MISMATCH"])):
        code, r = safe(new_run / "study.json", new_run / "anchor.json", new_run, compat=compat, safe_only=False, override=base.override(new_run))
        assert code == 2 and codes(r) == expected and "UNRECOGNISED" in " ".join(r["reject_reasons"])
        assert_checker_never_ran(r)


def test_a_new_run_anchor_with_the_old_wrong_description_is_refused_even_with_the_flag(new_run):
    a = _new_run(new_run)
    a.update(schema=T.HISTORICAL_ANCHOR_SCHEMA, pass_rule=dict(T.RECOGNISED_MISTAKE["recorded_description"]))
    a.pop("pass_rule_sha256"), a.pop("tool_version")
    a["tool"]["pin"]["sha256_lf"] = T.RECOGNISED_MISTAKE["written_by_tool_sha256_lf"]   # mimics a 0.2 anchor as closely as it can
    (new_run / "anchor.json").write_text(json.dumps(a), encoding="utf-8")
    code, r = safe(new_run / "study.json", new_run / "anchor.json", new_run, compat=True, safe_only=False, override=base.override(new_run))
    assert code == 2 and codes(r) == ["HISTORICAL_EXCEPTION_UNKNOWN_ANCHOR", "RULE_DESCRIPTION_MISMATCH"]
    assert "new runs never receive the historical exception" in r["reject_reasons"][0]
    assert r["mode"]["name"] == "HISTORICAL_COMPATIBILITY" and r["label_rederived"] == "VOID_REJECTED"
    assert_checker_never_ran(r)
    code, r = safe(new_run / "study.json", new_run / "anchor.json", new_run, compat=False, safe_only=False, override=base.override(new_run))
    assert code == 2 and codes(r) == ["RULE_DESCRIPTION_MISMATCH", "ANCHOR_SCHEMA_OUTDATED"]


def test_a_new_run_reading_with_the_old_wrong_description_is_refused_even_with_the_flag(tmp_path, no_checker):
    copy = tmp_path / "new_run_reading.json"                             # same schema, same wrong rule -- but not the original
    edit_json_to = json.loads((REAL_PACKAGE / READINGS["helm2_experimental"]).read_text(encoding="utf-8"))
    edit_json_to["per_seed"]["20260917"]["frozen_18_before"] = 3
    copy.write_text(json.dumps(edit_json_to, indent=1, sort_keys=True), encoding="utf-8")
    code, r = check(copy, tmp_path)
    assert code == 2 and codes(r) == ["HISTORICAL_EXCEPTION_UNKNOWN_READING", "RULE_DESCRIPTION_MISMATCH"]
    assert r["label"] == "VOID_REJECTED"


def test_an_overflowing_number_is_still_caught_after_the_0_4_speed_up(new_run):
    (new_run / "anchor.json").write_text(json.dumps(_new_run(new_run)), encoding="utf-8")
    path = new_run / "receipt/collected/results/artifacts/course_p10_predictions.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    d["predictions"][5]["scores"] = {"typed-slot-x": {"ABSENT": 0.123456789, "PRESENT": 0.0}}
    path.write_text(json.dumps(d).replace("0.123456789", "1e999"), encoding="utf-8")   # no NaN/Infinity token: it overflows
    code, r = safe(new_run / "study.json", new_run / "anchor.json", new_run, compat=False, override=base.override(new_run))
    assert "NONFINITE_NUMBER" in codes(r) and r["checks"]["FINITE_NUMBERS"]["status"] == "FAIL"


def test_trusted_check_reading_accepts_a_clean_0_4_reading_and_refuses_each_defect(new_run, tmp_path):
    """No 0.4 reading exists yet (a full reading runs on the cloud machine). This builds one by hand for a NEW run --
    Helm 1.0 seed 20260918's recorded counts on a fresh 0.3 anchor -- to exercise the trusted verification path."""
    study = json.loads((new_run / "study.json").read_text(encoding="utf-8"))
    study["jobs"] = [dict(j, receipt_dir=str(new_run / "receipt")) for j in study["jobs"]]   # no override needed
    (new_run / "study.json").write_text(json.dumps(study), encoding="utf-8")
    anchor = T.safe_anchor_part(new_run / "study.json", {})
    part = base._course_part_without_loading()
    anchor["checker"]["profile_digest"] = part.pop("profile_digest")
    anchor.update(part)
    (new_run / "anchor.json").write_text(json.dumps(anchor), encoding="utf-8")
    _, shell = safe(new_run / "study.json", new_run / "anchor.json", new_run, compat=False)
    recorded = json.loads((REAL_PACKAGE / READINGS["helm1_certified"]).read_text(encoding="utf-8"))["per_seed"]["20260918"]
    p, passed = T.historical_decision(recorded["gained"], recorded["broken"], len(recorded["kinds_improved"]), recorded["worlds_improved"])
    seed = {"gained": recorded["gained"], "broken": recorded["broken"], "kinds_improved": recorded["kinds_improved"],
            "worlds_improved": recorded["worlds_improved"], "p_one_sided": str(p), "passed": passed,
            "receipt_dir": anchor["seeds"]["20260918"]["receipt_dir"],
            "phases": {ph: {"predictions_sha256_lf": anchor["seeds"]["20260918"]["predictions"][ph]["sha256_lf"]} for ph in T.PHASES}}
    clean = dict(shell, verdict="RESCORE_OK", reject_reasons=[], label_rederived="LEARNS_NEW_WORLDS", per_seed={"20260918": seed},
                 checks={k: {"status": "PASS", "detail": ""} for k in shell["checks"]})
    cases = {
        None: clean,
        "READING_DECISION_MISMATCH": dict(clean, per_seed={"20260918": dict(seed, passed=False)}),
        "READING_NOT_TRUSTED": dict(clean, mode={"name": T.HISTORICAL, "flag": T.HISTORICAL_FLAG, "requested_explicitly": True}),
        "RULE_DESCRIPTION_MISMATCH": dict(clean, rule=dict(clean["rule"], recorded_in_anchor=T.RECOGNISED_MISTAKE["recorded_description"])),
        "READING_NOT_CLEAN": dict(clean, verdict="RESCORE_INCOMPLETE"),
        "READING_INCONSISTENT": dict(clean, per_seed={"20260918": dict(seed, receipt_dir="records/typed_pointer_001/receipt_20260918")}),
    }
    (tmp_path / "out").mkdir()
    for expected, body in cases.items():
        (tmp_path / "r.json").write_text(json.dumps(body), encoding="utf-8")
        code, r = check(tmp_path / "r.json", tmp_path / "out", compat=False)
        if expected is None:
            assert code == 0 and r["verdict"] == "READING_VERIFIED" and r["label"] == "LEARNS_NEW_WORLDS", r["reject_reasons"]
        else:
            assert code == 2 and expected in codes(r), (expected, r["reject_reasons"])
        code, r = check(tmp_path / "r.json", tmp_path / "out", compat=True)   # a new run never gets the exception
        assert code == 2 and "HISTORICAL_EXCEPTION_UNKNOWN_READING" in codes(r)


@pytest.mark.parametrize("compat", [False, True])
def test_malformed_unknown_schema_and_incomplete_anchors_are_refused(compat, new_run):
    a = _new_run(new_run)
    text = json.dumps(a)
    cases = {
        "ANCHOR_MALFORMED": text[:-1] + ', "pass_rule": %s}' % json.dumps(T.RECOGNISED_MISTAKE["recorded_description"]),   # a second pass_rule
        "ANCHOR_SCHEMA_UNKNOWN": json.dumps(dict(a, schema="cncm.trusted-rescore-anchor/9.9")),
        "ANCHOR_INCOMPLETE": json.dumps({k: v for k, v in a.items() if k != "expected_record_ids"}),
    }
    for expected, body in cases.items():
        (new_run / "anchor.json").write_text(body, encoding="utf-8")
        code, r = safe(new_run / "study.json", new_run / "anchor.json", new_run, compat=compat, safe_only=False, override=base.override(new_run))
        assert code == 2 and codes(r) == [expected], (expected, r["reject_reasons"])


def test_malformed_unknown_schema_and_incomplete_readings_are_refused(tmp_path, no_checker):
    original = json.loads((REAL_PACKAGE / READINGS["helm1_certified"]).read_text(encoding="utf-8"))
    text = json.dumps(original)
    cases = {
        "READING_MALFORMED": text[:-1] + ', "verdict": "RESCORE_OK"}',
        "READING_SCHEMA_UNKNOWN": json.dumps(dict(original, schema="cncm.trusted-rescore-reading/9.9")),
        "READING_INCOMPLETE": json.dumps({k: v for k, v in original.items() if k != "per_seed"}),
    }
    for expected, body in cases.items():
        (tmp_path / "r.json").write_text(body, encoding="utf-8")
        for compat in (False, True):
            code, r = check(tmp_path / "r.json", tmp_path, compat=compat)
            assert code == 2 and codes(r) == [expected], (expected, compat, r["reject_reasons"])


def test_write_anchor_is_create_only_and_never_touches_an_original(tmp_path, no_checker):
    original = REAL_PACKAGE / T.HISTORICAL_EXCEPTION["helm1_certified"]["anchor"][0]
    before = original.read_bytes()
    assert T.write_anchor(study_of("helm1_certified"), original, {}) == 2
    existing = tmp_path / "exists.json"
    existing.write_text("{}", encoding="utf-8")
    assert T.write_anchor(study_of("helm1_certified"), existing, {}) == 2 and existing.read_text(encoding="utf-8") == "{}"
    proc = subprocess.run([sys.executable, str(RESCORE), "--study", str(study_of("helm1_certified")), "--anchor", str(tmp_path / "new.json"),
                           "--write-anchor", T.HISTORICAL_FLAG], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2 and "ANCHOR_REFUSED" in proc.stdout and not (tmp_path / "new.json").exists()
    assert original.read_bytes() == before


# ================================ HISTORICAL MODE: acceptance ================================
@pytest.mark.parametrize("name,rel", [(n, READINGS[n]) for n in sorted(READINGS)] + [(n, AWS_COPIES[n]) for n in sorted(AWS_COPIES)])
def test_the_historical_mode_reproduces_the_six_decisions_from_the_committed_readings(name, rel, tmp_path, no_checker):
    guarded = T.protected_paths(REAL_PACKAGE / rel)
    before = raw_digests(guarded)
    code, r = check(REAL_PACKAGE / rel, tmp_path)
    assert raw_digests(guarded) == before and r["originals"]["unchanged"] is True        # the originals are byte-unchanged
    assert code == 4 and r["verdict"] == "HISTORICAL_COMPATIBILITY_OK" and r["reject_reasons"] == []
    assert all(c["status"] == "PASS" for c in r["checks"].values())
    assert r["mode"] == {"name": "HISTORICAL_COMPATIBILITY", "flag": "--historical-compatibility", "requested_explicitly": True}
    entry = T.HISTORICAL_EXCEPTION[name]
    assert r["label"] == entry["label"] and r["historical_exception"]["entry"] == name
    for seed, (b, c, p, passed) in REVIEW_DECISIONS[name].items():
        row = r["decisions"][seed]
        assert row["agree"] is True and row["frozen_grader"]["passed"] is passed
        assert {k: row["replay_with_the_preserved_rule"][k] for k in ("gained", "broken", "p_one_sided", "passed")} == \
            {"gained": b, "broken": c, "p_one_sided": p, "passed": passed}
    # the warning and both rule descriptions, side by side
    h = r["historical_exception"]
    assert h["warning"].startswith("WARNING: HISTORICAL-COMPATIBILITY MODE") and "PRESERVED HISTORICAL RULE" in h["warning"]
    assert h["rule_descriptions"] == {"recorded_in_the_original_record_WRONG": T.RECOGNISED_MISTAKE["recorded_description"],
                                      "preserved_historical_rule_APPLIED": T.HISTORICAL_RULE}
    rows = {x["field"]: x for x in h["side_by_side"]}
    assert rows["broken_must_be"]["recorded_in_the_original_record_WRONG"] == 0 and rows["broken_must_be"]["preserved_historical_rule_APPLIED"] == T.ABSENT
    assert rows["zero_loss_veto"]["preserved_historical_rule_APPLIED"] is False and rows["alpha"]["preserved_historical_rule_APPLIED"] == "1/100"
    assert r["rule"]["recorded_is_the_recognised_mistake"] is True


def test_the_recognised_mistake_changed_one_recorded_seed_decision_and_the_mode_rederives_it(tmp_path, no_checker):
    code, r = check(REAL_PACKAGE / READINGS["helm2_experimental"], tmp_path)
    changed = {s: row for s, row in r["decisions"].items() if row["recorded_decision_differs_from_history"]}
    assert code == 4 and sorted(changed) == ["20260917"]             # 11 gains, 1 loss: the 0.2 record says False
    row = changed["20260917"]
    assert row["decision_recorded_in_the_original_record"] is False and row["what_the_wrong_description_gives"] is False
    assert row["replay_with_the_preserved_rule"]["passed"] is True and row["frozen_grader"]["passed"] is True
    assert r["label"] == "NO_TRANSFER_TO_NEW_WORLDS"                  # unaffected: seed 20260919 (7/1, p 9/256) fails either way


def test_the_warning_and_both_descriptions_are_printed_through_the_command_line():
    proc = subprocess.run([sys.executable, str(RESCORE), T.HISTORICAL_FLAG, "--check-reading", str(REAL_PACKAGE / READINGS["helm1_certified"])],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 4
    assert "WARNING: HISTORICAL-COMPATIBILITY MODE" in proc.stdout
    assert "recorded in the original record (WRONG)" in proc.stdout and "preserved historical rule (APPLIED)" in proc.stdout
    assert "broken_must_be" in proc.stdout and "zero_loss_veto" in proc.stdout and "min_passing_b" in proc.stdout
    plain = subprocess.run([sys.executable, str(RESCORE), "--check-reading", str(REAL_PACKAGE / READINGS["helm1_certified"])],
                           capture_output=True, text=True, timeout=120)
    assert plain.returncode == 2 and "RULE_DESCRIPTION_MISMATCH" in plain.stdout and "WARNING" not in plain.stdout


@pytest.mark.parametrize("name", sorted(T.HISTORICAL_EXCEPTION))
def test_historical_safe_checks_verify_every_original_file_and_never_import_the_checker(name, tmp_path, no_checker):
    anchor = REAL_PACKAGE / T.HISTORICAL_EXCEPTION[name]["anchor"][0]
    code, r = safe(study_of(name), anchor, tmp_path)
    assert r["reject_reasons"] == [] and all(r["checks"][n]["status"] == "PASS" for n in T.SAFE_CHECKS)
    assert code == 3 and r["verdict"] == "RESCORE_INCOMPLETE" and r["label_rederived"] == "NOT_DERIVED"   # NOT_RUN is not OK
    assert_checker_never_ran(r)
    items = r["historical_exception"]["evidence"]
    assert len(items) == 1 + 3 * (1 + 4 + 1)                          # grader reading; per seed: manifest, 4 label files, checkpoints
    assert all(i["status"] in ("MATCH", "RECORDED_DIGESTS_ONLY") for i in items)
    assert sum(i.get("recorded", 0) for i in items) == 15              # 5 checkpoint digests per seed, as recorded
    assert r["historical_exception"]["warning"] == T.WARNING and r["rule"]["applied"] == T.HISTORICAL_RULE


# ================================ HISTORICAL MODE: refusals (sandbox) ================================
def test_the_sandbox_itself_is_accepted(sandbox, tmp_path):
    root = sandbox("helm2_experimental")
    code, r = check(root / READINGS["helm2_experimental"], tmp_path)
    assert code == 4 and r["verdict"] == "HISTORICAL_COMPATIBILITY_OK"     # so every refusal below is caused by its one edit


def _p10(root, seed, fname):
    rel = T.HISTORICAL_EXCEPTION["helm2_experimental"]["receipt_manifests"][seed][0].rsplit("/", 1)[0]
    return root / rel / "collected/results/artifacts" / fname


def _alter_predictions(root):
    path = _p10(root, "20260917", "course_p10_predictions.json")
    path.write_bytes(path.read_bytes() + b" ")


def _alter_scoring(root):
    edit_json(_p10(root, "20260917", "course_p10_scoring.json"), lambda d: d["rows"][0].update(correct=not d["rows"][0]["correct"]))


def _alter_scoring_and_rewrite_manifest(root):                     # the forgery that fooled the frozen grader
    _alter_scoring(root)
    path = _p10(root, "20260917", "course_p10_scoring.json")
    body = path.read_bytes()
    mpath = root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["receipt_manifests"]["20260917"][0]
    edit_json(mpath, lambda m: [r.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body)) for r in m["artifacts"] if r["name"] == "course_p10_scoring.json"])


def _alter_gate(root):
    edit_json(root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["frozen_grader_reading"][0], lambda g: g.update(label="LEARNS_NEW_WORLDS"))


def _plant_checkpoint(root):
    _p10(root, "20260918", "final.pt").write_bytes(b"not the recorded weights")


def _remove(rel_fn):
    return lambda root: rel_fn(root).unlink()


@pytest.mark.parametrize("alter,expected", [
    (_alter_predictions, {"PREDICTIONS_IDENTITY", "HISTORICAL_EVIDENCE_ALTERED"}),
    (_alter_scoring, {"HISTORICAL_EVIDENCE_ALTERED"}),
    (_alter_scoring_and_rewrite_manifest, {"HISTORICAL_EVIDENCE_ALTERED"}),
    (_alter_gate, {"HISTORICAL_EVIDENCE_ALTERED"}),
    (_plant_checkpoint, {"HISTORICAL_EVIDENCE_ALTERED"}),
    (_remove(lambda root: _p10(root, "20260919", "course_p00_scoring.json")), {"HISTORICAL_EVIDENCE_INCOMPLETE"}),
    (_remove(lambda root: root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["receipt_manifests"]["20260918"][0]), {"HISTORICAL_EVIDENCE_INCOMPLETE"}),
    (_remove(lambda root: root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["frozen_grader_reading"][0]), {"HISTORICAL_EVIDENCE_INCOMPLETE"}),
    (_remove(lambda root: root / T.CODE_CLOSURE[3]), {"CHECKER_CODE_IDENTITY"}),
], ids=["altered-predictions", "altered-scoring", "scoring-forgery-with-rewritten-manifest", "altered-frozen-grader-reading",
        "altered-checkpoint", "missing-scoring", "missing-manifest", "missing-frozen-grader-reading", "missing-checker-source"])
def test_altered_or_incomplete_evidence_is_refused_in_historical_mode(alter, expected, sandbox, tmp_path):
    root = sandbox("helm2_experimental")
    alter(root)
    code, r = check(root / READINGS["helm2_experimental"], tmp_path)
    assert code == 2 and r["verdict"] == "REJECT" and expected <= set(codes(r)), r["reject_reasons"]
    assert r["label"] == "VOID_REJECTED"
    code, r = safe(root / _rel(study_of("helm2_experimental")), root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0],
                   tmp_path, safe_only=False)                         # NOT safe_only: the gate itself must stop the import
    assert code == 2 and expected <= set(codes(r)) and r["label_rederived"] == "VOID_REJECTED", r["reject_reasons"]
    assert_checker_never_ran(r)


def test_an_altered_anchor_or_reading_is_unknown_and_refused(sandbox, tmp_path):
    root = sandbox("helm2_experimental")
    anchor = root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0]
    edit_json(anchor, lambda a: a.update(custody=a["custody"] + " "))
    code, r = safe(root / _rel(study_of("helm2_experimental")), anchor, tmp_path, safe_only=False)
    assert code == 2 and codes(r) == ["HISTORICAL_EXCEPTION_UNKNOWN_ANCHOR", "RULE_DESCRIPTION_MISMATCH"]   # off the list, the wrong rule is refused
    assert_checker_never_ran(r)
    code, r = check(root / READINGS["helm2_experimental"], tmp_path)
    assert code == 2 and "READING_EVIDENCE_ALTERED" in codes(r)        # the reading pinned the original anchor
    reading = root / READINGS["helm2_experimental"]
    edit_json(reading, lambda d: d["per_seed"]["20260919"].update(gained=8))
    code, r = check(reading, tmp_path)
    assert code == 2 and "HISTORICAL_EXCEPTION_UNKNOWN_READING" in codes(r)


def test_a_deleted_anchor_is_incomplete_evidence(sandbox, tmp_path):
    root = sandbox("helm1_certified")
    (root / T.HISTORICAL_EXCEPTION["helm1_certified"]["anchor"][0]).unlink()
    code, r = check(root / READINGS["helm1_certified"], tmp_path)
    assert code == 2 and "READING_EVIDENCE_INCOMPLETE" in codes(r)


def test_overrides_and_substitute_readings_are_refused_in_historical_mode(tmp_path, no_checker):
    name = "helm2_experimental"
    anchor, study = REAL_PACKAGE / T.HISTORICAL_EXCEPTION[name]["anchor"][0], study_of(name)
    code, r = safe(study, anchor, tmp_path, safe_only=False, override={"20260917": str(REAL_PACKAGE / "records/typed_pointer_001/receipt_20260917")})
    assert code == 2 and "HISTORICAL_EXCEPTION_REQUIRES_ORIGINAL_EVIDENCE" in codes(r)
    assert_checker_never_ran(r)
    code, r = safe(study, anchor, tmp_path, safe_only=False, compare_frozen=False)
    assert code == 2 and "HISTORICAL_EXCEPTION_REQUIRES_FROZEN_READING" in codes(r)
    assert_checker_never_ran(r)
    other = REAL_PACKAGE / T.HISTORICAL_EXCEPTION["helm1_certified"]["frozen_grader_reading"][0]
    code, r = safe(study, anchor, tmp_path, safe_only=False, frozen_reading=other)
    assert code == 2 and "HISTORICAL_EXCEPTION_REQUIRES_ORIGINAL_EVIDENCE" in codes(r)
    assert_checker_never_ran(r)


def test_an_output_path_that_is_an_original_is_refused_and_nothing_is_written(sandbox, tmp_path):
    root = sandbox("helm2_experimental")
    reading = root / READINGS["helm2_experimental"]
    anchor = root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0]
    before = {p: p.read_bytes() for p in (reading, anchor)}
    assert T.check_reading(reading, reading, historical_compatibility=True) == 2
    assert T.rescore(root / _rel(study_of("helm2_experimental")), anchor, {}, anchor, safe_only=True, historical_compatibility=True) == 2
    assert T.rescore(root / _rel(study_of("helm2_experimental")), anchor, {}, anchor, safe_only=True) == 2
    assert {p: p.read_bytes() for p in (reading, anchor)} == before


# =================================== SLOW (cloud machine) ===================================
@pytest.fixture(scope="module")
def material():
    return T._load_frozen_and_checker()


@slow
@pytest.mark.parametrize("name", sorted(T.HISTORICAL_EXCEPTION))
def test_full_historical_rescore_reproduces_history(name, material, tmp_path):
    entry = T.HISTORICAL_EXCEPTION[name]
    guarded = T.protected_paths()
    before = raw_digests(guarded)
    out = tmp_path / ("historical_reading_%s.json" % name)
    code = T.rescore(study_of(name), REAL_PACKAGE / entry["anchor"][0], {}, out, material=material, historical_compatibility=True)
    r = json.loads(out.read_text(encoding="utf-8"))
    assert raw_digests(guarded) == before
    assert code == 4 and r["verdict"] == "HISTORICAL_COMPATIBILITY_OK" and r["label_rederived"] == entry["label"], r["reject_reasons"]
    assert all(c["status"] == "PASS" for c in r["checks"].values())
    assert all(s["phases"][ph]["rescored"] == 564 and s["phases"][ph]["disagreements"] == 0 for s in r["per_seed"].values() for ph in T.PHASES)
    assert {s: (v["gained"], v["broken"], v["p_one_sided"], v["passed"]) for s, v in r["per_seed"].items()} == REVIEW_DECISIONS[name]
    assert r["historical_exception"]["warning"] == T.WARNING and r["mode"]["name"] == "HISTORICAL_COMPATIBILITY"
