"""stale_freeze_probe.py <sealed_v9_tree> <amended_copy_parent> <work_dir> -- is the one failing kit test
(test_runner_refuses_a_key_file_in_the_carrier) failing ONLY because the amended copy's PACKAGE_FREEZE.json still pins v9's
member hashes? (1) a pristine throwaway copy of the v9 tree: run the test; (2) a throwaway copy of the amended tree whose
PACKAGE_FREEZE.json member pins are re-written (sha256 + bytes) for the files the amendment changed (DIAGNOSTIC ONLY;
never sealed, never kept): run the test. Neighbours from <amended_copy_parent>/deps. Scratch only."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

V9, AMD, WORK = (Path(a).resolve() for a in sys.argv[1:4])
TEST = "tests_r1w7.test_kit_w7.KitTests.test_runner_refuses_a_key_file_in_the_carrier"


def run_test(root: Path) -> str:
    code = ("import sys, unittest; sys.path.insert(0, %r); r = unittest.TextTestRunner(verbosity=0).run("
            "unittest.defaultTestLoader.loadTestsFromNames([%r])); print('RESULT ran', r.testsRun, 'failures', "
            "len(r.failures), 'errors', len(r.errors), 'skipped', len(r.skipped))" % (str(root), TEST))
    p = subprocess.run([sys.executable, "-X", "utf8", "-B", "-I", "-c", code], capture_output=True, text=True,
                       cwd=str(root.parent), timeout=600)
    return ([x for x in p.stdout.splitlines() if x.startswith("RESULT")] or ["NO RESULT " + p.stderr[-400:]])[-1]


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    shutil.copytree(AMD / "deps", WORK / "deps")
    pristine = WORK / "pristine" / V9.name
    shutil.copytree(V9, pristine)
    shutil.copytree(AMD / "deps", WORK / "pristine" / "deps")
    print("pristine v9 copy:", run_test(pristine))
    fixed = WORK / "refrozen" / V9.name
    shutil.copytree(AMD / V9.name, fixed)
    shutil.copytree(AMD / "deps", WORK / "refrozen" / "deps")
    fz = fixed / "PACKAGE_FREEZE.json"
    d = json.loads(fz.read_bytes().decode("utf-8"))
    changed = []
    for rel, pin in d["members"].items():
        b = (fixed / rel).read_bytes()
        h = hashlib.sha256(b).hexdigest()
        if h != pin["sha256"]:
            d["members"][rel] = {"bytes": len(b), "sha256": h}
            changed.append(rel)
    fz.write_bytes((json.dumps(d, sort_keys=True, indent=1) + "\n").encode("ascii"))
    print("member pins re-written in the throwaway copy:", changed)
    print("amended copy, member pins re-written:", run_test(fixed))
    shutil.rmtree(WORK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
