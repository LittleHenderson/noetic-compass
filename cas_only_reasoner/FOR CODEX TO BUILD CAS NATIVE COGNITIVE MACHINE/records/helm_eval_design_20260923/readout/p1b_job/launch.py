"""P1b: the unchanged-arm reproduction reader on ONE AWS g7.2xlarge (readout plan item 8). CLAUDE_BUILT_CLAUDE_CHECKED.
BUILT, NOT LAUNCHED. The coordinator is the only runner.

TWO MODES, one machine each, one launch each (no retries):
  acceptance  stage 0: the reader's own tests (`test_unchanged_repro.py`, pure Python, GPU switch unset); stage 1: the
              timing preflight; stage 2: `recompute_reproduction_evidence.py --mode acceptance`, the 11 registered
              cases, each compared with the frozen expected table (`repro_common.ACCEPTANCE_EXPECTED`, reader fix 7);
              then `p1b_machine.py decide` re-derives every case from its observed fields. Public inputs only.
  reading     ONCE, after READING_ELIGIBILITY.json is committed (Codex bus codex-0021; Claude default Q-F): the
              preflight, then `--mode reading` on the Helm 2.0 seed-17 final.pt and U17's final.pt. It writes the
              evidence only; the verdict is read later, on the laptop, by `read_reproduction.py`. The reading is
              refused unless the eligibility record is committed at --receipt-commit, is the only commit of it, came
              after the freeze 3344ae5d, binds exactly the reader this bundle ships and a READER_ACCEPTANCE_PASS receipt
              of that same reader, and no evidence is committed yet. That gate runs FIRST, before anything is built.

THE MACHINE: g7.2xlarge (NVIDIA RTX PRO 4500), the historical AMI ami-0fbbd0facbc9e3cff, the pinned package
source.zip c42370c4... unpacked at /opt/cas-graph6curr/package (the root both checkpoints record), and the historical
worker's own install: `python3.12|3.11|3 -m venv`, `pip install torch==2.11.0` from the cu128 index, the two wheels
with --no-deps, then requirements-gpu.txt 9d0be781... (numpy 2.2.6). IMDSv2 instance-id line. 60-minute session:
in-machine timer 57 min, OS power-off 59 min, client deadline 62 min (watch.py terminates). The preflight refuses a
projected end past 55 minutes. Cap $2.64 per session (worst case at the client deadline) plus the $0.10 allowance.

THE BUNDLE is built from GIT OBJECTS only, never from working files:
  tree/   the reader folder records/typed_pointer_001/admission_unchanged_repro_001/ and the package archive, at the
          reader commit (acceptance) or the receipt commit (reading); acceptance adds the five files the tests read
          (four historical aws launchers, pointer_contract.py) and the package receipt.json;
  ref/    Helm 2.0 seed-17 final.pt (c6c49e98...) and final_checkpoint.json, from c8d5c430;
  cand/   (reading) U17's final.pt from the receipt commit, bound to its three records and the frozen job;
  claude/ p1b_machine.py (and, reading, a copy of the eligibility record); anchors.json.

    python -B launch.py --mode acceptance --dry-run [--reader-commit SHA] [--bundle-dir NEW_DIR]
    python -B launch.py --mode reading --dry-run --rehearsal [--reader-commit SHA]    # stand-in candidate; never launches
    python -B launch.py --mode reading --receipt-commit SHA --receipt-branch BRANCH [--dry-run]
    python -B launch.py --mode acceptance [--reader-commit SHA]                        # the coordinator only

A dry run makes NO network call and NO AWS call; it never imports boto3.
"""
import argparse
import ast
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
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[3]                     # p1b_job -> readout -> helm_eval_design_20260923 -> records -> the CNCM root
REPO_PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"

# ---- machine, money, time ---------------------------------------------------------------------------------------------
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, AMI = "g7.2xlarge", "ami-0fbbd0facbc9e3cff"        # AMI: Helm 2.0 seed-17 preflight.json at c8d5c430
PRICE_PER_HOUR = 2.52             # the g7.2xlarge on-demand quote that preflight recorded; launch() re-reads it and refuses above
ADDRESS_PER_HOUR, ROOT_GB, GB_MONTH_USD, HOURS_PER_MONTH = 0.005, 75, 0.08, 730   # 75 GiB gp3: the historical ebs size
SESSION_MINUTES = 60
MAX_SECONDS, POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES = 57 * 60, 59, 62
COST_CAP_USD, ALLOWANCE_USD = 2.64, 0.10
EXPECTED_MINUTES = {"acceptance": (35, 50), "reading": (20, 32)}
LINK_SECONDS = 3 * 3600
USER_DATA_LIMIT, LINK_BYTES_ASSUMED = 16000, 2048
TORCH_VERSION, TORCH_INDEX = "2.11.0", "https://download.pytorch.org/whl/cu128"
GPU_FAMILIES = ["g4dn.*", "g4ad.*", "g5.*", "g5g.*", "g6.*", "g6e.*", "gr6.*", "g7.*", "g7e.*", "p3.*", "p3dn.*", "p4d.*",
                "p4de.*", "p5.*", "p5e.*", "p5en.*"]
PRICING_FILTERS = (("instanceType", INSTANCE_TYPE), ("location", "US West (Oregon)"), ("operatingSystem", "Linux"),
                   ("tenancy", "Shared"), ("preInstalledSw", "NA"), ("capacitystatus", "Used"),
                   ("marketoption", "OnDemand"), ("operation", "RunInstances"))   # as the Helm 2.0 preflight asked
BASHISMS = (">(", "<(", "[[", "]]", "$((", "function ")

# ---- pins (repro_common.py revision 4; the reader-rev branch) --------------------------------------------------------
FREEZE_COMMIT = "3344ae5d7bcc0d5ff50f1bce220f77a063ece65a"
READER_BRANCH = "claude/helm-unchanged-reader-rev-20260924"
READER_COMMIT = "fee4ebecca7457a341bc3427bb8773b040aa0666"   # reader revision 4; after Codex's check pass --reader-commit
REFERENCE_COMMIT = "c8d5c430eec23a8fadd98bbcd045fecf03d86239"
HERE_REL = "records/typed_pointer_001/admission_unchanged_repro_001"
PACKAGE_REL = "research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_20208c92"
ARCHIVE_REL = PACKAGE_REL + "/source.zip"
ARCHIVE_SHA256, ARCHIVE_BYTES = "c42370c4941384c852feda33303dd70a01e956d28953cf07dd1b981220f31ed8", 5977155
REQUIREMENTS_MEMBER = "research/CAS_META_2_COMPOSITION/requirements-gpu.txt"
REQUIREMENTS_SHA256 = "9d0be7810014ec3a58a112dc0024a74060400dc841523abd405e5fb579179379"
WHEEL_MEMBERS = ("research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/casformer_reference-0.1.0-py3-none-any.whl",
                 "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/cas_neural_cjt-0.2.0-py3-none-any.whl")
