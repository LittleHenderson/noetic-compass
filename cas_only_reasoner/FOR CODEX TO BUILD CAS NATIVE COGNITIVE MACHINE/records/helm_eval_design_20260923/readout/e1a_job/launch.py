"""E1a: checks before any results, on ONE AWS T4 (readout plan item 9). CLAUDE_BUILT_CLAUDE_CHECKED. NOT LAUNCHED.

A NEW folder. It copies patterns from `../gates_job/launch.py` (bundle streamed from git objects, custody filters,
IMDSv2 instance line, one attempt) and `../../larger_question_t4_job/launch.py` (the pinned T4 image, torch build,
e05889ee source); it re-uses neither folder.

WHAT RUNS ON THE MACHINE (`e1a_machine.py`, `job.sh.template`). No TEST data. No analogy number is printed.
  0  IMDSv2 instance id -> env.txt; pinned tools; every bundled file against anchors.json; torch/CUDA/T4 smoke.
     TIMING PREFLIGHT: real probe and fixture calls are timed and the whole job is projected; over the wall budget
     (or over a harness process's own 3,600 s wall) it stops here: PREFLIGHT_OVER_WALL_LIMIT.
  1  ROUTE: the smoke switch-ON final.pt and the six study finals through the e05889ee route
     (`larger_question_learner.predict_packet`): the three repaired finals and the smoke final with the switch ON,
     the three unchanged finals (U17 fresh; Helm 2.0 seeds 20260918 and 20260919) with the switch OFF. The switch is
     read back and asserted. Public fixtures only; no right/wrong, answer digest or check digest is written.
  2  PROBE v0.3 VALIDATION on the real harness (prereg v0.3 section 6: fresh container, seed 20260917, switch OFF).
  3  THE 18 PROBE READS (3 repaired seeds x pass_01, main_checkpoint_0294/0588/0882/1176, final), then ITEM2. They
     start only if the stage-2 validation re-derives as VALIDATION_PASS from its raw tables.
  4  MATCHED START (A5.5): the real-file self-test, then the reading.
  5  CHECKPOINT ROSTER on each repaired receipt.
  Stages 1, 2 and 4+5 run side by side; stage 3 waits for all of them.

THE BUNDLE is built from GIT OBJECTS only, streamed one blob at a time to a NEW folder outside every git tree:
  * source at e05889ee (the accepted route): cncm/*.py, cas_meta2/**/*.py, the eval_paths route files and fixtures,
    the course, tokenizer, development file and both wheels, Helm 2.0's three initial.pt and the finals of seeds
    20260918 and 20260919 -- every data file and checkpoint checked against its pin;
  * the readout programs at READOUT_COMMIT (probe v0.3 with its side files, the ITEM2 reader, matched start, roster),
    each checked against its LF sha256 pin;
  * the smoke switch-ON final.pt at 1ddf6a1e (pinned 5b896bec...);
  * THE STUDY RECEIPTS: the three repaired receipts named by the frozen repaired study (c0d65ce8...) at
    --repaired-commit, and U17's receipt named by the frozen unchanged study (60140ae0...) at --unchanged-commit.
    Every receipt file is bound to its receipt's collected_inventory.json (sha256 and bytes).
  REFUSED WITHOUT THE STUDY RECEIPTS: a real launch refuses before building anything; a dry run builds what exists,
  runs the custody filters, prints the plan and then refuses (exit 2, STUDY_RECEIPTS_MISSING).

    python -B launch.py --dry-run [--repaired-commit SHA] [--unchanged-commit SHA] [--bundle-dir DIR]
    python -B launch.py --repaired-commit SHA --unchanged-commit SHA --acceptance-record PATH     (the coordinator)

A dry run never imports boto3 and never touches the network (no AWS call, no git fetch).
"""
import argparse
import datetime
import gzip
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[3]                     # e1a_job -> readout -> helm_eval_design_20260923 -> records -> CNCM
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, PRICE_PER_HOUR = "g4dn.2xlarge", 0.752          # NVIDIA T4, 8 vCPU, 32 GiB; on-demand us-west-2
ADDRESS_PER_HOUR, ROOT_GB, GB_MONTH_USD = 0.005, 100, 0.08
PINNED_AMI = "ami-07d69ce07bfe5628f"          # the T4 image of P1a and the analogy T4 job. No substitute.
MAX_SECONDS, OS_POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES = 120 * 60, 123, 130
JOB_BUDGET_SECONDS = 110 * 60                 # the in-machine preflight projects against this (10 min under the timer)
COST_CAP_USD, ALLOWANCE_USD = 2.00, 0.10      # readout plan item 9: cap $2.00 + $0.10
EXPECTED_MINUTES = (60, 75)                   # readout plan estimate, NOT measured
UV_VERSION, PYTHON_VERSION = "0.12.17", "3.14.7"
TORCH_VERSION, TORCH_LOCAL, NUMPY_VERSION = "2.11.0", "2.11.0+cu128", "2.5.2"
GPU_FAMILIES = ["g4dn.*", "g4ad.*", "g5.*", "g5g.*", "g6.*", "g6e.*", "g6f.*", "gr6.*", "g7.*", "g7e.*",
                "p3.*", "p3dn.*", "p4d.*", "p4de.*", "p5.*", "p5e.*", "p5en.*"]
LINK_SECONDS, USER_DATA_LIMIT = 4 * 3600, 16000
MAX_BUNDLE_FILES, MAX_BUNDLE_BYTES = 2000, 400 * 1024 ** 2

