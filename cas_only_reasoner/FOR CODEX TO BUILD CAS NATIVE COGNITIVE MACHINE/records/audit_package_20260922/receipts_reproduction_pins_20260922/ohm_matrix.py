"""Run every (implementation revision x test revision) pair of the older CAS-Ohm module from clean scratch copies.

The implementation is quantifiers.py + __init__.py at IMPL; the test file is test_quantifiers.py at TESTS.
Each pair runs as `python -B api/cas_ohm/test_quantifiers.py` from a fresh directory, exactly as 03_REPRODUCE.md
instructs. Output: the final PASSED line and the names of failing tests, per pair.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

repo = pathlib.Path(sys.argv[1])
work = pathlib.Path(sys.argv[2])
PY = sys.executable
D = "noetic-compass-scaffold/noetic-compass/api/cas_ohm/"
IMPLS = ["078d00ed", "86ba3d75", "a4b2e0d7", "9fe1eb36"]
TESTS = ["078d00ed", "86ba3d75", "a4b2e0d7"]


def blob(rev, name):
    return subprocess.run(["git", "-C", str(repo), "show", rev + ":" + D + name], capture_output=True, check=True).stdout


rows = []
for impl in IMPLS:
    for tests in TESTS:
        d = work / ("impl_%s__tests_%s" % (impl, tests))
        if d.exists():
            shutil.rmtree(d)
        (d / "api" / "cas_ohm").mkdir(parents=True)
        (d / "api" / "__init__.py").write_bytes(b"")
        for name in ("quantifiers.py", "__init__.py"):
            (d / "api" / "cas_ohm" / name).write_bytes(blob(impl, name))
        (d / "api" / "cas_ohm" / "test_quantifiers.py").write_bytes(blob(tests, "test_quantifiers.py"))
        r = subprocess.run([PY, "-B", "api/cas_ohm/test_quantifiers.py"], cwd=d, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env={"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
                                                                 "SYSTEMROOT": "C:\\Windows", "PATH": ""})
        out = r.stdout + r.stderr
        passed = re.findall(r"PASSED\s+\d+/\d+", out)
        fails = sorted(set(re.findall(r"FAIL(?:ED)?[:\s]+(test_\w+)", out)))
        rows.append({"impl": impl, "tests": tests, "exit": r.returncode, "summary": passed[-1] if passed else out.strip().splitlines()[-1:],
                     "failing": fails})
        print("impl %-9s tests %-9s exit %d  %-16s failing=%s" % (impl, tests, r.returncode, rows[-1]["summary"], fails))
(work / "ohm_matrix.json").write_text(json.dumps(rows, indent=1), encoding="utf-8", newline=chr(10))
