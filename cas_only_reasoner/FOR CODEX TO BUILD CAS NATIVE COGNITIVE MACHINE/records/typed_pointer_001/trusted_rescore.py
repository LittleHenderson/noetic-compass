"""T01 -- the evaluator boundary, tool version 0.4. Rescore RAW PREDICTIONS with the run's own private checker,
against an anchor that lives OUTSIDE any receipt directory, and compare with what the frozen grader printed.

WHY. `evaluate_gates.py` (frozen, sha256 d3e0ea97...) reads the `correct` flags out of `course_p00_scoring.json`
and `course_p10_scoring.json` and prints the label from them. It never checks those two files against
anything. The independent audit of 2026-09-20 demonstrated the consequence: a hand-edited scoring file
produced `LEARNS_NEW_WORLDS` with `integrity: pass`. This program re-derives the label from the raw
predictions instead, and refuses, by name, every way of tampering it knows about.

WHAT 0.4 CHANGES (owner direction 2026-09-24, item 2 "RESCORER"):

  * TRUSTED MODE (the default). An anchor or a reading whose recorded pass-rule description is not the preserved
    historical rule is REFUSED for trusted acceptance, by name: RULE_DESCRIPTION_MISMATCH. The 0.2 anchors and
    readings of Helm 1.0 certified and Helm 2.0 experimental are refused here: tool 0.2 recorded -- and applied --
    a zero-loss veto and a 7-gain minimum that the frozen grader never had. New anchors (schema 0.3) carry the
    preserved rule and its digest, and are CREATE-ONLY: no anchor is ever written over an existing file.
  * HISTORICAL-COMPATIBILITY MODE, only with the explicit flag --historical-compatibility (recorded in every
    output). It accepts ONLY the recognised mistake: the exact 0.2 description (canonical sha256 frozen below as
    RECOGNISED_MISTAKE), and ONLY for the records on the frozen list HISTORICAL_EXCEPTION (identified by sha256_lf).
    It first verifies the original evidence: every hash the anchor names, the frozen grader reading, each run's
    own artifact manifest and the four label-deciding files it pins, and the checkpoint digests as recorded.
    It then applies the PRESERVED HISTORICAL RULE, never the recorded description. Every output carries a
    WARNING and both rule descriptions side by side. It never writes to an original record.
  * BOTH MODES refuse unknown, altered, incomplete or incompatible evidence. A new run -- anything not on the
    frozen list -- never receives the historical exception, even with the flag.
  * --check-reading verifies a committed reading WITHOUT rescoring: it re-derives the decisions from the counts
    the reading recorded, and it never imports or runs the checker. Seconds, not the 30-minute full reading.
  * 0.3 is kept as history only: byte-identical at history/trusted_rescore_0_3.py (sha256_lf 50295072...) and in
    git at 60e382b0. Its behaviour -- accept a 0.2 anchor and only report the wrong description -- is gone here.

HOW IT IS ORDERED (the order is the point):

  1. SAFE CHECKS, which only read files. The tool's own frozen constants first, then the anchor (well-formed,
     known schema, complete), its rule description and the mode, then (historical mode only) the original
     evidence. Then: the study file's identity and its seed set, the frozen grader's hash, the hash of EVERY source
     file the private checker executes, and for every prediction file its hash, duplicate ids, missing or extra
     ids, non-finite numbers and duplicate JSON keys. Every reason found is collected.
  2. THE GATE. If the constants, the anchor, its rule description, the historical evidence, the study, the grader
     or the checker code does not match, the checker code is NEVER IMPORTED OR RUN.
  3. CHECKS THAT RUN THE CHECKER. Cached bytecode is ignored, so what runs is compiled from the very sources that
     were just hashed. Every prediction is re-checked, the label is re-derived from those fresh results only with
     the preserved historical rule, and it is compared with the frozen grader's reading (and, in historical mode,
     with the six frozen historical decisions).
  4. ORIGINALS. The small original records of both historical studies (anchors, readings, frozen grader readings,
     run manifests), the label-deciding files of the historical study this run reads, and every file named on the
     command line are hashed byte for byte before and after the run; any change is a rejection. An output path that
     is ANY original record the historical list names (label-deciding files included) is refused and nothing is written.

EVERY CHECK HAS A STATUS: PASS, FAIL, NOT_RUN (it could not run -- which is not the same as failing), or
NOT_REQUESTED (the caller or the mode said so explicitly). The verdict and exit code are
    REJECT                        2  if any reason was recorded (irreversible: nothing later can clear a reason);
    RESCORE_INCOMPLETE            3  if nothing failed but a check that was supposed to run did not;
    RESCORE_OK                    0  trusted mode, every check PASS or NOT_REQUESTED;
    HISTORICAL_COMPATIBILITY_OK   4  historical mode, every check PASS (never 0: a script that expects 0 does not
                                     mistake the historical exception for plain trusted acceptance).
--check-reading uses READING_VERIFIED (0), REJECT (2), CHECK_INCOMPLETE (3) and HISTORICAL_COMPATIBILITY_OK (4).

HASH POLICY (cncm.hash-policy/1.0). Every pinned file here is text. Each pin records TWO digests: the
LF-normalised one (CRLF -> LF only; nothing else is touched) which is what gets COMPARED, and the raw one
as observed when the pin was written, which is informational. The before/after check of the originals (step 4)
compares RAW bytes: it proves the files were not rewritten, not merely that their text is the same.

LIMIT, stated plainly: an anchor written by the same session that built the model is not independent
custody. Every anchor and reading carries `custody: EVALUATION_NOT_INDEPENDENT`.

Usage:
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --anchor <NEW path> --write-anchor   # create-only
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> [--frozen-reading <gate_reading.json>]
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --safe-only        # file checks only, seconds
    python records/typed_pointer_001/trusted_rescore.py --check-reading <reading.json>         # no checker import, seconds
  The frozen historical records only (explicit flag, recorded in the output):
    python records/typed_pointer_001/trusted_rescore.py --historical-compatibility \\
        --check-reading records/typed_pointer_001/trusted_rescore_reading_helm1_certified.json
    python records/typed_pointer_001/trusted_rescore.py --historical-compatibility \\
        --study records/typed_pointer_001/study_helm1_certified.json \\
        --anchor records/typed_pointer_001/trust_anchor_helm1_certified.json --out <NEW reading path>
"""
import argparse
import collections
import datetime
import hashlib
import json
import math
import os
import pathlib
import re
import sys
import tempfile
from fractions import Fraction

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
CODE_ROOT = PACKAGE / "research" / "CAS_META_2_COMPOSITION"

TOOL_VERSION = "0.4"
SCHEMA = "cncm.trusted-rescore-reading/0.4"
CHECK_SCHEMA = "cncm.trusted-rescore-reading-check/0.1"
ANCHOR_SCHEMA = "cncm.trusted-rescore-anchor/0.3"
HISTORICAL_ANCHOR_SCHEMA = "cncm.trusted-rescore-anchor/0.2"
HISTORICAL_READING_SCHEMA = "cncm.trusted-rescore-reading/0.2"
READING_SCHEMA_0_3 = "cncm.trusted-rescore-reading/0.3"
KNOWN_ANCHOR_SCHEMAS = (HISTORICAL_ANCHOR_SCHEMA, ANCHOR_SCHEMA)
KNOWN_READING_SCHEMAS = (HISTORICAL_READING_SCHEMA, READING_SCHEMA_0_3, SCHEMA)
PHASES = ("course_p00", "course_p10")
LABEL_FILES = tuple("%s_%s.json" % (ph, kind) for ph in PHASES for kind in ("predictions", "scoring"))
MIN_IMPROVED_KINDS, MIN_IMPROVED_WORLDS = 2, 2
HISTORICAL_RULE = {
    "id": "HELM_HISTORICAL_PAIRED_RULE_20260919",
    "test": "exact one-sided Binomial(b+c, 1/2) upper tail at b",
    "alpha": "1/100", "require_b_greater_than_c": True,
    "min_improved_kinds": 2, "min_improved_worlds": 2,
    "all_seeds_must_pass": True, "zero_loss_veto": False,
}
# sha256 of the canonical JSON bytes (sorted keys, no spaces) of HISTORICAL_RULE. Checked on every run.
HISTORICAL_RULE_SHA256 = "986c66b067ac276bdfcc09e9fdabbc621b34671d65d454ad682683664195c7b2"

TRUSTED, HISTORICAL = "TRUSTED", "HISTORICAL_COMPATIBILITY"
HISTORICAL_FLAG = "--historical-compatibility"

# ---- the ONE recognised mistake, frozen --------------------------------------------------------------------
RECOGNISED_MISTAKE = {
    "id": "HELM_RESCORER_0_2_ZERO_LOSS_VETO_DESCRIPTION",
    "what": ("trusted_rescore 0.2 recorded -- and applied -- a zero-loss veto (broken_must_be 0) and a 7-gain minimum. "
             "The frozen grader evaluate_gates.py (sha256_lf d3e0ea97...) never had either: its rule is b > c, "
             "exact one-sided p <= 1/100, at least 2 kinds and 2 worlds."),
    "recorded_description": {"all_seeds_must_pass": True, "broken_must_be": 0, "min_improved_kinds": 2,
                             "min_improved_worlds": 2, "min_passing_b": 7},
    "recorded_description_sha256": "8e74f0793d18fa1ccc0290ca1871b113c96a74f156d6767f15e13166b2d60ff6",
    "anchor_schema": HISTORICAL_ANCHOR_SCHEMA,
    "reading_schema": HISTORICAL_READING_SCHEMA,
    "written_by_tool_sha256_lf": "8e9a751a15358043b8d1bbc7428fd0e475325174e58fe9e00ec5297cbdd5953a",
    "written_by_tool_commit": "8b2bb942",
}