# ---- the pinned sources --------------------------------------------------------------------------------------------
SOURCE_COMMIT = "e05889eec0f800a9a17b0c39a8d8d37f544b43bf"     # the accepted larger-question route (P1a ROUTE_ACCEPTED)
SOURCE_BRANCH = "claude/helm-builder-continuation-20260923"
READOUT_COMMIT = "994c32ebe8b4aa70b3c7b6f09df864e5d39f1f36"    # probe-v03 994c32eb, matched-start f781c1a6, roster fb18fe8f
READOUT_BRANCH = "research/helm-integration-20260923"
SMOKE_COMMIT = "1ddf6a1e4cdefee8aed30760904c7ec4cf49333e"      # switch-ON smoke attempt 2 receipt
REPAIRED_BRANCH = "claude/helm-on-launch-20260924"
UNCHANGED_BRANCH = "claude/helm-unchanged-repro-20260924"
R = "records/typed_pointer_001/"
SEEDS = (20260917, 20260918, 20260919)
SOURCE_TREES = ("cncm/", "research/CAS_META_2_COMPOSITION/cas_meta2/")          # *.py only
EVAL = "research/CAS_META_2_COMPOSITION/eval_paths/"
WHEELS = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
# Raw sha256 of committed blobs at SOURCE_COMMIT (P1a REQUIRED_INPUTS and its identity record).
SOURCE_PINS = {
    "records/typed_course_001/checks_002/public_course.json": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
    "records/typed_interface_001/checks_002/training_tokenizer.json": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c",
    "records/typed_matched_001/development_001/compact_development.json": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4",
    WHEELS + "casformer_reference-0.1.0-py3-none-any.whl": "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
    WHEELS + "cas_neural_cjt-0.2.0-py3-none-any.whl": "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9",
    EVAL + "__init__.py": "38a1d4f57995cd43b5a0ed1616b2e941726327abed0919f3d8ce7a793f1e0ae4",
    EVAL + "larger_question_scope.py": "a09a172510b2f5ad1dd2ba2bc56d6cd46f354b619264bac90d18aa06748f9f32",
    EVAL + "larger_question_learner.py": "82e963a4b30b2aab8a8cb7371faaca32b66c011a90bece59d1f9106a7bd7d35d",
    EVAL + "larger_question_fixtures.py": "567331464043e7fdb4edffc1dc056f266c75141c312fecdca43d10dff3c3e86d",
    EVAL + "fixtures/larger_question_fixtures_v0_1.json": "7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3",
    R + "receipt_20260917/checkpoints/initial.pt": "59dd46877bd7bf97dbb4059975051cc6102b374d5c387d3a183884048b71b004",
    R + "receipt_20260918/checkpoints/initial.pt": "d3c6292f2c0d09e29952bfe353d47fff058741d42c0a8e8dbe7a80eaad8fd645",
    R + "receipt_20260919/checkpoints/initial.pt": "93b84558c0123673eabcc462f68afe8ecb1537b598e297ee16f7a7458787ee9f",
    R + "receipt_20260918/checkpoints/final.pt": "a6e72caac1fccbd994433a46684846f5a3de48683dcc6b5def5946b85ef20658",
    R + "receipt_20260919/checkpoints/final.pt": "c83e0123643a2433e1650bd4898dc28865204fd3d03fbedd22910632caf7dec8",
}
PROBE_DIR = "records/helm_eval_design_20260923/readout/probe-v03/"
MATCHED_DIR = "records/helm_eval_design_20260923/readout/matched_start/"
ROSTER_DIR = "records/helm_eval_design_20260923/readout/roster/"
# LF sha256 at READOUT_COMMIT. The three probe hashes are what an acceptance record must name (prereg v0.3 s9).
READOUT_PINS = {
    PROBE_DIR + "probe_v0_3_harness.py": "5971a39653b9bce52af17edf24799d1cfbe77f785d0d9426bce748e85163c3a4",
    PROBE_DIR + "probe_v0_3_metric.py": "220d1dcd0b6bbd6af8b8bdbc4bcee0ba23bb981f80a25d4b8c111d4d4269c131",
    PROBE_DIR + "PREREG_ANALOGY_WIRING_PROBE_v0_3.md": "e524392375b63419e512f94ccf1cdc147c768f6a1dd7a8f4f8f2a613686760a7",
    PROBE_DIR + "item2_reader.py": "57d02ee3e43162a5b01ced56585d136ba6f5f0b34836cc2ea52bd1c0dffd11e3",
    MATCHED_DIR + "matched_start.py": "1695fa078628b61986787d04a13594405a4f84d40c5829ba436b3d5320159738",
    ROSTER_DIR + "check_roster.py": "fc8e128a2cef9e010845c2d2aa2c47f2be078a385a62d6911a8876d6c78ee7f4",
}
ACCEPTANCE_FIELDS = {"prereg_sha256_lf": PROBE_DIR + "PREREG_ANALOGY_WIRING_PROBE_v0_3.md",
                     "metric_sha256_lf": PROBE_DIR + "probe_v0_3_metric.py",
                     "harness_sha256_lf": PROBE_DIR + "probe_v0_3_harness.py"}
SMOKE_FINAL = R + "receipt_analogy_on_smoke_20260917/collected/results/artifacts/final.pt"
SMOKE_FINAL_SHA256 = "5b896bec3d0be48367aeda9cb9b0a5319e9517c78d5b0f4c62601bf34cbf9725"
# The frozen studies that NAME the receipt folders (LF sha256).
REPAIRED_STUDY = (R + "admission_analogy_on_001/seeds/study.json",
                  "c0d65ce8d1e040c3631ef5148fff4a3934a79ff74ba4f48d8a634380b78e904d")
UNCHANGED_STUDY = (R + "admission_unchanged_repro_001/frozen/study.json",
                   "60140ae0587e983120f37cb3499ecdc19e59f23cc0363520b2814e9e413f8a12")
# Prereg A5: (roster label, ITEM2 path, path under collected/, registered main updates).
A5 = (("pass_01", "pass_01.pt", "results/artifacts/pass_01.pt", 147),
      ("main_checkpoint_0294", "evidence/main_checkpoint_0294.pt", "results/evidence/main_checkpoint_0294.pt", 294),
      ("main_checkpoint_0588", "evidence/main_checkpoint_0588.pt", "results/evidence/main_checkpoint_0588.pt", 588),
      ("main_checkpoint_0882", "evidence/main_checkpoint_0882.pt", "results/evidence/main_checkpoint_0882.pt", 882),
      ("main_checkpoint_1176", "evidence/main_checkpoint_1176.pt", "results/evidence/main_checkpoint_1176.pt", 1176),
      ("final", "final.pt", "results/artifacts/final.pt", 1470))
