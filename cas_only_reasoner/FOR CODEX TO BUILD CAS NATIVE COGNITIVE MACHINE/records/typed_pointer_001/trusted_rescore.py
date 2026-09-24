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
    own artifact manifest and the four label-deciding files it pins, and (revision 1) every checkpoint weight file
    that manifest records, byte for byte -- an absent one is incomplete evidence, refused by name.
    It then applies the PRESERVED HISTORICAL RULE, never the recorded description. Every output carries a
    WARNING and both rule descriptions side by side. It never writes to an original record.
  * BOTH MODES refuse unknown, altered, incomplete or incompatible evidence. A new run -- anything not on the
    frozen list -- never receives the historical exception, even with the flag.
  * --check-reading verifies a committed reading WITHOUT rescoring: it re-derives the decisions from the counts
    the reading recorded, and it never imports or runs the checker. Seconds, not the 30-minute full reading.
  * 0.3 is kept as history only: byte-identical at history/trusted_rescore_0_3.py (sha256_lf 50295072...) and in
    git at 60e382b0. Its behaviour -- accept a 0.2 anchor and only report the wrong description -- is gone here.

WHAT 0.4 REVISION 1 CHANGES (review REVIEW_RESCORER_0_4_6e7f62a1.md, commit 4c89e737; coordinator decision 1):

  * A TRUSTED --check-reading NEVER gives trusted acceptance. It re-derives decisions from counts that a file
    states; it does not rescore. Its best verdict is READING_CONSISTENT_NOT_RESCORED, exit 5, with the label
    NOT_DERIVED. Only a full rescore (RESCORE_OK, exit 0) is trusted acceptance. The recorded counts must also be
    possible: p_one_sided present, kinds distinct and drawn from the anchor's kind_of, world ids from its world_of,
    gained + broken at most the population, worlds at most gained, before/after counts that add up, every recorded
    check PASS (the two historical checks NOT_REQUESTED), and agreement with the pinned frozen grader reading.
  * CHECKPOINT WEIGHTS. An absent or unverifiable checkpoint weight file is INCOMPLETE evidence, refused by name in
    both modes: HISTORICAL_EVIDENCE_INCOMPLETE in historical mode, RUN_EVIDENCE_INCOMPLETE in trusted mode. Never
    PASS, never exit 4, never exit 0. New anchors (schema 0.4) pin the run manifest and every checkpoint digest it
    records; --write-anchor byte-checks every weight file first and refuses if one is absent or altered.
  * --out IS CREATE-ONLY. An existing path (any file, above all an original record) is refused by name BEFORE any
    work starts, and the file is opened with mode "x", which also defeats a hard link or a file that appears late.
  * The decision reads every threshold from the hashed HISTORICAL_RULE; the whole RECOGNISED_MISTAKE is hashed.
  * Usage errors exit 64. A malformed reading or anchor field is refused by name, never a crash.

HOW IT IS ORDERED (the order is the point):

  1. SAFE CHECKS, which only read files. The tool's own frozen constants first, then the anchor (well-formed,
     known schema, complete), its rule description and the mode, then (historical mode only) the original
     evidence. Then: the study file's identity and its seed set, the frozen grader's hash, the hash of EVERY source
     file the private checker executes, (trusted mode, revision 1) the run evidence -- each run manifest as the
     anchor pinned it and every checkpoint weight file it records, byte for byte -- and for every prediction file
     its hash, duplicate ids, missing or extra ids, non-finite numbers and duplicate JSON keys. Every reason found
     is collected.
  2. THE GATE. If the constants, the anchor, its rule description, the historical or run evidence, the study, the
     grader or the checker code does not match, the checker code is NEVER IMPORTED OR RUN.
  3. CHECKS THAT RUN THE CHECKER. Cached bytecode is ignored, so what runs is compiled from the very sources that
     were just hashed. Every prediction is re-checked, the label is re-derived from those fresh results only with
     the preserved historical rule, and it is compared with the frozen grader's reading (and, in historical mode,
     with the six frozen historical decisions).
  4. ORIGINALS. The small original records of both historical studies (anchors, readings, frozen grader readings,
     run manifests), the label-deciding files of the historical study this run reads, and every file named on the
     command line are hashed byte for byte before and after the run; any change is a rejection. --out is
     create-only: an existing path is refused before any work (OUTPUT_EXISTS), and so is any original record the
     historical list names, even one that was deleted (OUTPUT_WOULD_OVERWRITE_ORIGINAL). Nothing is written then.

EVERY CHECK HAS A STATUS: PASS, FAIL, NOT_RUN (it could not run -- which is not the same as failing), or
NOT_REQUESTED (the caller or the mode said so explicitly). The verdict and exit code are
    REJECT                        2  if any reason was recorded (irreversible: nothing later can clear a reason);
    RESCORE_INCOMPLETE            3  if nothing failed but a check that was supposed to run did not;
    RESCORE_OK                    0  trusted mode, full rescore, every check PASS or NOT_REQUESTED -- the ONLY
                                     trusted acceptance;
    HISTORICAL_COMPATIBILITY_OK   4  historical mode, every check PASS except RUN_EVIDENCE, which is NOT_REQUESTED
                                     there (HISTORICAL_EVIDENCE covers it). Never 0: a script that expects 0 does
                                     not mistake the historical exception for plain trusted acceptance.
--check-reading uses REJECT (2), CHECK_INCOMPLETE (3), HISTORICAL_COMPATIBILITY_OK (4, historical mode only) and
READING_CONSISTENT_NOT_RESCORED (5, trusted mode: consistent counts are not a rescore). It never exits 0.
A usage error exits 64. --write-anchor exits 0 when the anchor was written and 2 when it was refused.

HASH POLICY (cncm.hash-policy/1.0). Every pinned file here is text. Each pin records TWO digests: the
LF-normalised one (CRLF -> LF only; nothing else is touched) which is what gets COMPARED, and the raw one
as observed when the pin was written, which is informational. The before/after check of the originals (step 4)
compares RAW bytes: it proves the files were not rewritten, not merely that their text is the same.

LIMIT, stated plainly: an anchor written by the same session that built the model is not independent
custody. Every anchor and reading carries `custody: EVALUATION_NOT_INDEPENDENT`.