# ---- the frozen list of historical records the exception covers: two studies, six seed decisions ----------
# Paths are package-relative. Digests are sha256_lf of the files as last committed (anchors and readings at
# 64bf94a0, the owner-approved AWS re-check; frozen grader readings at df20eb46 / 27fd5698; run manifests at
# df20eb46 / 27fd5698). Decisions are the frozen grader's, reproduced by RESCORER_REVIEW.json (0d8e8316).
_R = "records/typed_pointer_001/"
HISTORICAL_EXCEPTION = {
    "helm1_certified": {
        "anchor": [_R + "trust_anchor_helm1_certified.json",
                   "b1798323f6f7f9c9656b1c30eef724e94104715e180eb6724ad11c6c3b2b49ef"],
        "reading": [_R + "trusted_rescore_reading_helm1_certified.json",
                    "18265eab046b4604b9bb9fe9c00698260b00d0127dec210f6eea2be990cdd061"],
        "frozen_grader_reading": [_R + "admission_helm1_certified/gate_reading.json",
                                  "475379d2f9d47387a821c79e03a239f9a1f1277a0bbb25b298417557f9b058a9"],
        "receipt_manifests": {
            "20260917": [_R + "receipt_helm1_certified_20260917/artifact_manifest.json",
                         "454ebea561b057b639162b1ebb4680847c6f0c4e95914b4cc4679a81fd927f13"],
            "20260918": [_R + "receipt_helm1_certified_20260918/artifact_manifest.json",
                         "da9d0f5c188aacbe7942b8e123668b4f744a4483d175aeff391683a80ff9f2e1"],
            "20260919": [_R + "receipt_helm1_certified_20260919/artifact_manifest.json",
                         "44109895b4d412086f36f01f5f94be71c9f541ab3a89331bc3c1e88674825b6f"],
        },
        "label": "LEARNS_NEW_WORLDS",
        "decisions": {
            "20260917": {"gained": 10, "broken": 0, "p_one_sided": "1/1024", "passed": True},
            "20260918": {"gained": 12, "broken": 0, "p_one_sided": "1/4096", "passed": True},
            "20260919": {"gained": 11, "broken": 0, "p_one_sided": "1/2048", "passed": True},
        },
    },
    "helm2_experimental": {
        "anchor": [_R + "trust_anchor_helm2_experimental_20208c92.json",
                   "f71fa001209eb0bb8a7ab980cae24c1dab394ca3f12ce333a84e985a76a1f834"],
        "reading": [_R + "trusted_rescore_reading_helm2_experimental.json",
                    "f0b470da443866b4e8e35a204a0383369d1caa2bd570c238af4eae33b9625602"],
        "frozen_grader_reading": [_R + "admission_001/gate_reading.json",
                                  "52877c1670132c70dfd82e5e133e4e6ef90d8595a4b49387a6b0bace9f9d10d6"],
        "receipt_manifests": {
            "20260917": [_R + "receipt_20260917/artifact_manifest.json",
                         "437e57e504f27979acfc85e56b87e8b52d4586c69576ad9a9a1da84618f77e46"],
            "20260918": [_R + "receipt_20260918/artifact_manifest.json",
                         "2f8e3ac87c23c0592e2b48ebb121020018c3fc0fb3d1ff38da85a131c2309a7d"],
            "20260919": [_R + "receipt_20260919/artifact_manifest.json",
                         "b9b65c668c8752294cb47df9edd5f4f13c63313b074effda3001dec3294a355f"],
        },
        "label": "NO_TRANSFER_TO_NEW_WORLDS",
        "decisions": {
            "20260917": {"gained": 11, "broken": 1, "p_one_sided": "13/4096", "passed": True},
            "20260918": {"gained": 12, "broken": 0, "p_one_sided": "1/4096", "passed": True},
            "20260919": {"gained": 7, "broken": 1, "p_one_sided": "9/256", "passed": False},
        },
    },
}
# sha256 of the canonical JSON bytes of HISTORICAL_EXCEPTION. The list cannot grow silently: checked on every run.
HISTORICAL_EXCEPTION_SHA256 = "f2ea2b187a9a34cba1af3e08ed3a6e49a8f90c8468ead012f1c5b82c8e4a99b9"

WARNING = ("WARNING: HISTORICAL-COMPATIBILITY MODE, requested explicitly with --historical-compatibility. "
           "The original record states its pass rule WRONGLY: tool 0.2 recorded a zero-loss veto and a 7-gain minimum "
           "that the frozen grader never applied. This result applies the PRESERVED HISTORICAL RULE, not the recorded "
           "description. The exception covers only the frozen historical records of Helm 1.0 certified and Helm 2.0 "
           "experimental (six seed decisions). New runs never receive it. The original records were read, never rewritten.")
ABSENT = "(absent)"

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

SAFE_CHECKS = ("TOOL_CONSTANTS", "ANCHOR_READABLE", "RULE_DESCRIPTION", "HISTORICAL_EVIDENCE", "STUDY_IDENTITY", "SEED_SET",
               "EVALUATOR_IDENTITY", "CHECKER_CODE_IDENTITY", "PREDICTIONS_IDENTITY", "ID_SET", "FINITE_NUMBERS", "WELL_FORMED_JSON")
CHECKER_CHECKS = ("CHECKER_PROFILE", "COURSE_IDENTITY", "POPULATION_IDENTITY", "CODE_CLOSURE_COMPLETE", "CODE_UNCHANGED_DURING_RUN",
                  "RESCORE", "SCORING_FILE_AGREEMENT", "FROZEN_GRADER_AGREEMENT", "HISTORICAL_DECISIONS")
FINAL_CHECKS = ("ORIGINALS_UNCHANGED",)
GATE = ("TOOL_CONSTANTS", "ANCHOR_READABLE", "RULE_DESCRIPTION", "HISTORICAL_EVIDENCE", "STUDY_IDENTITY", "SEED_SET",
        "EVALUATOR_IDENTITY", "CHECKER_CODE_IDENTITY")
READING_CHECKS = ("TOOL_CONSTANTS", "READING_READABLE", "RULE_DESCRIPTION", "HISTORICAL_EVIDENCE", "ANCHOR_EVIDENCE",
                  "READING_CONSISTENCY", "DECISIONS_REPLAYED", "ORIGINALS_UNCHANGED")
NOT_REQUESTED_TRUSTED = {"status": "NOT_REQUESTED", "detail": "trusted mode: the historical exception is not in use"}


# ---------------------------------------------------------------------------------------------
def _sha(data):
    return hashlib.sha256(data).hexdigest()


def file_pin(path):
    raw = pathlib.Path(path).read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    return {"sha256_lf": _sha(lf), "bytes_lf": len(lf), "sha256_raw_observed": _sha(raw), "bytes_raw_observed": len(raw)}


def _lf_sha(path):
    return file_pin(path)["sha256_lf"]


def _raw_sha_stream(path):
    """Raw sha256 and size of a (possibly binary, possibly large) file, read in 1 MiB pieces."""
    digest, size = hashlib.sha256(), 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def rule_sha(rule):
    return _sha(_canon(rule))


