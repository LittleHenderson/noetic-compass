"""Builder tool (NOT sealed): one exact once-only edit — the package's own suite runner (`tests_r1w7/run_tests.py`, the script
the host runs as W7_TESTS_SCRIPT) gains `tests_r1w7.test_multi_qty_w7` so A-R1W7-7's seven tests run from the seal and on
the host. Found at the first v7 seal: run_tests.py names its suites explicitly, so the amendment's test file was carried
but not run (Ran 34). Appends to PATCH_V7_LOG.json.

    python -X utf8 -B -I patch_v7b_run_tests.py <v7 package dir> <log json>
"""
import hashlib
import json
import sys
from pathlib import Path

PKG, LOG = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
rel = "tests_r1w7/run_tests.py"
old = '    suite = unittest.defaultTestLoader.loadTestsFromNames(["tests_r1w7.test_units_w7", "tests_r1w7.test_kit_w7"])'
new = ('    suite = unittest.defaultTestLoader.loadTestsFromNames(["tests_r1w7.test_units_w7", "tests_r1w7.test_kit_w7",\n'
       '                                                          "tests_r1w7.test_multi_qty_w7"])   # v7: A-R1W7-7\'s seven tests')
p = PKG / rel
t = p.read_bytes().decode("utf-8")
if t.count(old) != 1:
    raise SystemExit("anchor not found exactly once")
p.write_bytes(t.replace(old, new).encode("utf-8"))
old2 = "runs the two suites in one process"
if t.count(old2) == 1:
    t2 = p.read_bytes().decode("utf-8").replace(old2, "runs the three suites in one process (v7: + A-R1W7-7's test_multi_qty_w7)")
    p.write_bytes(t2.encode("utf-8"))
if b"\x08" in p.read_bytes():
    raise SystemExit("stray backspace byte")
log = json.loads(LOG.read_text(encoding="utf-8"))
log["edits"].append({"file": rel, "old": old[:90], "new": new[:90]})
log["edits"].append({"file": rel, "old": old2, "new": "runs the three suites in one process (v7: + A-R1W7-7's test_multi_qty_w7)"})
log["files_sha256"][rel] = hashlib.sha256(p.read_bytes()).hexdigest()
log["note_v7b"] = ("second pass: the first v7 seal ran the package suites from the extract and got Ran 34 (the amendment's test file "
                   "carried but not named by run_tests.py); run_tests.py now names it; resealed")
LOG.write_bytes((json.dumps(log, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({"edits": len(log["edits"])}))
