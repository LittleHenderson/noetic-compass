"""T01 -- the evaluator boundary, tool version 0.2. Rescore RAW PREDICTIONS with the run's own private checker,
against an anchor that lives OUTSIDE any receipt directory, and compare with what the frozen grader printed.

WHY. `evaluate_gates.py` (frozen, sha256 d3e0ea97...) reads the `correct` flags out of `course_p00_scoring.json`
and `course_p10_scoring.json` and prints the label from them. It never checks those two files against
anything. The independent audit of 2026-09-20 demonstrated the consequence: a hand-edited scoring file
produced `LEARNS_NEW_WORLDS` with `integrity: pass`. This program re-derives the label from the raw
predictions instead, and refuses, by name, every way of tampering it knows about.

HOW IT IS ORDERED (version 0.2 -- the order is the point):

  1. SAFE CHECKS, which only read files. The anchor is read FIRST. Then: the study file's identity and its
     seed set, the frozen grader's hash, the hash of EVERY source file the private checker executes (the
     whole import closure, not three files), and for every prediction file its hash, duplicate ids, missing
     or extra ids, non-finite numbers and duplicate JSON keys. Every reason found is collected.
  2. THE GATE. If the anchor, the study, the grader or the checker code does not match, the checker code is
     NEVER IMPORTED OR RUN -- a substituted evaluator is not executed to find out what else it would do.
     Every check that needs the checker is recorded as NOT_RUN, and the verdict is REJECT.
  3. CHECKS THAT RUN THE CHECKER. Cached bytecode is ignored (a fresh empty bytecode directory, and none
     written), so what runs is compiled from the very sources that were just hashed; after the import every
     executed module under the package must be in the anchored closure and must still hash the same. Then
     every prediction is re-checked, the label is re-derived from those fresh results only, each stored
     scoring row is compared, and the label and per-seed counts are compared with the frozen grader's reading.

EVERY CHECK HAS A STATUS: PASS, FAIL, NOT_RUN (it could not run -- which is not the same as failing), or
NOT_REQUESTED (the caller said so explicitly, e.g. --no-frozen-reading). The verdict is
    REJECT              if any reason was recorded (irreversible: nothing later can clear a reason);
    RESCORE_INCOMPLETE  if nothing failed but a check that was supposed to run did not;
    RESCORE_OK          only if every check is PASS or NOT_REQUESTED.

HASH POLICY (cncm.hash-policy/1.0). Every pinned file here is text. Each pin records TWO digests: the
LF-normalised one (CRLF -> LF only; nothing else is touched) which is what gets COMPARED, and the raw one
as observed when the pin was written, which is informational -- it tells a forensic reader which exact bytes
were on disk, and it legitimately differs between a Windows working copy and a fresh checkout. A match
therefore means "the same text under the declared newline rule", not "the same raw bytes".

LIMIT, stated plainly: an anchor written by the same session that built the model is not independent
custody. Every anchor and reading carries `custody: EVALUATION_NOT_INDEPENDENT`. What this program DOES
establish is that no one can move the label by editing a receipt, and that a third party can re-run it.

Usage:
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --write-anchor
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> [--frozen-reading <gate_reading.json>]
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --safe-only        # file checks only, seconds
"""
import argparse
import collections
import hashlib
import json
import math
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
CODE_ROOT = PACKAGE / "research" / "CAS_META_2_COMPOSITION"