def _rel(path):
    """Package-relative with forward slashes when the path is inside the package; otherwise the path as given."""
    path = pathlib.Path(path)
    try:
        return path.resolve().relative_to(PACKAGE.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _key(path):
    """A comparable identity for a path (resolved, case-folded where the file system folds case)."""
    return os.path.normcase(str(pathlib.Path(path).resolve()))


def _get(node, *path):
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


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

    def number(self, text):
        value = float(text)
        if not math.isfinite(value):                           # e.g. 1e999 overflows to inf without any NaN/Infinity token
            self.nonfinite.append(text)
        return value

    def pairs(self, pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            self.duplicate_keys.extend(sorted({k for k in keys if keys.count(k) > 1}))
        return dict(pairs)


def strict_json(text):
    """Parse JSON and report what plain json.loads hides: NaN/Infinity tokens, numbers that overflow to infinity, and
    duplicate object keys. Every non-finite float in the result is recorded in `nonfinite` (0.4: exact, so callers
    scan record by record only when something was recorded)."""
    problems = _JsonProblems()
    value = json.loads(text, parse_constant=problems.constant, parse_float=problems.number, object_pairs_hook=problems.pairs)
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


# ---- the rules ------------------------------------------------------------------------------
def historical_decision(b, c, n_kinds, n_worlds):
    """The preserved grader's rule on counts: (exact one-sided p as a Fraction, passed).

    Seven gains is sufficient only when there are no losses. Losses contribute
    to the exact probability; they do not automatically veto a pass.
    """
    if any(type(v) is not int or v < 0 for v in (b, c, n_kinds, n_worlds)):
        raise ValueError("nonnegative integer counts required")
    p = Fraction(sum(math.comb(b + c, k) for k in range(b, b + c + 1)), 2 ** (b + c))
    passed = (b > c and p <= Fraction(HISTORICAL_RULE["alpha"])
              and n_kinds >= MIN_IMPROVED_KINDS and n_worlds >= MIN_IMPROVED_WORLDS)
    return p, passed


def historical_seed_result(b, c, kinds, worlds):
    """The preserved grader's rule, not a future release criterion."""
    if type(b) is not int or type(c) is not int or min(b, c) < 0:
        raise ValueError("nonnegative integer transition counts required")
    kinds, worlds = sorted(set(kinds)), sorted(set(worlds))
    p, passed = historical_decision(b, c, len(kinds), len(worlds))
    return {"p_one_sided": str(p), "p_float": float(p),
            "kinds_improved": kinds, "world_ids_improved": worlds,
            "worlds_improved": len(worlds), "passed": passed}


def what_the_recorded_description_gives(b, c, n_kinds, n_worlds):
    """What the RECOGNISED WRONG description decides on the same counts. Used ONLY to confirm that a 0.2 record is
    internally consistent with the recognised mistake -- never to decide anything."""
    d = RECOGNISED_MISTAKE["recorded_description"]
    return (b >= d["min_passing_b"] and c == d["broken_must_be"]
            and n_kinds >= d["min_improved_kinds"] and n_worlds >= d["min_improved_worlds"])


def describe_rule(sha):
    if sha == HISTORICAL_RULE_SHA256:
        return "the preserved historical rule"
    if sha == RECOGNISED_MISTAKE["recorded_description_sha256"]:
        return "the recognised 0.2 grading-description mistake (zero-loss veto, 7-gain minimum)"
    return "an UNRECOGNISED rule description (sha256 %s)" % (str(sha)[:16] if sha else "none")


def constants_problems():
    """The frozen constants must still match their frozen digests (an edit to the rule or the list shows here)."""
    bad = []
    if rule_sha(HISTORICAL_RULE) != HISTORICAL_RULE_SHA256:
        bad.append("HISTORICAL_RULE")
    if rule_sha(RECOGNISED_MISTAKE["recorded_description"]) != RECOGNISED_MISTAKE["recorded_description_sha256"]:
        bad.append("RECOGNISED_MISTAKE")
    if _sha(_canon(HISTORICAL_EXCEPTION)) != HISTORICAL_EXCEPTION_SHA256:
        bad.append("HISTORICAL_EXCEPTION")
    return bad


def historical_entry(kind, sha):
    """The frozen-list entry whose `kind` ("anchor" or "reading") has this sha256_lf, else None."""
    for name, entry in HISTORICAL_EXCEPTION.items():
        if entry[kind][1] == sha:
            return name
    return None


def side_by_side(recorded, applied):
    recorded = recorded if isinstance(recorded, dict) else {}
    return [{"field": key, "recorded_in_the_original_record_WRONG": recorded.get(key, ABSENT),
             "preserved_historical_rule_APPLIED": applied.get(key, ABSENT)}
            for key in sorted(set(recorded) | set(applied))]


def compare_seed_result(frozen, rescored):
    """Compare each decision and its inputs, including breadth and exact p."""
    fb, fc = _count(frozen.get("wrong_to_right")), _count(frozen.get("right_to_wrong"))
    fields = {
        "counts": [fb, fc] == [rescored["gained"], rescored["broken"]],
        "passed": type(frozen.get("passed")) is bool and frozen["passed"] == rescored["passed"],
        "p_one_sided": frozen.get("p_one_sided") == rescored["p_one_sided"],
        "improved_kinds": frozen.get("improved_kinds") == rescored["kinds_improved"],
        "improved_worlds": frozen.get("improved_worlds") == rescored["world_ids_improved"],
    }
    return {"rescored_gained_broken": [rescored["gained"], rescored["broken"]],
            "frozen_gained_broken": [fb, fc], "rescored_passed": rescored["passed"],
            "frozen_passed": frozen.get("passed"), "field_agreement": fields,
            "agree": all(fields.values())}


# ---- originals: never rewritten -------------------------------------------------------------
def protected_paths(*extra):
    """Every original record the historical list names (anchors, readings, frozen grader readings, run manifests and
    the label-deciding files they pin), plus any extra file named on the command line."""
    paths = []
    for entry in HISTORICAL_EXCEPTION.values():
        for key in ("anchor", "reading", "frozen_grader_reading"):
            paths.append(PACKAGE / entry[key][0])
        for rel, _ in entry["receipt_manifests"].values():
            manifest = PACKAGE / rel
            paths.append(manifest)
            paths.extend(manifest.parent / "collected/results/artifacts" / name for name in LABEL_FILES)
    paths.extend(pathlib.Path(p) for p in extra if p)
    unique = {}
    for p in paths:
        unique.setdefault(_key(p), p)
    return [unique[k] for k in sorted(unique)]


def snapshot_paths(*given):
    """What is hashed before and after a run: the small original records of every listed study (anchors, readings,
    frozen grader readings, run manifests), the label-deciding files of the listed study this run reads (if any),
    and every file named on the command line. The overwrite guard (protected_paths) is wider: it covers them all."""
    names = set()
    for p in given:
        if p and pathlib.Path(p).is_file():
            sha = _lf_sha(p)
            names |= {n for n, e in HISTORICAL_EXCEPTION.items() if sha in (e["anchor"][1], e["reading"][1])}
    paths = []
    for name, entry in HISTORICAL_EXCEPTION.items():
        paths.extend(PACKAGE / entry[key][0] for key in ("anchor", "reading", "frozen_grader_reading"))
        for rel, _ in entry["receipt_manifests"].values():
            paths.append(PACKAGE / rel)
            if name in names:
                paths.extend((PACKAGE / rel).parent / "collected/results/artifacts" / f for f in LABEL_FILES)
    paths.extend(pathlib.Path(p) for p in given if p)
    unique = {}
    for p in paths:
        unique.setdefault(_key(p), p)
    return [unique[k] for k in sorted(unique)]


def snapshot(paths):
    """Raw sha256 of each existing path (None when absent), keyed by package-relative path."""
    return {_rel(p): (_raw_sha_stream(p)[0] if pathlib.Path(p).is_file() else None) for p in paths}


def _originals_check(run, paths, before, out_path, guard):
    after = snapshot(paths)
    changed = sorted(rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel))
    if changed:
        run.fail("ORIGINALS_UNCHANGED", "ORIGINAL_CHANGED_DURING_RUN", "these originals changed during the run: %s" % changed[:6])
    if out_path and _key(out_path) in {_key(p) for p in guard}:
        run.fail("ORIGINALS_UNCHANGED", "OUTPUT_WOULD_OVERWRITE_ORIGINAL", "--out %s is an original record; nothing was written" % _rel(out_path))
    run.passed("ORIGINALS_UNCHANGED", "%d original files byte-identical before and after (raw sha256)" % sum(1 for v in after.values() if v))
    return {"files_checked": len(after), "files_present": sum(1 for v in after.values() if v), "unchanged": not changed,
            "raw_sha256_after": after}


def _write_output(run, out_path, record):
    if not out_path or any(r.startswith("OUTPUT_WOULD_OVERWRITE_ORIGINAL:") for r in run.reasons):
        return False
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, indent=1, sort_keys=True))
    return True


# ---- historical evidence ----------------------------------------------------------------------
def historical_evidence(name, anchor, receipt_override=None, frozen_reading=None, compare_frozen=True):
    """READS files only. Verify the original evidence behind a frozen-list anchor. Returns (items, problems) where
    problems are (code, detail) pairs. Nothing is imported and nothing is written."""
    entry = HISTORICAL_EXCEPTION[name]
    items, problems = [], []

    def pinned(what, rel, expected):
        path = PACKAGE / rel
        if not path.is_file():
            items.append({"what": what, "path": rel, "pinned_sha256_lf": expected, "observed_sha256_lf": None, "status": "ABSENT"})
            problems.append(("HISTORICAL_EVIDENCE_INCOMPLETE", "%s is absent: %s" % (what, rel)))
            return None
        observed = _lf_sha(path)
        items.append({"what": what, "path": rel, "pinned_sha256_lf": expected, "observed_sha256_lf": observed,
                      "status": "MATCH" if observed == expected else "ALTERED"})
        if observed != expected:
            problems.append(("HISTORICAL_EVIDENCE_ALTERED", "%s differs from its frozen digest: %s" % (what, rel)))
            return None
        return path

    if receipt_override:
        problems.append(("HISTORICAL_EXCEPTION_REQUIRES_ORIGINAL_EVIDENCE",
                         "receipt overrides %s are not allowed: the historical exception reads the original receipts only" % sorted(receipt_override)))
    if not compare_frozen:
        problems.append(("HISTORICAL_EXCEPTION_REQUIRES_FROZEN_READING",
                         "--no-frozen-reading is not allowed: the historical exception is checked against the frozen grader's reading"))
    frel, fsha = entry["frozen_grader_reading"]
    if frozen_reading is not None and _key(frozen_reading) != _key(PACKAGE / frel):
        problems.append(("HISTORICAL_EXCEPTION_REQUIRES_ORIGINAL_EVIDENCE",
                         "--frozen-reading %s is not the original %s" % (_rel(frozen_reading), frel)))
    pinned("frozen grader reading", frel, fsha)

    if sorted(str(s) for s in anchor.get("seed_set") or []) != sorted(entry["receipt_manifests"]):
        problems.append(("HISTORICAL_EXCEPTION_INCOMPATIBLE", "anchor seed set %s is not the frozen %s" % (anchor.get("seed_set"), sorted(entry["receipt_manifests"]))))
    for seed, (mrel, msha) in sorted(entry["receipt_manifests"].items()):
        anchored_dir = _get(anchor, "seeds", seed, "receipt_dir")
        if anchored_dir is None or anchored_dir.rstrip("/") + "/artifact_manifest.json" != mrel:
            problems.append(("HISTORICAL_EXCEPTION_INCOMPATIBLE", "seed %s: anchored receipt %r is not the frozen %s" % (seed, anchored_dir, mrel)))
        mpath = pinned("run manifest, seed %s" % seed, mrel, msha)
        if mpath is None:
            continue
        try:
            manifest, mprob = strict_json(mpath.read_text(encoding="utf-8"))
            rows = {r["name"]: r for r in manifest["artifacts"]}
            assert not mprob.duplicate_keys and not mprob.nonfinite
        except Exception as error:
            problems.append(("HISTORICAL_EVIDENCE_INCOMPLETE", "seed %s: run manifest unreadable (%s)" % (seed, type(error).__name__)))
            continue
        art = mpath.parent / "collected/results/artifacts"
        for fname in LABEL_FILES:
            row, path = rows.get(fname), art / fname
            what = "label-deciding file %s, seed %s" % (fname, seed)
            if not isinstance(row, dict) or not isinstance(row.get("sha256"), str) or type(row.get("bytes")) is not int:
                problems.append(("HISTORICAL_EVIDENCE_INCOMPLETE", "%s: the run manifest has no digest for it" % what))
                continue
            if not path.is_file():
                items.append({"what": what, "path": _rel(path), "pinned_sha256_lf": row["sha256"], "observed_sha256_lf": None, "status": "ABSENT"})
                problems.append(("HISTORICAL_EVIDENCE_INCOMPLETE", "%s is absent" % what))
                continue
            pin = file_pin(path)
            ok = pin["sha256_lf"] == row["sha256"] and pin["bytes_lf"] == row["bytes"]
            items.append({"what": what, "path": _rel(path), "pinned_sha256_lf": row["sha256"], "observed_sha256_lf": pin["sha256_lf"],
                          "status": "MATCH" if ok else "ALTERED"})
            if not ok:
                problems.append(("HISTORICAL_EVIDENCE_ALTERED", "%s differs from the run's own manifest" % what))
            if fname.endswith("_predictions.json"):
                anchored = _get(anchor, "seeds", seed, "predictions", fname[:-len("_predictions.json")], "sha256_lf")
                if anchored != row["sha256"]:
                    problems.append(("HISTORICAL_EVIDENCE_ALTERED", "%s: the anchor's pin and the run's manifest disagree" % what))
        # checkpoint digests AS RECORDED: the frozen manifest must carry a well-formed digest for every checkpoint;
        # a checkpoint that is present here must match it. The weights are not decision evidence and are excluded from
        # this checkout on purpose, so an absent weight file is reported, not refused.
        ckpts = [r for r in rows.values() if str(r.get("name", "")).endswith(".pt")]
        summary = {"what": "checkpoint digests as recorded, seed %s" % seed, "path": _rel(art), "recorded": len(ckpts),
                   "present_and_matching": 0, "present_and_altered": 0, "absent_here": 0}
        if not ckpts:
            problems.append(("HISTORICAL_EVIDENCE_INCOMPLETE", "seed %s: the run manifest records no checkpoint digest" % seed))
        for row in ckpts:
            if not (isinstance(row.get("sha256"), str) and re.fullmatch("[0-9a-f]{64}", row["sha256"]) and type(row.get("bytes")) is int):
                problems.append(("HISTORICAL_EVIDENCE_INCOMPLETE", "seed %s: checkpoint %s has no well-formed recorded digest" % (seed, row.get("name"))))
                continue
            path = art / row["name"]
            if not path.is_file():
                summary["absent_here"] += 1
                continue
            digest, size = _raw_sha_stream(path)
            if digest == row["sha256"] and size == row["bytes"]:
                summary["present_and_matching"] += 1
            else:
                summary["present_and_altered"] += 1
                problems.append(("HISTORICAL_EVIDENCE_ALTERED", "seed %s: checkpoint %s differs from its recorded digest" % (seed, row["name"])))
        summary["status"] = ("ALTERED" if summary["present_and_altered"] else
                             "RECORDED_DIGESTS_ONLY" if summary["absent_here"] == summary["recorded"] else "MATCH")
        items.append(summary)
    return items, problems


