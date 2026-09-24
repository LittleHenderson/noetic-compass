"""trusted_rescore 0.4 -- the explicit historical-compatibility mode, and the trusted-mode refusals around it.

Owner direction 2026-09-24 (item 2, RESCORER): use an explicit historical-compatibility mode for the recognised old
grading-description mistake only; require verified original evidence and apply the preserved historical rule; show
the warning and both rule descriptions; never rewrite the original record; reject unknown, altered, incomplete or
incompatible evidence for trusted acceptance; new runs do not receive the historical exception.

REVISION 1 (review REVIEW_RESCORER_0_4_6e7f62a1.md, commit 4c89e737; coordinator decision 1):
  * A trusted --check-reading is never trusted acceptance: at best READING_CONSISTENT_NOT_RESCORED, exit 5. Forged
    and impossible counts are refused -- tested here with the reviewer's own forgeries.
  * An absent or unverifiable checkpoint weight file is INCOMPLETE evidence in both modes. The 30 weight files of the
    two historical studies are NOT in this checkout, so here the historical mode must refuse them by name: exit 2,
    never 4. The acceptance path is exercised in a sandbox with SIMULATED weights (placeholder files that the test's
    hash stand-in reports under their recorded digests). The real weights are byte-checked only by the AWS tests.
  * --out is create-only and refused before any work.

FAST (always run; pure Python; no checker import -- a guard makes any import of the checker fail at once). Tampering
is done in a SANDBOX: a copy of the package files one historical study needs, with the tool's paths pointed at it, so
no test can ever touch an original record. SLOW / AWS (HELM_RUN_SLOW_TESTS=1, on the cloud machine, with the 30 real
checkpoint weight files bundled at their receipt paths): the historical --check-reading of the four committed
readings (seconds each), and the full 564-record rescore of both historical studies (about 14 minutes each).
"""
import hashlib
import itertools
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
                          reason="full 564-record rescore, about 14 minutes per study, and the real checkpoint weight files; "
                                 "set HELM_RUN_SLOW_TESTS=1 (cloud machine)")
aws_weights = pytest.mark.skipif(os.environ.get("HELM_RUN_SLOW_TESTS") != "1",
                                 reason="needs the 30 real checkpoint weight files of the historical runs; set HELM_RUN_SLOW_TESTS=1 "
                                        "on the cloud machine where they are bundled")
_real_weights_missing = base.historical_weights_missing
without_weights = pytest.mark.skipif(not _real_weights_missing(),
                                     reason="the real checkpoint weight files are present (AWS bundle); the AWS tests below cover this case")

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
ALL_READINGS = [(n, READINGS[n]) for n in sorted(READINGS)] + [(n, AWS_COPIES[n]) for n in sorted(AWS_COPIES)]
_OUT = itertools.count()


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
    out = pathlib.Path(tmp) / ("check_%03d.json" % next(_OUT))          # --out is create-only: a new name every time
    code = T.check_reading(path, out, historical_compatibility=compat)
    return code, json.loads(out.read_text(encoding="utf-8"))


def safe(study, anchor, tmp, compat=True, **kw):
    out = pathlib.Path(tmp) / ("reading_%03d.json" % next(_OUT))
    code = T.rescore(study, anchor, kw.pop("override", {}), out, safe_only=kw.pop("safe_only", True), historical_compatibility=compat, **kw)
    return code, json.loads(out.read_text(encoding="utf-8"))


def assert_checker_never_ran(record):
    assert record["imported_checker_code"] is False
    assert all(record["checks"][n]["status"] == "NOT_RUN" for n in T.CHECKER_CHECKS)


def checkpoint_items(record):
    return [i for i in record["historical_exception"]["evidence"] if "byte_checked" in i]


def study_of(name, package=REAL_PACKAGE):
    anchor = json.loads((package / T.HISTORICAL_EXCEPTION[name]["anchor"][0]).read_text(encoding="utf-8"))
    return package / anchor["study"]["path"]


def _sandbox_rels(name):
    entry = T.HISTORICAL_EXCEPTION[name]
    rels = list(T.CODE_CLOSURE) + ["records/typed_pointer_001/evaluate_gates.py", entry["anchor"][0], entry["reading"][0],
                                    AWS_COPIES[name], entry["frozen_grader_reading"][0], _rel(study_of(name))]
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


def _placeholder(where, name):
    return ("SIMULATED placeholder for %s / %s -- not the real weights" % (where, name)).encode("utf-8")


@pytest.fixture()
def simulated_weights(monkeypatch):
    """SIMULATES present, matching checkpoint weight files in a sandbox copy of a historical study. It plants a
    placeholder for every weight file the frozen run manifests record, and makes the tool's raw hash report the
    RECORDED digest for exactly those placeholder bytes at exactly those paths; any other bytes are hashed for real
    (so an altered or missing placeholder is still caught). This lets the fast tests reach the acceptance path. It
    proves nothing about the real weights: those are byte-checked only by the AWS tests below."""
    table, real = {}, T._raw_sha_stream

    def recorded_digest_for_placeholders(path):
        hit = table.get(os.path.normcase(str(pathlib.Path(path).resolve())))
        if hit is not None and pathlib.Path(path).read_bytes() == hit[0]:
            return hit[1], hit[2]
        return real(path)
    monkeypatch.setattr(T, "_raw_sha_stream", recorded_digest_for_placeholders)

    def plant(root, name):
        for mrel, _ in T.HISTORICAL_EXCEPTION[name]["receipt_manifests"].values():
            art = root / mrel.rsplit("/", 1)[0] / "collected/results/artifacts"
            for row in json.loads((root / mrel).read_text(encoding="utf-8"))["artifacts"]:
                if row["name"].endswith(T.CHECKPOINT_SUFFIX):
                    body = _placeholder(mrel, row["name"])
                    (art / row["name"]).write_bytes(body)
                    table[os.path.normcase(str((art / row["name"]).resolve()))] = (body, row["sha256"], row["bytes"])
        return root
    return plant


