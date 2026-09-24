"""Historical gates + rescore job on ONE AWS CPU machine (readout plan item 7). CLAUDE_BUILT_CLAUDE_CHECKED. NOT LAUNCHED.

WHAT IT RUNS. The frozen grader `records/typed_pointer_001/evaluate_gates.py` (LF sha256 d3e0ea97...) and the trusted
rescorer 0.4 revision 1 (`records/typed_pointer_001/trusted_rescore.py`, LF sha256 c3d6bdd0..., review 0d6bc2fd APPROVE)
on ONE study. The grader loads the frozen course, which ran the laptop out of memory, so it never runs here.

  --mode 1  Helm 2.0 only (`admission_001/study.json`, source commit 0d6bc2fd). The grader must reproduce the committed
            `admission_001/gate_reading.json` exactly (canonical sha256 52877c16...: NO_TRANSFER_TO_NEW_WORLDS; H1
            G_LEARN_population 11/1, 12/0, 7/1). The rescorer gets its first AWS acceptance: its builder report's R1.7
            steps 3, 4 and 6 on the Helm 2.0 study, and step 5 (its three test files in full, with HELM_RUN_SLOW_TESTS=1;
            they also read Helm 1.0's committed label files and weights, so those are bundled too).
  --mode 2  The repaired (switch-ON) three-seed study. REFUSED unless --item2-pass names a committed ITEM2_PASS record
            (prereg A5.3: "The frozen evaluate_gates.py is run unchanged on the ON receipts only under ITEM2_PASS").
            The check comes FIRST, before any git read of the receipts.

COPIED FROM `records/typed_pointer_001/aws_rescore_job/` (T01: c7i.2xlarge, presigned links only, no credentials on
the machine, terminate on shutdown, three kill switches plus the client watcher, one launch per approval) and from
`../../hset2_aws_job/` (bundle from GIT OBJECTS only, never from working files, with anchors.json). Changes:
  * the machine writes its own instance id (IMDSv2) into env.txt as `instance_id=<id>`, and stops if it cannot;
  * the bundle (about 420 MB before compression: three Helm 2.0 receipts and 30 weight files) is STREAMED to a file
    outside every git tree, one blob at a time; it is never held in memory (the laptop has about 1 GB free);
  * one launch attempt: no zone loop, no retries; one record per mode (`launch_record_mode<N>.json`);
  * custody filters on every bundle name, on top of an allowlist.

    python launch.py --mode 1 --dry-run [--bundle-dir DIR]   # builds the bundle, prints the plan and the cap; NO AWS call
    python launch.py --mode 1                                  # the coordinator only
    python launch.py --mode 2 --item2-pass PATH --receipts-commit SHA [--dry-run]

A dry run never imports boto3 and never touches the network.
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
PACKAGE = HERE.parents[3]                     # readout -> helm_eval_design_20260923 -> records -> the CNCM package
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, PRICE_PER_HOUR = "c7i.2xlarge", 0.357        # AWS on-demand, us-west-2, Linux (as T01, HSET-1A/1B, HSET-2)
ADDRESS_PER_HOUR, ROOT_GB, GB_MONTH_USD = 0.005, 20, 0.08
AMI_PARAMETER = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
MAX_SECONDS, OS_POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES = 80 * 60, 83, 90
COST_CAP_USD, ALLOWANCE_USD = 0.60, 0.10                    # readout plan: cap $0.60 per launch, plus the $0.10 allowance
EXPECTED_MINUTES = {1: (45, 60), 2: (20, 35)}
# Tools: the combination T01 measured on this machine type (env.txt of the 2026-09-21 run): uv 0.12.17, Python 3.14.7,
# pytest 9.1.1. The installer URL is the versioned one; the machine refuses any other uv or Python version.
UV_VERSION, PYTHON_VERSION, PYTEST_VERSION = "0.12.17", "3.14.7", "9.1.1"
LINK_SECONDS = 4 * 3600
MAX_BUNDLE_FILES, MAX_BUNDLE_BYTES = 2000, 700 * 1024 ** 2

R = "records/typed_pointer_001/"
SEEDS = ("20260917", "20260918", "20260919")
RESCORER_COMMIT = "0d6bc2fd8d7188b5474983422fe533a7cb0a874c"   # trusted_rescore 0.4 revision 1, delta review APPROVE
RESCORER_BRANCH = "claude/helm-rescorer-compat-20260924"
MODE1 = {
    "source_commit": RESCORER_COMMIT, "source_branch": RESCORER_BRANCH,
    "study": R + "admission_001/study.json",
    "expected_reading": R + "admission_001/gate_reading.json",
    "expected_reading_sha256": "52877c1670132c70dfd82e5e133e4e6ef90d8595a4b49387a6b0bace9f9d10d6",
    "expected_label": "NO_TRANSFER_TO_NEW_WORLDS",
    "expected_h1": {"20260917": [11, 1], "20260918": [12, 0], "20260919": [7, 1]},
    "label_only_receipts": ["receipt_helm1_certified_" + s for s in SEEDS],    # read by the rescorer's tests
}
MODE2 = {
    "source_branch": "claude/helm-on-launch-20260924",
    "study": R + "admission_analogy_on_001/seeds/study.json",
    "anchor_name": "trust_anchor_analogy_on_seeds_v0_4.json",
    "reading_name": "trusted_rescore_reading_analogy_on_seeds_0_4r1.json",
}
# sha256 of the LF-normalised blob (git stores LF), checked on every bundle build. A mismatch refuses the bundle.
LF_PINS = {
    R + "evaluate_gates.py": "d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d",
    R + "trusted_rescore.py": "c3d6bdd08f9f9f613fb77e1d590b557fd0e28df2d78b26f6ffd5b91661d5cdb1",
    "records/typed_course_001/checks_002/public_course.json": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
    "records/typed_interface_001/checks_002/training_tokenizer.json": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c",
    "records/typed_matched_001/development_001/compact_development.json": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4",
}
MODE1_LF_PINS = {
    R + "test_trusted_rescore.py": "edefa58bead6a47cb47510dd3014d113f3af67c2cb9c910f4c3302633a52ec56",
    R + "test_historical_compatibility.py": "d5eb5c22ea1fbd06630b4ecb7bceb49555574ae365475d37f4fe9605be6e5a1d",
    R + "test_historical_rescore_rule.py": "58d95cf01d3eb01da18db7fefa6d087cc3ce82a2e9c621110cd8da8464d6458e",
    R + "admission_001/study.json": "b8cbf375153bd924ff6e3ac049263c8c2a6d53650217be16dea09e9c4d6cc32b",
    R + "admission_001/gate_reading.json": "52877c1670132c70dfd82e5e133e4e6ef90d8595a4b49387a6b0bace9f9d10d6",
}
MODE2_LF_PINS = {R + "admission_analogy_on_001/seeds/study.json": "c0d65ce8d1e040c3631ef5148fff4a3934a79ff74ba4f48d8a634380b78e904d"}

# ---- the allowlist (package-relative paths) -----------------------------------------------------------------------
CODE_PREFIXES = ("cncm/", "research/CAS_META_2_COMPOSITION/cas_meta2/")        # .py only
DATA_FILES = frozenset(
    ["records/typed_course_001/checks_002/public_course.json",
     "records/typed_interface_001/checks_002/training_tokenizer.json",
     "records/typed_matched_001/development_001/compact_development.json",
     "research/CAS_META_2_COMPOSITION/records/learning_panel_001/supply.json",
     "research/CAS_META_2_COMPOSITION/records/complementary_teaching_001/preparation_20260916/historical_exclusions.json",
     "records/typed_practice_001/evaluate_gates.py"]
    + ["records/typed_practice_001/receipt_%s/checkpoints/initial_checkpoint.json" % s for s in SEEDS]       # I3 start
    + ["records/typed_matched_001/receipt_%s_m/collected/results/artifacts/initial_checkpoint.json" % s for s in SEEDS])
POINTER_EXTRA = frozenset(["history/trusted_rescore_0_3.py", "admission_001/study.json", "admission_001/gate_reading.json",
                           "admission_helm1_certified/gate_reading.json"])
ARTIFACTS = "collected/results/artifacts/"
LABEL_FILES = frozenset(ARTIFACTS + "course_%s_%s.json" % (p, k) for p in ("p00", "p10") for k in ("predictions", "scoring"))
# ---- custody: a second line after the allowlist. Every bundle name is checked, case-insensitively. -----------------
FORBIDDEN_NAME_PARTS = ("sealed", "_eval.jsonl", "salt", "private_target", "protected", "transcript", "hset",
                        "tkscas-archive", "helm_eval_design_20260923/hset")
FORBIDDEN_TREE_PREFIXES = ("records/helm_eval_design_20260923/", "records/typed_course_001/checks_002/private")
# ---- mode 2: the ITEM2 record = the output of the ITEM2 reader for probe v0.3 (readout/probe-v03/item2_reader.py,
# schema claude.item2-reading/0.3, as drafted on 2026-09-24; see JOB_LIMITS.md). Probe v0.2 cannot close the gate (A2.6).
ITEM2_SCHEMA = "claude.item2-reading/0.3"
A5_CHECKPOINTS = ("pass_01.pt", "evidence/main_checkpoint_0294.pt", "evidence/main_checkpoint_0588.pt",
                  "evidence/main_checkpoint_0882.pt", "evidence/main_checkpoint_1176.pt", "final.pt")
JOB_FILES = ["machine_gates.py"]
TEMPLATE = "job.sh.template"


class Refused(SystemExit):
    pass


def refuse(code, detail):
    print("LAUNCH_REFUSED: %s: %s" % (code, detail), flush=True)
    raise Refused(2)


# ---- git ---------------------------------------------------------------------------------------------------------
def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True).stdout


def prefix():
    return git("rev-parse", "--show-prefix").decode().strip()


def full_commit(ref):
    try:
        return git("rev-parse", "--verify", "--quiet", ref + "^{commit}").decode().strip()
    except subprocess.CalledProcessError:
        return None


def listing(commit):
    """{package-relative path: size} of every blob at `commit` under this package."""
    pre, out = prefix(), {}
    for entry in git("ls-tree", "-r", "-z", "-l", "--full-tree", commit, "--", pre).split(b"\0"):
        if not entry:
            continue
        meta, _, path = entry.decode("utf-8").partition("\t")
        kind, size = meta.split()[1], meta.split()[3]
        if kind == "blob" and path.startswith(pre):
            out[path[len(pre):]] = int(size)
    return out


class Blobs:
    """Exact stored bytes, one blob at a time, through ONE `git cat-file --batch` (no line-ending conversion)."""

    def __init__(self):
        self.pre = prefix()
        self.proc = subprocess.Popen(["git", "-C", str(PACKAGE), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)

    def read(self, commit, rel):
        self.proc.stdin.write(("%s:%s%s\n" % (commit, self.pre, rel)).encode("utf-8"))
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().decode("utf-8").rstrip("\n")
        if header.endswith(" missing") or len(header.split()) != 3:
            refuse("BUNDLE_FILE_MISSING", "%s at %s" % (rel, commit[:8]))
        size = int(header.split()[2])
        data = self.proc.stdout.read(size)
        self.proc.stdout.read(1)
        return data

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def lf_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


# ---- selection and custody ---------------------------------------------------------------------------------------
def receipt_names(study_bytes):
    """{seed: receipt folder name} from a study (the last component of each receipt_dir, Windows or POSIX)."""
    study = json.loads(study_bytes)
    of_seed = {str(job["model_seed"]): re.split(r"[\\/]", str(job["receipt_dir"]).rstrip("\\/"))[-1] for job in study["jobs"]}
    names = list(of_seed.values())
    if (sorted(of_seed) != list(SEEDS) or len(study["jobs"]) != 3 or len(set(names)) != 3
            or not all(re.fullmatch(r"receipt_[A-Za-z0-9_]+", n) for n in names)):
        refuse("STUDY_SHAPE", "the study must name the three seeds %s with three plain receipt folders; got %s" % (
            list(SEEDS), of_seed))
    return dict(sorted(of_seed.items()))


def select(paths, full_receipts, label_only_receipts, extra=()):
    """The allowlist. `paths` are package-relative; returns the sorted selection."""
    extra, full, lab = frozenset(extra), frozenset(full_receipts), frozenset(label_only_receipts)
    keep = []
    for p in paths:
        if (p.endswith(".py") and p.startswith(CODE_PREFIXES)) or p in DATA_FILES:
            keep.append(p)
            continue
        if not p.startswith(R):
            continue
        t = p[len(R):]
        head, _, rest = t.partition("/")
        if (("/" not in t and t.endswith((".py", ".json"))) or t in POINTER_EXTRA or t in extra
                or (t.startswith("aws_rescore_job/results/") and t.endswith(".json") and t.count("/") == 2)
                or (head in full and (rest in ("result.json", "artifact_manifest.json") or rest.startswith(ARTIFACTS)))
                or (head in lab and (rest == "artifact_manifest.json" or rest in LABEL_FILES
                                     or (rest.startswith(ARTIFACTS) and rest.endswith(".pt") and rest.count("/") == 3)))):
            keep.append(p)
    return sorted(keep)


def custody_refusals(bundle_names):
    """Every bundle name that breaks custody: a forbidden word anywhere, or a forbidden place in the tree."""
    bad = []
    for name in bundle_names:
        low = name.lower()
        rel = name[len("tree/"):] if name.startswith("tree/") else None
        if (any(part in low for part in FORBIDDEN_NAME_PARTS) or (rel is not None and rel.startswith(FORBIDDEN_TREE_PREFIXES))
                or "__pycache__" in name or name.endswith(".pyc") or ".." in name.split("/") or name.startswith("/")):
            bad.append(name)
    return bad


# ---- mode 2: the ITEM2_PASS record -------------------------------------------------------------------------------
def validate_item2_record(data):
    """(record, []) when the bytes are an ITEM2 reading that permits the frozen grader on the ON receipts; else
    (None, [reasons]). Needed: schema claude.item2-reading/0.3 (probe v0.3; v0.2 cannot close the gate, A2.6); outcome
    ITEM2_PASS; the reader's own field historical_gate_on_repaired_arm = MAY_RUN_FROZEN_EVALUATE_GATES; and all 18 A5.1
    checkpoints, each once, with verdict PRESENT_GRAPH_AND_DOMAIN, no problems, and a checkpoint sha256."""
    try:
        record = json.loads(data)
    except (ValueError, UnicodeDecodeError) as error:
        return None, ["ITEM2_RECORD_NOT_JSON:%s" % type(error).__name__]
    if not isinstance(record, dict):
        return None, ["ITEM2_RECORD_NOT_AN_OBJECT"]
    reasons = []
    if record.get("schema") != ITEM2_SCHEMA:
        reasons.append("ITEM2_SCHEMA_NOT_PROBE_V0_3:%r" % (record.get("schema"),))
    if record.get("outcome") != "ITEM2_PASS":
        reasons.append("ITEM2_OUTCOME_NOT_PASS:%r" % (str(record.get("outcome"))[:120],))
    if record.get("historical_gate_on_repaired_arm") != "MAY_RUN_FROZEN_EVALUATE_GATES":
        reasons.append("ITEM2_READER_SAYS_G_LEARN_ON_NOT_READ:%r" % (record.get("historical_gate_on_repaired_arm"),))
    entries = record.get("entries")
    if not isinstance(entries, list):
        return None, reasons + ["ITEM2_ENTRIES_MISSING"]
    seen = set()
    for row in entries:
        if not isinstance(row, dict):
            reasons.append("ITEM2_ENTRY_NOT_AN_OBJECT")
            continue
        key = (str(row.get("model_seed")), row.get("checkpoint_relative_path"))
        if key[0] not in SEEDS or key[1] not in A5_CHECKPOINTS:
            reasons.append("ITEM2_UNLISTED_CHECKPOINT:%s/%s" % key)
        elif key in seen:
            reasons.append("ITEM2_DUPLICATE_CHECKPOINT:%s/%s" % key)
        seen.add(key)
        if row.get("verdict") != "PRESENT_GRAPH_AND_DOMAIN" or row.get("problems") != []:
            reasons.append("ITEM2_CHECKPOINT_NOT_PRESENT_GRAPH_AND_DOMAIN:%s/%s:%r" % (key[0], key[1], row.get("verdict")))
        if not (isinstance(row.get("checkpoint_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", row["checkpoint_sha256"])):
            reasons.append("ITEM2_CHECKPOINT_SHA256_MISSING:%s/%s" % key)
    missing = [(s, c) for s in SEEDS for c in A5_CHECKPOINTS if (s, c) not in seen]
    if missing:
        reasons.append("ITEM2_CHECKPOINTS_MISSING:%d of 18: %s" % (len(missing), ["%s/%s" % m for m in missing[:4]]))
    return (record, []) if not reasons else (None, reasons)


def item2_gate(path):
    """Mode 2's FIRST check. The record must be a committed, unmodified file in this repository and pass contract v0.1."""
    if not path:
        refuse("ITEM2_PASS_REQUIRED", "mode 2 reads the repaired receipts with the frozen grader; prereg A5.3 allows that "
               "only under ITEM2_PASS. Give --item2-pass <committed ITEM2 record>. Otherwise the reading is G_LEARN_ON_NOT_READ")
    target = pathlib.Path(path).resolve()
    top = pathlib.Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    try:
        rel = target.relative_to(top).as_posix()
    except ValueError:
        refuse("ITEM2_RECORD_NOT_COMMITTED", "%s is outside this repository" % target)
    spec = str(target)                                          # an absolute pathspec: git -C runs in the package folder
    if not git("ls-files", "--", spec).strip() or git("status", "--porcelain", "--", spec).strip():
        refuse("ITEM2_RECORD_NOT_COMMITTED", "%s is not tracked, or differs from its committed version" % rel)
    commit = git("log", "-1", "--format=%H", "--", spec).decode().strip()
    data = git("show", "HEAD:" + rel)
    record, reasons = validate_item2_record(data)
    if reasons:
        refuse("ITEM2_RECORD_INVALID", "; ".join(reasons))
    return {"path": rel, "commit": commit, "sha256": hashlib.sha256(data).hexdigest(), "bytes": data, "record": record}


