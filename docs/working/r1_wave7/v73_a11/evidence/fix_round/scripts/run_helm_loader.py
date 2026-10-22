"""run_helm_loader.py <fix2 dir> <label> -- the host's exact HELM suite command (kit/run_r1w7.py: HELM_TESTS + HELM_LOADER,
python -X utf8 -B -I, from inside a scratch copy of helm_now, HELM_SESSION_DIR inside the scratch, HELM_CANONICAL_BRAIN_DIR
= the wave-1 package folder; A-R1W7-6's seal form) on a FRESH extract of the sealed v9 zip's helm_now, with the label's files
swapped in from the worktree:
  v9    nothing swapped (reader v7.2; the seal recorded Ran 280 OK (skipped=1))
  v73r  helm_wide_turn.py, test_helm_reader_gap.py, test_helm_cas_address.py
  v73   every cut file whose worktree bytes differ from v9 (the cut a v10 reseal would carry)
HELM_TESTS and HELM_LOADER are read from the sealed kit itself (kit/run_r1w7.py in the zip), not retyped. Prints the
'Ran N' and 'OK/FAILED' lines and every skipped test with its reason; writes <fix2>/loader/<label>/RESULT.json."""
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ZIP = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\build_v9\HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip")
ZIP_SHA = "ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c"
TOP = "HELM_R1_W7_20261020/"
WT = Path(r"C:\tmp\helm-ctt2r-c49-read")
W1 = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\x7v9_custody\pkg\deps\HELM_R1_W1_20261015")
SWAP_R = ["helm_wide_turn.py", "test_helm_reader_gap.py", "test_helm_cas_address.py"]


def kit_constants(z):
    src = z.read(TOP + "kit/run_r1w7.py").decode("utf-8")
    tree = ast.parse(src)
    vals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("HELM_TESTS", "HELM_LOADER"):
                vals[node.targets[0].id] = ast.literal_eval(node.value)
    return vals["HELM_TESTS"], vals["HELM_LOADER"]


def main(fix2, label):
    fix2 = Path(fix2)
    zb = ZIP.read_bytes()
    assert hashlib.sha256(zb).hexdigest() == ZIP_SHA
    z = zipfile.ZipFile(ZIP)
    tests, loader = kit_constants(z)
    base = fix2 / "loader" / label
    if base.exists():
        shutil.rmtree(base)
    helm = base / "helm_now_tests"
    for n in z.namelist():
        if n.startswith(TOP + "helm_now/") and not n.endswith("/"):
            p = helm / n[len(TOP + "helm_now/"):]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(z.read(n))
    cut = json.loads(z.read(TOP + "contract/HELM_CUT_R1W7.json"))
    if label == "v9":
        swap = []
    elif label == "v73r":
        swap = SWAP_R
    else:
        swap = [r for r in sorted(cut["files"]) if (WT / r).read_bytes() != (helm / r).read_bytes()]
    for r in swap:
        (helm / r).write_bytes((WT / r).read_bytes())
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("HELM_")}
    env["HELM_SESSION_DIR"] = str(base / "helm_test_sessions")
    env["HELM_CANONICAL_BRAIN_DIR"] = str(W1)
    argv = [sys.executable, "-X", "utf8", "-B", "-I", "-c", loader, str(helm)] + tests
    before = {p.relative_to(helm).as_posix() for p in helm.rglob("*") if p.is_file()}
    r = subprocess.run(argv, cwd=str(helm), env=env, capture_output=True, text=True, timeout=1200)
    log = r.stdout + r.stderr
    (base / "unittest_helm.log").write_text(log, encoding="utf-8")
    after = {p.relative_to(helm).as_posix() for p in helm.rglob("*") if p.is_file()}
    ran = [x for x in log.splitlines() if re.match(r"^Ran \d+ tests? in", x)]
    res = [x for x in log.splitlines() if re.match(r"^(OK|FAILED)", x)]
    skips = [x for x in log.splitlines() if " ... skipped " in x]
    out = {"label": label, "zip_sha256": ZIP_SHA, "swapped": swap,
           "swapped_sha256": {r: hashlib.sha256((helm / r).read_bytes()).hexdigest() for r in swap},
           "helm_tests_from_sealed_kit": tests, "command": ["python", "-X", "utf8", "-B", "-I", "-c", "<HELM_LOADER>",
                                                           "<scratch helm_now copy>"] + tests,
           "cwd": "inside the scratch helm_now copy", "HELM_SESSION_DIR": env["HELM_SESSION_DIR"],
           "HELM_CANONICAL_BRAIN_DIR": env["HELM_CANONICAL_BRAIN_DIR"], "exit": r.returncode,
           "ran_line": ran[-1] if ran else None, "result_line": res[-1] if res else None, "skipped": skips,
           "files_created_inside_copy": sorted(after - before)}
    (base / "RESULT.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