PANEL_MANIFEST_SHA256 = "a27b3839f6fe5cb07d498c591395a30f06725a1ea0ee5882dcccbb1c2647c3e2"
FROZEN_STUDY_SHA256 = "60140ae0587e983120f37cb3499ecdc19e59f23cc0363520b2814e9e413f8a12"
FROZEN_ADMISSION_SHA256 = "5042681aa3e6e034a88cf6e516ee8dbf2f9b97b2d09f2f9bf4e234ad552bfb50"
READER_SOURCE_FILES = ("read_reproduction.py", "repro_common.py", "recompute_reproduction_evidence.py",
                       "historical_refusal_allowlist.json")
TEST_FILE = "test_unchanged_repro.py"
PILOT = "research/CAS_META_2_COMPOSITION/"
STAGE0_FILES = tuple(PILOT + p for p in ("aws/typed_pointer_launch.py", "aws/graph_training_curriculum_launch.py",
                                         "aws/graph_training_candidate_launch.py", "aws/run_evidence.py",
                                         "cas_meta2/typed_teaching/pointer_contract.py")) + (PACKAGE_REL + "/receipt.json",)
REFERENCE_PT = "records/typed_pointer_001/receipt_20260917/collected/results/artifacts/final.pt"
REFERENCE_RECORD = "records/typed_pointer_001/receipt_20260917/collected/results/artifacts/final_checkpoint.json"
REFERENCE_PT_SHA256, REFERENCE_PT_BYTES = "c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb", 3670007
REFERENCE_RECORD_BLOB = "123f14c8ce64b99268702a64f3d9ef20235fa196"
REFERENCE_RECEIPT = "records/typed_pointer_001/receipt_20260917/"
U17_RECEIPT = "records/typed_pointer_001/receipt_unchanged_repro_20260917/"
HELM2_JOB = "cas-meta2-tpntr-20260920210258-20208c92-m-20260917"
RECORDS = {"manifest": "collected/results/artifacts/manifest.json", "inventory": "collected_inventory.json",
           "checkpoint": "collected/results/artifacts/final_checkpoint.json"}
FINAL_PT = "collected/results/artifacts/final.pt"
INVENTORY_PATHS = {"manifest": "results/artifacts/manifest.json", "checkpoint": "results/artifacts/final_checkpoint.json",
                   "final_pt": "results/artifacts/final.pt"}
EVIDENCE_REL = "records/typed_pointer_001/evidence_unchanged_repro_20260917/reproduction_evidence.json"
ELIGIBILITY_REL = HERE_REL + "/READING_ELIGIBILITY.json"
ELIGIBILITY_SCHEMA = "cncm.helm-unchanged-reproduction-reading-eligibility/1"
ELIGIBILITY_FIELDS = ("decide_source_sha256", "environment_lock", "execution_admission_as_is", "frozen_study", "job",
                      "job_kind", "label", "launch_basis", "model_seed", "note", "owner_direction_record",
                      "panel_manifest_sha256", "policy_pins_sha256", "reader", "reader_acceptance", "review", "schema",
                      "source_sha", "state", "written_by", "written_utc")
ELIGIBILITY_RECEIPTS = ("reader_acceptance", "environment_lock", "review")
ACCEPTANCE_CASES = ("self_identity", "equal_state_different_envelope", "continuation_only_different", "changed_value",
                    "changed_encoder_state", "missing_key", "dtype_change", "altered_output", "changed_buffer",
                    "state_equal_output_tampered", "corrupt_reference")
LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"
JOB_KIND, MODEL_SEED, SOURCE_SHA = "UNCHANGED_ARM_REPRODUCTION", 20260917, "20208c923d41c24614504d4ecc2b289ecb66eda8"
LAUNCH_BASIS = "OWNER_DIRECTION_20260924"

# ---- custody: every bundle name is checked, case-insensitively, on top of the fixed selection ---------------------------
FORBIDDEN_NAME_PARTS = ("sealed", "_eval.jsonl", "salt", "private_target", "protected", "transcript", "hset",
                        "tkscas-archive")
FORBIDDEN_TREE_PREFIXES = ("records/helm_eval_design_20260923/", "records/typed_course_001/checks_002/private")
JOB_FILES = ("p1b_machine.py", "watch.py", "read_results.py", "JOB_LIMITS.md")
TEMPLATE = "job.sh.template"


class Refused(SystemExit):
    pass


def refuse(code, detail):
    print("LAUNCH_REFUSED: %s: %s" % (code, detail), flush=True)
    raise Refused(2)


# ---- git (read-only) -------------------------------------------------------------------------------------------------
def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE), "-c", "core.autocrlf=false"] + list(args), input=data,
                          capture_output=True, check=True).stdout


def git_ok(*args):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), capture_output=True).returncode == 0


def full_commit(ref):
    if not isinstance(ref, str) or not ref:
        return None
    try:
        return git("rev-parse", "--verify", "--quiet", ref + "^{commit}").decode().strip() or None
    except subprocess.CalledProcessError:
        return None


def read_blobs(commit, rels):
    """{rel: exact stored bytes or None}, CNCM-relative paths, through ONE `git cat-file --batch`."""
    rels = list(rels)
    if not rels:
        return {}
    raw, out, pos = git("cat-file", "--batch", data="".join("%s:%s%s\n" % (commit, REPO_PREFIX, r) for r in rels).encode()), {}, 0
    for rel in rels:
        end = raw.index(b"\n", pos)
        header = raw[pos:end].decode("utf-8", "replace")
        parts = header.split()
        if header.endswith(" missing") or header.endswith(" ambiguous") or len(parts) != 3:
            out[rel], pos = None, end + 1                        # no content follows a missing/ambiguous line
            continue
        size = int(parts[2])
        out[rel] = raw[end + 1:end + 1 + size] if parts[1] == "blob" else None
        pos = end + 1 + size + 1
    return out