# ---- the bundle --------------------------------------------------------------------------------------------------
def job_files():
    """The job's own files: (rels, their LAST COMMIT or None, the uncommitted changes). The last commit that touched them
    is used, not HEAD, so the bundle stays the same while other agents commit to this branch."""
    rels = [(HERE / name).relative_to(PACKAGE).as_posix() for name in JOB_FILES + [TEMPLATE]]
    commit = git("log", "-1", "--format=%H", "--", *rels).decode().strip() or None
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *rels).decode().strip()
    return rels, commit, dirty


def read_job_file(blobs, commit, dirty, name):
    """Committed bytes when the job files are clean; the working copy otherwise (a dry run only; a launch refuses)."""
    if commit and not dirty:
        return blobs.read(commit, (HERE / name).relative_to(PACKAGE).as_posix())
    return (HERE / name).read_bytes().replace(b"\r\n", b"\n")


def plan_sources(mode, receipts_commit=None):
    """[(bundle name, commit, package-relative path)], the pins to check, and a description of the sources."""
    blobs = Blobs()
    try:
        if mode == 1:
            src = full_commit(MODE1["source_commit"])
            if src != MODE1["source_commit"]:
                refuse("SOURCE_COMMIT_MISSING", MODE1["source_commit"])
            study = blobs.read(src, MODE1["study"])
            of_seed = receipt_names(study)
            chosen = select(listing(src), of_seed.values(), MODE1["label_only_receipts"])
            entries = [("tree/" + p, src, p) for p in chosen]
            pins = dict(LF_PINS, **MODE1_LF_PINS)
            sources = {"tree": src, "tree_branch": MODE1["source_branch"], "receipt_of_seed": of_seed,
                       "label_only_receipts": MODE1["label_only_receipts"]}
        else:
            src = full_commit(receipts_commit or "")
            if not src:
                refuse("RECEIPTS_COMMIT_REQUIRED", "mode 2 needs --receipts-commit: ONE commit that holds the study and all "
                       "three repaired receipts (a merge commit if they were committed on separate branches)")
            names = listing(src)
            if MODE2["study"] not in names:
                refuse("STUDY_MISSING", "%s at %s" % (MODE2["study"], src[:8]))
            study = blobs.read(src, MODE2["study"])
            of_seed = receipt_names(study)
            beside = MODE2["study"].rsplit("/", 1)[0] + "/gate_reading.json"
            if beside in names:
                refuse("READING_ALREADY_EXISTS", "%s is already committed: the repaired arm is read once (A5.3)" % beside)
            for rec in of_seed.values():
                if R + rec + "/artifact_manifest.json" not in names or R + rec + "/result.json" not in names:
                    refuse("RECEIPT_INCOMPLETE", "%s has no artifact_manifest.json or result.json at %s" % (rec, src[:8]))
            chosen = [p for p in select(names, of_seed.values(), [], extra=[MODE2["study"][len(R):]])
                      if p != R + "trusted_rescore.py"]
            rescorer = full_commit(RESCORER_COMMIT)
            if rescorer != RESCORER_COMMIT:
                refuse("RESCORER_COMMIT_MISSING", RESCORER_COMMIT)
            entries = [("tree/" + p, src, p) for p in chosen] + [("tree/" + R + "trusted_rescore.py", rescorer, R + "trusted_rescore.py")]
            pins = dict(LF_PINS, **MODE2_LF_PINS)
            sources = {"tree": src, "tree_branch_expected": MODE2["source_branch"], "receipt_of_seed": of_seed,
                       "trusted_rescore_py_from": rescorer}
        return sorted(entries), pins, sources, blobs
    except BaseException:
        blobs.close()
        raise