@pytest.fixture()
def accepted(sandbox, simulated_weights):
    """A sandbox copy of one historical study with SIMULATED matching weights: the historical mode accepts it."""
    return lambda name: simulated_weights(sandbox(name), name)


def _rel(path):
    return pathlib.Path(path).resolve().relative_to(REAL_PACKAGE.resolve()).as_posix()


def edit_json(path, change):
    d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    change(d)
    pathlib.Path(path).write_text(json.dumps(d, indent=1, sort_keys=True), encoding="utf-8")


def _write(tmp, body):
    path = pathlib.Path(tmp) / ("reading_in_%03d.json" % next(_OUT))
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


# ================================ FROZEN CONSTANTS ================================
def test_the_frozen_constants_match_their_digests_and_the_reviewed_rule():
    assert T.TOOL_VERSION == "0.4" and T.TOOL_REVISION == 1 and T.constants_problems() == []
    assert T.HISTORICAL_RULE == REVIEW_RULE and T.HISTORICAL_RULE["zero_loss_veto"] is False
    canon = lambda v: json.dumps(v, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(canon(REVIEW_RULE)).hexdigest() == T.HISTORICAL_RULE_SHA256
    wrong = T.RECOGNISED_MISTAKE["recorded_description"]
    assert hashlib.sha256(canon(wrong)).hexdigest() == T.RECOGNISED_MISTAKE["recorded_description_sha256"]
    assert hashlib.sha256(canon(T.RECOGNISED_MISTAKE)).hexdigest() == T.RECOGNISED_MISTAKE_SHA256     # revision 1: every field
    for entry in T.HISTORICAL_EXCEPTION.values():                      # the recognised mistake IS what both anchors record
        assert json.loads((REAL_PACKAGE / entry["anchor"][0]).read_text(encoding="utf-8"))["pass_rule"] == wrong
    assert wrong["broken_must_be"] == 0 and wrong["min_passing_b"] == 7    # the zero-loss veto and the 7-gain minimum


def test_the_decision_reads_every_threshold_from_the_hashed_rule(monkeypatch):
    """Review MINOR 4: there is no second copy of a threshold, so any change to the rule shows as TOOL_CONSTANTS_ALTERED."""
    assert not hasattr(T, "MIN_IMPROVED_KINDS") and not hasattr(T, "MIN_IMPROVED_WORLDS")
    assert T.historical_decision(12, 0, 1, 2)[1] is False and T.historical_decision(12, 0, 2, 2)[1] is True
    monkeypatch.setattr(T, "HISTORICAL_RULE", dict(REVIEW_RULE, min_improved_kinds=1))
    assert T.historical_decision(12, 0, 1, 2)[1] is True and T.constants_problems() == ["HISTORICAL_RULE"]
    monkeypatch.setattr(T, "HISTORICAL_RULE", dict(REVIEW_RULE, zero_loss_veto=True))
    assert T.historical_decision(11, 1, 3, 5)[1] is False and T.constants_problems() == ["HISTORICAL_RULE"]
    monkeypatch.setattr(T, "HISTORICAL_RULE", dict(REVIEW_RULE, all_seeds_must_pass=False))
    with pytest.raises(ValueError):
        T.historical_label([True, False])


def test_every_field_of_the_recognised_mistake_is_hashed(monkeypatch):
    monkeypatch.setattr(T, "RECOGNISED_MISTAKE", dict(T.RECOGNISED_MISTAKE, written_by_tool_sha256_lf="0" * 64))
    assert T.constants_problems() == ["RECOGNISED_MISTAKE"]


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


def test_new_anchors_are_written_with_the_preserved_rule_and_the_run_evidence(new_run):
    a = _new_run(new_run)
    assert a["schema"] == T.ANCHOR_SCHEMA and a["tool_version"] == "0.4" and a["tool_revision"] == T.TOOL_REVISION
    assert a["pass_rule"] == T.HISTORICAL_RULE and a["pass_rule_sha256"] == T.HISTORICAL_RULE_SHA256
    evidence = a["seeds"][base.CERTIFIED_SEED]["run_evidence"]
    assert evidence["manifest"]["pin"]["sha256_lf"] and sorted(evidence["checkpoints"]) == sorted(base.PLACEHOLDER_CHECKPOINTS)


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


# ---- review BLOCKER 1: a trusted --check-reading is never trusted acceptance ----
RECEIPT_OF = {("helm1_certified", "20260918"): "receipt_helm1_certified_20260918", ("helm2_experimental", "20260919"): "receipt_20260919"}


def _gate_for(name, seed):
    """One historical seed of the frozen grader reading, as a one-seed frozen grader reading for a NEW run."""
    gate = json.loads((REAL_PACKAGE / T.HISTORICAL_EXCEPTION[name]["frozen_grader_reading"][0]).read_text(encoding="utf-8"))
    g = gate["seeds"][seed]["G_LEARN_population"]
    return {"label": "LEARNS_NEW_WORLDS" if g["passed"] else "NO_TRANSFER_TO_NEW_WORLDS", "seeds": {seed: {"G_LEARN_population": g}}}


@pytest.fixture()
def trusted_run(no_checker):
    """A NEW one-seed run built from one historical seed's four label files (plus its own run manifest and placeholder
    checkpoints), with a fresh 0.4 anchor and a one-seed frozen grader reading beside its study."""
    made = []

    def build(name, seed):
        tmp = base._make_sandbox(HERE / RECEIPT_OF[(name, seed)] / "collected/results/artifacts", seed, study_of(name))
        made.append(tmp)
        study = json.loads((tmp / "study.json").read_text(encoding="utf-8"))
        study["jobs"] = [dict(j, receipt_dir=str(tmp / "receipt")) for j in study["jobs"]]     # no override needed
        (tmp / "study.json").write_text(json.dumps(study), encoding="utf-8")
        anchor = T.safe_anchor_part(tmp / "study.json", {})
        part = base._course_part_without_loading()                     # both studies share one course and population
        anchor["checker"]["profile_digest"] = part.pop("profile_digest")
        anchor.update(part)
        (tmp / "anchor.json").write_text(json.dumps(anchor), encoding="utf-8")
        (tmp / "gate_reading.json").write_text(json.dumps(_gate_for(name, seed), indent=1), encoding="utf-8")
        return tmp
    yield build
    for tmp in made:
        shutil.rmtree(tmp, ignore_errors=True)


def _clean_reading(tmp, name, seed):
    """What a clean 0.4 revision-1 trusted RESCORE_OK reading of this new run looks like, built BY HAND from the frozen
    grader's counts (a real one needs the course loaded: cloud only). Its frame is a real trusted safe-only run."""
    _, shell = safe(tmp / "study.json", tmp / "anchor.json", tmp, compat=False)
    assert shell["reject_reasons"] == [] and shell["checks"]["RUN_EVIDENCE"]["status"] == "PASS", shell["reject_reasons"]
    anchor = json.loads((tmp / "anchor.json").read_text(encoding="utf-8"))
    g = _gate_for(name, seed)["seeds"][seed]["G_LEARN_population"]
    recorded = json.loads((REAL_PACKAGE / READINGS[name]).read_text(encoding="utf-8"))["per_seed"][seed]
    s = {"gained": g["wrong_to_right"], "broken": g["right_to_wrong"], "kinds_improved": g["improved_kinds"],
         "world_ids_improved": g["improved_worlds"], "worlds_improved": len(g["improved_worlds"]),
         "p_one_sided": g["p_one_sided"], "p_float": g["p_float"], "passed": g["passed"],
         "frozen_18_before": recorded["frozen_18_before"], "frozen_18_after": recorded["frozen_18_after"],
         "receipt_dir": anchor["seeds"][seed]["receipt_dir"], "receipt_resolved_from": "absolute-path-in-study",
         "phases": {ph: {"predictions_sha256_lf": anchor["seeds"][seed]["predictions"][ph]["sha256_lf"], "rescored": 564,
                         "scoring_rows_compared": 564, "disagreements": 0, "scoring_file_present": True} for ph in T.PHASES}}
    gate = tmp / "gate_reading.json"
    checks = {k: {"status": "NOT_REQUESTED" if k in T.TRUSTED_NOT_REQUESTED else "PASS", "detail": ""} for k in shell["checks"]}
    label = "LEARNS_NEW_WORLDS" if g["passed"] else "NO_TRANSFER_TO_NEW_WORLDS"
    return dict(shell, verdict="RESCORE_OK", reject_reasons=[], label_rederived=label, checks=checks, imported_checker_code=True,
                material_supplied_by_caller=False, per_seed={seed: s},
                comparison_with_frozen_grader={"requested": True, "frozen_reading_present": True, "frozen_reading_path": T._rel(gate),
                                               "frozen_reading_pin": T.file_pin(gate), "frozen_label": label, "labels_agree": True})


def test_a_trusted_check_reading_is_never_trusted_acceptance(trusted_run, tmp_path):
    tmp = trusted_run("helm1_certified", "20260918")
    path = _write(tmp_path, _clean_reading(tmp, "helm1_certified", "20260918"))
    code, r = check(path, tmp_path, compat=False)
    assert code == 5 and r["verdict"] == "READING_CONSISTENT_NOT_RESCORED" and r["reject_reasons"] == [], r["reject_reasons"]
    assert r["label"] == "NOT_DERIVED" and r["label_replayed_from_recorded_counts"] == "LEARNS_NEW_WORLDS"
    assert r["trusted_acceptance"] is False and r["rescored"] is False and "NOTHING WAS RESCORED" in r["boundary"]
    assert r["frozen_grader"]["per_seed"]["20260918"]["agree"] is True
    assert all(c["status"] in ("PASS", "NOT_REQUESTED") for c in r["checks"].values())
    proc = subprocess.run([sys.executable, str(RESCORE), "--check-reading", str(path)], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 5 and "NOT A RESCORE" in proc.stdout       # never 0, which only a full rescore gives
    code, r = check(path, tmp_path, compat=True)                          # a new run never gets the exception
    assert code == 2 and "HISTORICAL_EXCEPTION_UNKNOWN_READING" in codes(r)


def test_forged_counts_for_a_run_that_truly_fails_never_exit_0(trusted_run, tmp_path):
    """The reviewer's scenario. Helm 2.0 seed 20260919's four label files as a NEW run: the truth is 7 gains, 1 loss,
    p = 9/256, FAIL. The 0.4 tool before revision 1 gave a hand-written 12/0 reading exit 0 and LEARNS_NEW_WORLDS."""
    tmp = trusted_run("helm2_experimental", "20260919")
    honest = _clean_reading(tmp, "helm2_experimental", "20260919")
    code, r = check(_write(tmp_path, honest), tmp_path, compat=False)
    assert code == 5 and r["label_replayed_from_recorded_counts"] == "NO_TRANSFER_TO_NEW_WORLDS", r["reject_reasons"]
    s = honest["per_seed"]["20260919"]
    forged_seed = dict(s, gained=12, broken=0, p_one_sided="1/4096", p_float=1 / 4096, passed=True, frozen_18_after=s["frozen_18_before"] + 12)
    forged = dict(honest, per_seed={"20260919": forged_seed}, label_rederived="LEARNS_NEW_WORLDS")
    code, r = check(_write(tmp_path, forged), tmp_path, compat=False)
    assert code == 2 and set(codes(r)) == {"FROZEN_GRADER_DISAGREES"} and r["label"] == "VOID_REJECTED", r["reject_reasons"]
    # THE LIMIT, stated plainly: a forger who writes the reading AND a matching frozen grader reading gets a consistent
    # reading -- and still never trusted acceptance: exit 5, label NOT_DERIVED. Only a full rescore gives exit 0.
    fake = tmp / "forged_gate_reading.json"
    g = dict(_gate_for("helm2_experimental", "20260919")["seeds"]["20260919"]["G_LEARN_population"],
             wrong_to_right=12, right_to_wrong=0, p_one_sided="1/4096", passed=True)
    fake.write_text(json.dumps({"label": "LEARNS_NEW_WORLDS", "seeds": {"20260919": {"G_LEARN_population": g}}}), encoding="utf-8")
    both = dict(forged, comparison_with_frozen_grader=dict(honest["comparison_with_frozen_grader"], frozen_reading_path=T._rel(fake),
                                                            frozen_reading_pin=T.file_pin(fake)))
    code, r = check(_write(tmp_path, both), tmp_path, compat=False)
    assert code == 5 and r["label"] == "NOT_DERIVED" and r["trusted_acceptance"] is False


def _seed_edit(change):
    def edit(body):
        (seed, s), = body["per_seed"].items()
        return dict(body, per_seed={seed: change(dict(s))})
    return edit


_P10 = lambda s, **kw: dict(s, phases=dict(s["phases"], course_p10=dict(s["phases"]["course_p10"], **kw)))
DEFECTS = {
    # impossible or incomplete counts (the reviewer's four, and their neighbours)
    "99-gains-in-an-18-question-population": (_seed_edit(lambda s: dict(s, gained=99)), "READING_INCONSISTENT"),
    "one-kind-counted-twice": (_seed_edit(lambda s: dict(s, kinds_improved=["reach", "reach"])), "READING_INCONSISTENT"),
    "no-p_one_sided": (_seed_edit(lambda s: {k: v for k, v in s.items() if k != "p_one_sided"}), "READING_INCOMPLETE"),
    "a-kind-outside-the-population": (_seed_edit(lambda s: dict(s, kinds_improved=sorted(s["kinds_improved"] + ["flying"]))), "READING_INCONSISTENT"),
    "more-worlds-than-gains": (_seed_edit(lambda s: dict(s, worlds_improved=s["gained"] + 1)), "READING_INCONSISTENT"),
    "before-and-after-do-not-add-up": (_seed_edit(lambda s: dict(s, frozen_18_after=s["frozen_18_after"] + 1)), "READING_INCONSISTENT"),
    "a-phase-not-fully-rescored": (_seed_edit(lambda s: _P10(s, rescored=500, scoring_rows_compared=500)), "READING_INCONSISTENT"),
    "a-wrong-p": (_seed_edit(lambda s: dict(s, p_one_sided="1/2")), "READING_DECISION_MISMATCH"),
    "a-flipped-decision": (_seed_edit(lambda s: dict(s, passed=not s["passed"])), "READING_DECISION_MISMATCH"),
    "a-receipt-that-is-not-the-anchors": (_seed_edit(lambda s: dict(s, receipt_dir="records/typed_pointer_001/receipt_20260918")), "READING_INCONSISTENT"),
    # the recorded checks and the reading as a whole
    "no-checks-at-all": (lambda b: dict(b, checks={}), "READING_NOT_CLEAN"),
    "a-check-not-run": (lambda b: dict(b, checks=dict(b["checks"], SCORING_FILE_AGREEMENT={"status": "NOT_RUN", "detail": ""})), "READING_NOT_CLEAN"),
    "no-frozen-grader-comparison": (lambda b: dict(b, checks=dict(b["checks"], FROZEN_GRADER_AGREEMENT={"status": "NOT_REQUESTED", "detail": ""})), "READING_NOT_CLEAN"),
    "no-run-evidence-check": (lambda b: dict(b, checks={k: v for k, v in b["checks"].items() if k != "RUN_EVIDENCE"}), "READING_NOT_CLEAN"),
    "the-checker-never-ran": (lambda b: dict(b, imported_checker_code=False), "READING_NOT_CLEAN"),
    "an-unclean-verdict": (lambda b: dict(b, verdict="RESCORE_INCOMPLETE"), "READING_NOT_CLEAN"),
    "a-historical-mode": (lambda b: dict(b, mode={"name": T.HISTORICAL, "flag": T.HISTORICAL_FLAG, "requested_explicitly": True}), "READING_NOT_TRUSTED"),
    "a-wrong-rule": (lambda b: dict(b, rule=dict(b["rule"], recorded_in_anchor=T.RECOGNISED_MISTAKE["recorded_description"])), "RULE_DESCRIPTION_MISMATCH"),
    "written-before-revision-1": (lambda b: {k: v for k, v in b.items() if k != "tool_revision"}, "READING_INCOMPLETE"),
    "no-pinned-frozen-grader-reading": (lambda b: dict(b, comparison_with_frozen_grader={k: v for k, v in b["comparison_with_frozen_grader"].items()
                                                                                      if k != "frozen_reading_pin"}), "READING_INCOMPLETE"),
    "an-anchor-path-that-is-an-object": (lambda b: dict(b, anchor=dict(b["anchor"], path={"x": 1})), "READING_MALFORMED"),
}


def test_every_forged_impossible_or_incomplete_trusted_reading_is_refused_by_name(trusted_run, tmp_path):
    tmp = trusted_run("helm2_experimental", "20260919")
    clean = _clean_reading(tmp, "helm2_experimental", "20260919")
    wrong = []
    for name, (change, expected) in DEFECTS.items():
        code, r = check(_write(tmp_path, change(clean)), tmp_path, compat=False)
        if not (code == 2 and expected in codes(r) and r["label"] == "VOID_REJECTED"):
            wrong.append((name, code, r["reject_reasons"][:3]))
    assert wrong == []


def test_a_trusted_check_reading_rechecks_the_evidence_on_disk(trusted_run, tmp_path):
    tmp = trusted_run("helm1_certified", "20260918")
    path = _write(tmp_path, _clean_reading(tmp, "helm1_certified", "20260918"))
    gate = tmp / "gate_reading.json"
    kept = gate.read_bytes()
    edit_json(gate, lambda g: g.update(label="NO_TRANSFER_TO_NEW_WORLDS"))  # the frozen grader reading changed after the pin
    code, r = check(path, tmp_path, compat=False)
    assert code == 2 and codes(r) == ["READING_EVIDENCE_ALTERED"]
    gate.write_bytes(kept)
    (tmp / "receipt/collected/results/artifacts/final.pt").unlink()      # a checkpoint weight file went missing
    code, r = check(path, tmp_path, compat=False)
    assert code == 2 and codes(r) == ["RUN_EVIDENCE_INCOMPLETE"] and r["checks"]["ANCHOR_EVIDENCE"]["status"] == "FAIL"


def test_an_out_that_appears_during_the_run_is_never_overwritten(trusted_run, tmp_path, monkeypatch):
    tmp = trusted_run("helm1_certified", "20260918")
    path = _write(tmp_path, _clean_reading(tmp, "helm1_certified", "20260918"))
    out = tmp_path / "late.json"
    original = T._check_reading_body

    def body_then_someone_writes_the_out(*a, **k):
        label = original(*a, **k)
        out.write_text("written by someone else", encoding="utf-8")
        return label
    monkeypatch.setattr(T, "_check_reading_body", body_then_someone_writes_the_out)
    assert T.check_reading(path, out) == 2 and out.read_text(encoding="utf-8") == "written by someone else"


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
    # review MINOR 5: a field of the wrong type is refused by name, never a crash (it was a TypeError, exit 1)
    (tmp_path / "r.json").write_text(json.dumps(dict(original, anchor=dict(original["anchor"], path={"x": 1}))), encoding="utf-8")
    for compat in (False, True):
        code, r = check(tmp_path / "r.json", tmp_path, compat=compat)
        assert code == 2 and codes(r) == ["READING_MALFORMED"], r["reject_reasons"]


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


@without_weights
def test_write_anchor_for_a_historical_study_is_refused_here_because_the_weights_are_absent(tmp_path, no_checker):
    """Coordinator decision 1: a fresh anchor pins only byte-checked weights. Here they are absent, so it is refused
    before anything is loaded; on AWS, with the weights bundled, the same command writes the anchor."""
    new = tmp_path / "fresh_anchor.json"
    assert T.write_anchor(study_of("helm1_certified"), new, {}) == 2 and not new.exists()


# ================================ HISTORICAL MODE WITHOUT THE WEIGHTS (this checkout) ================================
@without_weights
@pytest.mark.parametrize("name,rel", ALL_READINGS)
def test_without_the_weights_the_historical_mode_refuses_each_by_name_and_still_replays_the_six_decisions(name, rel, tmp_path, no_checker):
    """Coordinator decision 1 (review MAJOR 2). Before revision 1 this gave PASS and exit 4 with 15 of 15 weight
    files absent. Now each absent file is refused by name: exit 2, never 4. The replay still runs and agrees."""
    guarded = T.protected_paths(REAL_PACKAGE / rel)
    before = raw_digests(guarded)
    code, r = check(REAL_PACKAGE / rel, tmp_path)
    assert raw_digests(guarded) == before and r["originals"]["unchanged"] is True        # the originals are byte-unchanged
    assert code == 2 and r["verdict"] == "REJECT" and r["label"] == "VOID_REJECTED"
    assert len(r["reject_reasons"]) == 15 and all(x.startswith("HISTORICAL_EVIDENCE_INCOMPLETE:") and "is absent here" in x
                                                  for x in r["reject_reasons"])
    named = {(x.split("seed ")[1][:8], x.split("weight file ")[1].split(" ")[0]) for x in r["reject_reasons"]}
    assert len(named) == 15                                                               # every weight file named once
    assert {c: v["status"] for c, v in r["checks"].items() if v["status"] != "PASS"} == {"HISTORICAL_EVIDENCE": "FAIL"}
    assert [i["status"] for i in checkpoint_items(r)] == ["INCOMPLETE"] * 3               # never MATCH, never "digests only"
    for seed, (b, c, p, passed) in REVIEW_DECISIONS[name].items():
        row = r["decisions"][seed]
        assert row["agree"] is True and row["frozen_grader"]["passed"] is passed
        assert {k: row["replay_with_the_preserved_rule"][k] for k in ("gained", "broken", "p_one_sided", "passed")} == \
            {"gained": b, "broken": c, "p_one_sided": p, "passed": passed}


@without_weights
def test_the_warning_and_both_descriptions_are_printed_through_the_command_line():
    proc = subprocess.run([sys.executable, str(RESCORE), T.HISTORICAL_FLAG, "--check-reading", str(REAL_PACKAGE / READINGS["helm1_certified"])],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2 and "HISTORICAL_EVIDENCE_INCOMPLETE" in proc.stdout    # the weights are not in this checkout
    assert "WARNING: HISTORICAL-COMPATIBILITY MODE" in proc.stdout
    assert "recorded in the original record (WRONG)" in proc.stdout and "preserved historical rule (APPLIED)" in proc.stdout
    assert "broken_must_be" in proc.stdout and "zero_loss_veto" in proc.stdout and "min_passing_b" in proc.stdout
    plain = subprocess.run([sys.executable, str(RESCORE), "--check-reading", str(REAL_PACKAGE / READINGS["helm1_certified"])],
                           capture_output=True, text=True, timeout=120)
    assert plain.returncode == 2 and "RULE_DESCRIPTION_MISMATCH" in plain.stdout and "WARNING" not in plain.stdout


# ================================ HISTORICAL MODE WITH EVERY WEIGHT FILE (simulated here; real on AWS) ================================
@pytest.mark.parametrize("name,rel", ALL_READINGS)
def test_with_every_weight_file_present_the_historical_mode_reproduces_the_six_decisions(name, rel, accepted, tmp_path):
    root = accepted(name)
    guarded = T.protected_paths(root / rel)
    before = raw_digests(guarded)
    code, r = check(root / rel, tmp_path)
    assert raw_digests(guarded) == before and r["originals"]["unchanged"] is True        # the originals are byte-unchanged
    assert code == 4 and r["verdict"] == "HISTORICAL_COMPATIBILITY_OK" and r["reject_reasons"] == []
    assert all(c["status"] == "PASS" for c in r["checks"].values())
    assert r["mode"] == {"name": "HISTORICAL_COMPATIBILITY", "flag": "--historical-compatibility", "requested_explicitly": True}
    entry = T.HISTORICAL_EXCEPTION[name]
    assert r["label"] == entry["label"] and r["historical_exception"]["entry"] == name and r["trusted_acceptance"] is False
    assert [i["status"] for i in checkpoint_items(r)] == ["MATCH"] * 3 and sum(i["byte_checked"] for i in checkpoint_items(r)) == 15
    assert "31 files byte-checked, including 15 of 15 recorded checkpoint weight files" in r["checks"]["HISTORICAL_EVIDENCE"]["detail"]
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


def test_the_recognised_mistake_changed_one_recorded_seed_decision_and_the_mode_rederives_it(accepted, tmp_path):
    root = accepted("helm2_experimental")
    code, r = check(root / READINGS["helm2_experimental"], tmp_path)
    changed = {s: row for s, row in r["decisions"].items() if row["recorded_decision_differs_from_history"]}
    assert code == 4 and sorted(changed) == ["20260917"]             # 11 gains, 1 loss: the 0.2 record says False
    row = changed["20260917"]
    assert row["decision_recorded_in_the_original_record"] is False and row["what_the_wrong_description_gives"] is False
    assert row["replay_with_the_preserved_rule"]["passed"] is True and row["frozen_grader"]["passed"] is True
    assert r["label"] == "NO_TRANSFER_TO_NEW_WORLDS"                  # unaffected: seed 20260919 (7/1, p 9/256) fails either way


@pytest.mark.parametrize("name", sorted(T.HISTORICAL_EXCEPTION))
def test_historical_safe_checks_verify_every_original_file_and_never_import_the_checker(name, accepted, tmp_path):
    root = accepted(name)
    code, r = safe(root / _rel(study_of(name)), root / T.HISTORICAL_EXCEPTION[name]["anchor"][0], tmp_path)
    assert r["reject_reasons"] == [] and all(r["checks"][n]["status"] == "PASS" for n in T.SAFE_CHECKS if n != "RUN_EVIDENCE")
    assert r["checks"]["RUN_EVIDENCE"] == T.NOT_REQUESTED_HISTORICAL                     # HISTORICAL_EVIDENCE covers it here
    assert code == 3 and r["verdict"] == "RESCORE_INCOMPLETE" and r["label_rederived"] == "NOT_DERIVED"   # NOT_RUN is not OK
    assert_checker_never_ran(r)
    items = r["historical_exception"]["evidence"]
    assert len(items) == 1 + 3 * (1 + 4 + 1)                          # grader reading; per seed: manifest, 4 label files, checkpoints
    assert all(i["status"] == "MATCH" for i in items)
    assert sum(i.get("recorded", 0) for i in items) == 15 and sum(i.get("byte_checked", 0) for i in items) == 15
    assert r["historical_exception"]["warning"] == T.WARNING and r["rule"]["applied"] == T.HISTORICAL_RULE


# ================================ HISTORICAL MODE: refusals (sandbox) ================================
def test_the_sandbox_itself_is_accepted_and_without_the_weights_is_refused_only_for_them(sandbox, simulated_weights, tmp_path):
    root = sandbox("helm2_experimental")
    code, r = check(root / READINGS["helm2_experimental"], tmp_path)
    assert code == 2 and len(r["reject_reasons"]) == 15 and set(codes(r)) == {"HISTORICAL_EVIDENCE_INCOMPLETE"}
    simulated_weights(root, "helm2_experimental")
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
    (_remove(lambda root: _p10(root, "20260918", "final.pt")), {"HISTORICAL_EVIDENCE_INCOMPLETE"}),
    (_remove(lambda root: _p10(root, "20260919", "course_p00_scoring.json")), {"HISTORICAL_EVIDENCE_INCOMPLETE"}),
    (_remove(lambda root: root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["receipt_manifests"]["20260918"][0]), {"HISTORICAL_EVIDENCE_INCOMPLETE"}),
    (_remove(lambda root: root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["frozen_grader_reading"][0]), {"HISTORICAL_EVIDENCE_INCOMPLETE"}),
    (_remove(lambda root: root / T.CODE_CLOSURE[3]), {"CHECKER_CODE_IDENTITY"}),
], ids=["altered-predictions", "altered-scoring", "scoring-forgery-with-rewritten-manifest", "altered-frozen-grader-reading",
        "altered-checkpoint", "missing-checkpoint", "missing-scoring", "missing-manifest", "missing-frozen-grader-reading",
        "missing-checker-source"])
def test_altered_or_incomplete_evidence_is_refused_in_historical_mode(alter, expected, accepted, tmp_path):
    root = accepted("helm2_experimental")
    alter(root)
    code, r = check(root / READINGS["helm2_experimental"], tmp_path)
    assert code == 2 and r["verdict"] == "REJECT" and expected <= set(codes(r)), r["reject_reasons"]
    assert r["label"] == "VOID_REJECTED"
    code, r = safe(root / _rel(study_of("helm2_experimental")), root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0],
                   tmp_path, safe_only=False)                         # NOT safe_only: the gate itself must stop the import
    assert code == 2 and expected <= set(codes(r)) and r["label_rederived"] == "VOID_REJECTED", r["reject_reasons"]
    assert_checker_never_ran(r)