Usage (every --out must be a NEW path):
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --anchor <NEW path> --write-anchor   # create-only
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> [--frozen-reading <gate_reading.json>] --out <NEW path>
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --safe-only        # file checks only, seconds
    python records/typed_pointer_001/trusted_rescore.py --check-reading <reading.json>         # no checker import, seconds; never exit 0
  The frozen historical records only (explicit flag, recorded in the output; the checkpoint weight files must be present):
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
TOOL_REVISION = 1                                   # 0.4 revision 1: the review of 6e7f62a1 (commit 4c89e737)
SCHEMA = "cncm.trusted-rescore-reading/0.4"
CHECK_SCHEMA = "cncm.trusted-rescore-reading-check/0.2"
ANCHOR_SCHEMA = "cncm.trusted-rescore-anchor/0.4"   # pins the run manifest and every checkpoint digest
ANCHOR_SCHEMA_0_3 = "cncm.trusted-rescore-anchor/0.3"   # 0.4 before revision 1: no run-manifest or checkpoint pins
HISTORICAL_ANCHOR_SCHEMA = "cncm.trusted-rescore-anchor/0.2"
HISTORICAL_READING_SCHEMA = "cncm.trusted-rescore-reading/0.2"
READING_SCHEMA_0_3 = "cncm.trusted-rescore-reading/0.3"
KNOWN_ANCHOR_SCHEMAS = (HISTORICAL_ANCHOR_SCHEMA, ANCHOR_SCHEMA_0_3, ANCHOR_SCHEMA)
KNOWN_READING_SCHEMAS = (HISTORICAL_READING_SCHEMA, READING_SCHEMA_0_3, SCHEMA)
PHASES = ("course_p00", "course_p10")
LABEL_FILES = tuple("%s_%s.json" % (ph, kind) for ph in PHASES for kind in ("predictions", "scoring"))
CHECKPOINT_SUFFIX = ".pt"
EXIT_CODES = {"RESCORE_OK": 0, "REJECT": 2, "RESCORE_INCOMPLETE": 3, "CHECK_INCOMPLETE": 3,
              "HISTORICAL_COMPATIBILITY_OK": 4, "READING_CONSISTENT_NOT_RESCORED": 5}
EXIT_USAGE = 64
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
# sha256 of the canonical JSON bytes of the WHOLE RECOGNISED_MISTAKE (revision 1: every field, not only the description).
RECOGNISED_MISTAKE_SHA256 = "fddc692ee219b0d6efe18675aa169bca693edd4e2b69918bd7ad818778c27a40"

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

SAFE_CHECKS = ("TOOL_CONSTANTS", "ANCHOR_READABLE", "RULE_DESCRIPTION", "HISTORICAL_EVIDENCE", "RUN_EVIDENCE", "STUDY_IDENTITY",
               "SEED_SET", "EVALUATOR_IDENTITY", "CHECKER_CODE_IDENTITY", "PREDICTIONS_IDENTITY", "ID_SET", "FINITE_NUMBERS",
               "WELL_FORMED_JSON")
CHECKER_CHECKS = ("CHECKER_PROFILE", "COURSE_IDENTITY", "POPULATION_IDENTITY", "CODE_CLOSURE_COMPLETE", "CODE_UNCHANGED_DURING_RUN",
                  "RESCORE", "SCORING_FILE_AGREEMENT", "FROZEN_GRADER_AGREEMENT", "HISTORICAL_DECISIONS")
FINAL_CHECKS = ("ORIGINALS_UNCHANGED",)
GATE = ("TOOL_CONSTANTS", "ANCHOR_READABLE", "RULE_DESCRIPTION", "HISTORICAL_EVIDENCE", "RUN_EVIDENCE", "STUDY_IDENTITY",
        "SEED_SET", "EVALUATOR_IDENTITY", "CHECKER_CODE_IDENTITY")
READING_CHECKS = ("TOOL_CONSTANTS", "READING_READABLE", "RULE_DESCRIPTION", "HISTORICAL_EVIDENCE", "ANCHOR_EVIDENCE",
                  "READING_CONSISTENCY", "DECISIONS_REPLAYED", "ORIGINALS_UNCHANGED")
NOT_REQUESTED_TRUSTED = {"status": "NOT_REQUESTED", "detail": "trusted mode: the historical exception is not in use"}
NOT_REQUESTED_HISTORICAL = {"status": "NOT_REQUESTED", "detail": "historical mode: the run manifests and checkpoint weight files are "
                                                                 "verified under HISTORICAL_EVIDENCE, against the frozen list"}
# In a clean trusted reading every check is PASS, except these two, which trusted mode records as NOT_REQUESTED.
TRUSTED_NOT_REQUESTED = ("HISTORICAL_EVIDENCE", "HISTORICAL_DECISIONS")


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
    """Package-relative with forward slashes when the path is inside the package; otherwise the resolved absolute path
    (revision 1: never a bare relative path, which a later reader would take as package-relative)."""
    path = pathlib.Path(path)
    try:
        return path.resolve().relative_to(PACKAGE.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


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
    rule = HISTORICAL_RULE                                 # revision 1: every threshold comes from the hashed rule
    p = Fraction(sum(math.comb(b + c, k) for k in range(b, b + c + 1)), 2 ** (b + c))
    passed = ((b > c or rule["require_b_greater_than_c"] is not True)
              and (c == 0 or rule["zero_loss_veto"] is not True)
              and p <= Fraction(rule["alpha"])
              and n_kinds >= rule["min_improved_kinds"] and n_worlds >= rule["min_improved_worlds"])
    return p, passed


def historical_label(passes):
    """The study label from the per-seed decisions, under the rule's all_seeds_must_pass (the only form it defines)."""
    if HISTORICAL_RULE["all_seeds_must_pass"] is not True:
        raise ValueError("the preserved rule defines the label only when every seed must pass")
    passes = list(passes)
    return "LEARNS_NEW_WORLDS" if passes and all(p is True for p in passes) else "NO_TRANSFER_TO_NEW_WORLDS"


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
    if (rule_sha(RECOGNISED_MISTAKE["recorded_description"]) != RECOGNISED_MISTAKE["recorded_description_sha256"]
            or _sha(_canon(RECOGNISED_MISTAKE)) != RECOGNISED_MISTAKE_SHA256):
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


def _originals_check(run, paths, before):
    after = snapshot(paths)
    changed = sorted(rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel))
    if changed:
        run.fail("ORIGINALS_UNCHANGED", "ORIGINAL_CHANGED_DURING_RUN", "these originals changed during the run: %s" % changed[:6])
    run.passed("ORIGINALS_UNCHANGED", "%d original files byte-identical before and after (raw sha256)" % sum(1 for v in after.values() if v))
    return {"files_checked": len(after), "files_present": sum(1 for v in after.values() if v), "unchanged": not changed,
            "raw_sha256_after": after}