# ---------------------------------------------------------------------------------------------
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
    return {"schema": ANCHOR_SCHEMA, "written": datetime.date.today().isoformat(), "tool_version": TOOL_VERSION,
            "hash_policy": HASH_POLICY,
            "study": {"path": _rel(study_path), "pin": file_pin(study_path)}, "seed_set": sorted(seeds),
            "grader": {"path": _rel(GRADER), "pin": file_pin(GRADER)},
            "checker": {"code_closure": code_closure_pins()},
            "tool": {"path": _rel(__file__), "pin": file_pin(__file__)},
            "pass_rule": dict(HISTORICAL_RULE), "pass_rule_sha256": HISTORICAL_RULE_SHA256,
            "seeds": seeds, "custody": CUSTODY}


def write_anchor(study_path, anchor_path, receipt_override, material=None):
    """Write a NEW anchor (schema 0.3, the preserved rule). Create-only: an existing file -- above all an original
    historical anchor -- is never overwritten."""
    target = pathlib.Path(anchor_path)
    if target.exists() or _key(target) in {_key(p) for p in protected_paths()}:
        print("ANCHOR_REFUSED: %s already exists; anchors are create-only and an original record is never rewritten" % _rel(target))
        return 2
    bad = constants_problems()
    if bad:
        print("ANCHOR_REFUSED: TOOL_CONSTANTS_ALTERED %s" % bad)
        return 2
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
    with open(target, "x", encoding="utf-8", newline="\n") as handle:        # "x": fails if the file appeared meanwhile
        handle.write(json.dumps(anchor, indent=1, sort_keys=True))
    print("anchor written: %s  sha256_lf %s" % (_rel(target), _lf_sha(target)[:16]))
    return 0


def anchor_missing_fields(anchor):
    """Every field the checks rely on. A missing one is INCOMPLETE evidence, never a silent default."""
    need = [("schema",), ("study", "path"), ("study", "pin", "sha256_lf"), ("seed_set",), ("grader", "pin", "sha256_lf"),
            ("checker", "code_closure"), ("checker", "profile_digest"), ("course_digest",), ("population", "digest"),
            ("population", "question_ids"), ("population", "kind_of"), ("population", "world_of"),
            ("expected_record_ids",), ("expected_record_count",), ("seeds",), ("pass_rule",), ("tool", "pin", "sha256_lf"),
            ("custody",)]
    if anchor.get("schema") == ANCHOR_SCHEMA:
        need += [("pass_rule_sha256",), ("tool_version",)]
    missing = [".".join(path) for path in need if _get(anchor, *path) is None]
    if missing:
        return missing
    if not isinstance(anchor["seed_set"], list) or not anchor["seed_set"]:
        missing.append("seed_set (empty)")
    closure = anchor["checker"]["code_closure"]
    if not isinstance(closure, dict) or not closure or any(not isinstance(p, dict) or not p.get("sha256_lf") for p in closure.values()):
        missing.append("checker.code_closure (empty, or an entry without sha256_lf)")
    ids = anchor["expected_record_ids"]
    if not isinstance(ids, list) or not ids or anchor["expected_record_count"] != len(ids):
        missing.append("expected_record_ids / expected_record_count (empty or inconsistent)")
    if not isinstance(anchor["pass_rule"], dict):
        missing.append("pass_rule (not an object)")
    for seed in anchor["seed_set"] if isinstance(anchor["seed_set"], list) else []:
        for ph in PHASES:
            if not _get(anchor, "seeds", str(seed), "predictions", ph, "sha256_lf"):
                missing.append("seeds.%s.predictions.%s.sha256_lf" % (seed, ph))
        if not _get(anchor, "seeds", str(seed), "receipt_dir"):
            missing.append("seeds.%s.receipt_dir" % seed)
    return missing


# ---------------------------------------------------------------------------------------------
class _Run:
    def __init__(self, names=SAFE_CHECKS + CHECKER_CHECKS + FINAL_CHECKS):
        self.reasons, self.failures = [], []
        self.checks = collections.OrderedDict((name, {"status": "NOT_RUN", "detail": "not reached"}) for name in names)

    def fail(self, check, code, detail):
        self.reasons.append("%s:%s" % (code, detail))
        self.failures.append((check, code, detail))
        self.checks[check] = {"status": "FAIL", "detail": detail if self.checks[check]["status"] != "FAIL" else self.checks[check]["detail"] + " | " + detail}

    def passed(self, check, detail=""):
        if self.checks[check]["status"] != "FAIL":
            self.checks[check] = {"status": "PASS", "detail": detail}

    def not_run(self, check, detail):
        if self.checks[check]["status"] != "FAIL":
            self.checks[check] = {"status": "NOT_RUN", "detail": detail}

    def failed(self, *names):
        return any(self.checks[n]["status"] == "FAIL" for n in names)


def _constants_check(run):
    bad = constants_problems()
    if bad:
        run.fail("TOOL_CONSTANTS", "TOOL_CONSTANTS_ALTERED", "frozen constants no longer match their frozen digests: %s" % bad)
    run.passed("TOOL_CONSTANTS", "rule %s, recognised mistake %s, historical list %s" % (
        HISTORICAL_RULE_SHA256[:12], RECOGNISED_MISTAKE["recorded_description_sha256"][:12], HISTORICAL_EXCEPTION_SHA256[:12]))


def _read_anchor(run, anchor_path):
    try:
        anchor, problems = strict_json(pathlib.Path(anchor_path).read_text(encoding="utf-8"))
    except Exception as error:
        run.fail("ANCHOR_READABLE", "ANCHOR_UNREADABLE", "%s: %s" % (type(error).__name__, str(error)[:120]))
        return None
    if not isinstance(anchor, dict) or problems.duplicate_keys or problems.nonfinite:
        run.fail("ANCHOR_READABLE", "ANCHOR_MALFORMED", "not a JSON object, or duplicate keys %s / non-finite numbers %s" % (
            problems.duplicate_keys[:5], problems.nonfinite[:5]))
        return None
    if anchor.get("schema") not in KNOWN_ANCHOR_SCHEMAS:
        run.fail("ANCHOR_READABLE", "ANCHOR_SCHEMA_UNKNOWN", "anchor schema %r is not one of %s" % (anchor.get("schema"), list(KNOWN_ANCHOR_SCHEMAS)))
        return None
    missing = anchor_missing_fields(anchor)
    if missing:
        run.fail("ANCHOR_READABLE", "ANCHOR_INCOMPLETE", "missing or empty: %s" % missing[:8])
        return None
    run.passed("ANCHOR_READABLE", _rel(anchor_path))
    return anchor