SCHEMA = "cncm.trusted-rescore-reading/0.2"
ANCHOR_SCHEMA = "cncm.trusted-rescore-anchor/0.2"
PHASES = ("course_p00", "course_p10")
MIN_PASSING_B, MIN_IMPROVED_KINDS, MIN_IMPROVED_WORLDS = 7, 2, 2
GRADER = HERE / "evaluate_gates.py"
CUSTODY = "EVALUATION_NOT_INDEPENDENT -- written by the session that also built the model and the lab"
HASH_POLICY = {
    "policy_id": "cncm.hash-policy/1.0", "algorithm": "sha256",
    "compared": "sha256_lf -- digest after CRLF -> LF only; lone CR, BOM, trailing newline, whitespace and Unicode are untouched",
    "informational": "sha256_raw_observed -- digest of the exact bytes on disk when the pin was written; never compared",
    "text_formats": [".py", ".json"], "binary_formats": "none are pinned by this tool; a binary file would be pinned raw only",
}
# Everything `_load_frozen_and_checker` executes, found by a static import trace and enforced at run time
# (CODE_CLOSURE_COMPLETE): package-relative, forward slashes.
_TT = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/"
CODE_CLOSURE = tuple(["research/CAS_META_2_COMPOSITION/cas_meta2/__init__.py"] + [_TT + name for name in (
    "__init__.py", "answers.py", "binding.py", "checker.py", "course.py", "course_plan.py", "development.py", "focal.py",
    "input_frames.py", "matched_contract.py", "pointer_contract.py", "practice_contract.py", "slots.py", "source.py",
    "tokenization.py", "worker_contract.py")] + ["records/typed_practice_001/evaluate_gates.py"])

SAFE_CHECKS = ("ANCHOR_READABLE", "STUDY_IDENTITY", "SEED_SET", "EVALUATOR_IDENTITY", "CHECKER_CODE_IDENTITY",
               "PREDICTIONS_IDENTITY", "ID_SET", "FINITE_NUMBERS", "WELL_FORMED_JSON")
CHECKER_CHECKS = ("CHECKER_PROFILE", "COURSE_IDENTITY", "POPULATION_IDENTITY", "CODE_CLOSURE_COMPLETE", "CODE_UNCHANGED_DURING_RUN",
                  "RESCORE", "SCORING_FILE_AGREEMENT", "FROZEN_GRADER_AGREEMENT")
GATE = ("ANCHOR_READABLE", "STUDY_IDENTITY", "SEED_SET", "EVALUATOR_IDENTITY", "CHECKER_CODE_IDENTITY")


# ---------------------------------------------------------------------------------------------
def _sha(data):
    return hashlib.sha256(data).hexdigest()


def file_pin(path):
    raw = pathlib.Path(path).read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    return {"sha256_lf": _sha(lf), "bytes_lf": len(lf), "sha256_raw_observed": _sha(raw), "bytes_raw_observed": len(raw)}