def tree_files(commit, folder_rel):
    names = git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", REPO_PREFIX + folder_rel + "/")
    return sorted(n[len(REPO_PREFIX):] for n in names.decode("utf-8").split("\0") if n.startswith(REPO_PREFIX))


def is_ancestor(older, newer):
    return git_ok("merge-base", "--is-ancestor", older, newer)


def commits_touching(commit, rel):
    """Every non-merge commit in `commit`'s full history that changed `rel` (as read_reproduction.commits_touching)."""
    return git("log", "--format=%H", "--full-history", "--no-merges", commit, "--", ":(top)" + REPO_PREFIX + rel).decode().split()


# ---- pure helpers ------------------------------------------------------------------------------------------------------
def sha256(data):
    return hashlib.sha256(data).hexdigest()


def lf_sha(data):
    return sha256(data.replace(b"\r\n", b"\n"))


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode()


def reader_digest(hashes):
    """repro_common.reader_source_digest: sha256 of the canonical {file: sha256} of the four reader sources."""
    return sha256(canonical(hashes))


def is_hex(value, length):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{%d}" % length, value) is not None


def relative_path_ok(value):
    return (isinstance(value, str) and 0 < len(value) <= 400 and not value.startswith("/") and "\\" not in value
            and all(part not in ("", ".", "..") for part in value.split("/")))


def strict_json_object(raw):
    """A JSON object with no duplicate keys and no NaN/Infinity, or None."""
    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate key")
        return dict(items)

    def bad_constant(name):
        raise ValueError(name)
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def decide_sha(raw):
    """sha256 of the exact source text of `decide()` in a read_reproduction.py (repro_common.decide_source_sha256)."""
    try:
        text = raw.decode("utf-8")
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and node.name == "decide":
                return sha256(ast.get_source_segment(text, node).encode("utf-8"))
    except (AttributeError, SyntaxError, UnicodeDecodeError, ValueError):
        return None
    return None


def static_test_count(raw):
    """Test methods of the unittest.TestCase classes in the reader's test file: what `Ran N tests` must print."""
    tree = ast.parse(raw.decode("utf-8"))
    return sum(1 for node in tree.body if isinstance(node, ast.ClassDef)
               and any(ast.unparse(base).endswith("TestCase") for base in node.bases)
               for item in node.body if isinstance(item, ast.FunctionDef) and item.name.startswith("test"))


def custody_refusals(names):
    bad = []
    for name in names:
        low, rel = name.lower(), name[len("tree/"):] if name.startswith("tree/") else None
        if (any(part in low for part in FORBIDDEN_NAME_PARTS) or (rel is not None and rel.startswith(FORBIDDEN_TREE_PREFIXES))
                or "__pycache__" in name or name.endswith(".pyc") or ".." in name.split("/") or name.startswith("/")):
            bad.append(name)
    return bad


def worst_case_usd(minutes=CLIENT_DEADLINE_MINUTES):
    """Machine + public address + gp3 root, for `minutes` (default: the whole client deadline)."""
    return (PRICE_PER_HOUR + ADDRESS_PER_HOUR + ROOT_GB * GB_MONTH_USD / HOURS_PER_MONTH) * minutes / 60.0


# ---- the tree -----------------------------------------------------------------------------------------------------------
def tree_selection(commit, mode):
    rels = [r for r in tree_files(commit, HERE_REL) if r != HERE_REL + "/reproduction_reading.json"] + [ARCHIVE_REL]
    if mode == "acceptance":
        rels += list(STAGE0_FILES)
    return sorted(set(rels))


def check_tree(files, mode):
    """Refuses unless the tree at the chosen commit carries the pinned package, panel, freeze and decide(). Returns facts."""
    def need(rel):
        if files.get(rel) is None:
            refuse("TREE_FILE_MISSING", rel)
        return files[rel]
    archive = need(ARCHIVE_REL)
    if sha256(archive) != ARCHIVE_SHA256 or len(archive) != ARCHIVE_BYTES:
        refuse("PIN_MISMATCH", "package archive %s (%d bytes)" % (sha256(archive)[:12], len(archive)))
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        members = set(bundle.namelist())
        if sha256(bundle.read(REQUIREMENTS_MEMBER)) != REQUIREMENTS_SHA256:
            refuse("PIN_MISMATCH", "requirements-gpu.txt inside the archive")
        if not all(w in members for w in WHEEL_MEMBERS):
            refuse("PIN_MISMATCH", "the two historical wheels are not in the archive")
        bad = custody_refusals(["tree/" + m for m in members])
        if bad:
            refuse("CUSTODY", "archive members %s" % bad[:5])
    pins = {HERE_REL + "/public_panel_manifest.json": PANEL_MANIFEST_SHA256,
            HERE_REL + "/frozen/study.json": FROZEN_STUDY_SHA256,
            HERE_REL + "/EXECUTION_ADMISSION.json": FROZEN_ADMISSION_SHA256}
    for rel, pin in pins.items():
        if sha256(need(rel)) != pin:
            refuse("PIN_MISMATCH", "%s (sha256 %s, pinned %s)" % (rel, sha256(files[rel])[:12], pin[:12]))
    hashes = {name: sha256(need(HERE_REL + "/" + name)) for name in READER_SOURCE_FILES}
    test_raw = need(HERE_REL + "/" + TEST_FILE)
    facts = {"reader_sources_sha256": hashes, "reader_source_sha256": reader_digest(hashes),
             "decide_source_sha256": decide_sha(files[HERE_REL + "/read_reproduction.py"]),
             "expected_tests": static_test_count(test_raw),
             "frozen_job": json.loads(files[HERE_REL + "/frozen/study.json"])["jobs"][0]["job"],
             "policy_pins_sha256": sha256(need(HERE_REL + "/policy_pins.json"))}
    if mode == "acceptance":
        for rel in STAGE0_FILES:
            need(rel)
        text = test_raw.decode("utf-8")
        read = sorted({PILOT + p for p in re.findall(r"PILOT / '([^']+)'", text)})
        missing = [r for r in read if r not in files]
        if missing:
            refuse("STAGE0_READS_AN_UNBUNDLED_FILE", missing)
        facts["stage0_pilot_reads_checked"] = read
    return facts