def _anchor_rule_and_mode(run, anchor, anchor_path, mode):
    """RULE_DESCRIPTION, and the anchor-level part of HISTORICAL_EVIDENCE. Returns what the output needs to show."""
    recorded = anchor["pass_rule"]
    rsha, asha = rule_sha(recorded), _lf_sha(anchor_path)
    info = {"anchor_sha256_lf": asha, "recorded_rule": recorded, "recorded_rule_sha256": rsha, "entry": None, "evidence": None}
    if mode == TRUSTED:
        run.checks["HISTORICAL_EVIDENCE"] = dict(NOT_REQUESTED_TRUSTED)
        if rsha != HISTORICAL_RULE_SHA256:
            listed = historical_entry("anchor", asha)
            run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_MISMATCH",
                     "the anchor records %s, not the preserved historical rule; refused for trusted acceptance%s" % (
                         describe_rule(rsha), (" (this is the frozen historical anchor %r; it can be read only with %s)" % (listed, HISTORICAL_FLAG)) if listed else ""))
        elif anchor["schema"] == ANCHOR_SCHEMA and anchor.get("pass_rule_sha256") != rsha:
            run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_MISMATCH", "pass_rule_sha256 does not match the recorded pass_rule")
        if anchor["schema"] != ANCHOR_SCHEMA:
            run.fail("ANCHOR_READABLE", "ANCHOR_SCHEMA_OUTDATED", "anchor schema %r; trusted mode needs %r -- write a NEW anchor with --write-anchor "
                     "(create-only; the original is kept as history)" % (anchor["schema"], ANCHOR_SCHEMA))
        run.passed("RULE_DESCRIPTION", "the preserved historical rule (sha256 %s)" % rsha[:16])
        return info
    name = historical_entry("anchor", asha)
    info["entry"] = name
    if name is None:
        run.fail("HISTORICAL_EVIDENCE", "HISTORICAL_EXCEPTION_UNKNOWN_ANCHOR",
                 "anchor sha256_lf %s is not on the frozen historical list %s; new runs never receive the historical exception" % (
                     asha[:16], sorted(HISTORICAL_EXCEPTION)))
        if rsha != HISTORICAL_RULE_SHA256:
            run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_MISMATCH", "the anchor records %s; outside the frozen list that is refused" % describe_rule(rsha))
        run.passed("RULE_DESCRIPTION", "the preserved historical rule; this anchor needs no exception -- run without %s" % HISTORICAL_FLAG)
        return info
    if rsha != RECOGNISED_MISTAKE["recorded_description_sha256"]:
        run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_UNRECOGNISED", "the listed anchor records %s, not the recognised mistake" % describe_rule(rsha))
    run.passed("RULE_DESCRIPTION", "WRONG description recorded: %s; the preserved historical rule is applied instead" % describe_rule(rsha))
    if anchor["schema"] != HISTORICAL_ANCHOR_SCHEMA or anchor["tool"]["pin"]["sha256_lf"] != RECOGNISED_MISTAKE["written_by_tool_sha256_lf"]:
        run.fail("HISTORICAL_EVIDENCE", "HISTORICAL_EXCEPTION_INCOMPATIBLE", "schema %r / writing tool %s are not the recognised 0.2 ones" % (
            anchor["schema"], str(anchor["tool"]["pin"]["sha256_lf"])[:16]))
    return info


def _safe_checks(run, study_path, anchor_path, receipt_override, mode=TRUSTED, frozen_reading=None, compare_frozen=True):
    """Step 1: read files only. Returns (anchor, study, per-seed prediction lists, historical info) -- any may be None."""
    _constants_check(run)
    anchor = _read_anchor(run, anchor_path)
    if anchor is None:
        return None, None, {}, None
    info = _anchor_rule_and_mode(run, anchor, anchor_path, mode)
    if run.failed("TOOL_CONSTANTS", "ANCHOR_READABLE", "RULE_DESCRIPTION", "HISTORICAL_EVIDENCE"):
        return anchor, None, {}, info                     # the anchor itself is refused: nothing behind it is read
    if mode == HISTORICAL:
        items, problems = historical_evidence(info["entry"], anchor, receipt_override, frozen_reading, compare_frozen)
        info["evidence"] = items
        for code, detail in problems:
            run.fail("HISTORICAL_EVIDENCE", code, detail)
        run.passed("HISTORICAL_EVIDENCE", "%d original evidence items verified against frozen or recorded digests" % len(items))
    try:
        study = json.loads(pathlib.Path(study_path).read_text(encoding="utf-8"))
        jobs = study["jobs"]
    except Exception as error:
        run.fail("STUDY_IDENTITY", "STUDY_UNREADABLE", "%s: %s" % (type(error).__name__, str(error)[:120]))
        return anchor, None, {}, info
    if _lf_sha(study_path) != anchor["study"]["pin"]["sha256_lf"]:
        run.fail("STUDY_IDENTITY", "STUDY_IDENTITY", "the study file differs from the one the anchor was written for")
    run.passed("STUDY_IDENTITY")
    seeds_now = sorted(str(j["model_seed"]) for j in jobs)
    if seeds_now != sorted(str(s) for s in anchor["seed_set"]) or len(set(seeds_now)) != len(seeds_now):
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
        predictions[seed] = {"receipt_dir": _rel(rdir), "receipt_resolved_from": how,
                             "phases": {ph: {"predictions_sha256_lf": None, "predictions": None} for ph in PHASES}}
        if mode == HISTORICAL and how != "package-relative":
            run.fail("HISTORICAL_EVIDENCE", "HISTORICAL_EVIDENCE_INCOMPLETE", "seed %s: the original receipt is not inside this package (%s); nothing read" % (seed, how))
            continue
        art = rdir / "collected/results/artifacts"
        for ph in PHASES:
            ppath = art / ("%s_predictions.json" % ph)
            slot = predictions[seed]["phases"][ph]
            if not ppath.is_file():
                run.fail("ID_SET", "MISSING_OR_EXTRA_PREDICTIONS", "%s:%s:file absent" % (seed, ph))
                continue
            slot["predictions_sha256_lf"] = _lf_sha(ppath)
            if slot["predictions_sha256_lf"] != _get(anchor, "seeds", seed, "predictions", ph, "sha256_lf"):
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
            for p in (preds if problems.nonfinite else ()):      # the parser records every non-finite float, so no record
                if _has_nonfinite(p):                             # can hold one when nothing was recorded
                    run.fail("FINITE_NUMBERS", "NONFINITE_NUMBER", "%s:%s:%s" % (seed, ph, str(p.get("record_id"))[:30]))
            ids = [p.get("record_id") for p in preds]
            if len(ids) != len(set(ids)):
                run.fail("ID_SET", "DUPLICATE_IDS", "%s:%s:%d duplicate record ids" % (seed, ph, len(ids) - len(set(ids))))
            if set(ids) != set(expected):
                run.fail("ID_SET", "MISSING_OR_EXTRA_PREDICTIONS", "%s:%s:missing %d, extra %d" % (seed, ph, len(set(expected) - set(ids)), len(set(ids) - set(expected))))
            slot["predictions"] = preds
    for name in ("PREDICTIONS_IDENTITY", "ID_SET", "FINITE_NUMBERS", "WELL_FORMED_JSON"):
        run.passed(name)
    return anchor, study, predictions, info


def _mode_block(mode):
    return {"name": mode, "flag": HISTORICAL_FLAG if mode == HISTORICAL else None,
            "requested_explicitly": mode == HISTORICAL}


def _rule_block(recorded, applied_recorded=None):
    rsha = rule_sha(recorded) if isinstance(recorded, dict) else None
    return {"applied": dict(HISTORICAL_RULE), "applied_sha256": HISTORICAL_RULE_SHA256,
            "recorded_in_anchor": recorded, "recorded_sha256": rsha,
            "recorded_describes": describe_rule(rsha) if rsha else None,
            "recorded_is_the_applied_rule": rsha == HISTORICAL_RULE_SHA256,
            "recorded_is_the_recognised_mistake": rsha == RECOGNISED_MISTAKE["recorded_description_sha256"],
            **({"rule_the_original_tool_applied": applied_recorded} if applied_recorded is not None else {})}


def _historical_block(info, decisions=None):
    info = info or {}
    return {"warning": WARNING, "flag": HISTORICAL_FLAG, "entry": info.get("entry"),
            "covers_only": sorted(HISTORICAL_EXCEPTION), "frozen_list_sha256": HISTORICAL_EXCEPTION_SHA256,
            "recognised_mistake": RECOGNISED_MISTAKE,
            "rule_descriptions": {"recorded_in_the_original_record_WRONG": info.get("recorded_rule"),
                                  "preserved_historical_rule_APPLIED": dict(HISTORICAL_RULE)},
            "side_by_side": side_by_side(info.get("recorded_rule"), HISTORICAL_RULE),
            "evidence": info.get("evidence"), "decisions": decisions}


def _print_historical(block):
    print(block["warning"])
    rows = block["side_by_side"]
    fmt = lambda v: v if v == ABSENT else json.dumps(v)
    left, right = "recorded in the original record (WRONG)", "preserved historical rule (APPLIED)"
    w0 = max([len("field")] + [len(r["field"]) for r in rows])
    w1 = max([len(left)] + [len(fmt(r["recorded_in_the_original_record_WRONG"])) for r in rows])
    print("  %-*s | %-*s | %s" % (w0, "field", w1, left, right))
    for r in rows:
        print("  %-*s | %-*s | %s" % (w0, r["field"], w1, fmt(r["recorded_in_the_original_record_WRONG"]), fmt(r["preserved_historical_rule_APPLIED"])))