def output_refusal(out_path, guard):
    """--out is CREATE-ONLY (revision 1). Checked BEFORE any work. Returns (code, detail), or None when the path is new.
    An original record on the historical list -- even one that has been deleted -- or a file named on this command line
    is OUTPUT_WOULD_OVERWRITE_ORIGINAL; any other existing path (a file, a directory, a link) is OUTPUT_EXISTS."""
    if not out_path:
        return None
    if _key(out_path) in {_key(p) for p in guard}:
        return ("OUTPUT_WOULD_OVERWRITE_ORIGINAL", "--out %s is an original record or a file named on this command line; "
                "nothing was done and nothing was written" % _rel(out_path))
    if os.path.lexists(out_path):
        return ("OUTPUT_EXISTS", "--out %s already exists; outputs are create-only, so nothing was done and nothing was "
                "written" % _rel(out_path))
    return None


def _print_output_refusal(refusal, mode):
    print(json.dumps({"verdict": "REJECT", "reject_reasons": ["%s:%s" % refusal]}, indent=1))
    print("  mode: %s" % mode)
    return EXIT_CODES["REJECT"]


def _write_output(out_path, record):
    """Create-only: mode "x" fails if the path exists, including a hard link or a file that appeared during the run."""
    if not out_path:
        return True
    try:
        with open(out_path, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, indent=1, sort_keys=True))
    except FileExistsError:
        print("OUTPUT_EXISTS: --out %s appeared during the run; nothing was written" % _rel(out_path))
        return False
    return True


# ---- run manifests and checkpoint weight files (revision 1, coordinator decision 1) ---------------
def read_run_manifest(path):
    """Strictly parse a run's artifact_manifest.json into {name: row}. Raises ValueError on anything malformed:
    duplicate keys, non-finite numbers, no artifacts list, a row without a name, or a name listed twice."""
    body, problems = strict_json(pathlib.Path(path).read_text(encoding="utf-8"))
    if problems.duplicate_keys or problems.nonfinite:
        raise ValueError("duplicate keys or non-finite numbers")
    if not isinstance(body, dict) or not isinstance(body.get("artifacts"), list):
        raise ValueError("no artifacts list")
    rows = {}
    for row in body["artifacts"]:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise ValueError("an artifact row without a name")
        if row["name"] in rows:
            raise ValueError("artifact %s is listed twice" % row["name"])
        rows[row["name"]] = row
    return rows


def _well_formed_digest(row):
    return (isinstance(row, dict) and isinstance(row.get("sha256"), str) and re.fullmatch("[0-9a-f]{64}", row["sha256"]) is not None
            and type(row.get("bytes")) is int and row["bytes"] >= 0)


def checkpoint_rows(rows):
    """The checkpoint weight files a run manifest records."""
    return {name: row for name, row in rows.items() if name.endswith(CHECKPOINT_SUFFIX)}


def verify_checkpoints(seed, ckpts, art, incomplete, altered):
    """READS files only. Byte-check every checkpoint weight file the run manifest records. An absent or unverifiable
    weight file is INCOMPLETE evidence (coordinator decision 1): it is refused by name, never passed, never counted as
    a match. Returns (summary, problems); the summary's status is MATCH only when EVERY recorded file matched."""
    summary = {"what": "checkpoint weight files, seed %s" % seed, "path": _rel(art), "recorded": len(ckpts),
               "byte_checked": 0, "matching": 0, "absent": [], "unverifiable": [], "altered": []}
    problems = []
    if not ckpts:
        problems.append((incomplete, "seed %s: the run manifest records no checkpoint weight file" % seed))
    for name, row in sorted(ckpts.items()):
        if not _well_formed_digest(row) or re.fullmatch(r"[A-Za-z0-9_.-]+", name) is None or name.startswith("."):
            summary["unverifiable"].append(name)
            problems.append((incomplete, "seed %s: checkpoint %s is unverifiable (no well-formed recorded digest, or not a "
                             "plain file name); an unverifiable weight file is incomplete evidence" % (seed, name)))
            continue
        path = art / name
        if not path.is_file():
            summary["absent"].append(name)
            problems.append((incomplete, "seed %s: checkpoint weight file %s is absent here; an absent weight file is "
                             "incomplete evidence" % (seed, name)))
            continue
        digest, size = _raw_sha_stream(path)
        summary["byte_checked"] += 1
        if digest == row["sha256"] and size == row["bytes"]:
            summary["matching"] += 1
        else:
            summary["altered"].append(name)
            problems.append((altered, "seed %s: checkpoint %s differs from its recorded digest" % (seed, name)))
    summary["status"] = ("ALTERED" if summary["altered"] else
                         "MATCH" if ckpts and summary["matching"] == len(ckpts) else "INCOMPLETE")
    return summary, problems


def _receipt_path(recorded):
    """A recorded path: package-relative when relative, else as given."""
    path = pathlib.Path(str(recorded))
    return path if path.is_absolute() else PACKAGE / path


def run_evidence_pins(rdir):
    """What a NEW anchor pins about a run beyond its predictions: the run manifest, and every checkpoint digest it
    records. READS files only. None when there is no readable manifest (then the anchor is incomplete)."""
    mpath = pathlib.Path(rdir) / "artifact_manifest.json"
    if not mpath.is_file():
        return None
    try:
        rows = read_run_manifest(mpath)
    except (ValueError, UnicodeDecodeError, OSError):
        return None
    return {"manifest": {"path": _rel(mpath), "pin": file_pin(mpath)},
            "checkpoints": {name: {"sha256": row.get("sha256"), "bytes": row.get("bytes")}
                            for name, row in sorted(checkpoint_rows(rows).items())}}


