"""Launch E1b, the sealed HSET-2 TEST readout, on ONE AWS T4 (readout plan item 10). CLAUDE_BUILT_CLAUDE_CHECKED.
BUILT, NOT LAUNCHED. The coordinator is the only runner; a dry run never imports boto3 and never touches the network.

WHAT RUNS ON THE MACHINE: job.sh.template, then e1b_machine.py (stages 0-4; see its docstring and JOB_LIMITS.md).

WHAT MUST EXIST FIRST (plan item 10: "It reads only after P2, the U17 verdict, ITEM2 and the matched start"). One
committed file, E1B_INPUTS.json (schema claude.e1b-inputs/0.1), names every input by (commit, path, sha256):
  * hset2_build_commit: the commit P2 ran; its builder files must equal the build summary's recorded LF sha256;
  * build_summary, public_cells: P2's PUBLIC outputs (HSET2_BUILD_SUMMARY.json with mode SEALED_BUILD, build_ok);
  * runs: six rows (R17/R18/R19 repaired, U17 fresh unchanged, the two historical Helm 2.0 finals), each final.pt;
  * item2_reading (any outcome; an open gate only masks the repaired analogy cell), matched_start (must read
    MATCHED_START_REPRODUCED), reproduction_reading (must read STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED; otherwise the
    plan says stop and ask the owner), inference_ruling (optional: without it the confirmatory claim reads
    INFERENCE_ASSUMPTIONS_UNSUPPORTED), h1h2 (one h1h2_paired.py document per seed pair);
  * touched: the design s8 manifest, every kind (updates, development_evaluation, dev_reading, probe, smoke, fixture)
    as a list of (commit, path, sha256) or the string "NONE:<reason>".
The sealed P2 tarball is NEVER in git and never in the bundle: at launch the coordinator gives its private-bucket key
and sha256 (--sealed-s3-key, --sealed-sha256); the machine fetches it through its own time-limited link.

REFUSALS BEFORE ANY SPEND: inputs file missing, uncommitted or malformed; any blob missing or not its sha256; a gate
record that does not admit the reading; builder code not the sealed build's; a bundle name that breaks custody
(sealed, _eval.jsonl, salt, private_target, protected, transcript, archive); worst case above the cap; machine script
over the user-data limit; job files not committed (a real launch); launch_record.json already present.

    python -B launch.py --dry-run [--inputs E1B_INPUTS.json] [--bundle-dir DIR]
    python -B launch.py --sealed-s3-key KEY --sealed-sha256 HEX [--inputs E1B_INPUTS.json]    (the coordinator only)
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
PACKAGE = HERE.parents[3]                     # e1b_job -> readout -> helm_eval_design_20260923 -> records -> CNCM root
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, PRICE_PER_HOUR = "g4dn.2xlarge", 0.752      # on-demand, us-west-2, Linux (P1a's T4 machine)
ADDRESS_PER_HOUR, ROOT_GB, GB_MONTH_USD = 0.005, 100, 0.08
PINNED_AMI = "ami-07d69ce07bfe5628f"          # the T4 reference image of P1a and the analogy T4 job; no substitute
MAX_SECONDS, OS_POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES = 120 * 60, 123, 130
WALL_SECONDS = 95 * 60                         # e1b_machine's own budget for stages 0-4
COST_CAP_USD, ALLOWANCE_USD = 2.00, 0.10       # plan item 10: cap $2.00 + $0.10
PROCESSES = 6                                  # g4dn.2xlarge: 8 vCPU, 32 GiB, one T4
UV_VERSION, PYTHON_VERSION = "0.12.17", "3.14.7"
TORCH_VERSION, TORCH_LOCAL, NUMPY_VERSION = "2.11.0", "2.11.0+cu128", "2.5.2"
LINK_SECONDS, USER_DATA_LIMIT, LINK_BYTES_ASSUMED = 4 * 3600, 16000, 2048   # P1a's long-link convention
GPU_FAMILIES = ["g4dn.*", "g4ad.*", "g5.*", "g5g.*", "g6.*", "g6e.*", "g7.*", "g7e.*", "gr6.*", "p3.*", "p3dn.*",
                "p4d.*", "p4de.*", "p5.*", "p5e.*", "p5en.*"]         # g7 added: training runs on g7.2xlarge
ARCHIVE = pathlib.Path("D:/tksCAS-archive")
INPUTS_SCHEMA = "claude.e1b-inputs/0.1"
ROUTE_COMMIT = "e05889eec0f800a9a17b0c39a8d8d37f544b43bf"   # accepted larger-question route (P1a ROUTE_ACCEPTED)
ROUTE_BRANCH = "claude/helm-builder-continuation-20260923"
RS = "research/CAS_META_2_COMPOSITION/"
DESIGN = "records/helm_eval_design_20260923/"
ROUTE_CODE_PREFIXES = ("cncm/", RS + "cas_meta2/", RS + "eval_paths/")
_WHEELS = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
ROUTE_DATA_PINS = {                           # P1a's REQUIRED_INPUTS without its six Helm 2.0 checkpoints (sha256 raw)
    "records/typed_course_001/checks_002/public_course.json": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
    "records/typed_interface_001/checks_002/training_tokenizer.json": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c",
    "records/typed_matched_001/development_001/compact_development.json": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4",
    _WHEELS + "casformer_reference-0.1.0-py3-none-any.whl": "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
    _WHEELS + "cas_neural_cjt-0.2.0-py3-none-any.whl": "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9",
    RS + "eval_paths/fixtures/larger_question_fixtures_v0_1.json": "7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3"}
JOB_CODE = ("e1b_machine.py", "e1b_scorer.py", "custody_manifest.py", "machine_checks.py")
TEMPLATE = "job.sh.template"
FORBIDDEN_NAME_PARTS = ("sealed", "_eval.jsonl", "salt", "private_target", "protected", "transcript", "archive")
GATE_WORDS = {"matched_start": ("helm.matched-start-reading/0.1", "MATCHED_START_REPRODUCED"),
              "reproduction_reading": ("cncm.helm-unchanged-reproduction-reading/0.5",
                                       "STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED")}
TOUCHED_KINDS = ("updates", "development_evaluation", "dev_reading", "probe", "smoke", "fixture")
SEEDS = (20260917, 20260918, 20260919)
BUILDER_FILES = {"builder_sha256_lf": "hset2/hset2_build.py", "stage0_sha256_lf": "hset2/hset2_stage0_public.py",
                 "hset_worlds_sha256_lf": "hset1a/hset_worlds.py", "hset1a_build_sha256_lf": "hset1a/hset1a_build.py",
                 "hset1b_build_sha256_lf": "hset1a/hset1b_build.py",
                 "oracle_sha256_lf": "d1_acceptance/oracle_isomorphism.py"}


class Refused(SystemExit):
    pass


def refuse(code, detail):
    print("LAUNCH_REFUSED: %s: %s" % (code, detail), flush=True)
    raise Refused(2)


def lf_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


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


def listing(commit, under):
    pre, out = prefix(), []
    for entry in git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", pre + under).split(b"\0"):
        name = entry.decode("utf-8")
        if name.startswith(pre):
            out.append(name[len(pre):])
    return sorted(out)


class Blobs:
    """Exact stored bytes, one blob at a time, through ONE `git cat-file --batch`."""

    def __init__(self):
        self.pre = prefix()
        self.proc = subprocess.Popen(["git", "-C", str(PACKAGE), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)

    def read(self, commit, rel):
        self.proc.stdin.write(("%s:%s%s\n" % (commit, self.pre, rel)).encode("utf-8"))
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().decode("utf-8").rstrip("\n")
        if header.endswith(" missing") or len(header.split()) != 3:
            refuse("BLOB_MISSING", "%s at %s" % (rel, commit[:8]))
        data = self.proc.stdout.read(int(header.split()[2]))
        self.proc.stdout.read(1)
        return data

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def outside_git(folder):
    folder = pathlib.Path(folder).resolve()
    return not any((q / ".git").exists() for q in [folder] + list(folder.parents))


# ---- inputs ------------------------------------------------------------------------------------------------------
def committed_inputs(path):
    """The inputs file must be tracked and unmodified; its committed bytes are what is read."""
    target = pathlib.Path(path).resolve()
    if not target.is_file():
        refuse("INPUTS_NOT_YET_WRITTEN", "%s does not exist (it is written after training, E1a and P2)" % target.name)
    top = pathlib.Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    rel = target.relative_to(top).as_posix()
    if not git("ls-files", "--", str(target)).strip() or git("status", "--porcelain", "--", str(target)).strip():
        refuse("INPUTS_NOT_COMMITTED", rel)
    data = git("show", "HEAD:" + rel)
    return data, {"path": rel, "sha256": hashlib.sha256(data).hexdigest(),
                  "commit": git("log", "-1", "--format=%H", "--", str(target)).decode().strip()}


def check_ref(ref, what):
    if (not isinstance(ref, dict) or not isinstance(ref.get("commit"), str) or not isinstance(ref.get("path"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", str(ref.get("sha256")))):
        refuse("INPUTS_REF", what)
    commit = full_commit(ref["commit"])
    if not commit:
        refuse("INPUTS_COMMIT_MISSING", "%s: %s (fetch it first)" % (what, ref["commit"]))
    return dict(ref, commit=commit)


def validate_inputs(doc):
    """Shape of E1B_INPUTS.json. Returns [(bundle name, ref)] and the argument plan; refuses on any gap."""
    if not isinstance(doc, dict) or doc.get("schema") != INPUTS_SCHEMA:
        refuse("INPUTS_SCHEMA", doc.get("schema") if isinstance(doc, dict) else type(doc).__name__)
    if not full_commit(str(doc.get("hset2_build_commit"))):
        refuse("HSET2_COMMIT_MISSING", doc.get("hset2_build_commit"))
    entries = [("inputs/build_summary.json", check_ref(doc.get("build_summary"), "build_summary")),
               ("inputs/public_cells.json", check_ref(doc.get("public_cells"), "public_cells")),
               ("inputs/item2_reading.json", check_ref(doc.get("item2_reading"), "item2_reading")),
               ("inputs/matched_start.json", check_ref(doc.get("matched_start"), "matched_start")),
               ("inputs/reproduction_reading.json", check_ref(doc.get("reproduction_reading"), "reproduction_reading"))]
    optional = []
    if doc.get("inference_ruling") is not None:
        entries.append(("inputs/inference_ruling.json", check_ref(doc["inference_ruling"], "inference_ruling")))
        optional += ["--inference-ruling", "inputs/inference_ruling.json"]
    h1h2 = doc.get("h1h2") or {}
    for seed in SEEDS:
        if str(seed) in h1h2:
            name = "inputs/h1h2_%d.json" % seed
            entries.append((name, check_ref(h1h2[str(seed)], "h1h2 %d" % seed)))
            optional += ["--h1h2", "%d=%s" % (seed, name)]
    touched = doc.get("touched") or {}
    for kind in TOUCHED_KINDS:
        value = touched.get(kind)
        if isinstance(value, str) and value.startswith("NONE:") and len(value) > 5:
            optional += ["--touched", "%s=%s" % (kind, value)]
        elif isinstance(value, list) and value:
            for k, ref in enumerate(value):
                name = "inputs/touched/%s_%d.json" % (kind, k)
                entries.append((name, check_ref(ref, "touched %s %d" % (kind, k))))
                optional += ["--touched", "%s=%s" % (kind, name)]
        else:
            refuse("TOUCHED_KIND_NOT_DECLARED", "%s (design s8: every kind, or NONE:<reason>)" % kind)
    runs = doc.get("runs")
    if not isinstance(runs, list) or len(runs) != 6:
        refuse("RUNS", "six rows needed")
    run_rows = []
    for run in runs:
        ref = check_ref(run, "run %s" % run.get("run_id"))
        if not re.fullmatch(r"[A-Z][0-9]{2}", str(run.get("run_id"))) or any(
                k not in run for k in ("arm", "seed", "provenance", "switch")):
            refuse("RUN_ROW", run.get("run_id"))
        entries.append(("runs/%s_final.pt" % run["run_id"], ref))
        run_rows.append({k: run[k] for k in ("run_id", "arm", "seed", "provenance", "switch")}
                        | {"checkpoint": "%s_final.pt" % run["run_id"], "checkpoint_sha256": ref["sha256"]})
    return entries, optional, run_rows


def gate_records(blobs, entries):
    """The pre-launch reading gates, on the committed records' own bytes."""
    by_name = dict(entries)
    for key, (schema, word) in GATE_WORDS.items():
        ref = by_name["inputs/%s.json" % key]
        rec = json.loads(blobs.read(ref["commit"], ref["path"]))
        if rec.get("schema") != schema or rec.get("verdict") != word:
            refuse("GATE_NOT_ADMITTED", "%s reads %r (needs %s); the plan says stop and ask the owner"
                   % (key, rec.get("verdict"), word))
    ref = by_name["inputs/item2_reading.json"]
    if json.loads(blobs.read(ref["commit"], ref["path"])).get("schema") != "claude.item2-reading/0.3":
        refuse("ITEM2_NOT_PROBE_V0_3", "the corrected probe must have read (A5.1); any outcome is accepted")
    ref = by_name["inputs/build_summary.json"]
    summary = json.loads(blobs.read(ref["commit"], ref["path"]))
    if summary.get("mode") != "SEALED_BUILD" or summary.get("build_ok") is not True:
        refuse("SUMMARY_NOT_THE_SEALED_BUILD", "%r build_ok=%r" % (summary.get("mode"), summary.get("build_ok")))
    return summary