def check_reference(ref, panel_manifest_raw):
    raw, record = ref.get(REFERENCE_PT), ref.get(REFERENCE_RECORD)
    if raw is None or record is None:
        refuse("REFERENCE_MISSING", "fetch the Helm 2.0 receipt commit %s" % REFERENCE_COMMIT[:8])
    if sha256(raw) != REFERENCE_PT_SHA256 or len(raw) != REFERENCE_PT_BYTES:
        refuse("PIN_MISMATCH", "reference final.pt")
    blob = hashlib.sha1(b"blob %d\0" % len(record) + record).hexdigest()
    pinned = json.loads(panel_manifest_raw)["inputs"]["checkpoint_record"]["sha256"]
    if blob != REFERENCE_RECORD_BLOB or sha256(record) != pinned:
        refuse("PIN_MISMATCH", "reference final_checkpoint.json (blob %s)" % blob[:8])


# ---- reading: the U17 candidate ---------------------------------------------------------------------------------------
def stated_row(row):
    if isinstance(row, dict) and is_hex(row.get("sha256"), 64) and type(row.get("bytes")) is int and row["bytes"] > 0:
        return row["sha256"], row["bytes"]
    return None


def inventory_row(inventory, relative_path):
    rows = [r for r in (inventory.get("files") or []) if isinstance(r, dict) and r.get("relative_path") == relative_path]
    return stated_row(rows[0]) if len(rows) == 1 else None


def candidate_problems(final_pt, records, job):
    """Pure. The receipt's final.pt must be the one all three records name, for this job (as the reader binds them)."""
    if final_pt is None:
        return ["CANDIDATE_FINAL_PT_MISSING"]
    have, problems, docs = (sha256(final_pt), len(final_pt)), [], {}
    for name, raw in records.items():
        doc = strict_json_object(raw) if raw is not None else None
        if doc is None:
            problems.append("CANDIDATE_RECORD_MISSING_OR_UNREADABLE:" + name)
        docs[name] = doc or {}
    artifacts = [r for r in (docs["manifest"].get("artifacts") or []) if isinstance(r, dict) and r.get("name") == "final.pt"]
    stated = {"manifest": stated_row(artifacts[0]) if len(artifacts) == 1 else None,
              "inventory": inventory_row(docs["inventory"], INVENTORY_PATHS["final_pt"]),
              "checkpoint": stated_row(docs["checkpoint"])}
    problems += ["CANDIDATE_RECORD_DOES_NOT_NAME_THIS_FINAL_PT:" + n for n, v in sorted(stated.items()) if v != have]
    if docs["inventory"].get("job") != job:
        problems.append("CANDIDATE_INVENTORY_IS_FOR_ANOTHER_JOB")
    meta = docs["checkpoint"].get("metadata") if isinstance(docs["checkpoint"].get("metadata"), dict) else {}
    run_ids = (((meta.get("run_identity") or {}).get("context") or {}).get("run_id"),
               ((meta.get("init_args") or {}).get("run_context") or {}).get("run_id"))
    if run_ids != (job, job):
        problems.append("CANDIDATE_CHECKPOINT_IS_FOR_ANOTHER_JOB")
    for name in ("manifest", "checkpoint"):
        raw = records.get(name)
        if raw is not None and inventory_row(docs["inventory"], INVENTORY_PATHS[name]) != (sha256(raw), len(raw)):
            problems.append("CANDIDATE_RECORD_IS_NOT_THE_ONE_THE_JOB_COLLECTED:" + name)
    return problems


def candidate_from(commit, receipt, job):
    got = read_blobs(commit, [receipt + FINAL_PT] + [receipt + r for r in RECORDS.values()])
    final_pt = got[receipt + FINAL_PT]
    problems = candidate_problems(final_pt, {n: got[receipt + r] for n, r in RECORDS.items()}, job)
    if problems:
        refuse("CANDIDATE_NOT_BOUND", "%s at %s: %s" % (receipt, commit[:8], problems))
    return {"bytes": final_pt, "sha256": sha256(final_pt), "size": len(final_pt), "job": job, "receipt": receipt,
            "commit": commit}