def test_a_partly_present_seed_is_incomplete_never_match(accepted, tmp_path):
    """Review MAJOR 2: a seed with some weight files present and some absent was labelled MATCH."""
    root = accepted("helm2_experimental")
    _p10(root, "20260918", "final.pt").unlink()
    code, r = safe(root / _rel(study_of("helm2_experimental")), root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0], tmp_path)
    assert code == 2 and codes(r) == ["HISTORICAL_EVIDENCE_INCOMPLETE"] and "final.pt" in r["reject_reasons"][0]
    by_seed = {i["what"][-8:]: i for i in checkpoint_items(r)}
    assert {s: i["status"] for s, i in by_seed.items()} == {"20260917": "MATCH", "20260918": "INCOMPLETE", "20260919": "MATCH"}
    assert by_seed["20260918"]["matching"] == 4 and by_seed["20260918"]["absent"] == ["final.pt"]


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


# ================================ --out IS CREATE-ONLY (review MAJOR 3) ================================
def test_an_output_path_that_is_an_original_is_refused_and_nothing_is_written(sandbox, tmp_path):
    root = sandbox("helm2_experimental")
    reading = root / READINGS["helm2_experimental"]
    anchor = root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0]
    before = {p: p.read_bytes() for p in (reading, anchor)}
    assert T.check_reading(reading, reading, historical_compatibility=True) == 2
    assert T.rescore(root / _rel(study_of("helm2_experimental")), anchor, {}, anchor, safe_only=True, historical_compatibility=True) == 2
    assert T.rescore(root / _rel(study_of("helm2_experimental")), anchor, {}, anchor, safe_only=True) == 2
    assert {p: p.read_bytes() for p in (reading, anchor)} == before