def check_builder(blobs, commit, summary):
    ident = summary.get("identity") or {}
    for field, rel in BUILDER_FILES.items():
        got = lf_sha(blobs.read(commit, DESIGN + rel))
        if got != ident.get(field):
            refuse("BUILDER_NOT_THE_SEALED_BUILDS", "%s at %s: %s..., summary %s" % (rel, commit[:8], got[:12],
                                                                                   str(ident.get(field))[:12]))


def custody_refusals(names):
    return [n for n in names if any(part in n.lower() for part in FORBIDDEN_NAME_PARTS)
            or ".." in n.split("/") or n.startswith("/") or "__pycache__" in n or n.endswith(".pyc")]


# ---- the bundle --------------------------------------------------------------------------------------------------
def job_files():
    rels = [(HERE / n).relative_to(PACKAGE).as_posix() for n in JOB_CODE + (TEMPLATE,)]
    commit = git("log", "-1", "--format=%H", "--", *rels).decode().strip() or None
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *rels).decode().strip()
    return rels, commit, dirty


def plan_entries(blobs, doc, entries):
    """[(bundle name, commit, package path, pinned raw sha256 or None)] for everything but generated files."""
    route = full_commit(ROUTE_COMMIT)
    if route != ROUTE_COMMIT:
        refuse("ROUTE_COMMIT_MISSING", "%s (git fetch origin %s)" % (ROUTE_COMMIT, ROUTE_BRANCH))
    out = []
    for rel in listing(ROUTE_COMMIT, ""):
        if (rel.endswith(".py") and rel.startswith(ROUTE_CODE_PREFIXES)) or rel in ROUTE_DATA_PINS:
            out.append(("tree/" + rel, ROUTE_COMMIT, rel, ROUTE_DATA_PINS.get(rel)))
    missing = sorted(set(ROUTE_DATA_PINS) - {e[2] for e in out})
    if missing:
        refuse("ROUTE_DATA_MISSING", missing)
    hc = full_commit(doc["hset2_build_commit"])
    for rel in BUILDER_FILES.values():                  # exactly the six modules the scorer fingerprints; nothing else
        out.append(("hset2code/" + rel, hc, DESIGN + rel, None))
    for name, ref in entries:
        out.append((name, ref["commit"], ref["path"], ref["sha256"]))
    return sorted(out)