# ---- reading: the eligibility gate (FIRST) ------------------------------------------------------------------------------
def eligibility_problems(raw, facts, bundled):
    """Pure. Every way the committed eligibility record does not admit THIS reading run with THIS bundled reader.
    `facts` are the git facts (eligibility_facts); `bundled` is check_tree's facts for the receipt commit's tree.
    It mirrors the reader's own eligibility rule where a failure would waste the one-shot reading; the reader
    (read_reproduction.eligibility_violations) remains the deciding check."""
    record = strict_json_object(raw)
    if record is None:
        return ["ELIGIBILITY_NOT_A_STRICT_JSON_OBJECT"]
    problems = []
    if (sorted(record) != sorted(ELIGIBILITY_FIELDS) or record.get("schema") != ELIGIBILITY_SCHEMA
            or record.get("label") != LABEL or record.get("state") != "READING_ELIGIBLE"):
        problems.append("ELIGIBILITY_FIELDS_SCHEMA_LABEL_OR_STATE")
    if record.get("job") != bundled["frozen_job"]:
        problems.append("NOT_FOR_THE_FROZEN_JOB:%s" % str(record.get("job"))[:80])
    if (record.get("job_kind"), record.get("model_seed"), record.get("source_sha")) != (JOB_KIND, MODEL_SEED, SOURCE_SHA):
        problems.append("NOT_THIS_JOB_KIND")
    if record.get("frozen_study") != {"commit": FREEZE_COMMIT, "path": REPO_PREFIX + HERE_REL + "/frozen/study.json",
                                      "sha256": FROZEN_STUDY_SHA256}:
        problems.append("FROZEN_STUDY_BINDING")
    if record.get("execution_admission_as_is") != {"path": REPO_PREFIX + HERE_REL + "/EXECUTION_ADMISSION.json",
                                                   "sha256": FROZEN_ADMISSION_SHA256, "state": "NOT_READY"}:
        problems.append("ADMISSION_IS_NOT_THE_BYTE_IDENTICAL_AS_IS_RECORD")
    if record.get("reader") != {"reader_source_sha256": bundled["reader_source_sha256"],
                                "reader_sources_sha256": bundled["reader_sources_sha256"]}:
        problems.append("NOT_THE_READER_THIS_BUNDLE_SHIPS")
    if record.get("policy_pins_sha256") != bundled["policy_pins_sha256"]:
        problems.append("POLICY_PINS")
    if record.get("panel_manifest_sha256") != PANEL_MANIFEST_SHA256:
        problems.append("PANEL_MANIFEST")
    if record.get("launch_basis") != LAUNCH_BASIS:
        problems.append("LAUNCH_BASIS")
    decide = record.get("decide_source_sha256")
    if not (is_hex(decide, 64) and decide == bundled["decide_source_sha256"] == facts.get("decide_at_freeze")):
        problems.append("DECIDE_IS_NOT_THE_FROZEN_DECIDE")
    touching = facts.get("eligibility_commits") or []
    if len(touching) != 1:
        problems.append("ELIGIBILITY_NOT_EXACTLY_ONE_COMMITTED_VERSION:%d" % len(touching))
    if facts.get("freeze_precedes_eligibility") is not True:
        problems.append("ELIGIBILITY_NOT_COMMITTED_AFTER_THE_FREEZE")
    if facts.get("evidence_present") is not False:
        problems.append("EVIDENCE_ALREADY_COMMITTED:the reading is one shot")
    receipts = facts.get("receipts") or {}
    for name in ELIGIBILITY_RECEIPTS:
        entry = record.get(name)
        if not (isinstance(entry, dict) and sorted(entry) == ["receipt_commit", "receipt_path", "receipt_sha256"]
                and is_hex(entry["receipt_commit"], 40) and relative_path_ok(entry["receipt_path"])
                and is_hex(entry["receipt_sha256"], 64)):
            problems.append("RECEIPT_REFERENCE_FORM:" + name)
            continue
        got = receipts.get(name) or {}
        if not isinstance(got.get("raw"), bytes):
            problems.append("RECEIPT_NOT_A_COMMITTED_BLOB:" + name)
        elif got.get("anchored") is not True:
            problems.append("RECEIPT_NOT_COMMITTED_BEFORE_THE_ELIGIBILITY_RECORD:" + name)
        elif sha256(got["raw"]) != entry["receipt_sha256"]:
            problems.append("RECEIPT_SHA256:" + name)
    acceptance = strict_json_object((receipts.get("reader_acceptance") or {}).get("raw") or b"")
    if acceptance is not None:
        producer = acceptance.get("producer") if isinstance(acceptance.get("producer"), dict) else {}
        if acceptance.get("status") != "READER_ACCEPTANCE_PASS":
            problems.append("ACCEPTANCE_RECEIPT_NOT_PASS:%s" % acceptance.get("status"))
        if producer.get("reader_source_sha256") != bundled["reader_source_sha256"]:
            problems.append("ACCEPTANCE_RAN_ANOTHER_READER")
        if [c.get("case") if isinstance(c, dict) else None for c in (acceptance.get("cases") or [])] != list(ACCEPTANCE_CASES):
            problems.append("ACCEPTANCE_CASES_NOT_THE_REGISTERED_ELEVEN")
    elif "RECEIPT_REFERENCE_FORM:reader_acceptance" not in problems:
        problems.append("ACCEPTANCE_RECEIPT_UNREADABLE")
    return problems


def eligibility_facts(commit, raw):
    """Impure: the git facts eligibility_problems reads (no fetch, no network)."""
    record = strict_json_object(raw) or {}
    touching = commits_touching(commit, ELIGIBILITY_REL)
    anchor = touching[0] if len(touching) == 1 else None
    receipts = {}
    for name in ELIGIBILITY_RECEIPTS:
        entry = record.get(name) if isinstance(record.get(name), dict) else {}
        c, p = entry.get("receipt_commit"), entry.get("receipt_path")
        if is_hex(c, 40) and relative_path_ok(p):
            present = full_commit(c) == c
            receipts[name] = {"commit": c, "path": p, "raw": read_blobs(c, [p])[p] if present else None,
                              "anchored": anchor is not None and present and is_ancestor(c, anchor)}
    return {"eligibility_commits": touching,
            "freeze_precedes_eligibility": anchor is not None and anchor != FREEZE_COMMIT and is_ancestor(FREEZE_COMMIT, anchor),
            "evidence_present": read_blobs(commit, [EVIDENCE_REL])[EVIDENCE_REL] is not None,
            "decide_at_freeze": decide_sha(read_blobs(FREEZE_COMMIT, [HERE_REL + "/read_reproduction.py"])[HERE_REL + "/read_reproduction.py"] or b""),
            "receipts": receipts}


def eligibility_gate(receipt_commit):
    """Reading mode's FIRST check: nothing is built, uploaded or launched before it passes."""
    if not receipt_commit:
        refuse("ELIGIBILITY_RECEIPT_COMMIT_REQUIRED", "the reading runs once, only after READING_ELIGIBILITY.json is "
               "committed. Give --receipt-commit: ONE commit holding the U17 receipt, the eligibility record and the "
               "reader it binds (a --dry-run --rehearsal builds the reading bundle's shape with public stand-ins)")
    commit = full_commit(receipt_commit)
    if commit is None:
        refuse("RECEIPT_COMMIT_NOT_FOUND", "%s (fetch its branch with an explicit refspec)" % receipt_commit)
    raw = read_blobs(commit, [ELIGIBILITY_REL])[ELIGIBILITY_REL]
    if raw is None:
        refuse("ELIGIBILITY_RECORD_REQUIRED", "%s is not committed at %s. The reading mode runs only after the separate "
               "eligibility record (after the freeze %s, before the evidence) is committed" % (
                   ELIGIBILITY_REL, commit[:8], FREEZE_COMMIT[:8]))
    files = read_blobs(commit, tree_selection(commit, "reading"))
    bundled = check_tree(files, "reading")
    problems = eligibility_problems(raw, eligibility_facts(commit, raw), bundled)
    if problems:
        refuse("ELIGIBILITY_RECORD_INVALID", "; ".join(problems))
    print("ELIGIBILITY: PASS (%s at %s; reader %s...; the reader's own check stays deciding)"
          % (ELIGIBILITY_REL, commit[:8], bundled["reader_source_sha256"][:16]), flush=True)
    return {"commit": commit, "raw": raw, "sha256": sha256(raw), "files": files, "bundled": bundled}


# ---- the bundle ---------------------------------------------------------------------------------------------------------
def job_files():
    rels = [(HERE / name).relative_to(PACKAGE).as_posix() for name in JOB_FILES + (TEMPLATE, "launch.py")]
    commit = git("log", "-1", "--format=%H", "--", *rels).decode().strip() or None
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *rels).decode().strip()
    return rels, commit, dirty