# Receipt files, relative to collected/ (bound to collected_inventory.json) -- the roster, the probe and matched start.
REPAIRED_COLLECTED = (["results/artifacts/initial.pt", "results/artifacts/pass_01_checkpoint.json",
                       "results/artifacts/final_checkpoint.json", "results/artifacts/worker_report.json"]
                      + [row[2] for row in A5]
                      + ["results/evidence/main_checkpoint_%04d.json" % n for n in (294, 588, 882, 1176)]
                      + ["results/artifacts/pass_%02d_updates.jsonl" % n for n in range(1, 11)])
UNCHANGED_COLLECTED = ("results/artifacts/final.pt", "results/artifacts/final_checkpoint.json")
ROOT_REQUIRED, ROOT_OPTIONAL = ("collected_inventory.json",), ("reduced_schedule.json",)
# ---- custody: an allowlist (above) plus a second line on every bundle name, case-insensitive --------------------------
FORBIDDEN_NAME_PARTS = ("sealed", "_eval.jsonl", "salt", "private_target", "protected", "transcript", "hset",
                        "tkscas-archive", "test_new", "_scoring.json", "_predictions.json")
DESIGN_PREFIX = "records/helm_eval_design_20260923/"
JOB_FILES = ("e1a_machine.py",)
TEMPLATE = "job.sh.template"
LABELS = ["CLAUDE_BUILT_CLAUDE_CHECKED", "EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT"]


class Refused(SystemExit):
    pass


def refuse(code, detail):
    print("LAUNCH_REFUSED: %s: %s" % (code, detail), flush=True)
    raise Refused(2)


# ---- git (read only) -----------------------------------------------------------------------------------------------
def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True).stdout


def prefix():
    return git("rev-parse", "--show-prefix").decode().strip()


def full_commit(ref):
    if not ref:
        return None
    try:
        return git("rev-parse", "--verify", "--quiet", ref + "^{commit}").decode().strip() or None
    except subprocess.CalledProcessError:
        return None


def listing(commit, *folders):
    """{package-relative path: size} of every blob at `commit` under the given package-relative folders."""
    pre, out = prefix(), {}
    raw = git("ls-tree", "-r", "-z", "-l", "--full-tree", commit, "--", *[pre + f for f in folders])
    for entry in raw.split(b"\0"):
        if entry:
            meta, _, path = entry.decode("utf-8").partition("\t")
            if meta.split()[1] == "blob" and path.startswith(pre):
                out[path[len(pre):]] = int(meta.split()[3])
    return out