def rescore(study_path, anchor_path, receipt_override, out_path, material=None, frozen_reading=None,
            compare_frozen=True, safe_only=False, historical_compatibility=False):
    mode = HISTORICAL if historical_compatibility else TRUSTED
    run = _Run()
    guard = protected_paths(anchor_path, study_path, frozen_reading)
    watched = snapshot_paths(anchor_path, study_path, frozen_reading)
    before = snapshot(watched)
    anchor, study, predictions, info = _safe_checks(run, study_path, anchor_path, receipt_override or {}, mode, frozen_reading, compare_frozen)
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
        for seed, info_seed in predictions.items():
            art = (PACKAGE / info_seed["receipt_dir"]) if not pathlib.Path(info_seed["receipt_dir"]).is_absolute() else pathlib.Path(info_seed["receipt_dir"])
            art = art / "collected/results/artifacts"
            seed_report = {"receipt_dir": info_seed["receipt_dir"], "receipt_resolved_from": info_seed["receipt_resolved_from"], "phases": {}}
            question_correct = {}
            for ph in PHASES:
                slot = info_seed["phases"][ph]
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
            before_q, after_q = question_correct.get("course_p00", {}), question_correct.get("course_p10", {})
            gained = [q for q in pop if not before_q.get(q, False) and after_q.get(q, False)]
            lost = [q for q in pop if before_q.get(q, False) and not after_q.get(q, False)]
            kinds = sorted({anchor["population"]["kind_of"][q] for q in gained})
            worlds = sorted({anchor["population"]["world_of"][q] for q in gained})
            seed_report.update({"frozen_18_before": sum(1 for q in pop if before_q.get(q, False)), "frozen_18_after": sum(1 for q in pop if after_q.get(q, False)),
                                "gained": len(gained), "broken": len(lost),
                                **historical_seed_result(len(gained), len(lost), kinds, worlds)})
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

        # the frozen grader's reading: beside the study by default; --frozen-reading when it lives elsewhere; in
        # historical mode always the original on the frozen list (verified in step 1)
        if not compare_frozen:
            run.checks["FROZEN_GRADER_AGREEMENT"] = {"status": "NOT_REQUESTED", "detail": "--no-frozen-reading"}
        else:
            if mode == HISTORICAL:
                fpath = PACKAGE / HISTORICAL_EXCEPTION[info["entry"]]["frozen_grader_reading"][0]
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
                        per[seed] = compare_seed_result(gs, s)
                    comparison.update({"frozen_label": g.get("label"), "labels_agree": g.get("label") == label, "per_seed": per})
                    comparison["seed_sets_agree"] = set(g.get("seeds") or {}) == set(per_seed)
                    if not comparison["labels_agree"] or not comparison["seed_sets_agree"] or not all(v["agree"] for v in per.values()):
                        run.fail("FROZEN_GRADER_AGREEMENT", "FROZEN_GRADER_DISAGREES", "label, seed set or per-seed counts/decision/probability/breadth differ between the fresh rescore and %s" % _rel(fpath))
                    run.passed("FROZEN_GRADER_AGREEMENT")
                except Exception as error:
                    run.fail("FROZEN_GRADER_AGREEMENT", "FROZEN_READING_UNREADABLE", "%s: %s" % (type(error).__name__, str(error)[:120]))

        if mode == HISTORICAL:
            entry = HISTORICAL_EXCEPTION[info["entry"]]
            got = {seed: {"gained": s["gained"], "broken": s["broken"], "p_one_sided": s["p_one_sided"], "passed": s["passed"]} for seed, s in per_seed.items()}
            if got != entry["decisions"] or label != entry["label"]:
                run.fail("HISTORICAL_DECISIONS", "HISTORICAL_DECISION_MISMATCH", "the fresh rescore does not reproduce the frozen historical decisions of %s" % info["entry"])
            run.passed("HISTORICAL_DECISIONS", "all %d frozen decisions and the label %s reproduced" % (len(entry["decisions"]), entry["label"]))
        else:
            run.checks["HISTORICAL_DECISIONS"] = dict(NOT_REQUESTED_TRUSTED)

    originals = _originals_check(run, watched, before, out_path, guard)
    statuses = [c["status"] for c in run.checks.values()]
    ok = "HISTORICAL_COMPATIBILITY_OK" if mode == HISTORICAL else "RESCORE_OK"
    verdict = "REJECT" if run.reasons else ("RESCORE_INCOMPLETE" if "NOT_RUN" in statuses else ok)
    if run.reasons:
        label = "VOID_REJECTED"
    elif not imported:
        label = "NOT_DERIVED"
    hist_block = _historical_block(info, per_seed and {s: {k: v[k] for k in ("gained", "broken", "p_one_sided", "passed")} for s, v in per_seed.items()}) if mode == HISTORICAL else None
    reading = {"schema": SCHEMA, "tool_version": TOOL_VERSION, "mode": _mode_block(mode),
               "verdict": verdict, "label_rederived": label, "reject_reasons": run.reasons, "checks": run.checks,
               "imported_checker_code": imported, "bytecode_policy": bytecode_policy, "material_supplied_by_caller": material is not None,
               "anchor": {"path": _rel(anchor_path), "pin": file_pin(anchor_path) if pathlib.Path(anchor_path).is_file() else None},
               "tool": {"path": _rel(__file__), "pin": file_pin(__file__)}, "hash_policy": HASH_POLICY["policy_id"],
               "rule": _rule_block(info["recorded_rule"] if info else None),
               "historical_exception": hist_block, "originals": originals,
               "per_seed": per_seed, "comparison_with_frozen_grader": comparison, "custody": CUSTODY,
               "boundary": "the scoring files' correct flags were NOT read for the label; every prediction was re-checked with the private checker"}
    _write_output(run, out_path, reading)
    print(json.dumps({k: reading[k] for k in ("verdict", "label_rederived", "reject_reasons")}, indent=1))
    print("  mode: %s" % mode)
    if hist_block:
        _print_historical(hist_block)
    print("  checks:", ", ".join("%s=%s" % (k, v["status"]) for k, v in run.checks.items()))
    for seed, s in per_seed.items():
        print("  seed %s: frozen18 %s -> %s, gained %d broken %d, p %s, passed %s, rescored %s, disagreements %s" % (
            seed, s["frozen_18_before"], s["frozen_18_after"], s["gained"], s["broken"], s["p_one_sided"], s["passed"],
            [s["phases"][ph]["rescored"] for ph in PHASES], [s["phases"][ph]["disagreements"] for ph in PHASES]))
    return {"RESCORE_OK": 0, "REJECT": 2, "RESCORE_INCOMPLETE": 3, "HISTORICAL_COMPATIBILITY_OK": 4}[verdict]


# ---- verify a committed reading WITHOUT rescoring ---------------------------------------------
def reading_missing_fields(reading):
    need = [("anchor", "path"), ("anchor", "pin", "sha256_lf"), ("tool", "pin", "sha256_lf"), ("per_seed",),
            ("label_rederived",), ("verdict",), ("reject_reasons",), ("checks",)]
    if reading.get("schema") == SCHEMA:
        need += [("rule", "recorded_in_anchor"), ("rule", "applied"), ("mode", "name")]
    elif reading.get("schema") == READING_SCHEMA_0_3:
        need += [("anchor_rule_metadata",), ("historical_rule_applied",)]
    else:
        need += [("comparison_with_frozen_grader", "frozen_reading_path")]
    missing = [".".join(p) for p in need if _get(reading, *p) is None]
    if missing:
        return missing
    if not isinstance(reading["per_seed"], dict) or not reading["per_seed"]:
        missing.append("per_seed (empty)")
        return missing
    for seed, s in reading["per_seed"].items():
        for field in ("gained", "broken", "kinds_improved", "worlds_improved", "passed", "receipt_dir"):
            if _get(s, field) is None:
                missing.append("per_seed.%s.%s" % (seed, field))
        for ph in PHASES:
            if not _get(s, "phases", ph, "predictions_sha256_lf"):
                missing.append("per_seed.%s.phases.%s.predictions_sha256_lf" % (seed, ph))
    return missing


def _merge(run, sub, default_check):
    """Carry the evidence reasons of a sub-run over, under the reading check they belong to."""
    for check, code, detail in sub.failures:
        if check == "TOOL_CONSTANTS":
            continue                                          # already checked once, on this run
        run.fail(check if check in ("RULE_DESCRIPTION", "HISTORICAL_EVIDENCE") else default_check, code, detail)


def _reading_consistency(run, reading, anchor, entry=None):
    seeds_r, seeds_a = sorted(reading["per_seed"]), sorted(str(s) for s in anchor["seed_set"])
    if seeds_r != seeds_a:
        run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", "reading seeds %s, anchored seeds %s" % (seeds_r, seeds_a))
    for seed in sorted(set(seeds_r) & set(seeds_a)):
        s = reading["per_seed"][seed]
        for ph in PHASES:
            if _get(s, "phases", ph, "predictions_sha256_lf") != _get(anchor, "seeds", seed, "predictions", ph, "sha256_lf"):
                run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", "%s:%s: the reading's predictions digest is not the anchor's" % (seed, ph))
        if s.get("receipt_dir") != _get(anchor, "seeds", seed, "receipt_dir"):
            run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", "%s: the reading's receipt is not the anchor's" % seed)
        for field in ("gained", "broken", "worlds_improved"):
            if type(s.get(field)) is not int or s[field] < 0:
                run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", "%s: %s is not a nonnegative integer" % (seed, field))
        if not isinstance(s.get("kinds_improved"), list):
            run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", "%s: kinds_improved is not a list" % seed)
    if entry is not None and _get(reading, "comparison_with_frozen_grader", "frozen_reading_path") != entry["frozen_grader_reading"][0]:
        run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", "the reading was compared with %r, not the original frozen grader reading %s" % (
            _get(reading, "comparison_with_frozen_grader", "frozen_reading_path"), entry["frozen_grader_reading"][0]))
    run.passed("READING_CONSISTENCY", "seeds, predictions digests and receipts agree with the anchor")