def job_file(commit, dirty, name):
    """Committed bytes when the job files are clean; the working copy otherwise (dry run only; a launch refuses)."""
    if commit and not dirty:
        rel = (HERE / name).relative_to(PACKAGE).as_posix()
        return read_blobs(commit, [rel])[rel]
    return (HERE / name).read_bytes().replace(b"\r\n", b"\n")


def build_bundle(files):
    """Deterministic tar.gz: sorted names, mtime 0, root owner; anchors.json last. Returns (body, sha256, anchors)."""
    anchors = {"schema": "claude.p1b-job-anchors/0.1",
               "files": {n: {"sha256": sha256(files[n]), "bytes": len(files[n])} for n in sorted(files)}}
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as zipped, \
            tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(files) + ["anchors.json"]:
            data = files[name] if name != "anchors.json" else json.dumps(anchors, indent=1, sort_keys=True).encode()
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = len(data), 0, 0o644, 0, 0, "", ""
            tar.addfile(info, io.BytesIO(data))
    body = buffer.getvalue()
    return body, sha256(body), anchors


def outside_git(folder):
    folder = pathlib.Path(folder).resolve()
    return not any((q / ".git").exists() for q in [folder] + list(folder.parents))


def render(template, values):
    script = template
    for key, value in values.items():
        script = script.replace(key, value)
    left = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", script)))
    if left:
        raise AssertionError("unfilled placeholders: %s" % left)
    found = [b for b in BASHISMS if b in script]
    if found:
        raise AssertionError("bash-only syntax in the machine script (the historical AMI rule): %s" % found)
    if len(script.encode("utf-8")) >= USER_DATA_LIMIT:
        raise AssertionError("the machine script is over the %d-byte user-data limit" % USER_DATA_LIMIT)
    return script


def script_values(mode, urls, bundle_sha, facts, candidate, source_commit):
    return {"__MODE__": mode, "__INSTANCE_TYPE__": INSTANCE_TYPE, "__AMI__": AMI, "__MAX_SECONDS__": str(MAX_SECONDS),
            "__POWER_OFF_MINUTES__": str(POWER_OFF_MINUTES), "__BUNDLE_URL__": urls["bundle"],
            "__RESULTS_URL__": urls["results"], "__PROGRESS_URL__": urls["progress"], "__BUNDLE_SHA256__": bundle_sha,
            "__ARCHIVE_SHA256__": ARCHIVE_SHA256, "__SOURCE_COMMIT__": source_commit,
            "__READER_DIGEST__": facts["reader_source_sha256"], "__EXPECTED_TESTS__": str(facts["expected_tests"]),
            "__CANDIDATE_SHA256__": candidate["sha256"] if candidate else "none",
            "__CANDIDATE_JOB__": candidate["job"] if candidate else "none",
            "__TORCH_VERSION__": TORCH_VERSION, "__TORCH_INDEX__": TORCH_INDEX}