def verify_run_evidence(seed, pinned, rdir, prediction_pins):
    """READS files only (trusted mode and --write-anchor). The run manifest must be the one the anchor pinned; it must
    agree with the anchor's prediction pins; every checkpoint weight file it records must be present here and
    byte-identical. Returns (items, problems)."""
    incomplete, altered = "RUN_EVIDENCE_INCOMPLETE", "RUN_EVIDENCE_ALTERED"
    mpath = pathlib.Path(rdir) / "artifact_manifest.json"
    mpin = _get(pinned, "manifest", "pin", "sha256_lf")
    item = {"what": "run manifest, seed %s" % seed, "path": _rel(mpath), "pinned_sha256_lf": mpin, "observed_sha256_lf": None}
    if not isinstance(mpin, str):
        return [dict(item, status="NOT_PINNED")], [(incomplete, "seed %s: the anchor pins no run manifest" % seed)]
    if not mpath.is_file():
        return [dict(item, status="ABSENT")], [(incomplete, "seed %s: the run manifest is absent: %s" % (seed, _rel(mpath)))]
    item["observed_sha256_lf"] = _lf_sha(mpath)
    if item["observed_sha256_lf"] != mpin:
        return [dict(item, status="ALTERED")], [(altered, "seed %s: the run manifest differs from the one the anchor pinned" % seed)]
    items, problems = [dict(item, status="MATCH")], []
    try:
        rows = read_run_manifest(mpath)
    except (ValueError, UnicodeDecodeError, OSError) as error:
        return items, [(incomplete, "seed %s: the run manifest is unreadable (%s)" % (seed, error))]
    for ph in PHASES:
        row = rows.get("%s_predictions.json" % ph)
        if not _well_formed_digest(row):
            problems.append((incomplete, "seed %s: the run manifest has no digest for %s_predictions.json" % (seed, ph)))
        elif row["sha256"] != _get(prediction_pins, ph, "sha256_lf"):
            problems.append((altered, "seed %s: %s_predictions.json: the anchor's pin and the run manifest disagree" % (seed, ph)))
    ckpts = checkpoint_rows(rows)
    recorded = {name: {"sha256": row.get("sha256"), "bytes": row.get("bytes")} for name, row in ckpts.items()}
    if recorded != _get(pinned, "checkpoints"):
        problems.append((altered, "seed %s: the checkpoint digests the anchor pinned are not the ones the run manifest records" % seed))
    summary, more = verify_checkpoints(seed, ckpts, pathlib.Path(rdir) / "collected/results/artifacts", incomplete, altered)
    return items + [summary], problems + more