def write_bundle(entries, generated, blobs, dest):
    files = {}
    with open(dest, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=6, mtime=0) as zipped, \
            tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = len(data), 0, 0o644, 0, 0, "", ""
            tar.addfile(info, io.BytesIO(data))
        for name, commit, rel, pin in entries:
            data = blobs.read(commit, rel)
            if pin is not None and hashlib.sha256(data).hexdigest() != pin:
                refuse("PIN_MISMATCH", "%s (%s...)" % (rel, hashlib.sha256(data).hexdigest()[:12]))
            files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "from_commit": commit}
            add(name, data)
        for name in sorted(generated):
            files[name] = {"sha256": hashlib.sha256(generated[name]).hexdigest(), "bytes": len(generated[name]),
                           "from_commit": "generated"}
            add(name, generated[name])
        add("anchors.json", json.dumps({"schema": "claude.e1b-anchors/0.1", "files": files}, indent=1,
                                       sort_keys=True).encode())
    digest = hashlib.sha256()
    with open(dest, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return files, digest.hexdigest(), pathlib.Path(dest).stat().st_size


# ---- money and the machine script ---------------------------------------------------------------------------------
def worst_case_usd(minutes=CLIENT_DEADLINE_MINUTES):
    return (PRICE_PER_HOUR + ADDRESS_PER_HOUR + ROOT_GB * GB_MONTH_USD / 730) * minutes / 60.0


def render(template, urls, bundle_sha, sealed_sha):
    values = {"__INSTANCE_TYPE__": INSTANCE_TYPE, "__MAX_SECONDS__": str(MAX_SECONDS),
              "__MAX_MINUTES__": str(OS_POWER_OFF_MINUTES), "__BUNDLE_URL__": urls["bundle"],
              "__SEALED_INPUT_URL__": urls["sealed_input"], "__RESULTS_URL__": urls["results"],
              "__SEALED_RESULTS_URL__": urls["sealed_results"], "__PROGRESS_URL__": urls["progress"],
              "__BUNDLE_SHA256__": bundle_sha, "__SEALED_SHA256__": sealed_sha, "__UV_VERSION__": UV_VERSION,
              "__PYTHON_VERSION__": PYTHON_VERSION, "__TORCH_VERSION__": TORCH_VERSION, "__TORCH_LOCAL__": TORCH_LOCAL,
              "__NUMPY_VERSION__": NUMPY_VERSION, "__PROCESSES__": str(PROCESSES), "__WALL_SECONDS__": str(WALL_SECONDS)}
    script = template
    for key, value in values.items():
        script = script.replace(key, value)
    left = re.findall(r"__[A-Z][A-Z0-9_]*__", script)
    if left:
        raise AssertionError("unfilled placeholders: %s" % sorted(set(left)))
    if len(script.encode("utf-8")) >= USER_DATA_LIMIT:
        raise AssertionError("the machine script is over the %d-byte user-data limit" % USER_DATA_LIMIT)
    return script


def user_data_fits(template):
    """(bool, detail): the machine script with five LINK_BYTES_ASSUMED-byte links (the variable readout arguments
    travel in the bundle as e1b/readout_args.json, so they never count against the limit)."""
    links = {k: "https://" + "L" * (LINK_BYTES_ASSUMED - 8) for k in ("bundle", "sealed_input", "results",
                                                                     "sealed_results", "progress")}
    try:
        script = render(template, links, "0" * 64, "0" * 64)
    except AssertionError as error:
        return False, str(error)
    return True, "%d bytes with %d-byte links" % (len(script.encode("utf-8")), LINK_BYTES_ASSUMED)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--inputs", default=str(HERE / "E1B_INPUTS.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sealed-s3-key", default=None, help="real launch: P2's sealed tarball key in the private bucket")
    parser.add_argument("--sealed-sha256", default=None, help="real launch: that tarball's sha256 (from the archive)")
    parser.add_argument("--bundle-dir", default=None)
    args = parser.parse_args(argv)
    worst = worst_case_usd()
    if worst > COST_CAP_USD:
        refuse("OVER_CAP", "worst case %.4f > cap %.2f" % (worst, COST_CAP_USD))
    fits, detail = user_data_fits((HERE / TEMPLATE).read_text(encoding="utf-8").replace("\r\n", "\n"))
    if not fits:
        refuse("USER_DATA_LIMIT", detail)
    record_path = HERE / "launch_record.json"
    if not args.dry_run:
        if record_path.exists():
            refuse("ALREADY_LAUNCHED", "launch_record.json exists: one approval, one machine")
        if not (args.sealed_s3_key and re.fullmatch(r"[0-9a-f]{64}", args.sealed_sha256 or "")):
            refuse("SEALED_INPUT_REQUIRED", "give --sealed-s3-key and --sealed-sha256 (the P2 tarball; never in git)")
    data, inputs_meta = committed_inputs(args.inputs)
    doc = json.loads(data)
    entries, optional, run_rows = validate_inputs(doc)
    blobs = Blobs()
    try:
        summary = gate_records(blobs, entries)
        hset2_commit = full_commit(doc["hset2_build_commit"])
        check_builder(blobs, hset2_commit, summary)
        rels, job_commit, dirty = job_files()
        if (dirty or not job_commit) and not args.dry_run:
            refuse("JOB_FILES_NOT_COMMITTED", dirty or rels)
        planned = plan_entries(blobs, doc, entries)
        generated = {"e1b/" + n: (blobs.read(job_commit, (HERE / n).relative_to(PACKAGE).as_posix())
                                  if job_commit and not dirty else (HERE / n).read_bytes().replace(b"\r\n", b"\n"))
                     for n in JOB_CODE}
        generated["e1b/readout_args.json"] = json.dumps(optional, indent=1).encode()
        generated["runs/runs.json"] = json.dumps({"schema": "claude.e1b-runs/0.1", "runs": run_rows}, indent=1,
                                                 sort_keys=True).encode()
        template = (blobs.read(job_commit, (HERE / TEMPLATE).relative_to(PACKAGE).as_posix()).decode()
                    if job_commit and not dirty else (HERE / TEMPLATE).read_text(encoding="utf-8").replace("\r\n", "\n"))
        names = [e[0] for e in planned] + sorted(generated) + ["anchors.json"]
        bad = custody_refusals(names)
        if bad:
            refuse("CUSTODY", "%d bundle names break custody: %s" % (len(bad), bad[:8]))
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        folder = pathlib.Path(args.bundle_dir) if args.bundle_dir else pathlib.Path(tempfile.gettempdir()) / ("e1b_" + stamp)
        if folder.exists() or not outside_git(folder.parent):
            refuse("BUNDLE_DIR", "%s must be a NEW folder outside every git work tree" % folder)
        folder.mkdir(parents=True)
        files, bundle_sha, bundle_bytes = write_bundle(planned, generated, blobs, folder / "bundle.tar.gz")
    finally:
        blobs.close()
    keys = {k: "helm-integration/e1b-%s/%s" % (stamp, v) for k, v in
            (("bundle", "bundle.tar.gz"), ("results", "results.tar.gz"), ("sealed_results", "sealed_results.tar.gz"),
             ("progress", "progress.log"))}
    print("CUSTODY: PASS (%d names; forbidden words %s; the sealed P2 tarball is not in the bundle)"
          % (len(names), list(FORBIDDEN_NAME_PARTS)))
    print("PLAN  ONE %s %s, $%.3f/h; timer %d min, OS power-off %d min, client deadline %d min; worst case $%.4f <= cap "
          "$%.2f (+ $%.2f allowance); bundle %d files, %.1f MB, sha256 %s; inputs %s @ %s"
          % (INSTANCE_TYPE, REGION, PRICE_PER_HOUR, MAX_SECONDS // 60, OS_POWER_OFF_MINUTES, CLIENT_DEADLINE_MINUTES,
             worst, COST_CAP_USD, ALLOWANCE_USD, len(files) + 1, bundle_bytes / 1e6, bundle_sha, inputs_meta["path"],
             inputs_meta["commit"][:8]))
    summary_out = {"schema": "claude.e1b-bundle/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED", "inputs": inputs_meta,
                   "bundle_sha256": bundle_sha, "bundle_bytes": bundle_bytes, "files": len(files) + 1,
                   "route_commit": ROUTE_COMMIT, "hset2_build_commit": hset2_commit, "job_files_commit": job_commit,
                   "job_files_from_working_copy": bool(dirty or not job_commit),
                   "worst_case_usd_at_client_deadline": round(worst, 4), "cost_cap_usd": COST_CAP_USD,
                   "allowance_usd": ALLOWANCE_USD}
    if args.dry_run:
        fake = {k: "https://DRY-RUN.invalid/%s" % k for k in ("bundle", "sealed_input", "results", "sealed_results",
                                                               "progress")}
        script = render(template, fake, bundle_sha, "0" * 64)
        (folder / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        (folder / "dry_run_record.json").write_text(json.dumps(dict(summary_out, dry_run=True), indent=1, sort_keys=True),
                                                    encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded, nothing launched, no AWS call. Files in %s" % folder)
        return 0
    return launch(stamp, keys, folder, bundle_sha, template, summary_out, record_path, args)


def launch(stamp, keys, folder, bundle_sha, template, summary_out, record_path, args):
    """The coordinator's launch: one attempt, one zone, no retry."""
    import boto3
    ec2 = boto3.client("ec2", region_name=REGION)
    live = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": GPU_FAMILIES},
                                           {"Name": "instance-state-name", "Values": ["pending", "running", "stopping"]}])
    if live["Reservations"]:
        refuse("GPU_MACHINE_RUNNING", "the 8-vCPU GPU quota is in use (one GPU machine at a time)")
    image = ec2.describe_images(ImageIds=[PINNED_AMI])["Images"][0]
    s3 = boto3.client("s3", region_name=REGION)
    s3.head_object(Bucket=BUCKET, Key=args.sealed_s3_key)                  # the sealed input exists; never downloaded here
    s3.upload_file(str(folder / "bundle.tar.gz"), BUCKET, keys["bundle"])
    urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=LINK_SECONDS),
            "sealed_input": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": args.sealed_s3_key},
                                                      ExpiresIn=LINK_SECONDS)}
    for k in ("results", "sealed_results", "progress"):
        urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=LINK_SECONDS)
    script = render(template, urls, bundle_sha, args.sealed_sha256)
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = sorted((s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
                      if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]), key=lambda s: s["AvailabilityZone"])
    if not subnets:
        refuse("NO_SUBNET", INSTANCE_TYPE)
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]},
                                                  {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        refuse("OPEN_SECURITY_GROUP", "the default security group allows inbound traffic from an address range")
    tags = [{"Key": "Name", "Value": "e1b-readout-%s" % stamp},
            {"Key": "Purpose", "Value": "HSET-2 sealed TEST readout E1b (readout item 10), CLAUDE_BUILT_CLAUDE_CHECKED"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched = ec2.run_instances(
        ImageId=PINNED_AMI, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnets[0]["SubnetId"],
        SecurityGroupIds=[group["GroupId"]], InstanceInitiatedShutdownBehavior="terminate", UserData=script,
        ClientToken="e1b-%s" % stamp, MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
        BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"],
                              "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
    instance = launched["Instances"][0]
    print("LAUNCHED INSTANCE ID: %s  (printed FIRST, before anything else can fail)" % instance["InstanceId"], flush=True)
    sealed_destination = ARCHIVE / ("e1b_sealed_%s" % stamp[:8]) / ("run_" + stamp)
    record = dict(summary_out, schema="claude.e1b-launch/0.1", dry_run=False,
                  approved={"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                            "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": COST_CAP_USD},
                  instance_id=instance["InstanceId"], launched_utc=instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                  availability_zone=subnets[0]["AvailabilityZone"], ami=PINNED_AMI, ami_name=image.get("Name"),
                  in_instance_timer_seconds=MAX_SECONDS, os_power_off_minutes=OS_POWER_OFF_MINUTES,
                  client_deadline_minutes=CLIENT_DEADLINE_MINUTES, bucket=BUCKET, keys=keys, root_volume_gb=ROOT_GB,
                  sealed_input={"s3_key": args.sealed_s3_key, "sha256": "RECORDED_IN_THE_ARCHIVE_ONLY"},
                  sealed_destination=str(sealed_destination),
                  links_stored="no -- time-limited links are never written to disk")
    sealed_destination.mkdir(parents=True, exist_ok=False)
    (sealed_destination / "launch_private.json").write_text(json.dumps(
        {"instance_id": instance["InstanceId"], "sealed_input_s3_key": args.sealed_s3_key,
         "sealed_input_sha256": args.sealed_sha256}, indent=1), encoding="utf-8")
    record_path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print("LAUNCHED %s. It destroys itself within %d minutes. Record: %s" % (instance["InstanceId"], OS_POWER_OFF_MINUTES,
                                                                            record_path.name), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as stop:
        sys.exit(stop.code)