def plan_text(mode, rehearsal, bundle, facts, candidate, sources, dirty):
    lo, hi = EXPECTED_MINUTES[mode]
    lines = ["PLAN (mode %s%s)" % (mode, ", REHEARSAL: public stand-in candidate, cannot launch" if rehearsal else ""),
             "  machine   ONE %s, %s, image %s, on-demand $%.2f/h, %d GiB gp3 deleted with it; no credentials on it"
             % (INSTANCE_TYPE, REGION, AMI, PRICE_PER_HOUR, ROOT_GB),
             "  limits    %d-minute session: in-machine timer %d min, OS power-off %d min, client deadline %d min "
             "(watch.py terminates); the preflight refuses a projected end past 55 min"
             % (SESSION_MINUTES, MAX_SECONDS // 60, POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES),
             "  COST CAP  worst case at the client deadline $%.4f <= cap $%.2f (plus the $%.2f allowance = $%.2f in the ledger)"
             % (worst_case_usd(), COST_CAP_USD, ALLOWANCE_USD, COST_CAP_USD + ALLOWANCE_USD),
             "  expected  about %d-%d min, about $%.2f-$%.2f" % (lo, hi, worst_case_usd(lo), worst_case_usd(hi)),
             "  retries   none: one launch attempt, one zone; launch_record_%s.json refuses a second" % mode,
             "  bundle    %d files, %.1f MB compressed, sha256 %s" % (bundle["files"], bundle["bytes"] / 1e6, bundle["sha256"]),
             "  reader    %s... (%s); decide() = the freeze's; %d tests expected" % (
                 facts["reader_source_sha256"][:16], sources["tree_commit"][:8], facts["expected_tests"]),
             "  sources   %s" % json.dumps(sources, sort_keys=True),
             "  job files %s" % ("committed" if not dirty else "WORKING COPY, not committed (dry run only; a launch refuses)"),
             "  stages    0 IMDSv2 instance id + AMI + type -> env.txt; bundle sha256; every file against anchors.json"]
    if mode == "acceptance":
        lines.append("            0b the reader's %d tests, pure Python, GPU switch unset (fail -> stop before GPU work)"
                     % facts["expected_tests"])
    lines += ["            1 historical install (venv, torch %s cu128, 2 wheels --no-deps, requirements-gpu.txt)"
              % TORCH_VERSION,
              "            2 timing preflight on the GPU: refuses over 55 min projected, or a non-pinned environment",
              "            3 recompute_reproduction_evidence.py --mode %s, once" % mode]
    if mode == "acceptance":
        lines.append("            4 decide: 11 cases in order, each re-derived against ACCEPTANCE_EXPECTED; READER_ACCEPTANCE_PASS")
    else:
        lines += ["            4 decide: the evidence was written by the bound reader for candidate %s... (job %s)"
                  % (candidate["sha256"][:16], candidate["job"]),
                  "            NO verdict on the machine: commit the evidence ONCE, then read_reproduction.py on the laptop"]
    lines.append("  labels    CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT")
    return "\n".join(lines)


# ---- main ---------------------------------------------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", choices=("acceptance", "reading"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rehearsal", action="store_true", help="reading + dry run only: public stand-ins, never launches")
    parser.add_argument("--reader-commit", default=None, help="acceptance / rehearsal: the reader-rev commit to ship")
    parser.add_argument("--receipt-commit", default=None, help="reading: ONE commit with the U17 receipt + eligibility record")
    parser.add_argument("--receipt-branch", default=None, help="reading, real launch: the pushed branch carrying it")
    parser.add_argument("--availability-zone", default=None)
    parser.add_argument("--bundle-dir", default=None, help="a NEW folder outside every git tree (default: a new temp folder)")
    args = parser.parse_args(argv)
    if args.rehearsal and (args.mode != "reading" or not args.dry_run or args.receipt_commit):
        refuse("USAGE", "--rehearsal is for --mode reading --dry-run only, without --receipt-commit")
    if args.mode == "acceptance" and (args.receipt_commit or args.receipt_branch):
        refuse("USAGE", "--receipt-commit / --receipt-branch belong to the reading mode")
    if args.mode == "reading" and not args.rehearsal and args.reader_commit:
        refuse("USAGE", "the reading ships the reader committed at --receipt-commit (the one the eligibility record binds)")
    gate, candidate = None, None
    if args.mode == "reading" and not args.rehearsal:
        gate = eligibility_gate(args.receipt_commit)            # FIRST: nothing else is read or built before this passes
    worst = worst_case_usd()
    if worst > COST_CAP_USD:
        refuse("OVER_CAP", "worst case %.4f > cap %.2f" % (worst, COST_CAP_USD))
    record_path = HERE / ("launch_record_%s.json" % args.mode)
    if not args.dry_run and record_path.exists():
        refuse("ALREADY_LAUNCHED", "%s exists: one approval, one machine, no retry" % record_path.name)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = pathlib.Path(args.bundle_dir) if args.bundle_dir else pathlib.Path(tempfile.gettempdir()) / (
        "p1b_job_%s_%s" % (args.mode, stamp))
    if folder.exists() or not outside_git(folder.parent):
        refuse("BUNDLE_DIR", "%s must be a NEW folder outside every git work tree" % folder)

    rels, job_commit, dirty = job_files()
    if (dirty or not job_commit) and not args.dry_run:
        refuse("JOB_FILES_NOT_COMMITTED", "commit the job files first:\n%s" % (dirty or rels))
    if gate is not None:
        source_commit, files, facts = gate["commit"], gate["files"], gate["bundled"]
        candidate = candidate_from(source_commit, U17_RECEIPT, facts["frozen_job"])
    else:
        source_commit = full_commit(args.reader_commit or READER_COMMIT)
        if source_commit is None or not is_ancestor(FREEZE_COMMIT, source_commit):
            refuse("READER_COMMIT", "%s is not a local commit that descends from the freeze %s (git fetch origin %s)"
                   % (args.reader_commit or READER_COMMIT, FREEZE_COMMIT[:8], READER_BRANCH))
        files = read_blobs(source_commit, tree_selection(source_commit, args.mode))
        facts = check_tree(files, args.mode)
        if args.rehearsal:
            candidate = candidate_from(REFERENCE_COMMIT, REFERENCE_RECEIPT, HELM2_JOB)
    if facts["decide_source_sha256"] is None or facts["decide_source_sha256"] != decide_sha(
            read_blobs(FREEZE_COMMIT, [HERE_REL + "/read_reproduction.py"])[HERE_REL + "/read_reproduction.py"] or b""):
        refuse("DECIDE_IS_NOT_THE_FROZEN_DECIDE", source_commit[:8])
    ref = read_blobs(REFERENCE_COMMIT, [REFERENCE_PT, REFERENCE_RECORD])
    check_reference(ref, files[HERE_REL + "/public_panel_manifest.json"])

    bundle_files = {"tree/" + rel: data for rel, data in files.items()}
    bundle_files["ref/final.pt"], bundle_files["ref/final_checkpoint.json"] = ref[REFERENCE_PT], ref[REFERENCE_RECORD]
    if candidate is not None:
        bundle_files["cand/final.pt"] = candidate["bytes"]
    bundle_files["claude/p1b_machine.py"] = job_file(job_commit, dirty, "p1b_machine.py")
    if gate is not None:
        bundle_files["claude/eligibility_record.json"] = gate["raw"]
    bad = custody_refusals(list(bundle_files) + ["anchors.json"])
    if bad:
        refuse("CUSTODY", "%d bundle names break custody: %s" % (len(bad), bad[:8]))
    print("CUSTODY: PASS (%d names; fixed selection plus forbidden words %s; no archive, S3, salt or sealed file)"
          % (len(bundle_files) + 1, list(FORBIDDEN_NAME_PARTS)), flush=True)
    body, bundle_sha, anchors = build_bundle(bundle_files)
    template = job_file(job_commit, dirty, TEMPLATE).decode("utf-8")
    sources = {"tree_commit": source_commit, "reference_commit": REFERENCE_COMMIT, "freeze_commit": FREEZE_COMMIT,
               "reader_branch" if gate is None else "receipt_branch": READER_BRANCH if gate is None else args.receipt_branch}
    if candidate is not None:
        sources["candidate"] = {k: candidate[k] for k in ("sha256", "size", "job", "receipt", "commit")}
    bundle = {"files": len(bundle_files) + 1, "bytes": len(body), "sha256": bundle_sha}
    print(plan_text(args.mode, args.rehearsal, bundle, facts, candidate, sources, dirty or not job_commit), flush=True)
    folder.mkdir(parents=True)
    (folder / "bundle.tar.gz").write_bytes(body)
    long_links = {k: "https://" + "L" * (LINK_BYTES_ASSUMED - 8) for k in ("bundle", "results", "progress")}
    render(template, script_values(args.mode, long_links, bundle_sha, facts, candidate, source_commit))  # size with long links
    keys = {k: "helm-integration/p1b-%s-%s/%s" % (args.mode, stamp, v)
            for k, v in (("bundle", "bundle.tar.gz"), ("results", "results.tar.gz"), ("progress", "progress.log"))}
    summary = {"schema": "claude.p1b-job-bundle/0.1", "label": LABEL, "mode": args.mode, "rehearsal": args.rehearsal,
               "launchable": not args.rehearsal, "bundle": bundle, "sources": sources,
               "reader": {k: facts[k] for k in ("reader_source_sha256", "reader_sources_sha256", "decide_source_sha256",
                                                "expected_tests", "policy_pins_sha256")},
               "frozen_job": facts["frozen_job"],
               "eligibility": None if gate is None else {"path": REPO_PREFIX + ELIGIBILITY_REL, "sha256": gate["sha256"],
                                                          "receipt_commit": gate["commit"]},
               "job_files": rels, "job_files_commit": None if dirty else job_commit,
               "job_files_from_working_copy": bool(dirty or not job_commit),
               "template_sha256_lf": lf_sha(template.encode("utf-8")), "launcher_sha256_lf": lf_sha(pathlib.Path(__file__).read_bytes()),
               "worst_case_usd_at_client_deadline": round(worst, 4), "cost_cap_usd": COST_CAP_USD, "allowance_usd": ALLOWANCE_USD,
               "session_minutes": SESSION_MINUTES, "in_machine_timer_seconds": MAX_SECONDS,
               "os_power_off_minutes": POWER_OFF_MINUTES, "client_deadline_minutes": CLIENT_DEADLINE_MINUTES}
    if args.dry_run:
        fake = {k: "https://DRY-RUN.invalid/%s" % v for k, v in keys.items()}
        script = render(template, script_values(args.mode, fake, bundle_sha, facts, candidate, source_commit))
        (folder / "dry_run_machine_script.sh").write_bytes(script.encode("utf-8"))
        summary.update(dry_run=True, aws_calls=[], network_calls=[], machine_script_bytes=len(script.encode("utf-8")),
                       machine_script_sha256=sha256(script.encode("utf-8")))
        (folder / "dry_run_record.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("DRY RUN: nothing uploaded, nothing launched, no AWS or network call. Bundle, machine script (%d bytes) "
              "and dry_run_record.json are in %s" % (len(script.encode("utf-8")), folder), flush=True)
        return 0
    return launch(args, stamp, keys, folder / "bundle.tar.gz", bundle_sha, template, facts, candidate, source_commit,
                  summary, record_path)


def pushed(branch, commit):
    tip = git("ls-remote", "origin", "refs/heads/" + branch).decode().split()
    return bool(tip) and full_commit(tip[0]) == tip[0] and is_ancestor(commit, tip[0])


def launch(args, stamp, keys, bundle_path, bundle_sha, template, facts, candidate, source_commit, summary, record_path):
    """The coordinator's launch. One attempt, one zone, no retries. Every refusal comes before the upload."""
    if args.rehearsal:
        refuse("REHEARSAL_CANNOT_LAUNCH", "a rehearsal carries a stand-in candidate")
    branch = args.receipt_branch if args.mode == "reading" else READER_BRANCH
    if not branch or not pushed(branch, source_commit):
        refuse("NOT_PUSHED", "%s is not on the pushed %s (fetch; push; name --receipt-branch for a reading)" % (
            source_commit[:8], branch))
    import boto3
    quotes = []
    for item in boto3.client("pricing", region_name="us-east-1").get_products(
            ServiceCode="AmazonEC2", Filters=[{"Type": "TERM_MATCH", "Field": f, "Value": v} for f, v in PRICING_FILTERS],
            MaxResults=20)["PriceList"]:
        product = json.loads(item) if isinstance(item, str) else item
        for term in product.get("terms", {}).get("OnDemand", {}).values():
            quotes += [float(d["pricePerUnit"]["USD"]) for d in term.get("priceDimensions", {}).values()]
    if not quotes or max(quotes) > PRICE_PER_HOUR:
        refuse("PRICE_NOT_WITHIN_THE_RATE_CEILING", "on-demand quotes %s vs ceiling %.2f" % (quotes, PRICE_PER_HOUR))
    ec2 = boto3.client("ec2", region_name=REGION)
    image = ec2.describe_images(ImageIds=[AMI])["Images"][0]
    live = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": GPU_FAMILIES}, {
        "Name": "instance-state-name", "Values": ["pending", "running", "stopping", "shutting-down"]}])["Reservations"]
    if live:
        refuse("GPU_MACHINE_RUNNING", "%s (quota 8 vCPU: one GPU machine at a time)"
               % [i["InstanceId"] for r in live for i in r["Instances"]])
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = sorted((s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
                      if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]
                      and (args.availability_zone in (None, s["AvailabilityZone"]))), key=lambda s: s["AvailabilityZone"])
    if not subnets:
        refuse("NO_SUBNET", "no default-VPC subnet offers %s with a public address" % INSTANCE_TYPE)
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]},
                                                  {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        refuse("OPEN_SECURITY_GROUP", "the default security group allows inbound traffic from an address range")
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(bundle_path), BUCKET, keys["bundle"])
    urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]},
                                                ExpiresIn=LINK_SECONDS)}
    for k in ("results", "progress"):
        urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=LINK_SECONDS)
    script = render(template, script_values(args.mode, urls, bundle_sha, facts, candidate, source_commit))
    subnet = subnets[0]
    tags = [{"Key": "Name", "Value": "p1b-%s-%s" % (args.mode, stamp)},
            {"Key": "Purpose", "Value": "P1b unchanged-arm reproduction reader, %s; CLAUDE_BUILT_CLAUDE_CHECKED" % args.mode},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched = ec2.run_instances(
        ImageId=AMI, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"],
        SecurityGroupIds=[group["GroupId"]], InstanceInitiatedShutdownBehavior="terminate", UserData=script,
        ClientToken="p1b-%s-%s" % (args.mode, stamp), MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
        BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"],
                              "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
    instance = launched["Instances"][0]
    print("LAUNCHED INSTANCE ID: %s  (printed FIRST, before anything else can fail)" % instance["InstanceId"], flush=True)
    record = dict(summary, schema="claude.p1b-job-launch/0.1", dry_run=False,
                  approved={"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                            "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": COST_CAP_USD},
                  on_demand_quotes_usd=quotes, instance_id=instance["InstanceId"],
                  launched_utc=instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                  availability_zone=subnet["AvailabilityZone"], subnet=subnet["SubnetId"], ami=AMI,
                  ami_name=image.get("Name"), security_group=group["GroupId"], bucket=BUCKET, keys=keys,
                  root_volume_gb=ROOT_GB, machine_script_sha256=sha256(script.encode("utf-8")),
                  links_stored="no -- time-limited links are never written to disk")
    record_path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("LAUNCHED %s (%s, %s). It powers itself off within %d minutes; watch.py terminates it at %d. Record: %s" % (
        instance["InstanceId"], INSTANCE_TYPE, subnet["AvailabilityZone"], POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES,
        record_path.name), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as stop:
        sys.exit(stop.code)