def evidence_detail(items):
    """How many evidence items were listed, and how many files were actually byte-checked (review MAJOR 2)."""
    items = items or []
    ckpt = [i for i in items if "byte_checked" in i]
    files = sum(1 for i in items if "byte_checked" not in i and i.get("observed_sha256_lf"))
    weights = sum(i["byte_checked"] for i in ckpt)
    recorded = sum(i["recorded"] for i in ckpt)
    return "%d evidence items; %d files byte-checked, including %d of %d recorded checkpoint weight files" % (
        len(items), files + weights, weights, recorded)


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
            rows = read_run_manifest(mpath)
        except (ValueError, UnicodeDecodeError, OSError) as error:
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
        # checkpoint weight files (revision 1, coordinator decision 1): every one the frozen manifest records must be
        # present here and byte-identical. An absent or unverifiable one is INCOMPLETE evidence, refused by name.
        summary, more = verify_checkpoints(seed, checkpoint_rows(rows), art, "HISTORICAL_EVIDENCE_INCOMPLETE", "HISTORICAL_EVIDENCE_ALTERED")
        items.append(summary)
        problems.extend(more)
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
        pins = {ph: (file_pin(art / ("%s_predictions.json" % ph)) if (art / ("%s_predictions.json" % ph)).is_file() else None) for ph in PHASES}
        seeds[str(job["model_seed"])] = {"receipt_dir": _rel(rdir), "receipt_resolved_from": how, "predictions": pins,
                                         "run_evidence": run_evidence_pins(rdir)}
    return {"schema": ANCHOR_SCHEMA, "written": datetime.date.today().isoformat(), "tool_version": TOOL_VERSION,
            "tool_revision": TOOL_REVISION, "hash_policy": HASH_POLICY,
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
    # revision 1: an anchor pins only run evidence that was byte-checked here and now -- above all the weights
    problems = []
    for seed, s in sorted(anchor["seeds"].items()):
        absent = [ph for ph, pin in s["predictions"].items() if pin is None]
        if absent:
            problems.append(("PREDICTIONS_IDENTITY", "seed %s: prediction files absent: %s" % (seed, absent)))
        if s["run_evidence"] is None:
            problems.append(("RUN_EVIDENCE_INCOMPLETE", "seed %s: no readable run manifest under %s" % (seed, s["receipt_dir"])))
            continue
        problems += verify_run_evidence(seed, s["run_evidence"], _receipt_path(s["receipt_dir"]), s["predictions"])[1]
    if problems:
        print("ANCHOR_REFUSED: the run evidence is incomplete or altered; an anchor is written only over byte-checked "
              "run manifests and checkpoint weight files: %s" % ["%s:%s" % p for p in problems[:8]])
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
    if anchor.get("schema") in (ANCHOR_SCHEMA_0_3, ANCHOR_SCHEMA):
        need += [("pass_rule_sha256",), ("tool_version",)]
    missing = [".".join(path) for path in need if _get(anchor, *path) is None]
    if missing:
        return missing
    if not isinstance(anchor["seeds"], dict):
        return ["seeds (not an object)"]
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
        if anchor["schema"] == ANCHOR_SCHEMA:             # revision 1: the run manifest and every checkpoint digest
            evidence = _get(anchor, "seeds", str(seed), "run_evidence")
            if not isinstance(_get(evidence, "manifest", "pin", "sha256_lf"), str):
                missing.append("seeds.%s.run_evidence.manifest.pin.sha256_lf" % seed)
            ckpts = _get(evidence, "checkpoints")
            if not isinstance(ckpts, dict) or not ckpts or not all(_well_formed_digest(r) for r in ckpts.values()):
                missing.append("seeds.%s.run_evidence.checkpoints (none, or one without a well-formed digest)" % seed)
    return missing


def anchor_type_problems(anchor):
    """Fields the checks index into must have the right JSON type. A wrong type is MALFORMED, never a crash."""
    want = [(("study", "path"), str), (("study", "pin", "sha256_lf"), str), (("grader", "pin", "sha256_lf"), str),
            (("tool", "pin", "sha256_lf"), str), (("checker", "profile_digest"), str), (("course_digest",), str),
            (("population", "digest"), str), (("population", "question_ids"), list), (("population", "kind_of"), dict),
            (("population", "world_of"), dict), (("expected_record_count",), int), (("custody",), str), (("schema",), str)]
    bad = [".".join(path) for path, kind in want if not isinstance(_get(anchor, *path), kind)]
    for seed, s in (anchor.get("seeds") or {}).items():
        if not isinstance(s, dict) or not isinstance(s.get("receipt_dir"), str):
            bad.append("seeds.%s" % seed)
    return bad


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
    wrong = anchor_type_problems(anchor)
    if wrong:
        run.fail("ANCHOR_READABLE", "ANCHOR_MALFORMED", "fields of the wrong JSON type: %s" % wrong[:8])
        return None
    run.passed("ANCHOR_READABLE", _rel(anchor_path))
    return anchor


def _anchor_rule_and_mode(run, anchor, anchor_path, mode):
    """RULE_DESCRIPTION, and the anchor-level part of HISTORICAL_EVIDENCE. Returns what the output needs to show."""
    recorded = anchor["pass_rule"]
    rsha, asha = rule_sha(recorded), _lf_sha(anchor_path)
    info = {"anchor_sha256_lf": asha, "recorded_rule": recorded, "recorded_rule_sha256": rsha, "entry": None, "evidence": None,
            "run_evidence": None}
    if mode == TRUSTED:
        run.checks["HISTORICAL_EVIDENCE"] = dict(NOT_REQUESTED_TRUSTED)
        if rsha != HISTORICAL_RULE_SHA256:
            listed = historical_entry("anchor", asha)
            run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_MISMATCH",
                     "the anchor records %s, not the preserved historical rule; refused for trusted acceptance%s" % (
                         describe_rule(rsha), (" (this is the frozen historical anchor %r; it can be read only with %s)" % (listed, HISTORICAL_FLAG)) if listed else ""))
        elif anchor["schema"] in (ANCHOR_SCHEMA_0_3, ANCHOR_SCHEMA) and anchor.get("pass_rule_sha256") != rsha:
            run.fail("RULE_DESCRIPTION", "RULE_DESCRIPTION_MISMATCH", "pass_rule_sha256 does not match the recorded pass_rule")
        if anchor["schema"] == ANCHOR_SCHEMA_0_3:
            run.fail("ANCHOR_READABLE", "ANCHOR_SCHEMA_OUTDATED", "anchor schema %r pins no run manifest and no checkpoint digest "
                     "(incomplete evidence); trusted mode needs %r -- write a NEW anchor with --write-anchor" % (anchor["schema"], ANCHOR_SCHEMA))
        elif anchor["schema"] != ANCHOR_SCHEMA:
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
        run.passed("HISTORICAL_EVIDENCE", "verified against frozen or recorded digests: " + evidence_detail(items))
        run.checks["RUN_EVIDENCE"] = dict(NOT_REQUESTED_HISTORICAL)
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
    if mode == TRUSTED:                                   # revision 1: the run manifest and every checkpoint weight file
        run_items = []
        for job in jobs:
            seed = str(job["model_seed"])
            pinned = _get(anchor, "seeds", seed)
            if not isinstance(pinned, dict):
                continue                                  # SEED_SET already names a seed the anchor does not know
            rdir, _ = _resolve_receipt(job, receipt_override)
            items, problems = verify_run_evidence(seed, pinned.get("run_evidence"), rdir, pinned.get("predictions"))
            run_items += items
            for code, detail in problems:
                run.fail("RUN_EVIDENCE", code, detail)
        info["run_evidence"] = run_items
        run.passed("RUN_EVIDENCE", "run manifests as anchored: " + evidence_detail(run_items))

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
    guard = protected_paths(anchor_path, study_path, frozen_reading)
    refusal = output_refusal(out_path, guard)
    if refusal:                                           # revision 1: create-only, refused before ANY work
        return _print_output_refusal(refusal, mode)
    run = _Run()
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
        label = historical_label(s["passed"] for s in per_seed.values())

        # the frozen grader's reading: beside the study by default; --frozen-reading when it lives elsewhere; in
        # historical mode always the original on the frozen list (verified in step 1)
        if not compare_frozen:
            run.checks["FROZEN_GRADER_AGREEMENT"] = {"status": "NOT_REQUESTED", "detail": "--no-frozen-reading"}
        else:
            if mode == HISTORICAL:
                fpath = PACKAGE / HISTORICAL_EXCEPTION[info["entry"]]["frozen_grader_reading"][0]
            else:
                fpath = pathlib.Path(frozen_reading) if frozen_reading else pathlib.Path(study_path).parent / "gate_reading.json"
            comparison.update({"frozen_reading_present": fpath.is_file(), "frozen_reading_path": _rel(fpath),
                               "frozen_reading_pin": file_pin(fpath) if fpath.is_file() else None})
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

    originals = _originals_check(run, watched, before)
    statuses = [c["status"] for c in run.checks.values()]
    ok = "HISTORICAL_COMPATIBILITY_OK" if mode == HISTORICAL else "RESCORE_OK"
    verdict = "REJECT" if run.reasons else ("RESCORE_INCOMPLETE" if "NOT_RUN" in statuses else ok)
    if run.reasons:
        label = "VOID_REJECTED"
    elif not imported:
        label = "NOT_DERIVED"
    hist_block = _historical_block(info, per_seed and {s: {k: v[k] for k in ("gained", "broken", "p_one_sided", "passed")} for s, v in per_seed.items()}) if mode == HISTORICAL else None
    reading = {"schema": SCHEMA, "tool_version": TOOL_VERSION, "tool_revision": TOOL_REVISION, "mode": _mode_block(mode),
               "verdict": verdict, "label_rederived": label, "reject_reasons": run.reasons, "checks": run.checks,
               "imported_checker_code": imported, "bytecode_policy": bytecode_policy, "material_supplied_by_caller": material is not None,
               "anchor": {"path": _rel(anchor_path), "pin": file_pin(anchor_path) if pathlib.Path(anchor_path).is_file() else None},
               "tool": {"path": _rel(__file__), "pin": file_pin(__file__)}, "hash_policy": HASH_POLICY["policy_id"],
               "rule": _rule_block(info["recorded_rule"] if info else None),
               "historical_exception": hist_block, "run_evidence": (info or {}).get("run_evidence"), "originals": originals,
               "per_seed": per_seed, "comparison_with_frozen_grader": comparison, "custody": CUSTODY,
               "boundary": "the scoring files' correct flags were NOT read for the label; every prediction was re-checked with the private checker"}
    written = _write_output(out_path, reading)
    print(json.dumps({k: reading[k] for k in ("verdict", "label_rederived", "reject_reasons")}, indent=1))
    print("  mode: %s" % mode)
    if hist_block:
        _print_historical(hist_block)
    print("  checks:", ", ".join("%s=%s" % (k, v["status"]) for k, v in run.checks.items()))
    for seed, s in per_seed.items():
        print("  seed %s: frozen18 %s -> %s, gained %d broken %d, p %s, passed %s, rescored %s, disagreements %s" % (
            seed, s["frozen_18_before"], s["frozen_18_after"], s["gained"], s["broken"], s["p_one_sided"], s["passed"],
            [s["phases"][ph]["rescored"] for ph in PHASES], [s["phases"][ph]["disagreements"] for ph in PHASES]))
    return EXIT_CODES[verdict] if written else EXIT_CODES["REJECT"]


