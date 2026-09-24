"""Launch the HELM-LARGER-QUESTION-PATH-1 T4 check job on ONE AWS T4 machine. Built, NOT launched, by its builder.

Label: CLAUDE_BUILT_CLAUDE_CHECKED. Modelled on `../analogy_repair_t4_job/launch.py` and its RUN_LOG lesson (attempt 1
lost its verdicts because a file read beside a tool was not bundled).

WHAT RUNS ON THE MACHINE. `research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py` at SOURCE_COMMIT
(branch `claude/helm-builder-continuation-20260923`): a smoke stage (job.sh), then the script's own timing preflight
(stage 1, inside the script, before any check), then its checks d, c, b, a (stage 2). Forward passes only.

THE BUNDLE is built from GIT OBJECTS at the ONE pinned commit SOURCE_COMMIT, never from working files:
  * every file the pinned script's own `--list-inputs` names: the 12 REQUIRED_INPUTS (course, tokenizer, development
    file, both wheels, the six Helm 2.0 checkpoints, the fixture file), each checked for bytes and sha256; every `*.py`
    of the two source trees; the five `eval_paths` files;
  * `identity.json` (commits, per-file hashes).
  The paths keep the CNCM-root layout the script expects (`PACKAGE = HERE.parents[2]`).

REFUSALS BEFORE ANY SPEND (dry run and launch alike): the pinned commit is missing or not on the pushed branch; the
`--list-inputs` output is not the expected schema; any input differs from its pin; the six checkpoints differ from
the analogy T4 job's; a bundled name contains "sealed" or ends in "_eval.jsonl"; a protected source file differs from
the scope module's pins; a bundled tool reads a file beside itself (`HERE / "..."`) that is not bundled; a project
import (`cncm`, `cas_meta2`, `eval_paths`, `research.`) in any bundled file does not resolve inside the bundle; the
script's static import closure reaches a module that is neither bundled, standard library, torch, numpy nor one of
the two wheels; the worst case is not below the ceiling; the machine script is over the user-data limit.

    python -B launch.py --dry-run [--instance-type g4dn.2xlarge|g4dn.xlarge]
    python -B launch.py [--instance-type ...]        (the runner only; one approval, one machine)

The dry run makes ONE read-only AWS call (`ec2.describe_images` for the pinned image). It uploads nothing, creates
no link and launches nothing. It writes `dry_run_machine_script.sh` and `dry_run_record.json` next to this file.
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

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
REPO_PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
# On-demand Linux prices in us-west-2 (USD per hour). g4dn.2xlarge is the machine the T4 reference history was
# recorded on (check a compares logit bits with it), so it is the default; g4dn.xlarge (4 vCPU, 16 GiB, the same T4)
# is allowed for a cheaper run.
PRICES = {"g4dn.2xlarge": 0.752, "g4dn.xlarge": 0.526}
DEFAULT_INSTANCE = "g4dn.2xlarge"
PUBLIC_IPV4_PER_HOUR, GP3_PER_GB_MONTH, HOURS_PER_MONTH = 0.005, 0.08, 730
PINNED_AMI = "ami-07d69ce07bfe5628f"          # the T4 reference image (analogy job, both attempts). No substitute.
ROOT_GB = 100
MAX_SECONDS = 120 * 60                         # in-machine timer; the OS powers off 3 minutes later
CLIENT_DEADLINE_MINUTES = 130                  # watch.py terminates the machine here
DOLLAR_CEILING = 3.00
USER_DATA_LIMIT, LINK_BYTES_ASSUMED = 16000, 2048
PYTHON_VERSION, TORCH_VERSION, TORCH_LOCAL, NUMPY_VERSION = "3.14.7", "2.11.0", "2.11.0+cu128", "2.5.2"
SOURCE_BRANCH = "claude/helm-builder-continuation-20260923"
SOURCE_COMMIT = "e05889eec0f800a9a17b0c39a8d8d37f544b43bf"   # builder revision 2 of the larger-question path
SCRIPT = "research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py"
SCOPE = "research/CAS_META_2_COMPOSITION/eval_paths/larger_question_scope.py"
TYPED = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/"
EXPECTED_SCHEMA = "claude.helm-larger-question-t4-checks/0.2"
ANALOGY_RECORD = HERE.parent / "analogy_repair_t4_job" / "launch_record.json"
FORBIDDEN_NAME = re.compile(r"sealed|_eval\.jsonl$", re.IGNORECASE)
# sys.path on the machine (the script's Context): the CNCM root and research/CAS_META_2_COMPOSITION.
IMPORT_ROOTS = {"cncm": "", "cas_meta2": "research/CAS_META_2_COMPOSITION/",
                "eval_paths": "research/CAS_META_2_COMPOSITION/", "research": ""}
KNOWN_EXTERNAL = {"torch", "numpy", "casformer", "cas_cjt"}
GPU_FAMILIES = ["g4dn.*", "g4ad.*", "g5.*", "g5g.*", "g6.*", "g6e.*", "gr6.*", "p3.*", "p3dn.*", "p4d.*", "p4de.*",
                "p5.*", "p5e.*", "p5en.*"]
JOB_FILES = ("launch.py", "job.sh.template", "watch.py", "read_results.py", "JOB_LIMITS.md", "README.md")


def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True).stdout


def prefix():
    pre = git("rev-parse", "--show-prefix").decode().strip()
    if pre.rstrip("/") != REPO_PREFIX:
        raise SystemExit("BUNDLE_REFUSED: this folder is not under %s" % REPO_PREFIX)
    return pre


def read_blobs(commit, rels):
    pre = prefix()
    request = "".join("%s:%s%s\n" % (commit, pre, r) for r in rels).encode("utf-8")
    raw, out, pos = git("cat-file", "--batch", data=request), {}, 0
    for r in rels:
        end = raw.index(b"\n", pos)
        header = raw[pos:end].decode()
        if header.endswith("missing"):
            raise SystemExit("BUNDLE_REFUSED: %s missing at %s" % (r, commit[:8]))
        size = int(header.split()[2])
        out[r] = raw[end + 1:end + 1 + size]
        pos = end + 1 + size + 1
    return out


def tree_py(commit, tree):
    pre = prefix()
    names = git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", pre + tree + "/").decode("utf-8")
    return sorted(n[len(pre):] for n in names.split("\0") if n.startswith(pre) and n.endswith(".py"))


def verify_source_commit():
    try:
        found = git("rev-parse", "--verify", "--quiet", SOURCE_COMMIT + "^{commit}").decode().strip()
    except subprocess.CalledProcessError:
        found = None
    if found != SOURCE_COMMIT:
        raise SystemExit("BUNDLE_REFUSED: source commit %s not found (git fetch origin %s)" % (SOURCE_COMMIT, SOURCE_BRANCH))
    # Pushed? Ask the remote for the branch tip (read-only), then check ancestry locally.
    tip = git("ls-remote", "origin", "refs/heads/" + SOURCE_BRANCH).decode().split()
    try:
        git("merge-base", "--is-ancestor", SOURCE_COMMIT, tip[0])
    except (subprocess.CalledProcessError, IndexError):
        raise SystemExit("BUNDLE_REFUSED: %s is not on the pushed %s (remote tip %s; fetch it first)"
                         % (SOURCE_COMMIT[:8], SOURCE_BRANCH, tip[:1]))
    return tip[0]


def list_inputs(script_bytes):
    """Run the PINNED script's own `--list-inputs` (stdlib only: it reads no file and imports no project code)."""
    with tempfile.TemporaryDirectory(prefix="lq_t4_list_inputs_") as folder:
        path = pathlib.Path(folder) / "t4_larger_question_checks.py"
        path.write_bytes(script_bytes)
        done = subprocess.run([sys.executable, "-I", "-B", str(path), "--list-inputs"], capture_output=True, timeout=60)
    if done.returncode != 0:
        raise SystemExit("BUNDLE_REFUSED: --list-inputs exit %d: %s" % (done.returncode, done.stderr[-400:]))
    listed = json.loads(done.stdout)
    if listed.get("schema") != EXPECTED_SCHEMA or listed.get("root") != REPO_PREFIX:
        raise SystemExit("BUNDLE_REFUSED: --list-inputs schema/root %r %r" % (listed.get("schema"), listed.get("root")))
    return listed


