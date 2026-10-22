"""dryrun2.py -- the fix round's dry run of A-R1W7-11 on FRESH scratch copies of the sealed v9 package, under
v73_scratch\\a11_dryrun2\\ (must not exist yet). Every step runs as its own process through gate.py (the 500 MB rule; one
memory reading logged per step). Steps:
  1. two fresh extracts of the v9 zip (ff, pkg), each with the custody deps copied beside it; each checked byte-equal
     to the zip and its neighbours to their freezes (check_copy.py)
  2. fail first: apply --plants-only to ff; the UNAMENDED reader on the plants (read_plants_ff.py records the fix state)
  3. apply the full amendment to pkg; a second apply must refuse (exit 4)
  4. pkg: the whole wave-7 suite (tests_r1w7/run_tests.py -v); the new tests alone; the plants on the AMENDED reader
  5. FIX FIRST at the scorer level on ff (unamended code) and pkg (amended code) (fixfirst_scorer.py)
  6. the isolated stale-freeze failure (stale_freeze_probe.py) and the mutation check (mutation_probe.py)
Scratch only; 0 USD; no network."""
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

S = Path(r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS"
         r"\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\v73_scratch")
ROOT = S / "a11_dryrun2"
FIX2 = S / "fix2"
GATE = FIX2 / "scripts" / "gate.py"
A11S = S / "a11_scripts"
ZIP = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\build_v9\HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip")
V9 = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\build_v9\HELM_R1_W7_20261020")
DEPS = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\x7v9_custody\pkg\deps")
TOOL = Path(r"C:\tmp\helm-ctt2r-c49-read\docs\working\r1_wave7\a_r1w7_11\apply_amendment_11.py")
TOP = "HELM_R1_W7_20261020"
PY = [sys.executable, "-X", "utf8", "-B", "-I"]
LOG = ROOT / "logs"
MEM = ROOT / "logs" / "memory_log.jsonl"
results = {}


def step(label, argv, cwd=None, want=0, env=()):
    out = LOG / (label + ".log")
    g = PY + [str(GATE), "--label", label, "--memlog", str(MEM), "--out", str(out), "--unset-helm-env"]
    if cwd:
        g += ["--cwd", str(cwd)]
    for e in env:
        g += ["--env", e]
    r = subprocess.run(g + ["--"] + argv, capture_output=True, text=True)
    print(r.stdout.strip(), flush=True)
    text = out.read_text(encoding="utf-8") if out.is_file() else ""
    results[label] = {"exit": r.returncode, "want": want, "ok": r.returncode == want, "log": str(out),
                      "tail": text.strip().splitlines()[-6:]}
    if r.returncode == 3 and "GATE STOP" in r.stdout:
        raise SystemExit("GATE STOP at " + label)
    return r.returncode, text


def main():
    if ROOT.exists():
        raise SystemExit("REFUSED: a11_dryrun2 already exists")
    LOG.mkdir(parents=True)
    for name in ("ff", "pkg"):
        d = ROOT / name
        d.mkdir()
        zipfile.ZipFile(ZIP).extractall(d)
        shutil.copytree(DEPS, d / "deps")
        step(f"check_copy_{name}", PY + [str(A11S / "check_copy.py"), str(ZIP), str(d / TOP), str(d / "deps")])
    # 2. fail first on the unamended reader
    step("apply_plants_only_ff", PY + [str(TOOL), str(ROOT / "ff" / TOP), "--plants-only"])
    step("plants_on_unamended_v9", PY + [str(FIX2 / "scripts" / "read_plants_ff.py"), str(ROOT / "ff" / TOP),
                                         str(ROOT / "PLANTS_ON_UNAMENDED_V9.json")])
    # 3. apply
    step("apply_full_pkg", PY + [str(TOOL), str(ROOT / "pkg" / TOP)])
    step("apply_full_pkg_second", PY + [str(TOOL), str(ROOT / "pkg" / TOP)], want=4)
    # 4. suites and plants on the amended package
    step("suite_w7_run_tests_v", PY + [str(ROOT / "pkg" / TOP / "tests_r1w7" / "run_tests.py"), "-v"],
         cwd=ROOT / "pkg" / TOP, want=1)
    code = ("import sys, unittest; sys.path.insert(0, sys.argv[1]); "
            "unittest.main(module=None, argv=['unittest', '-v'] + sys.argv[2:])")
    step("new_tests_alone", PY + ["-c", code, str(ROOT / "pkg" / TOP), "tests_r1w7.test_honest_ask_w7"],
         cwd=ROOT / "pkg" / TOP)
    step("plants_on_amended", PY + [str(FIX2 / "scripts" / "read_plants_ff.py"), str(ROOT / "pkg" / TOP),
                                    str(ROOT / "PLANTS_ON_AMENDED.json")])
    # 5. FIX FIRST at the scorer level
    step("fixfirst_scorer_unamended", PY + [str(A11S / "fixfirst_scorer.py"), str(ROOT / "ff" / TOP),
                                            str(ROOT / "FIXFIRST_SCORER_unamended.json")])
    step("fixfirst_scorer_amended", PY + [str(A11S / "fixfirst_scorer.py"), str(ROOT / "pkg" / TOP),
                                          str(ROOT / "FIXFIRST_SCORER_amended.json")])
    # 6. isolated stale-freeze failure; mutation check
    step("stale_freeze_probe", PY + [str(A11S / "stale_freeze_probe.py"), str(V9), str(ROOT / "pkg"),
                                     str(ROOT / "stale_freeze_work")])
    step("mutation_probe", PY + [str(A11S / "mutation_probe.py"), str(ROOT / "pkg"), str(ROOT / "mutation_work")])
    (ROOT / "DRYRUN2_STEPS.json").write_text(json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: (v["exit"], v["ok"]) for k, v in results.items()}, sort_keys=True))
    return 0 if all(v["ok"] for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