# ---- verify a committed reading WITHOUT rescoring ---------------------------------------------
def reading_missing_fields(reading):
    need = [("anchor", "path"), ("anchor", "pin", "sha256_lf"), ("tool", "pin", "sha256_lf"), ("per_seed",),
            ("label_rederived",), ("verdict",), ("reject_reasons",), ("checks",)]
    current = reading.get("schema") == SCHEMA
    if current:
        need += [("rule", "recorded_in_anchor"), ("rule", "applied"), ("mode", "name"), ("tool_revision",),
                 ("comparison_with_frozen_grader", "frozen_reading_path"), ("comparison_with_frozen_grader", "frozen_reading_pin", "sha256_lf")]
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
    fields = ["gained", "broken", "kinds_improved", "worlds_improved", "passed", "receipt_dir"]
    if current:                                           # revision 1: everything the replay and the sanity checks need
        fields += ["p_one_sided", "world_ids_improved", "frozen_18_before", "frozen_18_after"]
    for seed, s in reading["per_seed"].items():
        for field in fields:
            if _get(s, field) is None:
                missing.append("per_seed.%s.%s" % (seed, field))
        for ph in PHASES:
            for field in ["predictions_sha256_lf"] + (["rescored", "disagreements", "scoring_rows_compared"] if current else []):
                if _get(s, "phases", ph, field) is None or _get(s, "phases", ph, field) == "":
                    missing.append("per_seed.%s.phases.%s.%s" % (seed, ph, field))
    return missing


def reading_type_problems(reading):
    """Fields the checks index into must have the right JSON type: a wrong type is READING_MALFORMED, never a crash."""
    want = [(("anchor", "path"), str), (("anchor", "pin", "sha256_lf"), str), (("tool", "pin", "sha256_lf"), str),
            (("per_seed",), dict), (("label_rederived",), str), (("verdict",), str), (("reject_reasons",), list), (("checks",), dict)]
    if reading.get("schema") == SCHEMA:
        want += [(("rule", "recorded_in_anchor"), dict), (("rule", "applied"), dict), (("mode", "name"), str),
                 (("comparison_with_frozen_grader", "frozen_reading_path"), str),
                 (("comparison_with_frozen_grader", "frozen_reading_pin", "sha256_lf"), str)]
    elif reading.get("schema") == HISTORICAL_READING_SCHEMA:
        want += [(("comparison_with_frozen_grader", "frozen_reading_path"), str)]
    bad = [".".join(path) for path, kind in want if not isinstance(_get(reading, *path), kind)]
    for seed, s in (reading.get("per_seed") or {}).items() if isinstance(reading.get("per_seed"), dict) else ():
        if not isinstance(s, dict) or not isinstance(s.get("phases"), dict) or not isinstance(s.get("receipt_dir"), str) \
                or not isinstance(s.get("passed"), bool):
            bad.append("per_seed.%s" % seed)
    for name, c in (reading.get("checks") or {}).items() if isinstance(reading.get("checks"), dict) else ():
        if not isinstance(c, dict):
            bad.append("checks.%s" % name)
    return bad


def reading_count_problems(reading, anchor):
    """The recorded counts must be POSSIBLE for the anchored population (review BLOCKER 1): distinct kinds and worlds
    drawn from the anchor's kind_of / world_of, gained + broken at most the population, no more kinds or worlds than
    gains, before/after counts that add up, and every prediction of every phase re-checked with no disagreement."""
    pop = anchor["population"]["question_ids"]
    n, expected_n = len(pop), anchor["expected_record_count"]
    kinds_ok, worlds_ok = set(anchor["population"]["kind_of"].values()), set(anchor["population"]["world_of"].values())
    bad = []
    for seed, s in sorted(reading["per_seed"].items()):
        g, c, w = s.get("gained"), s.get("broken"), s.get("worlds_improved")
        if any(type(v) is not int or v < 0 for v in (g, c, w)):
            bad.append("%s: gained, broken and worlds_improved must be nonnegative integers" % seed)
            continue
        kinds = s.get("kinds_improved")
        if not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds):
            bad.append("%s: kinds_improved is not a list of kind names" % seed)
            continue
        if len(set(kinds)) != len(kinds):
            bad.append("%s: kinds_improved names a kind more than once: %s" % (seed, kinds))
        if not set(kinds) <= kinds_ok:
            bad.append("%s: %s are not kinds of the anchored population %s" % (seed, sorted(set(kinds) - kinds_ok), sorted(kinds_ok)))
        if g + c > n:
            bad.append("%s: gained %d + broken %d is more than the %d-question population" % (seed, g, c, n))
        if len(set(kinds)) > g or w > g:
            bad.append("%s: %d kinds and %d worlds improved from only %d gains" % (seed, len(set(kinds)), w, g))
        if w > len(worlds_ok):
            bad.append("%s: %d worlds improved, but the anchored population has %d worlds" % (seed, w, len(worlds_ok)))
        ids = s.get("world_ids_improved")
        if ids is not None:
            if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids) or len(set(ids)) != len(ids):
                bad.append("%s: world_ids_improved is not a list of distinct world ids" % seed)
            elif not set(ids) <= worlds_ok:
                bad.append("%s: world_ids_improved names worlds outside the anchored population" % seed)
            elif len(ids) != w:
                bad.append("%s: worlds_improved is %d but %d world ids are listed" % (seed, w, len(ids)))
        before, after = s.get("frozen_18_before"), s.get("frozen_18_after")
        if before is not None or after is not None:
            if type(before) is not int or type(after) is not int or not (0 <= before <= n and 0 <= after <= n):
                bad.append("%s: frozen_18_before / frozen_18_after are not counts within the population" % seed)
            elif after != before + g - c or c > before or g > n - before:
                bad.append("%s: before %d, gained %d, broken %d, after %d do not add up" % (seed, before, g, c, after))
        for ph in PHASES:
            entry = _get(s, "phases", ph) or {}
            done, differ, compared = entry.get("rescored"), entry.get("disagreements"), entry.get("scoring_rows_compared")
            if done is not None or differ is not None:
                if done != expected_n or differ != 0:
                    bad.append("%s:%s: %r of %d predictions re-checked, %r disagreements" % (seed, ph, done, expected_n, differ))
            if compared is not None and compared != done:
                bad.append("%s:%s: %r scoring rows compared for %r predictions re-checked" % (seed, ph, compared, done))
    return bad