def test_every_existing_out_is_refused_by_name_before_any_work(sandbox, tmp_path, monkeypatch, capsys):
    """The paths the old guard missed: the AWS copies of the historical readings, the study files, the grader, a checker
    source, the tool itself -- and any other existing file. Refused before any work; the bytes are unchanged."""
    root = sandbox("helm2_experimental")
    here = root / "records/typed_pointer_001"
    shutil.copyfile(RESCORE, here / "trusted_rescore.py")               # a sandbox copy of the tool, as a target only
    reading, anchor = root / READINGS["helm2_experimental"], root / T.HISTORICAL_EXCEPTION["helm2_experimental"]["anchor"][0]
    study = root / _rel(study_of("helm2_experimental"))
    plain = tmp_path / "exists.json"
    plain.write_text("{}", encoding="utf-8")
    targets = [root / AWS_COPIES["helm2_experimental"], study, here / "evaluate_gates.py", root / T.CODE_CLOSURE[3],
               here / "trusted_rescore.py", plain]

    def no_work(*a, **k):
        raise AssertionError("work started before the --out refusal")
    for name in ("snapshot", "_safe_checks", "_check_reading_body"):
        monkeypatch.setattr(T, name, no_work)
    for target in targets:
        before = target.read_bytes()
        for compat in (True, False):
            assert T.check_reading(reading, target, historical_compatibility=compat) == 2
            assert T.rescore(study, anchor, {}, target, safe_only=True, historical_compatibility=compat) == 2
        assert target.read_bytes() == before, target
        out = capsys.readouterr().out
        assert out.count("nothing was done and nothing was written") == 4 and ("OUTPUT_EXISTS" in out or "OUTPUT_WOULD_OVERWRITE_ORIGINAL" in out)