def write_bundle(entries, pins, generated, blobs, dest):
    """Stream a deterministic tar.gz to `dest`. Returns (anchors, bundle sha256, bundle bytes, raw bytes)."""
    files, raw_total, seen_pins = {}, 0, set()
    with open(dest, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=6, mtime=0) as zipped, \
            tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))

        for name, commit, rel in entries:
            data = blobs.read(commit, rel)
            if rel in pins:
                if lf_sha(data) != pins[rel]:
                    refuse("PIN_MISMATCH", "%s (LF sha256 %s, pinned %s)" % (rel, lf_sha(data)[:12], pins[rel][:12]))
                seen_pins.add(rel)
            files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "from_commit": commit}
            raw_total += len(data)
            add(name, data)
        missing_pins = sorted(set(pins) - seen_pins)
        if missing_pins:
            refuse("PINNED_FILE_NOT_BUNDLED", missing_pins)
        for name in sorted(generated):
            data = generated[name]
            files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "from_commit": "generated"}
            raw_total += len(data)
            add(name, data)
        anchors = {"schema": "claude.gates-job-anchors/0.1", "files": files}
        add("anchors.json", json.dumps(anchors, indent=1, sort_keys=True).encode("utf-8"))
    digest = hashlib.sha256()
    with open(dest, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return anchors, digest.hexdigest(), pathlib.Path(dest).stat().st_size, raw_total


def outside_git(folder):
    folder = pathlib.Path(folder).resolve()
    return not any((q / ".git").exists() for q in [folder] + list(folder.parents))


# ---- money and the machine script ---------------------------------------------------------------------------------
def worst_case_usd(minutes=CLIENT_DEADLINE_MINUTES):
    """Machine + auto-assigned public address + gp3 disk, for `minutes` (default: the whole client deadline)."""
    return (PRICE_PER_HOUR + ADDRESS_PER_HOUR + ROOT_GB * GB_MONTH_USD / 730) * minutes / 60.0


def render(template, mode, urls, bundle_sha, source_commit):
    values = {"__MODE__": str(mode), "__MAX_SECONDS__": str(MAX_SECONDS), "__MAX_MINUTES__": str(OS_POWER_OFF_MINUTES),
              "__BUNDLE_URL__": urls["bundle"], "__RESULTS_URL__": urls["results"], "__PROGRESS_URL__": urls["progress"],
              "__BUNDLE_SHA256__": bundle_sha, "__SOURCE_COMMIT__": source_commit, "__UV_VERSION__": UV_VERSION,
              "__PYTHON_VERSION__": PYTHON_VERSION, "__PYTEST_VERSION__": PYTEST_VERSION,
              "__STUDY__": MODE1["study"] if mode == 1 else MODE2["study"],
              "__ANCHOR2__": MODE2["anchor_name"], "__READING2__": MODE2["reading_name"]}
    script = template
    for key, value in values.items():
        script = script.replace(key, value)
    if re.search(r"__[A-Z0-9_]+__", script):
        raise AssertionError("an unfilled placeholder remains in the machine script")
    if len(script.encode("utf-8")) >= 16000:
        raise AssertionError("the machine script is over the 16,000-byte user-data limit")
    return script


def plan_text(mode, n_files, raw_bytes, bundle_bytes, bundle_sha, sources, dirty):
    lo, hi = EXPECTED_MINUTES[mode]
    lines = [
        "PLAN (mode %d, %s)" % (mode, "Helm 2.0 study only" if mode == 1 else "repaired switch-ON study, under ITEM2_PASS"),
        "  machine   ONE %s, %s, on-demand $%.3f/h, CPU only, %d GB gp3 deleted with the machine; no credentials on it"
        % (INSTANCE_TYPE, REGION, PRICE_PER_HOUR, ROOT_GB),
        "  limits    in-machine timer %d min, OS power-off at %d min, client deadline %d min (watch.py terminates)"
        % (MAX_SECONDS // 60, OS_POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES),
        "  COST CAP  worst case at the client deadline $%.4f <= cap $%.2f (plus the $%.2f allowance = $%.2f in the ledger)"
        % (worst_case_usd(), COST_CAP_USD, ALLOWANCE_USD, COST_CAP_USD + ALLOWANCE_USD),
        "  expected  about %d-%d min, about $%.2f-$%.2f" % (lo, hi, worst_case_usd(lo), worst_case_usd(hi)),
        "  retries   none: one launch attempt, one zone, no relaunch; launch_record_mode%d.json refuses a second" % mode,
        "  bundle    %d files, %.1f MB raw, %.1f MB compressed, sha256 %s" % (n_files, raw_bytes / 1e6, bundle_bytes / 1e6, bundle_sha),
        "  sources   %s" % json.dumps(sources, sort_keys=True),
        "  job files %s" % ("committed" if not dirty else "WORKING COPY, not committed (dry run only; a real launch refuses)"),
        "  stages",
        "    0  IMDSv2 instance id -> env.txt (stops if unreadable); uv %s, Python %s, pytest %s; bundle sha256 check;"
        % (UV_VERSION, PYTHON_VERSION, PYTEST_VERSION),
        "       every bundled file against anchors.json",
    ]
    if mode == 1:
        lines += [
            "    1  gates: evaluate_gates.py on a Linux-path copy of admission_001/study.json (only receipt_dir changed);",
            "       the reading, re-serialised canonically, must have sha256 %s..., label %s, H1 11/1 12/0 7/1"
            % (MODE1["expected_reading_sha256"][:16], MODE1["expected_label"]),
            "    2  rescorer R1.7 step 3: --historical-compatibility --check-reading (Helm 2.0 reading) -> expect exit 4",
            "       rescorer R1.7 step 4: --historical-compatibility full reading of the Helm 2.0 study -> expect exit 4",
            "    3  rescorer R1.7 step 6: --write-anchor trust_anchor_helm2_experimental_v0_4.json -> expect 0; trusted rescore",
            "       with --frozen-reading admission_001/gate_reading.json -> expect exit 0 and RESCORE_OK",
            "    4  rescorer R1.7 step 5: the three test files, HELM_RUN_SLOW_TESTS=1, one process each -> expect exit 0",
            "       (stages 1-4 run in parallel, each in its own copy of the bundle)",
            "    5  machine_gates.py decide -> GATES_JOB_RESULT.json; STATUS done only if every expectation holds",
        ]
    else:
        lines += [
            "    1  gates: evaluate_gates.py on a Linux-path copy of the repaired study; the frozen label is a historical-rule",
            "       reading of the ON arm, diagnostic only (A5.3); printed beside it, report only: per-seed b, c, p, kinds, worlds",
            "    2  rescorer trusted mode: --write-anchor %s; rescore against the fresh gate reading -> expect RESCORE_OK"
            % MODE2["anchor_name"],
            "    3  machine_gates.py decide -> GATES_JOB_RESULT.json. Nothing here is placed beside Helm 2.0 (A5.5).",
        ]
    lines.append("  labels    CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT")
    return "\n".join(lines)


# ---- main ----------------------------------------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", type=int, choices=(1, 2), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--item2-pass", default=None, help="mode 2 only: the committed ITEM2_PASS record")
    parser.add_argument("--receipts-commit", default=None, help="mode 2 only: one commit holding the study and the three receipts")
    parser.add_argument("--bundle-dir", default=None, help="a NEW folder outside every git tree (default: a new temp folder)")
    args = parser.parse_args(argv)
    item2 = None
    if args.mode == 2:
        item2 = item2_gate(args.item2_pass)                     # FIRST: nothing else is read before this passes
    elif args.item2_pass or args.receipts_commit:
        refuse("USAGE", "--item2-pass and --receipts-commit belong to mode 2")
    worst = worst_case_usd()
    if worst > COST_CAP_USD:
        refuse("OVER_CAP", "worst case %.4f > cap %.2f" % (worst, COST_CAP_USD))
    record_path = HERE / ("launch_record_mode%d.json" % args.mode)
    if not args.dry_run and record_path.exists():
        refuse("ALREADY_LAUNCHED", "%s exists: one approval, one machine" % record_path.name)

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = pathlib.Path(args.bundle_dir) if args.bundle_dir else pathlib.Path(tempfile.gettempdir()) / (
        "gates_job_mode%d_%s" % (args.mode, stamp))
    if folder.exists() or not outside_git(folder.parent):
        refuse("BUNDLE_DIR", "%s must be a NEW folder outside every git work tree" % folder)
    folder.mkdir(parents=True)

    rels, job_commit, dirty = job_files()
    if (dirty or not job_commit) and not args.dry_run:
        refuse("JOB_FILES_NOT_COMMITTED", "commit the job files first:\n%s" % (dirty or rels))
    entries, pins, sources, blobs = plan_sources(args.mode, args.receipts_commit)
    try:
        generated = {"claude/" + name: read_job_file(blobs, job_commit, dirty, name) for name in JOB_FILES}
        template = read_job_file(blobs, job_commit, dirty, TEMPLATE).decode("utf-8")
        if item2 is not None:
            generated["claude/item2_pass_record.json"] = item2["bytes"]
            bind_item2(item2["record"], sources, blobs)
        names = [e[0] for e in entries] + sorted(generated) + ["anchors.json"]
        bad = custody_refusals(names)
        if bad:
            refuse("CUSTODY", "%d bundle names break custody: %s" % (len(bad), bad[:8]))
        if len(names) > MAX_BUNDLE_FILES:
            refuse("BUNDLE_TOO_MANY_FILES", len(names))
        print("CUSTODY: PASS (%d names; allowlist plus forbidden words %s; no file from the archive, S3 or a salt)"
              % (len(names), list(FORBIDDEN_NAME_PARTS)), flush=True)
        bundle_path = folder / "bundle.tar.gz"
        anchors, bundle_sha, bundle_bytes, raw_bytes = write_bundle(entries, pins, generated, blobs, bundle_path)
    finally:
        blobs.close()
    if raw_bytes > MAX_BUNDLE_BYTES:
        refuse("BUNDLE_TOO_LARGE", "%d bytes" % raw_bytes)
    source_commit = sources["tree"]
    print(plan_text(args.mode, len(anchors["files"]) + 1, raw_bytes, bundle_bytes, bundle_sha, sources,
                    dirty or not job_commit), flush=True)
    keys = {k: "helm-integration/gates-job-mode%d-%s/%s" % (args.mode, stamp, v)
            for k, v in (("bundle", "bundle.tar.gz"), ("results", "results.tar.gz"), ("progress", "progress.log"))}
    summary = {"schema": "claude.gates-job-bundle/0.1", "mode": args.mode, "bundle_sha256": bundle_sha,
               "bundle_bytes": bundle_bytes, "raw_bytes": raw_bytes, "files": len(anchors["files"]) + 1,
               "sources": sources, "job_files_commit": job_commit if not dirty else None,
               "job_files_from_working_copy": bool(dirty or not job_commit), "job_files": rels,
               "template_sha256_lf": hashlib.sha256(template.encode("utf-8")).hexdigest(),
               "launcher_sha256_lf": lf_sha(pathlib.Path(__file__).read_bytes()),
               "worst_case_usd_at_client_deadline": round(worst, 4), "cost_cap_usd": COST_CAP_USD, "allowance_usd": ALLOWANCE_USD,
               "item2": None if item2 is None else {k: item2[k] for k in ("path", "commit", "sha256")}}

    if args.dry_run:
        fake = {k: "https://DRY-RUN.invalid/%s" % v for k, v in keys.items()}
        script = render(template, args.mode, fake, bundle_sha, source_commit)
        (folder / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        summary.update({"dry_run": True, "machine_script_bytes": len(script.encode("utf-8")),
                        "machine_script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest()})
        (folder / "dry_run_record.json").write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded, nothing launched, no AWS call. Bundle, machine script (%d bytes) and "
              "dry_run_record.json are in %s" % (len(script.encode("utf-8")), folder), flush=True)
        return 0
    return launch(args.mode, stamp, keys, bundle_path, bundle_sha, template, source_commit, summary, record_path)


def bind_item2(record, sources, blobs):
    """Mode 2: every checkpoint the ITEM2 record names must be the checkpoint in the receipts being read."""
    receipt_of = sources["receipt_of_seed"]
    for row in record["entries"]:
        seed, ckpt, want = str(row["model_seed"]), row["checkpoint_relative_path"], row["checkpoint_sha256"]
        rel = R + receipt_of[seed] + "/collected/results/" + (ckpt if ckpt.startswith("evidence/") else "artifacts/" + ckpt)
        got = hashlib.sha256(blobs.read(sources["tree"], rel)).hexdigest()
        if got != want:
            refuse("ITEM2_CHECKPOINT_NOT_THIS_RECEIPT", "%s: record %s..., receipt %s..." % (rel, want[:12], got[:12]))
    print("ITEM2: PASS record bound to the 18 checkpoints of %s" % sorted(receipt_of.values()), flush=True)


def launch(mode, stamp, keys, bundle_path, bundle_sha, template, source_commit, summary, record_path):
    """The coordinator's launch. One attempt, one zone, no retries."""
    import boto3
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(bundle_path), BUCKET, keys["bundle"])
    urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=LINK_SECONDS)}
    for k in ("results", "progress"):
        urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=LINK_SECONDS)
    script = render(template, mode, urls, bundle_sha, source_commit)
    ec2 = boto3.client("ec2", region_name=REGION)
    ami = boto3.client("ssm", region_name=REGION).get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
    image = ec2.describe_images(ImageIds=[ami])["Images"][0]
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
    running = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["gates-job-*"]},
                                              {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if running:
        refuse("ALREADY_RUNNING", [i["InstanceId"] for r in running for i in r["Instances"]])
    tags = [{"Key": "Name", "Value": "gates-job-mode%d-%s" % (mode, stamp)},
            {"Key": "Purpose", "Value": "Helm historical gates + rescore 0.4 (readout item 7), CLAUDE_BUILT_CLAUDE_CHECKED"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched = ec2.run_instances(
        ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"],
        SecurityGroupIds=[group["GroupId"]], InstanceInitiatedShutdownBehavior="terminate", UserData=script,
        ClientToken="gates-job-%d-%s" % (mode, stamp), MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
        BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
    instance = launched["Instances"][0]
    print("LAUNCHED INSTANCE ID: %s  (printed FIRST, before anything else can fail)" % instance["InstanceId"], flush=True)
    record = dict(summary, schema="claude.gates-job-launch/0.1", label="CLAUDE_BUILT_CLAUDE_CHECKED", dry_run=False,
                  approved={"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                            "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": COST_CAP_USD},
                  instance_id=instance["InstanceId"], launched_utc=instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                  availability_zone=subnet["AvailabilityZone"], subnet=subnet["SubnetId"], ami=ami, ami_name=image.get("Name"),
                  security_group=group["GroupId"], in_instance_timer_seconds=MAX_SECONDS, os_power_off_minutes=OS_POWER_OFF_MINUTES,
                  client_deadline_minutes=CLIENT_DEADLINE_MINUTES, bucket=BUCKET, keys=keys, root_volume_gb=ROOT_GB,
                  machine_script_sha256=hashlib.sha256(script.encode("utf-8")).hexdigest(),
                  links_stored="no -- time-limited links are never written to disk")
    record_path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes. Record: %s" % (
        instance["InstanceId"], INSTANCE_TYPE, subnet["AvailabilityZone"], OS_POWER_OFF_MINUTES, record_path.name), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as stop:
        sys.exit(stop.code)