def replay_historical(name, recorded_per_seed, gate, recorded_label=None):
    """Re-derive each seed decision from the RECORDED counts with the preserved historical rule, and require three-way
    agreement: the replay, the frozen grader's reading, and the frozen list. Also confirm that the decision the 0.2
    record states is exactly what the recognised wrong description gives on those counts. Returns (rows, label, problems)."""
    entry = HISTORICAL_EXCEPTION[name]
    rows, problems = {}, []
    for seed in sorted(set(entry["decisions"]) | set(recorded_per_seed)):
        rec, frozen = recorded_per_seed.get(seed), entry["decisions"].get(seed)
        g = _get(gate, "seeds", seed, "G_LEARN_population")
        if rec is None or frozen is None or not isinstance(g, dict):
            problems.append(("HISTORICAL_EVIDENCE_INCOMPLETE", "seed %s is missing from the reading, the frozen list or the frozen grader reading" % seed))
            continue
        b, c, nk, nw = rec["gained"], rec["broken"], len(rec["kinds_improved"]), rec["worlds_improved"]
        p, passed = historical_decision(b, c, nk, nw)
        grader = {"gained": _count(g.get("wrong_to_right")), "broken": _count(g.get("right_to_wrong")), "p_one_sided": g.get("p_one_sided"),
                  "passed": g.get("passed"), "kinds_improved": sorted(g.get("improved_kinds") or []), "worlds_improved": len(g.get("improved_worlds") or [])}
        replay = {"gained": b, "broken": c, "p_one_sided": str(p), "passed": passed, "kinds_improved": sorted(rec["kinds_improved"]), "worlds_improved": nw}
        agree = ({k: replay[k] for k in frozen} == frozen and replay == grader)
        wrong = what_the_recorded_description_gives(b, c, nk, nw)
        rows[seed] = {"replay_with_the_preserved_rule": replay, "frozen_grader": grader, "frozen_list": frozen, "agree": agree,
                      "decision_recorded_in_the_original_record": rec["passed"],
                      "what_the_wrong_description_gives": wrong,
                      "recorded_decision_differs_from_history": rec["passed"] is not passed}
        if not agree:
            problems.append(("HISTORICAL_DECISION_MISMATCH", "seed %s: replay %s, frozen grader %s, frozen list %s" % (seed, replay, grader, frozen)))
        if rec["passed"] is not wrong:
            problems.append(("HISTORICAL_EXCEPTION_INCOMPATIBLE", "seed %s: the recorded decision %s is not what the recognised mistake gives (%s)" % (seed, rec["passed"], wrong)))
    label = "LEARNS_NEW_WORLDS" if rows and all(r["replay_with_the_preserved_rule"]["passed"] for r in rows.values()) else "NO_TRANSFER_TO_NEW_WORLDS"
    if label != entry["label"] or _get(gate, "label") != entry["label"]:
        problems.append(("HISTORICAL_DECISION_MISMATCH", "label: replay %s, frozen grader %s, frozen list %s" % (label, _get(gate, "label"), entry["label"])))
    if recorded_label is not None:
        wrong_label = "LEARNS_NEW_WORLDS" if rows and all(r["what_the_wrong_description_gives"] for r in rows.values()) else "NO_TRANSFER_TO_NEW_WORLDS"
        if recorded_label != wrong_label:
            problems.append(("HISTORICAL_EXCEPTION_INCOMPATIBLE", "the recorded label %s is not what the recognised mistake gives (%s)" % (recorded_label, wrong_label)))
    return rows, label, problems


def _check_reading_body(run, reading, reading_path, mode, info):
    rsha = _lf_sha(reading_path)
    info["reading_sha256_lf"] = rsha
    schema = reading["schema"]
    apath = PACKAGE / reading["anchor"]["path"]
    anchor = None
    if not apath.is_file():
        run.fail("ANCHOR_EVIDENCE", "READING_EVIDENCE_INCOMPLETE", "the anchor the reading names is absent: %s" % reading["anchor"]["path"])
    elif _lf_sha(apath) != reading["anchor"]["pin"]["sha256_lf"]:
        run.fail("ANCHOR_EVIDENCE", "READING_EVIDENCE_ALTERED", "the anchor at %s is not the one the reading pinned" % reading["anchor"]["path"])
    else:
        sub = _Run()
        anchor = _read_anchor(sub, apath)
        _merge(run, sub, "ANCHOR_EVIDENCE")
    tool_sha = reading["tool"]["pin"]["sha256_lf"]
    if schema == SCHEMA:
        recorded, applied = reading["rule"]["recorded_in_anchor"], reading["rule"]["applied"]
    elif schema == READING_SCHEMA_0_3:
        recorded, applied = reading["anchor_rule_metadata"], reading["historical_rule_applied"]
    else:
        recorded = anchor.get("pass_rule") if anchor else None
        applied = RECOGNISED_MISTAKE["recorded_description"] if tool_sha == RECOGNISED_MISTAKE["written_by_tool_sha256_lf"] else None
    info["recorded_rule"], info["applied_rule_recorded"] = recorded, applied
    rec_sha = rule_sha(recorded) if isinstance(recorded, dict) else None
    app_sha = rule_sha(applied) if isinstance(applied, dict) else None

    anchor_unverified = anchor is None and schema == HISTORICAL_READING_SCHEMA     # a 0.2 reading's rule lives in its anchor
    if mode == TRUSTED:
        run.checks["HISTORICAL_EVIDENCE"] = dict(NOT_REQUESTED_TRUSTED)
        if anchor_unverified:
            run.not_run("RULE_DESCRIPTION", "the anchor that carries the rule description did not verify")
        elif rec_sha is None or app_sha is None:
            run.fail("RULE_DESCRIPTION", "READING_EVIDENCE_INCOMPLETE", "the rule description the reading recorded or applied could not be established")
        elif rec_sha != HISTORICAL_RULE_SHA256 or app_sha != HISTORICAL_RULE_SHA256:
            listed = historical_entry("reading", rsha)
            run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_MISMATCH", "the reading records %s and applied %s, not the preserved historical rule; refused for trusted acceptance%s" % (
                describe_rule(rec_sha), describe_rule(app_sha),
                (" (this is the frozen historical reading %r; it can be read only with %s)" % (listed, HISTORICAL_FLAG)) if listed else ""))
        run.passed("RULE_DESCRIPTION", "the preserved historical rule, recorded and applied")
        if schema != SCHEMA:
            run.fail("READING_READABLE", "READING_SCHEMA_OUTDATED", "reading schema %r; trusted acceptance needs %r" % (schema, SCHEMA))
        elif _get(reading, "mode", "name") != TRUSTED:
            run.fail("READING_CONSISTENCY", "READING_NOT_TRUSTED", "a historical-compatibility reading is never a trusted reading")
        if reading["verdict"] != "RESCORE_OK" or reading["reject_reasons"]:
            run.fail("READING_CONSISTENCY", "READING_NOT_CLEAN", "recorded verdict %r with %d reasons" % (reading["verdict"], len(reading["reject_reasons"])))
        if run.reasons or anchor is None:
            return "VOID_REJECTED"
        sub = _Run()
        _safe_checks(sub, PACKAGE / anchor["study"]["path"], apath, {}, TRUSTED)
        _merge(run, sub, "ANCHOR_EVIDENCE")
        run.passed("ANCHOR_EVIDENCE", "every pin the anchor names matches the file on disk")
        _reading_consistency(run, reading, anchor)
        if run.failed("READING_CONSISTENCY"):
            run.not_run("DECISIONS_REPLAYED", "the reading is inconsistent with its anchor")
            return "VOID_REJECTED"
        replay = {}
        for seed, s in sorted(reading["per_seed"].items()):
            p, passed = historical_decision(s["gained"], s["broken"], len(s["kinds_improved"]), s["worlds_improved"])
            replay[seed] = {"gained": s["gained"], "broken": s["broken"], "p_one_sided": str(p), "passed": passed, "recorded_passed": s["passed"]}
            if s["passed"] is not passed or s.get("p_one_sided", str(p)) != str(p):
                run.fail("DECISIONS_REPLAYED", "READING_DECISION_MISMATCH", "seed %s: recorded %s, the preserved rule gives %s (p %s)" % (seed, s["passed"], passed, p))
        label = "LEARNS_NEW_WORLDS" if replay and all(r["passed"] for r in replay.values()) else "NO_TRANSFER_TO_NEW_WORLDS"
        if reading["label_rederived"] != label:
            run.fail("DECISIONS_REPLAYED", "READING_DECISION_MISMATCH", "recorded label %s, the preserved rule gives %s" % (reading["label_rederived"], label))
        run.passed("DECISIONS_REPLAYED", "%d seed decisions re-derived from the recorded counts" % len(replay))
        info["decisions"] = replay
        return label

    # ---- HISTORICAL mode ----
    name = historical_entry("reading", rsha)
    info["entry"] = name
    if name is None:
        run.fail("HISTORICAL_EVIDENCE", "HISTORICAL_EXCEPTION_UNKNOWN_READING",
                 "reading sha256_lf %s is not on the frozen historical list %s; new runs never receive the historical exception" % (
                     rsha[:16], sorted(HISTORICAL_EXCEPTION)))
        if rec_sha is not None and rec_sha != HISTORICAL_RULE_SHA256:
            run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_MISMATCH", "the reading records %s; outside the frozen list that is refused" % describe_rule(rec_sha))
        return "VOID_REJECTED"
    entry = HISTORICAL_EXCEPTION[name]
    if (schema != HISTORICAL_READING_SCHEMA or tool_sha != RECOGNISED_MISTAKE["written_by_tool_sha256_lf"]
            or reading["anchor"]["pin"]["sha256_lf"] != entry["anchor"][1] or reading["anchor"]["path"] != entry["anchor"][0]):
        run.fail("HISTORICAL_EVIDENCE", "HISTORICAL_EXCEPTION_INCOMPATIBLE", "schema, writing tool or anchor are not the recognised 0.2 ones for %s" % name)
    if anchor_unverified:
        run.not_run("RULE_DESCRIPTION", "the anchor that carries the rule description did not verify")
        return "VOID_REJECTED"                                   # ANCHOR_EVIDENCE already holds the reason
    if rec_sha != RECOGNISED_MISTAKE["recorded_description_sha256"]:
        run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_UNRECOGNISED", "the listed reading records %s, not the recognised mistake" % describe_rule(rec_sha))
    run.passed("RULE_DESCRIPTION", "WRONG description recorded: %s; the preserved historical rule is applied instead" % describe_rule(rec_sha))
    if reading["verdict"] != "RESCORE_OK" or reading["reject_reasons"] or any(_get(c, "status") != "PASS" for c in reading["checks"].values()):
        run.fail("READING_CONSISTENCY", "HISTORICAL_READING_NOT_CLEAN", "the original reading did not record a clean RESCORE_OK")
    if anchor is None:
        return "VOID_REJECTED"
    sub = _Run()
    _, _, _, sub_info = _safe_checks(sub, PACKAGE / anchor["study"]["path"], apath, {}, HISTORICAL)
    info["evidence"] = (sub_info or {}).get("evidence")
    _merge(run, sub, "ANCHOR_EVIDENCE")
    run.passed("HISTORICAL_EVIDENCE", "%d original evidence items verified" % len(info["evidence"] or []))
    run.passed("ANCHOR_EVIDENCE", "every pin the anchor names matches the file on disk")
    _reading_consistency(run, reading, anchor, entry)
    frel, fsha = entry["frozen_grader_reading"]
    if not (PACKAGE / frel).is_file() or _lf_sha(PACKAGE / frel) != fsha or run.failed("READING_CONSISTENCY"):
        run.not_run("DECISIONS_REPLAYED", "the frozen grader reading did not verify, or the reading is inconsistent")
        return "VOID_REJECTED"
    gate = json.loads((PACKAGE / frel).read_text(encoding="utf-8"))
    rows, label, problems = replay_historical(name, reading["per_seed"], gate, reading["label_rederived"])
    for code, detail in problems:
        run.fail("DECISIONS_REPLAYED", code, detail)
    run.passed("DECISIONS_REPLAYED", "%d seed decisions re-derived with the preserved rule; replay, frozen grader and frozen list agree" % len(rows))
    info["decisions"] = rows
    return label