def test_a_deleted_original_and_a_hard_link_are_refused(sandbox, tmp_path):
    root = sandbox("helm1_certified")
    reading = root / READINGS["helm1_certified"]
    before = reading.read_bytes()
    gate = root / T.HISTORICAL_EXCEPTION["helm1_certified"]["frozen_grader_reading"][0]
    gate.unlink()
    assert T.check_reading(reading, gate, historical_compatibility=True) == 2 and not gate.exists()   # still an original
    link = tmp_path / "link.json"
    try:
        os.link(reading, link)
    except OSError:
        return                                                          # no hard links on this file system: nothing to test
    assert T.check_reading(reading, link, historical_compatibility=True) == 2 and reading.read_bytes() == before


def test_write_output_is_create_only(tmp_path):
    kept = tmp_path / "kept.json"
    kept.write_text("keep", encoding="utf-8")
    assert T._write_output(kept, {"a": 1}) is False and kept.read_text(encoding="utf-8") == "keep"
    assert T._write_output(tmp_path / "new.json", {"a": 1}) is True and json.loads((tmp_path / "new.json").read_text(encoding="utf-8")) == {"a": 1}


def test_the_command_line_refuses_an_existing_out_and_usage_errors_exit_64(tmp_path):
    existing = tmp_path / "exists.json"
    existing.write_text("keep", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(RESCORE), "--check-reading", str(REAL_PACKAGE / READINGS["helm1_certified"]), "--out", str(existing)],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2 and "OUTPUT_EXISTS" in proc.stdout and existing.read_text(encoding="utf-8") == "keep"
    proc = subprocess.run([sys.executable, str(RESCORE), "--check-reading", "x.json", "--study", "y.json"], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 64 and "USAGE_ERROR" in proc.stderr       # review MINOR 5: a usage error is not REJECT (2)
    proc = subprocess.run([sys.executable, str(RESCORE), "--study", str(study_of("helm1_certified")), "--receipt", "no-equals-sign", "--safe-only"],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 64 and "seed=dir" in proc.stderr          # it was a ValueError crash


# =================================== SLOW / AWS (cloud machine) ===================================
@aws_weights
@pytest.mark.parametrize("name,rel", ALL_READINGS)
def test_with_the_real_weights_the_historical_check_reading_gives_exit_4(name, rel, tmp_path, no_checker):
    """AWS: the 30 real checkpoint weight files must be bundled at their receipt paths. Seconds; no course load.
    A missing weight file FAILS this test (it does not skip): an unbundled job must not look like a pass."""
    assert _real_weights_missing() == [], "bundle the real checkpoint weight files first"
    code, r = check(REAL_PACKAGE / rel, tmp_path)
    assert code == 4 and r["verdict"] == "HISTORICAL_COMPATIBILITY_OK" and r["reject_reasons"] == [], r["reject_reasons"]
    assert [i["status"] for i in checkpoint_items(r)] == ["MATCH"] * 3 and sum(i["byte_checked"] for i in checkpoint_items(r)) == 15
    assert {s: tuple(row["replay_with_the_preserved_rule"][k] for k in ("gained", "broken", "p_one_sided", "passed"))
            for s, row in r["decisions"].items()} == REVIEW_DECISIONS[name]


@pytest.fixture(scope="module")
def material():
    return T._load_frozen_and_checker()


@slow
@pytest.mark.parametrize("name", sorted(T.HISTORICAL_EXCEPTION))
def test_full_historical_rescore_reproduces_history(name, material, tmp_path):
    assert _real_weights_missing() == [], "bundle the real checkpoint weight files first"
    entry = T.HISTORICAL_EXCEPTION[name]
    guarded = T.protected_paths()
    before = raw_digests(guarded)
    out = tmp_path / ("historical_reading_%s.json" % name)
    code = T.rescore(study_of(name), REAL_PACKAGE / entry["anchor"][0], {}, out, material=material, historical_compatibility=True)
    r = json.loads(out.read_text(encoding="utf-8"))
    assert raw_digests(guarded) == before
    assert code == 4 and r["verdict"] == "HISTORICAL_COMPATIBILITY_OK" and r["label_rederived"] == entry["label"], r["reject_reasons"]
    assert all(c["status"] == "PASS" for k, c in r["checks"].items() if k != "RUN_EVIDENCE")
    assert r["checks"]["RUN_EVIDENCE"] == T.NOT_REQUESTED_HISTORICAL                 # HISTORICAL_EVIDENCE covers the weights here
    assert all(s["phases"][ph]["rescored"] == 564 and s["phases"][ph]["disagreements"] == 0 for s in r["per_seed"].values() for ph in T.PHASES)
    assert {s: (v["gained"], v["broken"], v["p_one_sided"], v["passed"]) for s, v in r["per_seed"].items()} == REVIEW_DECISIONS[name]
    assert r["historical_exception"]["warning"] == T.WARNING and r["mode"]["name"] == "HISTORICAL_COMPATIBILITY"