def trusted_reading_clean_problems(reading):
    """A clean 0.4 trusted reading records EXACTLY this tool's checks, every one PASS except the two historical
    checks (NOT_REQUESTED in trusted mode), and records that the tool itself loaded and ran the checker."""
    bad, names, checks = [], set(SAFE_CHECKS + CHECKER_CHECKS + FINAL_CHECKS), reading["checks"]
    if set(checks) != names:
        bad.append("the reading's checks are not exactly this tool's checks (missing %s, extra %s)" % (
            sorted(names - set(checks))[:6], sorted(set(checks) - names)[:6]))
    for name in sorted(names & set(checks)):
        want = "NOT_REQUESTED" if name in TRUSTED_NOT_REQUESTED else "PASS"
        if _get(checks, name, "status") != want:
            bad.append("check %s is %r; a clean trusted reading records %s" % (name, _get(checks, name, "status"), want))
    if reading.get("imported_checker_code") is not True:
        bad.append("the reading does not record that the checker ran")
    if reading.get("material_supplied_by_caller") is not False:
        bad.append("the checker material was supplied by a caller, not loaded by the tool")
    return bad


def trusted_frozen_grader_problems(reading, replay, label):
    """Compare the replayed decisions with the frozen grader reading the rescore PINNED (review BLOCKER 1). This narrows
    the gap but cannot close it: a frozen grader reading is itself built from scoring files. Returns (problems, info)."""
    cmp = reading["comparison_with_frozen_grader"]
    rel, pin = cmp["frozen_reading_path"], cmp["frozen_reading_pin"]["sha256_lf"]
    path = _receipt_path(rel)
    if not path.is_file():
        return [("READING_EVIDENCE_INCOMPLETE", "the frozen grader reading the reading pinned is absent: %s" % rel)], None
    if _lf_sha(path) != pin:
        return [("READING_EVIDENCE_ALTERED", "the frozen grader reading at %s is not the one the reading pinned" % rel)], None
    try:
        gate, problems = strict_json(path.read_text(encoding="utf-8"))
        if not isinstance(gate, dict) or not isinstance(gate.get("seeds"), dict) or problems.duplicate_keys or problems.nonfinite:
            raise ValueError("not a frozen grader reading")
        per = {seed: compare_seed_result(_get(gate, "seeds", seed, "G_LEARN_population") or {}, r) for seed, r in sorted(replay.items())}
    except (ValueError, TypeError, UnicodeDecodeError) as error:
        return [("READING_EVIDENCE_INCOMPLETE", "the frozen grader reading %s is unreadable (%s)" % (rel, type(error).__name__))], None
    out = []
    if set(gate["seeds"]) != set(replay):
        out.append(("FROZEN_GRADER_DISAGREES", "seed sets differ: frozen grader %s, reading %s" % (sorted(gate["seeds"]), sorted(replay))))
    for seed, row in per.items():
        if not row["agree"]:
            out.append(("FROZEN_GRADER_DISAGREES", "seed %s: %s differ from the frozen grader reading" % (
                seed, sorted(k for k, v in row["field_agreement"].items() if not v))))
    if gate.get("label") != label:
        out.append(("FROZEN_GRADER_DISAGREES", "label: frozen grader %r, replay %r" % (gate.get("label"), label)))
    return out, {"path": rel, "sha256_lf": pin, "frozen_label": gate.get("label"), "per_seed": per}


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
    for detail in reading_count_problems(reading, anchor):        # revision 1: the counts must be possible
        run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", detail)
    if entry is not None and _get(reading, "comparison_with_frozen_grader", "frozen_reading_path") != entry["frozen_grader_reading"][0]:
        run.fail("READING_CONSISTENCY", "READING_INCONSISTENT", "the reading was compared with %r, not the original frozen grader reading %s" % (
            _get(reading, "comparison_with_frozen_grader", "frozen_reading_path"), entry["frozen_grader_reading"][0]))
    run.passed("READING_CONSISTENCY", "seeds, predictions digests and receipts agree with the anchor; the recorded counts are possible")


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
    label = historical_label(r["replay_with_the_preserved_rule"]["passed"] for r in rows.values())
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
    apath = _receipt_path(reading["anchor"]["path"])
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
            run.fail("READING_READABLE", "READING_SCHEMA_OUTDATED", "reading schema %r; this check needs %r" % (schema, SCHEMA))
        elif reading.get("tool_revision") != TOOL_REVISION:
            run.fail("READING_READABLE", "READING_SCHEMA_OUTDATED", "reading written by tool revision %r; this check needs revision %r "
                     "(checkpoint and frozen-grader pins)" % (reading.get("tool_revision"), TOOL_REVISION))
        elif _get(reading, "mode", "name") != TRUSTED:
            run.fail("READING_CONSISTENCY", "READING_NOT_TRUSTED", "a historical-compatibility reading is never a trusted reading")
        if reading["verdict"] != "RESCORE_OK" or reading["reject_reasons"]:
            run.fail("READING_CONSISTENCY", "READING_NOT_CLEAN", "recorded verdict %r with %d reasons" % (reading["verdict"], len(reading["reject_reasons"])))
        if schema == SCHEMA:                              # revision 1: every recorded check, exactly
            for detail in trusted_reading_clean_problems(reading):
                run.fail("READING_CONSISTENCY", "READING_NOT_CLEAN", detail)
        if run.reasons or anchor is None:
            return "VOID_REJECTED"
        sub = _Run()
        _safe_checks(sub, _receipt_path(anchor["study"]["path"]), apath, {}, TRUSTED)
        _merge(run, sub, "ANCHOR_EVIDENCE")
        run.passed("ANCHOR_EVIDENCE", "every pin the anchor names matches the file on disk, the run manifests and checkpoint weight files included")
        _reading_consistency(run, reading, anchor)
        if run.failed("READING_CONSISTENCY"):
            run.not_run("DECISIONS_REPLAYED", "the reading is inconsistent with its anchor")
            return "VOID_REJECTED"
        replay = {}
        for seed, s in sorted(reading["per_seed"].items()):
            p, passed = historical_decision(s["gained"], s["broken"], len(s["kinds_improved"]), s["worlds_improved"])
            replay[seed] = {"gained": s["gained"], "broken": s["broken"], "p_one_sided": str(p), "passed": passed,
                            "recorded_p_one_sided": s["p_one_sided"], "recorded_passed": s["passed"],
                            "kinds_improved": sorted(s["kinds_improved"]), "world_ids_improved": sorted(s["world_ids_improved"])}
            if s["passed"] is not passed or s["p_one_sided"] != str(p):
                run.fail("DECISIONS_REPLAYED", "READING_DECISION_MISMATCH", "seed %s: recorded %s (p %s), the preserved rule gives %s (p %s)" % (
                    seed, s["passed"], s["p_one_sided"], passed, p))
        label = historical_label(r["passed"] for r in replay.values())
        if reading["label_rederived"] != label:
            run.fail("DECISIONS_REPLAYED", "READING_DECISION_MISMATCH", "recorded label %s, the preserved rule gives %s" % (reading["label_rederived"], label))
        problems, frozen = trusted_frozen_grader_problems(reading, replay, label)
        for code, detail in problems:
            run.fail("DECISIONS_REPLAYED", code, detail)
        info["frozen_grader"] = frozen
        run.passed("DECISIONS_REPLAYED", "%d seed decisions re-derived from the RECORDED counts and compared with the pinned frozen "
                   "grader reading; this is NOT a rescore" % len(replay))
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
    _, _, _, sub_info = _safe_checks(sub, _receipt_path(anchor["study"]["path"]), apath, {}, HISTORICAL)
    info["evidence"] = (sub_info or {}).get("evidence")
    _merge(run, sub, "ANCHOR_EVIDENCE")
    run.passed("HISTORICAL_EVIDENCE", "verified against frozen or recorded digests: " + evidence_detail(info["evidence"]))
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
    """Verify a committed reading WITHOUT rescoring and without importing any checker code. In trusted mode this is
    never trusted acceptance: at best READING_CONSISTENT_NOT_RESCORED (exit 5). Only a full rescore gives exit 0."""
    mode = HISTORICAL if historical_compatibility else TRUSTED
    reading_path = pathlib.Path(reading_path)
    guard = protected_paths(reading_path)
    refusal = output_refusal(out_path, guard)
    if refusal:                                           # revision 1: create-only, refused before ANY work
        return _print_output_refusal(refusal, mode)
    run = _Run(READING_CHECKS)
    watched = snapshot_paths(reading_path)
    before = snapshot(watched)
    info = {"reading_sha256_lf": None, "entry": None, "recorded_rule": None, "applied_rule_recorded": None, "evidence": None,
            "decisions": None, "frozen_grader": None}
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
        wrong = reading_type_problems(reading)
        if wrong:
            run.fail("READING_READABLE", "READING_MALFORMED", "fields of the wrong JSON type: %s" % wrong[:8])
            reading = None
    if reading is not None:
        run.passed("READING_READABLE", _rel(reading_path))
        if not run.failed("TOOL_CONSTANTS"):
            try:
                label = _check_reading_body(run, reading, reading_path, mode, info)
            except (TypeError, ValueError, KeyError, AttributeError, IndexError) as error:     # refused by name, never a crash
                run.fail("READING_READABLE", "READING_MALFORMED", "the reading or the evidence it names has an unexpected structure "
                         "(%s: %s)" % (type(error).__name__, str(error)[:120]))
    if mode == TRUSTED and run.checks["HISTORICAL_EVIDENCE"]["status"] == "NOT_RUN":
        run.checks["HISTORICAL_EVIDENCE"] = dict(NOT_REQUESTED_TRUSTED)
    originals = _originals_check(run, watched, before)
    statuses = [c["status"] for c in run.checks.values()]
    ok = "HISTORICAL_COMPATIBILITY_OK" if mode == HISTORICAL else "READING_CONSISTENT_NOT_RESCORED"
    verdict = "REJECT" if run.reasons else ("CHECK_INCOMPLETE" if "NOT_RUN" in statuses else ok)
    replayed = label if (mode == TRUSTED and verdict == ok) else None
    if verdict == "REJECT":
        label = "VOID_REJECTED"
    elif verdict != "HISTORICAL_COMPATIBILITY_OK":
        label = "NOT_DERIVED"                             # consistent recorded counts are not a derived label
    hist_block = _historical_block(info, info["decisions"]) if mode == HISTORICAL else None
    tool_pin = file_pin(__file__)
    record = {"schema": CHECK_SCHEMA, "tool_version": TOOL_VERSION, "tool_revision": TOOL_REVISION, "mode": _mode_block(mode),
              "verdict": verdict, "label": label, "trusted_acceptance": False, "rescored": False,
              "label_replayed_from_recorded_counts": replayed,
              "reject_reasons": run.reasons, "checks": run.checks,
              "reading": {"path": _rel(reading_path), "sha256_lf": info["reading_sha256_lf"],
                          "written_by_this_tool_file": _get(reading, "tool", "pin", "sha256_lf") == tool_pin["sha256_lf"] if reading else None},
              "tool": {"path": _rel(__file__), "pin": tool_pin}, "hash_policy": HASH_POLICY["policy_id"],
              "rule": _rule_block(info["recorded_rule"], info["applied_rule_recorded"]),
              "historical_exception": hist_block, "decisions": info["decisions"], "frozen_grader": info["frozen_grader"],
              "originals": originals, "custody": CUSTODY,
              "boundary": "no checker code was imported or run and NOTHING WAS RESCORED; decisions were re-derived from the counts the "
                          "reading recorded, and the evidence behind it was verified by hash. Only a full rescore (RESCORE_OK, exit 0) "
                          "is trusted acceptance."}
    written = _write_output(out_path, record)
    print(json.dumps({k: record[k] for k in ("verdict", "label", "reject_reasons")}, indent=1))
    print("  mode: %s" % mode)
    if hist_block:
        _print_historical(hist_block)
    if mode == TRUSTED and verdict == ok:
        print("  NOT A RESCORE: the recorded counts are consistent (label %s), which is not trusted acceptance; "
              "only a full rescore (RESCORE_OK, exit 0) is" % replayed)
    print("  checks:", ", ".join("%s=%s" % (k, v["status"]) for k, v in run.checks.items()))
    for seed, row in sorted((info["decisions"] or {}).items()):
        if mode == HISTORICAL:
            r = row["replay_with_the_preserved_rule"]
            print("  seed %s: gained %d broken %d, p %s -> historical decision %s (frozen grader %s); the original record says %s%s" % (
                seed, r["gained"], r["broken"], r["p_one_sided"], r["passed"], row["frozen_grader"]["passed"],
                row["decision_recorded_in_the_original_record"],
                "  <- the recognised mistake" if row["recorded_decision_differs_from_history"] else ""))
        else:
            print("  seed %s: gained %d broken %d, p %s -> %s (recorded counts, not rescored)" % (
                seed, row["gained"], row["broken"], row["p_one_sided"], row["passed"]))
    return EXIT_CODES[verdict] if written else EXIT_CODES["REJECT"]


class _Parser(argparse.ArgumentParser):
    """A usage error has its own exit code (64), never 2, which is REJECT."""
    def error(self, message):
        self.print_usage(sys.stderr)
        print("%s: USAGE_ERROR: %s" % (self.prog, message), file=sys.stderr)
        sys.exit(EXIT_USAGE)


def main():
    parser = _Parser(description=__doc__.split("\n")[0])
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
    bad = [r for r in args.receipt if "=" not in r]
    if bad:
        parser.error("--receipt takes seed=dir; got %s" % bad)
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