def check_reading(reading_path, out_path=None, historical_compatibility=False):
    """Verify a committed reading WITHOUT rescoring and without importing any checker code."""
    mode = HISTORICAL if historical_compatibility else TRUSTED
    run = _Run(READING_CHECKS)
    reading_path = pathlib.Path(reading_path)
    guard = protected_paths(reading_path)
    watched = snapshot_paths(reading_path)
    before = snapshot(watched)
    info = {"reading_sha256_lf": None, "entry": None, "recorded_rule": None, "applied_rule_recorded": None, "evidence": None, "decisions": None}
    label = "VOID_REJECTED"
    _constants_check(run)
    reading = None
    try:
        reading, problems = strict_json(reading_path.read_text(encoding="utf-8"))
        if not isinstance(reading, dict) or problems.duplicate_keys or problems.nonfinite:
            run.fail("READING_READABLE", "READING_MALFORMED", "not a JSON object, or duplicate keys %s / non-finite numbers %s" % (problems.duplicate_keys[:5], problems.nonfinite[:5]))
            reading = None
    except Exception as error:
        run.fail("READING_READABLE", "READING_UNREADABLE", "%s: %s" % (type(error).__name__, str(error)[:120]))
    if reading is not None and reading.get("schema") not in KNOWN_READING_SCHEMAS:
        run.fail("READING_READABLE", "READING_SCHEMA_UNKNOWN", "reading schema %r is not one of %s" % (reading.get("schema"), list(KNOWN_READING_SCHEMAS)))
        reading = None
    if reading is not None:
        missing = reading_missing_fields(reading)
        if missing:
            run.fail("READING_READABLE", "READING_INCOMPLETE", "missing or empty: %s" % missing[:8])
            reading = None
    if reading is not None:
        run.passed("READING_READABLE", _rel(reading_path))
        if not run.failed("TOOL_CONSTANTS"):
            label = _check_reading_body(run, reading, reading_path, mode, info)
    if mode == TRUSTED and run.checks["HISTORICAL_EVIDENCE"]["status"] == "NOT_RUN":
        run.checks["HISTORICAL_EVIDENCE"] = dict(NOT_REQUESTED_TRUSTED)
    originals = _originals_check(run, watched, before, out_path, guard)
    statuses = [c["status"] for c in run.checks.values()]
    ok = "HISTORICAL_COMPATIBILITY_OK" if mode == HISTORICAL else "READING_VERIFIED"
    verdict = "REJECT" if run.reasons else ("CHECK_INCOMPLETE" if "NOT_RUN" in statuses else ok)
    if run.reasons:
        label = "VOID_REJECTED"
    hist_block = _historical_block(info, info["decisions"]) if mode == HISTORICAL else None
    record = {"schema": CHECK_SCHEMA, "tool_version": TOOL_VERSION, "mode": _mode_block(mode),
              "verdict": verdict, "label": label, "reject_reasons": run.reasons, "checks": run.checks,
              "reading": {"path": _rel(reading_path), "sha256_lf": info["reading_sha256_lf"]},
              "tool": {"path": _rel(__file__), "pin": file_pin(__file__)}, "hash_policy": HASH_POLICY["policy_id"],
              "rule": _rule_block(info["recorded_rule"], info["applied_rule_recorded"]),
              "historical_exception": hist_block, "decisions": info["decisions"], "originals": originals, "custody": CUSTODY,
              "boundary": "no checker code was imported or run; decisions were re-derived from the counts the reading recorded, and the evidence behind it was verified by hash"}
    _write_output(run, out_path, record)
    print(json.dumps({k: record[k] for k in ("verdict", "label", "reject_reasons")}, indent=1))
    print("  mode: %s" % mode)
    if hist_block:
        _print_historical(hist_block)
    print("  checks:", ", ".join("%s=%s" % (k, v["status"]) for k, v in run.checks.items()))
    for seed, row in sorted((info["decisions"] or {}).items()):
        if mode == HISTORICAL:
            r = row["replay_with_the_preserved_rule"]
            print("  seed %s: gained %d broken %d, p %s -> historical decision %s (frozen grader %s); the original record says %s%s" % (
                seed, r["gained"], r["broken"], r["p_one_sided"], r["passed"], row["frozen_grader"]["passed"],
                row["decision_recorded_in_the_original_record"],
                "  <- the recognised mistake" if row["recorded_decision_differs_from_history"] else ""))
        else:
            print("  seed %s: gained %d broken %d, p %s -> %s" % (seed, row["gained"], row["broken"], row["p_one_sided"], row["passed"]))
    return {"READING_VERIFIED": 0, "REJECT": 2, "CHECK_INCOMPLETE": 3, "HISTORICAL_COMPATIBILITY_OK": 4}[verdict]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--study", default=None)
    parser.add_argument("--anchor", default=None)
    parser.add_argument("--write-anchor", action="store_true", help="write a NEW anchor (create-only; never over an existing file)")
    parser.add_argument("--receipt", action="append", default=[], help="seed=dir override (tests; refused in historical mode)")
    parser.add_argument("--out", default=None)
    parser.add_argument("--frozen-reading", default=None, help="gate_reading.json to compare against (default: beside the study)")
    parser.add_argument("--no-frozen-reading", action="store_true", help="do not compare with a frozen grader reading (recorded as NOT_REQUESTED)")
    parser.add_argument("--safe-only", action="store_true", help="file checks only; never imports the checker; verdict is at best RESCORE_INCOMPLETE")
    parser.add_argument("--check-reading", default=None, help="verify a committed reading without rescoring (no checker import)")
    parser.add_argument(HISTORICAL_FLAG, dest="historical_compatibility", action="store_true",
                        help="EXPLICIT historical-compatibility mode: only for the frozen historical records; applies the preserved rule; recorded in the output")
    args = parser.parse_args()
    if args.check_reading:
        if args.study or args.write_anchor:
            parser.error("--check-reading takes no --study and no --write-anchor")
        return check_reading(args.check_reading, args.out, historical_compatibility=args.historical_compatibility)
    if not args.study:
        parser.error("--study is required unless --check-reading is given")
    study = pathlib.Path(args.study)
    anchor = pathlib.Path(args.anchor) if args.anchor else HERE / ("trust_anchor_%s.json" % study.parent.name)
    override = dict(r.split("=", 1) for r in args.receipt)
    if args.write_anchor:
        if args.historical_compatibility:
            print("ANCHOR_REFUSED: anchors are written only in trusted mode, with the preserved rule")
            return 2
        return write_anchor(study, anchor, override)
    return rescore(study, anchor, override, args.out, frozen_reading=args.frozen_reading,
                   compare_frozen=not args.no_frozen_reading, safe_only=args.safe_only,
                   historical_compatibility=args.historical_compatibility)


if __name__ == "__main__":
    sys.exit(main())