class Blobs:
    """Exact stored bytes, one blob at a time, through ONE `git cat-file --batch` (no line-ending conversion)."""

    def __init__(self):
        self.pre = prefix()
        self.proc = subprocess.Popen(["git", "-C", str(PACKAGE), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)

    def read(self, commit, rel, missing_ok=False):
        self.proc.stdin.write(("%s:%s%s\n" % (commit, self.pre, rel)).encode("utf-8"))
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().decode("utf-8").rstrip("\n")
        if header.endswith(" missing") or len(header.split()) != 3:
            if missing_ok:
                return None
            refuse("BUNDLE_FILE_MISSING", "%s at %s" % (rel, commit[:8]))
        data = self.proc.stdout.read(int(header.split()[2]))
        self.proc.stdout.read(1)
        return data

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def lf_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


# ---- custody -------------------------------------------------------------------------------------------------------
def custody_refusals(bundle_names):
    """Every bundle name that breaks custody: a forbidden word anywhere; any file of the evaluation-design tree other
    than the six pinned readout programs (so no HSET material can ride along); a private course file; a path escape."""
    allowed_design = {"tree/" + p for p in READOUT_PINS}
    bad = []
    for name in bundle_names:
        low = name.lower()
        rel = name[len("tree/"):] if name.startswith("tree/") else None
        if (any(part in low for part in FORBIDDEN_NAME_PARTS)
                or (rel is not None and rel.startswith(DESIGN_PREFIX) and name not in allowed_design)
                or (rel is not None and rel.startswith("records/typed_course_001/checks_002/private"))
                or "__pycache__" in name or name.endswith(".pyc") or ".." in name.split("/") or name.startswith("/")
                or not (name.startswith(("tree/", "claude/")) or name == "anchors.json")):
            bad.append(name)
    return bad


# ---- the study receipts --------------------------------------------------------------------------------------------
def receipt_folder(receipt_dir):
    name = re.split(r"[\\/]", str(receipt_dir).rstrip("\\/"))[-1]
    if not re.fullmatch(r"receipt_[A-Za-z0-9_]+", name):
        refuse("STUDY_RECEIPT_NAME", receipt_dir)
    return name


def study_receipt_names(study_bytes, kind):
    """{seed: receipt folder} from a frozen study's jobs[].receipt_dir."""
    study = json.loads(study_bytes)
    names = {int(job["model_seed"]): receipt_folder(job["receipt_dir"]) for job in study["jobs"]}
    want = list(SEEDS) if kind == "repaired" else [SEEDS[0]]
    if sorted(names) != want or len(set(names.values())) != len(want):
        refuse("STUDY_SHAPE", "%s study must name seeds %s with distinct receipts; got %s" % (kind, want, names))
    return names


def select_receipt(paths, folder, collected):
    """(wanted package-relative paths, missing). `paths` is the set of package-relative blob paths at the commit."""
    base = R + folder + "/"
    wanted = [base + f for f in ROOT_REQUIRED] + [base + "collected/" + c for c in collected]
    missing = [p for p in wanted if p not in paths]
    wanted += [base + f for f in ROOT_OPTIONAL if base + f in paths]
    return wanted, missing


def inventory_expectations(inventory_bytes, folder, collected):
    """{package-relative path: (sha256, bytes)} for the receipt's collected/ files, from collected_inventory.json.
    A file listed twice, not listed, or an inventory reporting failures is a refusal reason."""
    inventory = json.loads(inventory_bytes)
    rows, reasons = {}, []
    for row in inventory.get("files") or []:
        rel = row.get("relative_path")
        if rel in rows:
            reasons.append("INVENTORY_DUPLICATE:%s/%s" % (folder, rel))
        rows[rel] = row
    if inventory.get("failures"):
        reasons.append("INVENTORY_REPORTS_FAILURES:%s" % folder)
    out = {}
    for rel in collected:
        row = rows.get(rel)
        if row is None or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256"))):
            reasons.append("NOT_IN_INVENTORY:%s/%s" % (folder, rel))
            continue
        out[R + folder + "/collected/" + rel] = (row["sha256"], row.get("bytes"))
    return out, reasons


def resolve_receipts(blobs, repaired_commit, unchanged_commit):
    """Everything the study receipts contribute: bundle entries, expectations, spec parts and what is missing."""
    entries, expect, missing = [], {}, []
    parts = {"repaired_receipts": {}, "repaired_final_sha256": {}, "read_sha256": {}, "unchanged_final": None}
    study = blobs.read(repaired_commit, REPAIRED_STUDY[0], missing_ok=True) if repaired_commit else None
    if not repaired_commit:
        missing.append("REPAIRED_COMMIT_NOT_FOUND (give --repaired-commit, or fetch origin/%s)" % REPAIRED_BRANCH)
    elif study is None:
        missing.append("REPAIRED_STUDY_NOT_AT_%s (%s)" % (repaired_commit[:8], REPAIRED_STUDY[0]))
    else:
        if lf_sha(study) != REPAIRED_STUDY[1]:
            refuse("REPAIRED_STUDY", "%s at %s is not the frozen c0d65ce8" % (REPAIRED_STUDY[0], repaired_commit[:8]))
        names = study_receipt_names(study, "repaired")
        paths = set(listing(repaired_commit, *[R + n + "/" for n in names.values()]))
        for seed, folder in sorted(names.items()):
            parts["repaired_receipts"][str(seed)] = R + folder
            wanted, absent = select_receipt(paths, folder, REPAIRED_COLLECTED)
            if absent:
                missing.append("%s at %s: %d of %d files absent, e.g. %s" % (
                    folder, repaired_commit[:8], len(absent), len(wanted), absent[:3]))
                continue
            rows, reasons = inventory_expectations(blobs.read(repaired_commit, R + folder + "/collected_inventory.json"),
                                                   folder, REPAIRED_COLLECTED)
            if reasons:
                refuse("RECEIPT_INVENTORY", reasons[:6])
            expect.update(rows)
            entries += [("tree/" + p, repaired_commit, p) for p in wanted]
            parts["read_sha256"][str(seed)] = {row[0]: rows[R + folder + "/collected/" + row[2]][0] for row in A5}
            parts["repaired_final_sha256"][str(seed)] = rows[R + folder + "/collected/results/artifacts/final.pt"][0]
    study = blobs.read(unchanged_commit, UNCHANGED_STUDY[0], missing_ok=True) if unchanged_commit else None
    if not unchanged_commit:
        missing.append("UNCHANGED_COMMIT_NOT_FOUND (give --unchanged-commit, or fetch origin/%s)" % UNCHANGED_BRANCH)
    elif study is None:
        missing.append("UNCHANGED_STUDY_NOT_AT_%s (%s)" % (unchanged_commit[:8], UNCHANGED_STUDY[0]))
    else:
        if lf_sha(study) != UNCHANGED_STUDY[1]:
            refuse("UNCHANGED_STUDY", "%s at %s is not the frozen 60140ae0" % (UNCHANGED_STUDY[0], unchanged_commit[:8]))
        folder = study_receipt_names(study, "unchanged")[SEEDS[0]]
        paths = set(listing(unchanged_commit, R + folder + "/"))
        wanted, absent = select_receipt(paths, folder, UNCHANGED_COLLECTED)
        if absent:
            missing.append("%s at %s: %d of %d files absent, e.g. %s" % (
                folder, unchanged_commit[:8], len(absent), len(wanted), absent[:3]))
        else:
            rows, reasons = inventory_expectations(blobs.read(unchanged_commit, R + folder + "/collected_inventory.json"),
                                                   folder, UNCHANGED_COLLECTED)
            if reasons:
                refuse("RECEIPT_INVENTORY", reasons[:6])
            expect.update(rows)
            entries += [("tree/" + p, unchanged_commit, p) for p in wanted]
            final = R + folder + "/collected/results/artifacts/final.pt"
            parts["unchanged_final"] = {"checkpoint": final, "sha256": rows[final][0], "receipt": R + folder}
    return entries, expect, parts, missing


# ---- the fixed part of the bundle and the spec ---------------------------------------------------------------------
def fixed_entries():
    """(entries, raw-sha pins, LF-sha pins) for the source, the readout programs and the smoke final."""
    for commit, name in ((SOURCE_COMMIT, "source"), (READOUT_COMMIT, "readout"), (SMOKE_COMMIT, "smoke")):
        if full_commit(commit) != commit:
            refuse("PINNED_COMMIT_MISSING", "%s commit %s is not in this repository (git fetch it)" % (name, commit))
    source = listing(SOURCE_COMMIT, *SOURCE_TREES)
    code = sorted(p for p in source if p.endswith(".py"))
    if not any(p.startswith(SOURCE_TREES[0]) for p in code) or not any(p.startswith(SOURCE_TREES[1]) for p in code):
        refuse("SOURCE_TREE_EMPTY", SOURCE_TREES)
    entries = [("tree/" + p, SOURCE_COMMIT, p) for p in sorted(set(code) | set(SOURCE_PINS))]
    entries += [("tree/" + p, READOUT_COMMIT, p) for p in sorted(READOUT_PINS)]
    entries.append(("tree/" + SMOKE_FINAL, SMOKE_COMMIT, SMOKE_FINAL))
    return entries, dict(SOURCE_PINS, **{SMOKE_FINAL: SMOKE_FINAL_SHA256}), dict(READOUT_PINS)


def build_spec(parts, missing, commits, acceptance):
    """The machine's instructions (claude/e1a_spec.json). Paths are tree-relative."""
    containers = [{"label": "smoke_on_final", "arm": "repaired_smoke_reduced_run", "seed": SEEDS[0],
                   "checkpoint": SMOKE_FINAL, "sha256": SMOKE_FINAL_SHA256, "switch": True}]
    for seed in SEEDS:
        folder = parts["repaired_receipts"].get(str(seed))
        containers.append({"label": "repaired_final_%d" % seed, "arm": "repaired", "seed": seed,
                           "checkpoint": folder and folder + "/collected/results/artifacts/final.pt",
                           "sha256": parts["repaired_final_sha256"].get(str(seed)), "switch": True})
    unchanged = parts["unchanged_final"] or {}
    containers.append({"label": "unchanged_final_%d" % SEEDS[0], "arm": "unchanged_fresh_U17", "seed": SEEDS[0],
                       "checkpoint": unchanged.get("checkpoint"), "sha256": unchanged.get("sha256"), "switch": False})
    for seed in SEEDS[1:]:
        path = R + "receipt_%d/checkpoints/final.pt" % seed
        containers.append({"label": "unchanged_final_%d" % seed, "arm": "unchanged_historical_helm2", "seed": seed,
                           "checkpoint": path, "sha256": SOURCE_PINS[path], "switch": False})
    reads = {}
    for seed in SEEDS:
        folder = parts["repaired_receipts"].get(str(seed))
        shas = parts["read_sha256"].get(str(seed), {})
        reads[str(seed)] = [{"label": "on_%d_%s" % (seed, label), "roster_label": label,
                             "checkpoint_relative_path": item2_path, "main_updates_registered": updates,
                             "checkpoint": folder and folder + "/collected/" + collected, "sha256": shas.get(label)}
                            for label, item2_path, collected, updates in A5]
    return {"schema": "claude.e1a-spec/0.1", "seeds": list(SEEDS), "receipts_missing": missing,
            "source_commit": SOURCE_COMMIT, "readout_commit": READOUT_COMMIT, "smoke_commit": SMOKE_COMMIT,
            "repaired_commit": commits["repaired"], "unchanged_commit": commits["unchanged"],
            "route_containers": containers, "reads": reads, "waves": [[0, 1, 2], [3, 4, 5]],
            "repaired_receipts": parts["repaired_receipts"], "unchanged_receipt": unchanged.get("receipt"),
            "helm2_initial": {str(s): R + "receipt_%d/checkpoints/initial.pt" % s for s in SEEDS},
            "matched_start_on_dirs": {s: f + "/collected/results/artifacts" for s, f in parts["repaired_receipts"].items()},
            "probe_dir": PROBE_DIR.rstrip("/"), "matched_start_dir": MATCHED_DIR.rstrip("/"),
            "roster_dir": ROSTER_DIR.rstrip("/"),
            "validation": {"seed": SEEDS[0], "container_kwargs": {"analogy_focus_comparison": False},
                           "switch_expect": "false", "why": "prereg v0.3 section 6: fresh, seed 20260917, switch OFF"},
            "read_container_kwargs": {"analogy_focus_comparison": True}, "switch_attr": "analogy_focus_comparison",
            "acceptance_record": acceptance and "claude/probe_v0_3_acceptance.json", "labels": LABELS}


def acceptance_gate(path):
    """The probe v0.3 acceptance record (prereg v0.3 s9): a committed, unmodified file whose three hashes equal the
    pinned harness, metric and prereg. Returns its bytes and where it came from."""
    target = pathlib.Path(path).resolve()
    top = pathlib.Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    try:
        rel = target.relative_to(top).as_posix()
    except ValueError:
        refuse("ACCEPTANCE_RECORD_NOT_COMMITTED", "%s is outside this repository" % target)
    if not git("ls-files", "--", str(target)).strip() or git("status", "--porcelain", "--", str(target)).strip():
        refuse("ACCEPTANCE_RECORD_NOT_COMMITTED", "%s is not tracked, or differs from its committed version" % rel)
    data = git("show", "HEAD:" + rel)
    try:
        record = json.loads(data)
    except ValueError:
        refuse("ACCEPTANCE_RECORD_INVALID", "not JSON")
    wrong = [k for k, p in ACCEPTANCE_FIELDS.items() if not isinstance(record, dict) or record.get(k) != READOUT_PINS[p]]
    if (not isinstance(record, dict) or record.get("schema") != "claude.probe-v0.3-acceptance/0.1"
            or record.get("accepted_by") not in ("codex", "owner") or wrong):
        refuse("ACCEPTANCE_RECORD_INVALID", "schema/accepted_by/hashes do not bind the pinned probe v0.3: %s" % wrong)
    return {"path": rel, "commit": git("log", "-1", "--format=%H", "--", str(target)).decode().strip(),
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": data}


# ---- the bundle ----------------------------------------------------------------------------------------------------
def job_files():
    rels = [(HERE / name).relative_to(PACKAGE).as_posix() for name in JOB_FILES + (TEMPLATE,)]
    commit = git("log", "-1", "--format=%H", "--", *rels).decode().strip() or None
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *rels).decode().strip()
    return rels, commit, dirty


def read_job_file(blobs, commit, dirty, name):
    """Committed bytes when the job files are clean; the working copy otherwise (a dry run only; a launch refuses)."""
    if commit and not dirty:
        return blobs.read(commit, (HERE / name).relative_to(PACKAGE).as_posix())
    return (HERE / name).read_bytes().replace(b"\r\n", b"\n")


def write_bundle(entries, raw_pins, lf_pins, expect, generated, blobs, dest):
    """Stream a deterministic tar.gz to `dest`. Every pinned or inventoried file is checked as it streams.
    Returns (anchors, bundle sha256, bundle bytes, raw bytes)."""
    files, raw_total, seen = {}, 0, set()
    with open(dest, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=6, mtime=0) as zipped, \
            tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = len(data), 0, 0o644, 0, 0, "", ""
            tar.addfile(info, io.BytesIO(data))

        for name, commit, rel in entries:
            data = blobs.read(commit, rel)
            digest = hashlib.sha256(data).hexdigest()
            if rel in raw_pins and digest != raw_pins[rel]:
                refuse("PIN_MISMATCH", "%s (sha256 %s, pinned %s)" % (rel, digest[:12], raw_pins[rel][:12]))
            if rel in lf_pins and lf_sha(data) != lf_pins[rel]:
                refuse("PIN_MISMATCH", "%s (LF sha256 %s, pinned %s)" % (rel, lf_sha(data)[:12], lf_pins[rel][:12]))
            if rel in expect and (digest != expect[rel][0] or (expect[rel][1] is not None and len(data) != expect[rel][1])):
                refuse("RECEIPT_FILE_DIFFERS_FROM_INVENTORY", "%s (sha256 %s, inventory %s)" % (rel, digest[:12], expect[rel][0][:12]))
            seen.add(rel)
            files[name] = {"sha256": digest, "bytes": len(data), "from_commit": commit}
            raw_total += len(data)
            add(name, data)
        unseen = sorted((set(raw_pins) | set(lf_pins) | set(expect)) - seen)
        if unseen:
            refuse("PINNED_FILE_NOT_BUNDLED", unseen[:6])
        for name in sorted(generated):
            files[name] = {"sha256": hashlib.sha256(generated[name]).hexdigest(), "bytes": len(generated[name]),
                           "from_commit": "generated"}
            raw_total += len(generated[name])
            add(name, generated[name])
        anchors = {"schema": "claude.e1a-anchors/0.1", "files": files}
        add("anchors.json", json.dumps(anchors, indent=1, sort_keys=True).encode("utf-8"))
    digest = hashlib.sha256()
    with open(dest, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return anchors, digest.hexdigest(), pathlib.Path(dest).stat().st_size, raw_total


def outside_git(folder):
    folder = pathlib.Path(folder).resolve()
    return not any((q / ".git").exists() for q in [folder] + list(folder.parents))


# ---- money and the machine script ----------------------------------------------------------------------------------
def worst_case_usd(minutes=CLIENT_DEADLINE_MINUTES):
    """Machine + auto-assigned public address + gp3 disk for `minutes` (default: the whole client deadline)."""
    return (PRICE_PER_HOUR + ADDRESS_PER_HOUR + ROOT_GB * GB_MONTH_USD / 730) * minutes / 60.0


def render(template, urls, bundle_sha):
    values = {"__MAX_SECONDS__": str(MAX_SECONDS), "__MAX_MINUTES__": str(OS_POWER_OFF_MINUTES),
              "__BUDGET_SECONDS__": str(JOB_BUDGET_SECONDS), "__BUNDLE_URL__": urls["bundle"],
              "__RESULTS_URL__": urls["results"], "__PROGRESS_URL__": urls["progress"], "__BUNDLE_SHA256__": bundle_sha,
              "__UV_VERSION__": UV_VERSION, "__PYTHON_VERSION__": PYTHON_VERSION, "__TORCH_VERSION__": TORCH_VERSION,
              "__TORCH_LOCAL__": TORCH_LOCAL, "__NUMPY_VERSION__": NUMPY_VERSION, "__WHEELS__": WHEELS.rstrip("/"),
              "__PROBE_DIR__": PROBE_DIR.rstrip("/"), "__VALIDATION_SEED__": str(SEEDS[0]),
              "__SOURCE_COMMIT__": SOURCE_COMMIT}
    script = template
    for key, value in values.items():
        script = script.replace(key, value)
    left = re.findall(r"__[A-Z][A-Z0-9_]*__", script)
    if left:
        raise AssertionError("unfilled placeholders in the machine script: %s" % sorted(set(left)))
    if len(script.encode("utf-8")) >= USER_DATA_LIMIT:
        raise AssertionError("the machine script is over the 16,000-byte user-data limit")
    return script


def plan_text(n_files, raw_bytes, bundle_bytes, bundle_sha, spec, dirty, acceptance):
    lo, hi = EXPECTED_MINUTES
    lines = [
        "PLAN (E1a: route receipt, probe v0.3 validation, 18 probe reads + ITEM2, matched start, roster)",
        "  machine   ONE %s (NVIDIA T4), %s, on-demand $%.3f/h, image %s (pinned, no substitute), %d GB gp3 deleted"
        " with the machine; no credentials on it" % (INSTANCE_TYPE, REGION, PRICE_PER_HOUR, PINNED_AMI, ROOT_GB),
        "  gpu rule  refuses if any GPU machine (%s) is pending, running or stopping" % ", ".join(GPU_FAMILIES),
        "  limits    in-machine timer %d min, OS power-off at %d min, client deadline %d min (watch.py terminates);"
        " timing preflight budget %d min" % (MAX_SECONDS // 60, OS_POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES,
                                             JOB_BUDGET_SECONDS // 60),
        "  COST CAP  worst case at the client deadline $%.4f <= cap $%.2f (plus the $%.2f allowance = $%.2f in the ledger)"
        % (worst_case_usd(), COST_CAP_USD, ALLOWANCE_USD, COST_CAP_USD + ALLOWANCE_USD),
        "  expected  about %d-%d min (readout plan estimate, not measured), about $%.2f-$%.2f"
        % (lo, hi, worst_case_usd(lo), worst_case_usd(hi)),
        "  retries   none: one launch attempt, one zone, no relaunch; launch_record.json refuses a second",
        "  bundle    %d files, %.1f MB raw, %.1f MB compressed, sha256 %s" % (n_files, raw_bytes / 1e6, bundle_bytes / 1e6, bundle_sha),
        "  sources   route %s; readout programs %s; smoke %s; repaired receipts %s; unchanged receipt %s" % (
            SOURCE_COMMIT[:8], READOUT_COMMIT[:8], SMOKE_COMMIT[:8], (spec["repaired_commit"] or "NONE")[:8],
            (spec["unchanged_commit"] or "NONE")[:8]),
        "  job files %s" % ("committed" if not dirty else "WORKING COPY, not committed (dry run only; a real launch refuses)"),
        "  probe v0.3 acceptance record: %s" % (acceptance["path"] + " @ " + acceptance["commit"][:8] if acceptance
                                                else "NOT GIVEN (a real launch refuses: prereg v0.3 s9 binds before any read)"),
        "  stages    0 instance id (IMDSv2), tools, anchors, smoke, TIMING PREFLIGHT (stops if over the budget)",
        "            1 route: %s" % ", ".join("%s(%s)" % (c["label"], "ON" if c["switch"] else "OFF") for c in spec["route_containers"]),
        "            2 probe v0.3 validation (fresh, seed %d, switch OFF)   [1, 2 and 4+5 side by side]" % SEEDS[0],
        "            3 18 probe reads in 2 waves of 3 processes, only after VALIDATION_PASS; then ITEM2",
        "            4 matched start: self-test, then A5.5 reading     5 roster on the three repaired receipts",
        "  custody   public course, public fixtures, receipts' checkpoints and update files only; no TEST, sealed,",
        "            salt, HSET, scoring or prediction file; no analogy number is printed",
        "  labels    %s" % "; ".join(LABELS),
    ]
    return "\n".join(lines)


# ---- main ----------------------------------------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repaired-commit", default=None, help="one commit holding the three repaired receipts "
                        "(default: the local origin/%s)" % REPAIRED_BRANCH)
    parser.add_argument("--unchanged-commit", default=None, help="one commit holding U17's receipt "
                        "(default: the local origin/%s)" % UNCHANGED_BRANCH)
    parser.add_argument("--acceptance-record", default=None, help="the committed probe v0.3 acceptance record")
    parser.add_argument("--bundle-dir", default=None, help="a NEW folder outside every git tree")
    args = parser.parse_args(argv)
    worst = worst_case_usd()
    if worst > COST_CAP_USD:
        refuse("OVER_CAP", "worst case %.4f > cap %.2f" % (worst, COST_CAP_USD))
    record_path = HERE / "launch_record.json"
    if not args.dry_run and record_path.exists():
        refuse("ALREADY_LAUNCHED", "launch_record.json exists: one approval, one machine")
    commits = {"repaired": full_commit(args.repaired_commit or "refs/remotes/origin/" + REPAIRED_BRANCH),
               "unchanged": full_commit(args.unchanged_commit or "refs/remotes/origin/" + UNCHANGED_BRANCH)}
    for key, given in (("repaired", args.repaired_commit), ("unchanged", args.unchanged_commit)):
        if given and not commits[key]:
            refuse("COMMIT_NOT_FOUND", "--%s-commit %s is not in this repository" % (key, given))
    acceptance = acceptance_gate(args.acceptance_record) if args.acceptance_record else None
    blobs = Blobs()
    try:
        receipt_entries, expect, parts, missing = resolve_receipts(blobs, commits["repaired"], commits["unchanged"])
        if missing and not args.dry_run:
            refuse("STUDY_RECEIPTS_MISSING", "; ".join(missing))            # before building or uploading anything
        if not acceptance and not args.dry_run:
            refuse("ACCEPTANCE_RECORD_REQUIRED", "probe v0.3 binds only with its acceptance record (prereg v0.3 s9)")
        rels, job_commit, dirty = job_files()
        if (dirty or not job_commit) and not args.dry_run:
            refuse("JOB_FILES_NOT_COMMITTED", "commit the job files first:\n%s" % (dirty or rels))
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        folder = pathlib.Path(args.bundle_dir) if args.bundle_dir else pathlib.Path(tempfile.gettempdir()) / ("e1a_job_" + stamp)
        if folder.exists() or not outside_git(folder.parent):
            refuse("BUNDLE_DIR", "%s must be a NEW folder outside every git work tree" % folder)
        entries, raw_pins, lf_pins = fixed_entries()
        entries = sorted(entries + receipt_entries)
        spec = build_spec(parts, missing, commits, acceptance)
        generated = {"claude/" + name: read_job_file(blobs, job_commit, dirty, name) for name in JOB_FILES}
        generated["claude/e1a_spec.json"] = json.dumps(spec, indent=1, sort_keys=True).encode("utf-8")
        if acceptance:
            generated["claude/probe_v0_3_acceptance.json"] = acceptance["bytes"]
        template = read_job_file(blobs, job_commit, dirty, TEMPLATE).decode("utf-8")
        names = [e[0] for e in entries] + sorted(generated) + ["anchors.json"]
        bad = custody_refusals(names)
        if bad:
            refuse("CUSTODY", "%d bundle names break custody: %s" % (len(bad), bad[:8]))
        if len(names) != len(set(names)) or len(names) > MAX_BUNDLE_FILES:
            refuse("BUNDLE_NAMES", "duplicates or more than %d files" % MAX_BUNDLE_FILES)
        print("CUSTODY: PASS (%d names; allowlist plus forbidden words %s; only the six pinned readout programs from "
              "the evaluation-design tree; no file from the archive, S3, a salt or a TEST split)"
              % (len(names), list(FORBIDDEN_NAME_PARTS)), flush=True)
        folder.mkdir(parents=True)
        bundle_path = folder / "bundle.tar.gz"
        anchors, bundle_sha, bundle_bytes, raw_bytes = write_bundle(entries, raw_pins, lf_pins, expect, generated,
                                                                    blobs, bundle_path)
    finally:
        blobs.close()
    if raw_bytes > MAX_BUNDLE_BYTES:
        refuse("BUNDLE_TOO_LARGE", "%d bytes" % raw_bytes)
    print("PINS: PASS (%d source/data/checkpoint pins, %d readout-program LF pins, %d receipt files bound to their "
          "inventories)" % (len(raw_pins), len(lf_pins), len(expect)), flush=True)
    print(plan_text(len(anchors["files"]) + 1, raw_bytes, bundle_bytes, bundle_sha, spec, dirty or not job_commit,
                    acceptance), flush=True)
    keys = {k: "helm-integration/e1a-%s/%s" % (stamp, v)
            for k, v in (("bundle", "bundle.tar.gz"), ("results", "results.tar.gz"), ("progress", "progress.log"))}
    summary = {"schema": "claude.e1a-bundle/0.1", "bundle_sha256": bundle_sha, "bundle_bytes": bundle_bytes,
               "raw_bytes": raw_bytes, "files": len(anchors["files"]) + 1, "commits": commits,
               "source_commit": SOURCE_COMMIT, "readout_commit": READOUT_COMMIT, "smoke_commit": SMOKE_COMMIT,
               "receipts_missing": missing, "launchable": not missing and bool(acceptance) and not (dirty or not job_commit),
               "job_files_commit": job_commit if not dirty else None, "job_files_from_working_copy": bool(dirty or not job_commit),
               "template_sha256_lf": hashlib.sha256(template.encode("utf-8")).hexdigest(),
               "spec_sha256": anchors["files"]["claude/e1a_spec.json"]["sha256"],
               "launcher_sha256_lf": lf_sha(pathlib.Path(__file__).read_bytes()),
               "worst_case_usd_at_client_deadline": round(worst, 4), "cost_cap_usd": COST_CAP_USD,
               "allowance_usd": ALLOWANCE_USD, "instance_type": INSTANCE_TYPE, "ami": PINNED_AMI,
               "acceptance": None if acceptance is None else {k: acceptance[k] for k in ("path", "commit", "sha256")},
               "labels": LABELS}
    if args.dry_run:
        fake = {k: "https://DRY-RUN.invalid/%s" % v for k, v in keys.items()}
        script = render(template, fake, bundle_sha)
        (folder / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        summary.update({"dry_run": True, "aws_calls": [], "machine_script_bytes": len(script.encode("utf-8")),
                        "machine_script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest()})
        (folder / "dry_run_record.json").write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8",
                                                    newline="\n")
        print("DRY RUN: nothing uploaded, nothing launched, no AWS call. Bundle, machine script (%d bytes) and "
              "dry_run_record.json are in %s" % (len(script.encode("utf-8")), folder), flush=True)
        if missing:
            refuse("STUDY_RECEIPTS_MISSING", "; ".join(missing))
        return 0
    return launch(stamp, keys, bundle_path, bundle_sha, template, summary, record_path)


def pushed(commit, branch):
    """The commit is on the pushed branch: ask the remote for its tip (GitHub, read-only), then check ancestry."""
    tip = git("ls-remote", "origin", "refs/heads/" + branch).decode().split()
    try:
        git("merge-base", "--is-ancestor", commit, tip[0])
    except (subprocess.CalledProcessError, IndexError):
        refuse("NOT_PUSHED", "%s is not on the pushed %s (remote tip %s; fetch it)" % (commit[:8], branch, tip[:1]))


def launch(stamp, keys, bundle_path, bundle_sha, template, summary, record_path):
    """The coordinator's launch. Read-only checks first; then one upload and ONE run_instances. No retries."""
    for commit, branch in ((SOURCE_COMMIT, SOURCE_BRANCH), (READOUT_COMMIT, READOUT_BRANCH), (SMOKE_COMMIT, REPAIRED_BRANCH),
                           (summary["commits"]["repaired"], REPAIRED_BRANCH), (summary["commits"]["unchanged"], UNCHANGED_BRANCH)):
        pushed(commit, branch)
    import boto3
    ec2 = boto3.client("ec2", region_name=REGION)
    try:
        image = ec2.describe_images(ImageIds=[PINNED_AMI])["Images"][0]
    except Exception as error:  # noqa: BLE001 -- no substitute image
        refuse("PINNED_IMAGE_UNAVAILABLE", "%s: %s" % (PINNED_AMI, type(error).__name__))
    live = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": GPU_FAMILIES},
                                           {"Name": "instance-state-name", "Values": ["pending", "running", "stopping"]}])
    if live["Reservations"]:
        refuse("GPU_MACHINE_RUNNING", [i["InstanceId"] for r in live["Reservations"] for i in r["Instances"]])
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    if not subnets:
        refuse("NO_SUBNET", "no default-VPC subnet offers %s with a public address" % INSTANCE_TYPE)
    subnet = sorted(subnets, key=lambda s: s["AvailabilityZone"])[0]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        refuse("OPEN_SECURITY_GROUP", "the default security group allows inbound traffic from an address range")
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(bundle_path), BUCKET, keys["bundle"])
    urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=LINK_SECONDS)}
    for k in ("results", "progress"):
        urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=LINK_SECONDS)
    script = render(template, urls, bundle_sha)
    name = "helm-e1a-%s" % stamp
    tags = [{"Key": "Name", "Value": name},
            {"Key": "Purpose", "Value": "Helm E1a checks before results (readout item 9), CLAUDE_BUILT_CLAUDE_CHECKED"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched = ec2.run_instances(
        ImageId=PINNED_AMI, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"],
        SecurityGroupIds=[group["GroupId"]], InstanceInitiatedShutdownBehavior="terminate", UserData=script,
        ClientToken="helm-e1a-%s" % stamp, MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
        BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
    instance = launched["Instances"][0]
    print("LAUNCHED INSTANCE ID: %s  (printed FIRST, before anything else can fail)" % instance["InstanceId"], flush=True)
    record = dict(summary, schema="claude.e1a-launch/0.1", dry_run=False, instance_name=name,
                  approved={"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                            "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": COST_CAP_USD},
                  instance_id=instance["InstanceId"], launched_utc=instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                  availability_zone=subnet["AvailabilityZone"], subnet=subnet["SubnetId"], ami_name=image.get("Name"),
                  security_group=group["GroupId"], in_instance_timer_seconds=MAX_SECONDS,
                  os_power_off_minutes=OS_POWER_OFF_MINUTES, client_deadline_minutes=CLIENT_DEADLINE_MINUTES,
                  bucket=BUCKET, keys=keys, root_volume_gb=ROOT_GB,
                  machine_script_sha256=hashlib.sha256(script.encode("utf-8")).hexdigest(),
                  links_stored="no -- time-limited links are never written to disk")
    record_path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes; watch.py terminates it at %d. Record: %s" % (
        instance["InstanceId"], INSTANCE_TYPE, subnet["AvailabilityZone"], OS_POWER_OFF_MINUTES,
        CLIENT_DEADLINE_MINUTES, record_path.name), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as stop:
        sys.exit(stop.code)