def _lf_sha(path):
    return file_pin(path)["sha256_lf"]


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _rel(path):
    """Package-relative with forward slashes when the path is inside the package; otherwise the path as given."""
    path = pathlib.Path(path)
    try:
        return path.resolve().relative_to(PACKAGE.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_receipt(job, override):
    """A study may carry an absolute path into another worktree. Prefer the copy inside THIS package."""
    seed = str(job["model_seed"])
    if seed in override:
        return pathlib.Path(override[seed]), "override"
    recorded = pathlib.Path(str(job["receipt_dir"]).replace("\\", "/"))
    local = HERE / recorded.name
    if local.is_dir():
        return local, "package-relative"
    return recorded, "absolute-path-in-study"


def code_closure_pins():
    """Hash every source file the checker executes. READS files only; imports nothing. A missing file is None."""
    return {rel: (file_pin(PACKAGE / rel) if (PACKAGE / rel).is_file() else None) for rel in CODE_CLOSURE}


class _JsonProblems:
    def __init__(self):
        self.nonfinite, self.duplicate_keys = [], []

    def constant(self, name):
        self.nonfinite.append(name)
        return float("nan")

    def pairs(self, pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            self.duplicate_keys.extend(sorted({k for k in keys if keys.count(k) > 1}))
        return dict(pairs)


def strict_json(text):
    """Parse JSON and report what plain json.loads hides: NaN/Infinity tokens and duplicate object keys."""
    problems = _JsonProblems()
    value = json.loads(text, parse_constant=problems.constant, object_pairs_hook=problems.pairs)
    return value, problems


def _has_nonfinite(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_has_nonfinite(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_nonfinite(v) for v in value)
    return False


def _count(value):
    """A transition count as the frozen grader may store it: an int, or a list of keys, or absent (None)."""
    if value is None:
        return None
    return len(value) if isinstance(value, (list, dict)) else int(value)


def _load_frozen_and_checker():
    """Import and run the private checker code. Call ONLY after the code-identity gate has passed.
    Cached bytecode is ignored and none is written, so what runs is compiled from the hashed sources."""
    already = [m for m in sys.modules if m == "cas_meta2" or m.startswith("cas_meta2.")]
    policy = "MODULES_ALREADY_IMPORTED_BEFORE_THE_GATE" if already else "FRESH_EMPTY_PYCACHE_PREFIX_AND_NO_BYTECODE_WRITTEN"
    if not already:
        sys.dont_write_bytecode = True
        sys.pycache_prefix = tempfile.mkdtemp(prefix="trusted_rescore_pycache_")
    if str(CODE_ROOT) not in sys.path:
        sys.path.insert(0, str(CODE_ROOT))
    from cas_meta2.typed_teaching import pointer_contract as contract, checker
    frozen = contract.load_material(PACKAGE)[0]
    packets = dict(contract.public_packets(frozen))
    population = contract.relational_population(frozen)
    kind_of = {r["query"]["query_id"]: r["query"]["kind"] for r in frozen["registry"]}
    world_of = {r["query"]["query_id"]: r["source_world_id"] for r in frozen["registry"]}
    record_ids = sorted(r["record_id"] for r in frozen["registry"])
    return {"frozen": frozen, "packets": packets, "population": population, "kind_of": kind_of, "world_of": world_of,
            "record_ids": record_ids, "checker": checker, "bytecode_policy": policy}


def executed_package_modules():
    """Every imported module whose file is inside the package, except this tool's own folder (tool + tests)."""
    found = set()
    for module in list(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if not origin:
            continue
        try:
            rel = pathlib.Path(origin).resolve().relative_to(PACKAGE.resolve()).as_posix()
        except ValueError:
            continue
        if not rel.startswith("records/typed_pointer_001/"):
            found.add(rel)
    return sorted(found)


# ---------------------------------------------------------------------------------------------
def safe_anchor_part(study_path, receipt_override):
    """Everything an anchor holds that can be computed by READING files only."""
    study = json.loads(pathlib.Path(study_path).read_text(encoding="utf-8"))
    seeds = {}
    for job in study["jobs"]:
        rdir, how = _resolve_receipt(job, receipt_override)
        art = rdir / "collected/results/artifacts"
        seeds[str(job["model_seed"])] = {"receipt_dir": _rel(rdir), "receipt_resolved_from": how,
                                         "predictions": {ph: file_pin(art / ("%s_predictions.json" % ph)) for ph in PHASES}}
    return {"schema": ANCHOR_SCHEMA, "written": "2026-09-21", "hash_policy": HASH_POLICY,
            "study": {"path": _rel(study_path), "pin": file_pin(study_path)}, "seed_set": sorted(seeds),
            "grader": {"path": _rel(GRADER), "pin": file_pin(GRADER)},
            "checker": {"code_closure": code_closure_pins()},
            "tool": {"path": _rel(__file__), "pin": file_pin(__file__)},
            "pass_rule": {"min_passing_b": MIN_PASSING_B, "min_improved_kinds": MIN_IMPROVED_KINDS, "min_improved_worlds": MIN_IMPROVED_WORLDS,
                          "broken_must_be": 0, "all_seeds_must_pass": True},
            "seeds": seeds, "custody": CUSTODY}


def write_anchor(study_path, anchor_path, receipt_override, material=None):
    anchor = safe_anchor_part(study_path, receipt_override)
    missing = [rel for rel, pin in anchor["checker"]["code_closure"].items() if pin is None]
    if missing:
        print("ANCHOR_REFUSED: checker source files are missing: %s" % missing)
        return 2
    m = material or _load_frozen_and_checker()
    uncovered = [rel for rel in executed_package_modules() if rel not in CODE_CLOSURE]
    if uncovered:
        print("ANCHOR_REFUSED: the checker executed code the closure list does not cover: %s" % uncovered)
        return 2
    population = m["population"]
    anchor["checker"]["profile_digest"] = m["checker"].checker_profile()["profile_digest"]
    anchor["course_digest"] = m["frozen"]["course_digest"]
    anchor["population"] = {"digest": population["digest"], "question_ids": population["question_ids"],
                            "kind_of": {q: m["kind_of"][q] for q in population["question_ids"]},
                            "world_of": {q: m["world_of"][q] for q in population["question_ids"]}}
    anchor["expected_record_ids"] = m["record_ids"]
    anchor["expected_record_count"] = len(m["record_ids"])
    with open(anchor_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(anchor, indent=1, sort_keys=True))
    print("anchor written: %s  sha256_lf %s" % (_rel(anchor_path), _lf_sha(anchor_path)[:16]))
    return 0


# ---------------------------------------------------------------------------------------------
class _Run:
    def __init__(self):
        self.reasons = []
        self.checks = collections.OrderedDict((name, {"status": "NOT_RUN", "detail": "not reached"}) for name in SAFE_CHECKS + CHECKER_CHECKS)

    def fail(self, check, code, detail):
        self.reasons.append("%s:%s" % (code, detail))
        self.checks[check] = {"status": "FAIL", "detail": detail if self.checks[check]["status"] != "FAIL" else self.checks[check]["detail"] + " | " + detail}

    def passed(self, check, detail=""):
        if self.checks[check]["status"] != "FAIL":
            self.checks[check] = {"status": "PASS", "detail": detail}

    def not_run(self, check, detail):
        if self.checks[check]["status"] != "FAIL":
            self.checks[check] = {"status": "NOT_RUN", "detail": detail}

    def failed(self, *names):
        return any(self.checks[n]["status"] == "FAIL" for n in names)


def _safe_checks(run, study_path, anchor_path, receipt_override):
    """Step 1: read files only. Returns (anchor, study, per-seed prediction lists) -- any of them may be None."""
    try:
        anchor = json.loads(pathlib.Path(anchor_path).read_text(encoding="utf-8"))
        if anchor.get("schema") != ANCHOR_SCHEMA:
            run.fail("ANCHOR_READABLE", "ANCHOR_SCHEMA_OUTDATED", "anchor schema %r, this tool needs %r -- rewrite the anchor with --write-anchor" % (anchor.get("schema"), ANCHOR_SCHEMA))
            return None, None, {}
        run.passed("ANCHOR_READABLE", _rel(anchor_path))
    except Exception as error:
        run.fail("ANCHOR_READABLE", "ANCHOR_UNREADABLE", "%s: %s" % (type(error).__name__, str(error)[:120]))
        return None, None, {}
    try:
        study = json.loads(pathlib.Path(study_path).read_text(encoding="utf-8"))
        jobs = study["jobs"]
    except Exception as error:
        run.fail("STUDY_IDENTITY", "STUDY_UNREADABLE", "%s: %s" % (type(error).__name__, str(error)[:120]))
        return anchor, None, {}
    if _lf_sha(study_path) != anchor["study"]["pin"]["sha256_lf"]:
        run.fail("STUDY_IDENTITY", "STUDY_IDENTITY", "the study file differs from the one the anchor was written for")
    run.passed("STUDY_IDENTITY")
    seeds_now = sorted(str(j["model_seed"]) for j in jobs)
    if seeds_now != sorted(anchor["seed_set"]) or len(set(seeds_now)) != len(seeds_now):
        run.fail("SEED_SET", "SEED_SET", "study seeds %s, anchored seeds %s" % (seeds_now, sorted(anchor["seed_set"])))
    run.passed("SEED_SET")
    if _lf_sha(GRADER) != anchor["grader"]["pin"]["sha256_lf"]:
        run.fail("EVALUATOR_IDENTITY", "EVALUATOR_IDENTITY", "grader sha256_lf %s != anchored %s" % (_lf_sha(GRADER)[:12], anchor["grader"]["pin"]["sha256_lf"][:12]))
    run.passed("EVALUATOR_IDENTITY")
    now, anchored = code_closure_pins(), anchor["checker"]["code_closure"]
    for rel in sorted(set(now) | set(anchored)):
        a, b = anchored.get(rel), now.get(rel)
        if a is None or b is None:
            run.fail("CHECKER_CODE_IDENTITY", "CHECKER_CODE_IDENTITY", "%s is %s" % (rel, "not in the anchor" if a is None else "missing on disk"))
        elif a["sha256_lf"] != b["sha256_lf"]:
            run.fail("CHECKER_CODE_IDENTITY", "CHECKER_CODE_IDENTITY", "%s differs from the anchor" % rel)
    run.passed("CHECKER_CODE_IDENTITY", "%d source files" % len(now))

    expected = anchor.get("expected_record_ids") or []
    predictions = {}
    for job in jobs:
        seed = str(job["model_seed"])
        rdir, how = _resolve_receipt(job, receipt_override)
        art = rdir / "collected/results/artifacts"
        predictions[seed] = {"receipt_dir": _rel(rdir), "receipt_resolved_from": how, "phases": {}}
        for ph in PHASES:
            ppath = art / ("%s_predictions.json" % ph)
            slot = {"predictions_sha256_lf": None, "predictions": None}
            predictions[seed]["phases"][ph] = slot
            if not ppath.is_file():
                run.fail("ID_SET", "MISSING_OR_EXTRA_PREDICTIONS", "%s:%s:file absent" % (seed, ph))
                continue
            slot["predictions_sha256_lf"] = _lf_sha(ppath)
            if slot["predictions_sha256_lf"] != anchor["seeds"].get(seed, {}).get("predictions", {}).get(ph, {}).get("sha256_lf"):
                run.fail("PREDICTIONS_IDENTITY", "PREDICTIONS_IDENTITY", "%s:%s:raw predictions differ from the anchor (altered, or the wrong phase/split file)" % (seed, ph))
            try:
                body, problems = strict_json(ppath.read_text(encoding="utf-8"))
                preds = body["predictions"]
                assert isinstance(preds, list) and all(isinstance(p, dict) for p in preds)
            except Exception as error:
                run.fail("WELL_FORMED_JSON", "MALFORMED_PREDICTION", "%s:%s:%s" % (seed, ph, type(error).__name__))
                continue
            if problems.duplicate_keys:
                run.fail("WELL_FORMED_JSON", "DUPLICATE_JSON_KEYS", "%s:%s:%s" % (seed, ph, problems.duplicate_keys[:5]))
            for p in preds:
                if _has_nonfinite(p):
                    run.fail("FINITE_NUMBERS", "NONFINITE_NUMBER", "%s:%s:%s" % (seed, ph, str(p.get("record_id"))[:30]))
            ids = [p.get("record_id") for p in preds]
            if len(ids) != len(set(ids)):
                run.fail("ID_SET", "DUPLICATE_IDS", "%s:%s:%d duplicate record ids" % (seed, ph, len(ids) - len(set(ids))))
            if set(ids) != set(expected):
                run.fail("ID_SET", "MISSING_OR_EXTRA_PREDICTIONS", "%s:%s:missing %d, extra %d" % (seed, ph, len(set(expected) - set(ids)), len(set(ids) - set(expected))))
            slot["predictions"] = preds
    for name in ("PREDICTIONS_IDENTITY", "ID_SET", "FINITE_NUMBERS", "WELL_FORMED_JSON"):
        run.passed(name)
    return anchor, study, predictions


def rescore(study_path, anchor_path, receipt_override, out_path, material=None, frozen_reading=None,
            compare_frozen=True, safe_only=False):
    run = _Run()
    anchor, study, predictions = _safe_checks(run, study_path, anchor_path, receipt_override)
    per_seed, comparison, label = {}, {"requested": compare_frozen}, "VOID_REJECTED"
    imported, bytecode_policy = False, None

    gate_failed = anchor is None or study is None or run.failed(*GATE)
    if gate_failed or safe_only:
        why = ("the identity gate failed; the checker code was not imported or run" if gate_failed
               else "--safe-only: file checks only, the checker was not imported")
        for name in CHECKER_CHECKS:
            run.not_run(name, why)
    else:
        before_import = code_closure_pins()
        m = material or _load_frozen_and_checker()
        imported, bytecode_policy = True, m.get("bytecode_policy", "MATERIAL_SUPPLIED_BY_CALLER")
        checker, packets, population = m["checker"], m["packets"], m["population"]
        uncovered = [rel for rel in executed_package_modules() if rel not in anchor["checker"]["code_closure"]]
        if uncovered:
            run.fail("CODE_CLOSURE_COMPLETE", "CODE_CLOSURE_INCOMPLETE", "executed but not anchored: %s" % uncovered[:6])
        run.passed("CODE_CLOSURE_COMPLETE", "%d executed package modules, all anchored" % len(executed_package_modules()))
        if checker.checker_profile()["profile_digest"] != anchor["checker"].get("profile_digest"):
            run.fail("CHECKER_PROFILE", "CHECKER_IDENTITY", "checker profile digest differs from the anchor")
        run.passed("CHECKER_PROFILE")
        if m["frozen"]["course_digest"] != anchor.get("course_digest"):
            run.fail("COURSE_IDENTITY", "COURSE_IDENTITY", "%s != %s" % (m["frozen"]["course_digest"][:12], str(anchor.get("course_digest"))[:12]))
        run.passed("COURSE_IDENTITY")
        if population["digest"] != anchor["population"]["digest"] or population["question_ids"] != anchor["population"]["question_ids"] \
                or m["record_ids"] != anchor.get("expected_record_ids"):
            run.fail("POPULATION_IDENTITY", "POPULATION_IDENTITY", "the relational population or the record ids do not match the anchor")
        run.passed("POPULATION_IDENTITY")

        pop, expected_n = anchor["population"]["question_ids"], len(anchor["expected_record_ids"])
        compared_all = True
        for seed, info in predictions.items():
            art = (PACKAGE / info["receipt_dir"]) if not pathlib.Path(info["receipt_dir"]).is_absolute() else pathlib.Path(info["receipt_dir"])
            art = art / "collected/results/artifacts"
            seed_report = {"receipt_dir": info["receipt_dir"], "receipt_resolved_from": info["receipt_resolved_from"], "phases": {}}
            question_correct = {}
            for ph in PHASES:
                slot = info["phases"][ph]
                entry = {"predictions_sha256_lf": slot["predictions_sha256_lf"], "rescored": 0, "scoring_rows_compared": 0,
                         "disagreements": 0, "scoring_file_present": False}
                seed_report["phases"][ph] = entry
                if slot["predictions"] is None:
                    continue
                stored, spath = {}, art / ("%s_scoring.json" % ph)
                if spath.is_file():
                    entry["scoring_file_present"] = True
                    try:
                        stored = {r["prediction_id"]: r for r in json.loads(spath.read_text(encoding="utf-8"))["rows"]}
                    except Exception as error:
                        run.fail("SCORING_FILE_AGREEMENT", "MALFORMED_SCORING_FILE", "%s:%s:%s" % (seed, ph, type(error).__name__))
                fresh_by_query = collections.defaultdict(list)
                for p in slot["predictions"]:
                    rid = p.get("record_id")
                    if _has_nonfinite(p) or rid not in packets:
                        continue
                    try:
                        row = checker.check_answer(packets[rid]["source"], packets[rid]["record"]["query"], p["answer"])
                    except Exception as error:
                        run.fail("RESCORE", "MALFORMED_PREDICTION", "%s:%s:%s:%s" % (seed, ph, str(rid)[:30], type(error).__name__))
                        continue
                    entry["rescored"] += 1
                    fresh_by_query[row["query_id"]].append(row["correct"])
                    s = stored.get(p.get("prediction_id"))
                    if s is not None:
                        entry["scoring_rows_compared"] += 1
                        if s.get("check_digest") != row["check_digest"] or bool(s.get("correct")) != row["correct"]:
                            entry["disagreements"] += 1
                if entry["disagreements"]:
                    run.fail("SCORING_FILE_AGREEMENT", "SCORING_FILE_DISAGREES_WITH_RESCORE", "%s:%s:%d rows" % (seed, ph, entry["disagreements"]))
                if entry["scoring_rows_compared"] != entry["rescored"] or not entry["scoring_file_present"]:
                    compared_all = False
                if entry["rescored"] != expected_n:
                    run.fail("RESCORE", "INCOMPLETE_RESCORE", "%s:%s:%d of %d predictions could be re-checked" % (seed, ph, entry["rescored"], expected_n))
                question_correct[ph] = {q: (len(v) > 0 and all(v)) for q, v in fresh_by_query.items()}
            before, after = question_correct.get("course_p00", {}), question_correct.get("course_p10", {})
            gained = [q for q in pop if not before.get(q, False) and after.get(q, False)]
            lost = [q for q in pop if before.get(q, False) and not after.get(q, False)]
            kinds = sorted({anchor["population"]["kind_of"][q] for q in gained})
            worlds = sorted({anchor["population"]["world_of"][q] for q in gained})
            seed_report.update({"frozen_18_before": sum(1 for q in pop if before.get(q, False)), "frozen_18_after": sum(1 for q in pop if after.get(q, False)),
                                "gained": len(gained), "broken": len(lost), "kinds_improved": kinds, "worlds_improved": len(worlds),
                                "passed": len(gained) >= MIN_PASSING_B and len(lost) == 0 and len(kinds) >= MIN_IMPROVED_KINDS and len(worlds) >= MIN_IMPROVED_WORLDS})
            per_seed[seed] = seed_report
        run.passed("RESCORE", "%d predictions re-checked" % sum(s["phases"][ph]["rescored"] for s in per_seed.values() for ph in PHASES))
        if compared_all:
            run.passed("SCORING_FILE_AGREEMENT")
        else:
            run.not_run("SCORING_FILE_AGREEMENT", "a scoring file is absent, or some re-checked predictions have no stored scoring row to compare with")
        after_import = code_closure_pins()
        if any((before_import[r] or {}).get("sha256_lf") != (after_import[r] or {}).get("sha256_lf") for r in CODE_CLOSURE):
            run.fail("CODE_UNCHANGED_DURING_RUN", "CODE_CHANGED_DURING_RUN", "a checker source file changed between the gate and the end of the run")
        run.passed("CODE_UNCHANGED_DURING_RUN")
        label = "LEARNS_NEW_WORLDS" if per_seed and all(s["passed"] for s in per_seed.values()) else "NO_TRANSFER_TO_NEW_WORLDS"

        # the frozen grader's reading: beside the study by default; --frozen-reading when it lives elsewhere
        if not compare_frozen:
            run.checks["FROZEN_GRADER_AGREEMENT"] = {"status": "NOT_REQUESTED", "detail": "--no-frozen-reading"}
        else:
            fpath = pathlib.Path(frozen_reading) if frozen_reading else pathlib.Path(study_path).parent / "gate_reading.json"
            comparison.update({"frozen_reading_present": fpath.is_file(), "frozen_reading_path": _rel(fpath)})
            if not fpath.is_file():
                run.not_run("FROZEN_GRADER_AGREEMENT", "no gate_reading.json at %s" % _rel(fpath))
            else:
                try:
                    g = json.loads(fpath.read_text(encoding="utf-8"))
                    per = {}
                    for seed, s in per_seed.items():
                        gs = (g.get("seeds") or {}).get(seed, {}).get("G_LEARN_population", {})
                        fb, fc = _count(gs.get("wrong_to_right")), _count(gs.get("right_to_wrong"))
                        per[seed] = {"rescored_gained_broken": [s["gained"], s["broken"]], "frozen_gained_broken": [fb, fc],
                                     "agree": fb == s["gained"] and fc == s["broken"]}
                    comparison.update({"frozen_label": g.get("label"), "labels_agree": g.get("label") == label, "per_seed": per})
                    if not comparison["labels_agree"] or not all(v["agree"] for v in per.values()):
                        run.fail("FROZEN_GRADER_AGREEMENT", "FROZEN_GRADER_DISAGREES", "label or per-seed counts differ between the fresh rescore and %s" % _rel(fpath))
                    run.passed("FROZEN_GRADER_AGREEMENT")
                except Exception as error:
                    run.fail("FROZEN_GRADER_AGREEMENT", "FROZEN_READING_UNREADABLE", "%s: %s" % (type(error).__name__, str(error)[:120]))

    statuses = [c["status"] for c in run.checks.values()]
    verdict = "REJECT" if run.reasons else ("RESCORE_INCOMPLETE" if "NOT_RUN" in statuses else "RESCORE_OK")
    if run.reasons:
        label = "VOID_REJECTED"
    elif not imported:
        label = "NOT_DERIVED"
    reading = {"schema": SCHEMA, "verdict": verdict, "label_rederived": label, "reject_reasons": run.reasons, "checks": run.checks,
               "imported_checker_code": imported, "bytecode_policy": bytecode_policy, "material_supplied_by_caller": material is not None,
               "anchor": {"path": _rel(anchor_path), "pin": file_pin(anchor_path) if pathlib.Path(anchor_path).is_file() else None},
               "tool": {"path": _rel(__file__), "pin": file_pin(__file__)}, "hash_policy": HASH_POLICY["policy_id"],
               "per_seed": per_seed, "comparison_with_frozen_grader": comparison, "custody": CUSTODY,
               "boundary": "the scoring files' correct flags were NOT read for the label; every prediction was re-checked with the private checker"}
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(reading, indent=1, sort_keys=True))
    print(json.dumps({k: reading[k] for k in ("verdict", "label_rederived", "reject_reasons")}, indent=1))
    print("  checks:", ", ".join("%s=%s" % (k, v["status"]) for k, v in run.checks.items()))
    for seed, s in per_seed.items():
        print("  seed %s: frozen18 %s -> %s, gained %d broken %d, rescored %s, disagreements %s" % (
            seed, s["frozen_18_before"], s["frozen_18_after"], s["gained"], s["broken"],
            [s["phases"][ph]["rescored"] for ph in PHASES], [s["phases"][ph]["disagreements"] for ph in PHASES]))
    return {"RESCORE_OK": 0, "REJECT": 2, "RESCORE_INCOMPLETE": 3}[verdict]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True)
    parser.add_argument("--anchor", default=None)
    parser.add_argument("--write-anchor", action="store_true")
    parser.add_argument("--receipt", action="append", default=[], help="seed=dir override (tests)")
    parser.add_argument("--out", default=None)
    parser.add_argument("--frozen-reading", default=None, help="gate_reading.json to compare against (default: beside the study)")
    parser.add_argument("--no-frozen-reading", action="store_true", help="do not compare with a frozen grader reading (recorded as NOT_REQUESTED)")
    parser.add_argument("--safe-only", action="store_true", help="file checks only; never imports the checker; verdict is at best RESCORE_INCOMPLETE")
    args = parser.parse_args()
    study = pathlib.Path(args.study)
    anchor = pathlib.Path(args.anchor) if args.anchor else HERE / ("trust_anchor_%s.json" % study.parent.name)
    override = dict(r.split("=", 1) for r in args.receipt)
    if args.write_anchor:
        return write_anchor(study, anchor, override)
    return rescore(study, anchor, override, args.out, frozen_reading=args.frozen_reading,
                   compare_frozen=not args.no_frozen_reading, safe_only=args.safe_only)


if __name__ == "__main__":
    sys.exit(main())
