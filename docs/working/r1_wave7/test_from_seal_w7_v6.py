"""Builder tool (NOT sealed): extract the sealed v6 zip into a fresh folder beside the neighbours, re-hash every member
against the freeze, run the wave-7 suites FROM THE EXTRACT, and run EXACTLY the host's HELM suite list with the host's
command form on a scratch copy of the sealed helm_now/ (A-R1W7-6 rule). Writes TEST_COUNTS_R1W7_v6.json beside the zip.

    python -X utf8 -B -I test_from_seal_w7_v6.py

The host's list is read from the sealed kit (`kit/run_r1w7.py` HELM_TESTS, the script the stage plan runs) and compared with
this tool's own typed copy HOST_EXACT_SUITE_LIST; the tool refuses unless they are equal, the loader strings are equal, and
`kit/STAGE_R1W7.json` argv[0] is `kit/run_r1w7.py`. The command form is the kit's own (run_r1w7.py line 242): one process,
`python -X utf8 -B -I -c HELM_LOADER <scratch>/helm_now_tests <names>`, cwd = the scratch copy, HELM_SESSION_DIR inside the
scratch, HELM_CANONICAL_BRAIN_DIR = the wave-1 package folder.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "HELM_R1_W7_20261020_SOURCE_R1W7_v6.zip"
DEPS = ROOT.parent / "deps"
HOST_EXACT_SUITE_LIST = ['test_helm_brain_wide', 'test_helm_end_to_end_loop', 'test_helm_english_in',
                         'test_helm_english_in_stock_frame', 'test_helm_voice', 'test_helm_faces_in', 'test_helm_triad',
                         'test_helm_wide_alongside', 'test_helm_cas_address', 'test_helm_units_note',
                         'test_helm_pin_hygiene']          # v6 (A-R1W7-6): the 10 names c53 ran + the pin-hygiene suite
HOST_LOADER = ("import sys, unittest; sys.path.insert(0, sys.argv[1]); "
               "unittest.main(module=None, argv=['unittest', '-v'] + sys.argv[2:])")
PY = [sys.executable, "-X", "utf8", "-B", "-I"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse(text):
    ran = [int(x) for x in re.findall(r'^Ran ([0-9]+) tests? in ', text, flags=re.MULTILINE)]
    s = re.findall(r'^(OK|FAILED)(?: \(([^)]*)\))?\s*$', text, flags=re.MULTILINE)
    lines = [ln for ln in text.splitlines() if ln.startswith("Ran ") or ln.startswith("OK") or ln.startswith("FAILED")]
    return {"ran": ran, "verdict": s[-1][0] if s else None, "detail": s[-1][1] if s else None, "ran_ok_lines": lines}


def load_kit(pkg):
    spec = importlib.util.spec_from_file_location("run_r1w7_sealed", pkg / "kit" / "run_r1w7.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    zsha = sha(ZIP)
    base = ROOT / "build" / "from_seal"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    with zipfile.ZipFile(ZIP) as zf:
        zf.extractall(base)
    pkg = base / "HELM_R1_W7_20261020"
    freeze = json.loads((pkg / "PACKAGE_FREEZE.json").read_text(encoding="utf-8"))
    bad = [r for r, p in freeze["members"].items() if sha(pkg / r) != p["sha256"]]
    env = dict(os.environ)
    env.pop("HELM_WIDE_BRAIN", None)
    env.pop("PYTHONPATH", None)
    env.pop("HELM_CANONICAL_BRAIN_DIR", None)
    for n, d in (("W1", "HELM_R1_W1_20261015"), ("W3", "HELM_R1_W3_20261019"), ("W3B", "HELM_R1_W3B_20261019"),
                 ("W6", "HELM_R1_W6_20261019"), ("RBW1T", "HELM_RBW1T_20261019")):
        env[f"R1W7_{n}_DIR"] = str(DEPS / d)
    w1 = DEPS / "HELM_R1_W1_20261015"
    env["HELM_CANONICAL_BRAIN_DIR"] = str(w1)
    # ---- the host's exact list, computed twice
    kit = load_kit(pkg)
    stage = json.loads((pkg / "kit" / "STAGE_R1W7.json").read_text(encoding="utf-8"))
    if list(kit.HELM_TESTS) != HOST_EXACT_SUITE_LIST:
        raise SystemExit(f"HOST_LIST_MISMATCH: sealed kit {list(kit.HELM_TESTS)!r} vs typed {HOST_EXACT_SUITE_LIST!r}")
    if kit.HELM_LOADER != HOST_LOADER:
        raise SystemExit("HOST_LOADER_MISMATCH")
    if stage["argv"][0] != "kit/run_r1w7.py":
        raise SystemExit("STAGE_ARGV0_IS_NOT_THE_KIT_RUNNER: " + stage["argv"][0])
    out = {"schema": "helm.r1w7.test-counts/2", "package_zip_sha256": zsha,
           "package_freeze_sha256": sha(pkg / "PACKAGE_FREEZE.json"), "members": len(freeze["members"]),
           "members_rehashed_bad": bad, "python": sys.version.split()[0], "platform": sys.platform}
    t0 = time.time()
    r = subprocess.run(PY + [str(pkg / "tests_r1w7" / "run_tests.py"), "-v"], cwd=str(base), env=env,
                       capture_output=True, text=True, timeout=900)
    out["r1w7_suites_from_sealed_extract"] = dict(parse(r.stderr + r.stdout), seconds=round(time.time() - t0, 1))
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        hc = scratch / "helm_now_tests"
        shutil.copytree(pkg / "helm_now", hc)
        e2 = dict(env, HELM_SESSION_DIR=str(scratch / "helm_test_sessions"))
        cmd = PY + ["-c", kit.HELM_LOADER, str(hc), *kit.HELM_TESTS]
        t1 = time.time()
        r2 = subprocess.run(cmd, cwd=str(hc), env=e2, capture_output=True, text=True, timeout=900)
        parsed = parse(r2.stderr + r2.stdout)
        out["host_exact_suite_list"] = {
            "rule": "A-R1W7-6: the seal step runs EXACTLY the host's HELM suite list with the host's command form, from a fresh extract",
            "names": list(kit.HELM_TESTS), "count": len(kit.HELM_TESTS),
            "source_in_the_sealed_package": "kit/run_r1w7.py HELM_TESTS (the script kit/STAGE_R1W7.json argv[0] runs)",
            "equals_this_tools_typed_copy": list(kit.HELM_TESTS) == HOST_EXACT_SUITE_LIST,
            "stage_plan_argv0": stage["argv"][0],
            "command_form": ["python", "-X", "utf8", "-B", "-I", "-c", "<HELM_LOADER>", "<scratch>/helm_now_tests", *kit.HELM_TESTS],
            "loader": kit.HELM_LOADER, "cwd": "<scratch>/helm_now_tests",
            "env": {"HELM_SESSION_DIR": "<scratch>/helm_test_sessions", "HELM_CANONICAL_BRAIN_DIR": "<wave-1 package folder>",
                    "HELM_WIDE_BRAIN": "unset", "PYTHONPATH": "unset (-I ignores it anyway)"},
            "as_run_here": {"scratch": "<tempdir>", "wave1_folder": str(w1), "exit": r2.returncode},
            "ran": parsed["ran"], "verdict": parsed["verdict"], "detail": parsed["detail"], "ran_ok_lines": parsed["ran_ok_lines"],
            "seconds": round(time.time() - t1, 1),
            "pin_line": [ln for ln in (r2.stderr + r2.stdout).splitlines() if "test_off_is_byte_identical" in ln][:2],
            "c53_host_for_comparison": {"names": 10, "python": "3.12.3", "ran": 236, "verdict": "FAILED", "detail": "failures=1, skipped=2"}}
        after = sorted(q.relative_to(pkg).as_posix() for q in (pkg / "helm_now").rglob("*") if q.is_file() and "__pycache__" not in q.parts)
        members_hn = sorted(r for r in freeze["members"] if r.startswith("helm_now/"))
        out["sealed_helm_now_unchanged_by_the_suites"] = after == members_hn and not [r for r in members_hn if sha(pkg / r) != freeze["members"][r]["sha256"]]
    data = (json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8")
    (ROOT / "TEST_COUNTS_R1W7_v6.json").write_bytes(data)
    print(json.dumps(out, indent=1))
    if r.returncode or out["r1w7_suites_from_sealed_extract"]["verdict"] != "OK":
        print(r.stderr[-3000:])
    if r2.returncode or out["host_exact_suite_list"]["verdict"] != "OK":
        print(r2.stderr[-3000:])


if __name__ == "__main__":
    main()