def _literal_dict(tree, name, env=None):
    """A module-level dict literal; `Name + "text"` keys are resolved from `env` (for `_TYPED + "x.py"`)."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", None) == name:
            if env is None:
                return ast.literal_eval(node.value)
            out = {}
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.BinOp) and isinstance(key.left, ast.Name) and isinstance(key.op, ast.Add):
                    key_text = env[key.left.id] + ast.literal_eval(key.right)
                else:
                    key_text = ast.literal_eval(key)
                out[key_text] = ast.literal_eval(value)
            return out
    raise SystemExit("BUNDLE_REFUSED: %s not found as a literal" % name)


def lf_sha256(raw):
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def check_siblings(files, tools):
    """Every `HERE / "a" / "b"` a bundled tool reads must be in the bundle (a file, or a folder of bundled files)."""
    names, checked = set(files), []
    folders = {str(parent) for p in files for parent in pathlib.PurePosixPath(p).parents}
    for tool in tools:
        text = files[tool].decode("utf-8")
        for chain in re.findall(r'HERE((?:\s*/\s*"[^"]+")+)', text):
            parts = re.findall(r'"([^"]+)"', chain)
            target = str(pathlib.PurePosixPath(tool).parent.joinpath(*parts))
            if target not in names and target not in folders:
                raise SystemExit("BUNDLE_REFUSED: %s reads %s beside itself, which is not bundled" % (tool, target))
            checked.append(target)
    return sorted(set(checked))


def _top_level_names(tree):
    names, stack = set(), list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                names.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split(".")[0] for a in node.names)
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            stack.extend(node.body + getattr(node, "orelse", []) + getattr(node, "finalbody", [])
                         + [s for h in getattr(node, "handlers", []) for s in h.body])
    return names


def check_imports(files):
    """Static import check over the bundle (names only; nothing is imported or run).

    1. Every project import (`cncm`, `cas_meta2`, `eval_paths`, and `research.` namespace imports) in ANY bundled file
       must resolve inside the bundle, down to the imported name.
    2. The import CLOSURE of the script (module-level and function-level imports, followed through the bundle) may
       reach only bundled modules, the standard library, torch, numpy and the two wheels' modules.
    """
    modules, trees = {}, {}
    for path in files:
        if not path.endswith(".py"):
            continue
        for top, root in IMPORT_ROOTS.items():
            if path.startswith(root + top + "/"):
                dotted = path[len(root):-3].replace("/", ".")
                is_package = dotted.endswith(".__init__")
                modules[dotted[:-9] if is_package else dotted] = (path, is_package)
                parts = dotted.split(".")[:-1]
                for i in range(1, len(parts) + 1):          # folders without __init__.py: namespace packages
                    modules.setdefault(".".join(parts[:i]), (None, True))
    unresolved, external, count, edges = [], {}, 0, {}
    for module, (path, is_package) in modules.items():
        if path is None:
            continue
        tree = trees.setdefault(path, ast.parse(files[path], path))
        package = module if is_package else module.rpartition(".")[0]
        reached = edges.setdefault(module, set())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = [(a.name, None) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")
                    base = base[:len(base) - (node.level - 1)] if node.level - 1 <= len(base) else None
                    if not base:
                        unresolved.append("%s: relative import beyond the top" % path)
                        continue
                    target = ".".join(base) + ("." + node.module if node.module else "")
                else:
                    target = node.module
                targets = [(target, [a.name for a in node.names])]
            else:
                continue
            for target, names in targets:
                top = target.split(".")[0]
                if top not in IMPORT_ROOTS:
                    if top not in sys.stdlib_module_names and top != "__future__":
                        reached.add("external:" + top)
                        if top not in KNOWN_EXTERNAL:
                            external[top] = external.get(top, 0) + 1
                    continue
                count += 1
                if target not in modules:
                    unresolved.append("%s: %s" % (path, target))
                    continue
                parts = target.split(".")
                reached.update(".".join(parts[:i]) for i in range(1, len(parts) + 1))
                for name in names or ():
                    if name == "*":
                        continue
                    if target + "." + name in modules:
                        reached.add(target + "." + name)
                        continue
                    owner = modules[target][0]
                    if owner is None or name not in _top_level_names(trees.setdefault(owner, ast.parse(files[owner], owner))):
                        unresolved.append("%s: %s.%s" % (path, target, name))
    if unresolved:
        raise SystemExit("BUNDLE_REFUSED: project imports that do not resolve in the bundle: %s" % unresolved[:20])
    start = SCRIPT[len("research/CAS_META_2_COMPOSITION/"):-3].replace("/", ".")
    closure, queue, outside = set(), [start], set()
    while queue:
        module = queue.pop()
        if module in closure:
            continue
        closure.add(module)
        for item in edges.get(module, ()):
            if item.startswith("external:"):
                if item[9:] not in KNOWN_EXTERNAL:
                    outside.add("%s <- %s" % (item[9:], module))
            else:
                queue.append(item)
    if outside:
        raise SystemExit("BUNDLE_REFUSED: the script's import closure reaches modules that are not bundled: %s"
                         % sorted(outside))
    return {"project_imports_checked": count, "modules": len(modules), "script_import_closure_modules": len(closure),
            "script_import_closure_external": sorted({i[9:] for m in closure for i in edges.get(m, ())
                                                      if i.startswith("external:")}),
            "other_top_level_imports_not_bundled": dict(sorted(external.items()))}


def assemble():
    remote_tip = verify_source_commit()
    script = read_blobs(SOURCE_COMMIT, [SCRIPT])[SCRIPT]
    listed = list_inputs(script)
    required = {row["path"]: row for row in listed["required_inputs"]}
    trees = [row["path"] for row in listed["required_source_trees"]]
    if [row["pattern"] for row in listed["required_source_trees"]] != ["*.py"] * len(trees):
        raise SystemExit("BUNDLE_REFUSED: unexpected source-tree pattern")
    paths = sorted(set(required) | set(listed["eval_paths_files"]) | {p for t in trees for p in tree_py(SOURCE_COMMIT, t)})
    forbidden = [p for p in paths if FORBIDDEN_NAME.search(p)]
    if forbidden:
        raise SystemExit("BUNDLE_REFUSED: forbidden names in the bundle list: %s" % forbidden)
    files = read_blobs(SOURCE_COMMIT, paths)
    for path, row in required.items():
        if len(files[path]) != row["bytes"] or hashlib.sha256(files[path]).hexdigest() != row["sha256"]:
            raise SystemExit("BUNDLE_REFUSED: %s differs from its --list-inputs pin" % path)
    for tree in trees:
        if not any(p.startswith(tree + "/") for p in files):
            raise SystemExit("BUNDLE_REFUSED: source tree %s is empty at %s" % (tree, SOURCE_COMMIT[:8]))
    # The six checkpoints are the analogy T4 job's (the history check a compares with).
    analogy = json.loads(ANALOGY_RECORD.read_text(encoding="utf-8"))["identity"]["checkpoint_sha256"]
    checkpoints = {p: hashlib.sha256(b).hexdigest() for p, b in files.items() if p.endswith(".pt")}
    if checkpoints != analogy:
        raise SystemExit("BUNDLE_REFUSED: the checkpoints differ from the analogy T4 job's six")
    # The wheels the script lists as installed modules must be the two wheel files in the bundle.
    wheels = sorted(p for p in required if p.endswith(".whl"))
    expected = sorted("%s-%s-py3-none-any.whl" % (v["distribution"], v["version"])
                      for v in listed["installed_wheel_modules"].values())
    if [pathlib.PurePosixPath(p).name for p in wheels] != expected:
        raise SystemExit("BUNDLE_REFUSED: wheel files %s do not match the listed modules %s" % (wheels, expected))
    # Protected source: the scope module's pins, and check a's five reference files, before any spend.
    scope_tree = ast.parse(files[SCOPE], SCOPE)
    pins = _literal_dict(scope_tree, "PROTECTED_SOURCE_LF_SHA256")
    drift = sorted(n for n, pin in pins.items() if lf_sha256(files[TYPED + n]) != pin)
    script_tree = ast.parse(script, SCRIPT)
    reference = _literal_dict(script_tree, "T4_REFERENCE_SOURCE_LF_SHA256", env={"_TYPED": TYPED})
    drift += sorted(n for n, pin in reference.items() if lf_sha256(files[n]) != pin)
    if drift:
        raise SystemExit("BUNDLE_REFUSED: protected source differs from its pins: %s" % drift)
    tools = [p for p in listed["eval_paths_files"] if p.endswith(".py")]
    siblings = check_siblings(files, tools)
    imports = check_imports(files)
    identity = {"schema": "claude.larger-question-t4-bundle-identity/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
                "source_commit": SOURCE_COMMIT, "source_branch": SOURCE_BRANCH, "script": SCRIPT,
                "list_inputs_sha256": hashlib.sha256(json.dumps(listed, sort_keys=True).encode()).hexdigest(),
                "required_inputs_sha256": {p: required[p]["sha256"] for p in sorted(required)},
                "eval_paths_lf_sha256": {p: lf_sha256(files[p]) for p in listed["eval_paths_files"]},
                "source_trees": {t: {"py_files": sum(p.startswith(t + "/") for p in files),
                                     "digest": hashlib.sha256("\n".join(
                                         "%s %s" % (p, hashlib.sha256(files[p]).hexdigest())
                                         for p in sorted(files) if p.startswith(t + "/")).encode()).hexdigest()}
                                 for t in trees},
                "protected_source_lf_sha256_checked": sorted(pins), "t4_reference_source_checked": sorted(reference),
                "sibling_reads_checked": siblings, "imports": imports}
    # identity.json depends on SOURCE_COMMIT only, so the bundle's sha256 is reproducible from it. The job-branch
    # commit and the remote tip go into the dry-run and launch records instead.
    files["identity.json"] = json.dumps(identity, indent=1, sort_keys=True).encode()
    provenance = {"job_commit": git("rev-parse", "HEAD").decode().strip(), "source_branch_remote_tip": remote_tip}
    return files, identity, provenance


def build_bundle(files):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as zipped, \
            tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(files):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(files[name]), 0, 0o644
            tar.addfile(info, io.BytesIO(files[name]))
    body = buffer.getvalue()
    return body, hashlib.sha256(body).hexdigest()


def fill(template, urls, bundle_sha, instance_type):
    script = template
    for key, value in {"__MAX_SECONDS__": str(MAX_SECONDS), "__MAX_MINUTES__": str(MAX_SECONDS // 60 + 3),
                       "__BUNDLE_URL__": urls["bundle"], "__RESULTS_URL__": urls["results"],
                       "__PROGRESS_URL__": urls["progress"], "__ROWS_URL__": urls["rows"],
                       "__BUNDLE_SHA256__": bundle_sha, "__PYTHON_VERSION__": PYTHON_VERSION,
                       "__TORCH_VERSION__": TORCH_VERSION, "__TORCH_LOCAL__": TORCH_LOCAL,
                       "__NUMPY_VERSION__": NUMPY_VERSION, "__INSTANCE_TYPE__": instance_type,
                       "__SCRIPT__": SCRIPT}.items():
        script = script.replace(key, value)
    left = re.findall(r"__[A-Z][A-Z0-9_]*__", script)
    if left:
        raise SystemExit("an unfilled placeholder remains: %s" % sorted(set(left)))
    return script


def worst_case(instance_type):
    per_hour = PRICES[instance_type] + PUBLIC_IPV4_PER_HOUR + ROOT_GB * GP3_PER_GB_MONTH / HOURS_PER_MONTH
    return per_hour, per_hour * CLIENT_DEADLINE_MINUTES / 60.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--instance-type", choices=sorted(PRICES), default=DEFAULT_INSTANCE)
    args = parser.parse_args()
    files, identity, provenance = assemble()
    body, bundle_sha = build_bundle(files)
    print("bundle: %d files, %d bytes (%.2f MB), sha256 %s; source %s; job commit %s"
          % (len(files), len(body), len(body) / 1e6, bundle_sha, SOURCE_COMMIT[:8], provenance["job_commit"][:8]))
    print("checked: %d inputs by --list-inputs; %d .py in the source trees; %d project imports resolved; sibling reads %s"
          % (len(identity["required_inputs_sha256"]), sum(t["py_files"] for t in identity["source_trees"].values()),
             identity["imports"]["project_imports_checked"], identity["sibling_reads_checked"]))
    print("script import closure: %d modules; outside the bundle only %s"
          % (identity["imports"]["script_import_closure_modules"], identity["imports"]["script_import_closure_external"]))
    print("other files' imports outside the bundle and stdlib (information): %s"
          % identity["imports"]["other_top_level_imports_not_bundled"])
    per_hour, worst = worst_case(args.instance_type)
    arithmetic = ("%s: (%.3f machine + %.3f public address + %d GB x %.2f / %d disk) = %.6f USD/hour; x %d/60 hours "
                  "(client deadline) = %.4f USD; ceiling %.2f"
                  % (args.instance_type, PRICES[args.instance_type], PUBLIC_IPV4_PER_HOUR, ROOT_GB, GP3_PER_GB_MONTH,
                     HOURS_PER_MONTH, per_hour, CLIENT_DEADLINE_MINUTES, worst, DOLLAR_CEILING))
    print("worst case: " + arithmetic)
    if not worst < DOLLAR_CEILING:
        raise SystemExit("LAUNCH_REFUSED: worst case %.4f is not below the ceiling" % worst)
    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    long_links = {k: "https://" + "L" * (LINK_BYTES_ASSUMED - 8) for k in ("bundle", "results", "progress", "rows")}
    if len(fill(template, long_links, bundle_sha, args.instance_type).encode("utf-8")) >= USER_DATA_LIMIT:
        raise SystemExit("LAUNCH_REFUSED: the machine script would exceed the user-data limit with %d-byte links"
                         % LINK_BYTES_ASSUMED)
    import boto3
    ec2 = boto3.client("ec2", region_name=REGION)
    try:
        image = ec2.describe_images(ImageIds=[PINNED_AMI])["Images"][0]
        image_note = "pinned reference image available"
    except Exception as error:  # noqa: BLE001 -- no substitute: check a compares bits with this image's history
        image, image_note = None, "PINNED_IMAGE_UNAVAILABLE (%s): a real launch refuses" % type(error).__name__
    print("image: %s (%s) %s" % (PINNED_AMI, image and image.get("Name"), image_note))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key_prefix = "helm-integration/larger-question-t4-%s/" % stamp
    keys = {"bundle": key_prefix + "bundle.tar.gz", "results": key_prefix + "results.tar.gz",
            "progress": key_prefix + "progress.log", "rows": key_prefix + "rows_progress.jsonl"}
    if args.dry_run:
        script = fill(template, {k: "https://DRY-RUN/" + v for k, v in keys.items()}, bundle_sha, args.instance_type)
        (HERE / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        record = {"schema": "claude.larger-question-t4-dry-run/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
                  "instance_type": args.instance_type, "image": PINNED_AMI, "image_name": image and image.get("Name"),
                  "image_note": image_note, "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha},
                  "identity": identity, "provenance": provenance, "worst_case_arithmetic": arithmetic,
                  "worst_case_usd": round(worst, 4),
                  "dollar_ceiling": DOLLAR_CEILING, "in_machine_timer_seconds": MAX_SECONDS,
                  "power_off_minutes": MAX_SECONDS // 60 + 3, "client_deadline_minutes": CLIENT_DEADLINE_MINUTES,
                  "machine_script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
                  "machine_script_template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
                  "aws_calls": ["ec2.describe_images (read-only)"], "uploaded": False, "launched": False}
        (HERE / "dry_run_record.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                                                  encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded, no link made, nothing launched. Worst case %.2f USD (ceiling %.2f)."
              % (worst, DOLLAR_CEILING))
        return 3 if image is None else 0
    # ---- real launch: the runner only ------------------------------------------------------------------------------
    if image is None:
        raise SystemExit("LAUNCH_REFUSED: the pinned reference image is unavailable; no substitute")
    if (HERE / "launch_record.json").exists():
        raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- one approval, one machine, no retry")
    dirty = git("status", "--porcelain", "--", *[str(HERE / name) for name in JOB_FILES]).decode().strip()
    if dirty:
        raise SystemExit("LAUNCH_REFUSED: commit the job files first:\n" + dirty)
    live = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": GPU_FAMILIES},
                                           {"Name": "instance-state-name", "Values": ["pending", "running", "stopping"]}])
    if live["Reservations"]:
        raise SystemExit("LAUNCH_REFUSED: a GPU machine is already running (quota 8 vCPU; one GPU machine at a time)")
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[{"Name": "instance-type", "Values": [args.instance_type]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]},
                                                  {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        raise SystemExit("LAUNCH_REFUSED: the default security group allows inbound traffic from an address range")
    s3 = boto3.client("s3", region_name=REGION)
    s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
    urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]},
                                                ExpiresIn=4 * 3600)}
    for k in ("results", "progress", "rows"):
        urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=4 * 3600)
    script = fill(template, urls, bundle_sha, args.instance_type)
    if len(script.encode("utf-8")) >= USER_DATA_LIMIT:
        raise SystemExit("LAUNCH_REFUSED: user-data limit")
    name = "helm-larger-question-t4-%s" % stamp
    tags = [{"Key": "Name", "Value": name},
            {"Key": "Purpose", "Value": "HELM-LARGER-QUESTION-PATH-1 T4 checks; CLAUDE_BUILT_CLAUDE_CHECKED"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched, last_error = None, None
    for subnet in sorted(subnets, key=lambda s: s["AvailabilityZone"]):   # placement only: at most one machine
        existing = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [name]},
                                                   {"Name": "instance-state-name", "Values": ["pending", "running"]}])
        if existing["Reservations"]:
            launched = {"Instances": existing["Reservations"][0]["Instances"]}
            break
        try:
            launched = ec2.run_instances(
                ImageId=PINNED_AMI, InstanceType=args.instance_type, MinCount=1, MaxCount=1,
                SubnetId=subnet["SubnetId"], SecurityGroupIds=[group["GroupId"]],
                InstanceInitiatedShutdownBehavior="terminate", UserData=script,
                ClientToken="helm-lq-t4-%s-%s" % (stamp, subnet["AvailabilityZone"]),
                MetadataOptions={"HttpTokens": "required"},
                BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"],
                                      "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
                TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
            break
        except Exception as error:  # noqa: BLE001
            last_error = "%s: %s" % (subnet["AvailabilityZone"], str(error)[:200])
            print("launch in %s refused: %s" % (subnet["AvailabilityZone"], str(error)[:160]), flush=True)
    if launched is None:
        raise SystemExit("LAUNCH_FAILED in every zone; last error %s" % last_error)
    instance = launched["Instances"][0]
    record = {"schema": "claude.larger-question-t4-launch/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
              "authority": "see JOB_LIMITS.md; the runner records the owner's go here before launching",
              "approved": {"machine": args.instance_type, "region": REGION, "price_per_hour_usd": PRICES[args.instance_type],
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "instance_name": name,
              "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": PINNED_AMI,
              "ami_name": image.get("Name"), "root_volume_gb": ROOT_GB, "in_instance_timer_seconds": MAX_SECONDS,
              "client_deadline_minutes": CLIENT_DEADLINE_MINUTES, "worst_case_usd_at_client_deadline": round(worst, 4),
              "worst_case_arithmetic": arithmetic, "bucket": BUCKET, "keys": keys, "python": PYTHON_VERSION,
              "torch": TORCH_LOCAL, "numpy": NUMPY_VERSION, "identity": identity, "provenance": provenance,
              "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha},
              "machine_script_template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
              "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It powers itself off within %d minutes; watch.py terminates it at %d."
          % (instance["InstanceId"], args.instance_type, instance["Placement"]["AvailabilityZone"],
             MAX_SECONDS // 60 + 3, CLIENT_DEADLINE_MINUTES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
