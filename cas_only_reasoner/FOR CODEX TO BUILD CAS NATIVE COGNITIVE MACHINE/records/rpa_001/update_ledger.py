"""Append source-bound CAS-RPA adoption without changing prior requirements."""
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HOME = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
EXPECTED = "6ac4c82754148193ca08358be6e1d2d9adf43881d6598b5051c88386c500dbce"
test_path = Path(__file__).with_name("final_full_suite_tests.xml")
suite = ET.fromstring(test_path.read_bytes()).find("testsuite")
assert suite is not None and int(suite.attrib["failures"]) == int(suite.attrib["errors"]) == 0
assert int(suite.attrib["tests"]) == 1033 and int(suite.attrib["skipped"]) == 0
receipt_path = Path(__file__).with_name("demo2") / "receipt.json"
receipt = json.loads(receipt_path.read_bytes())
assert receipt["status"] == "REAL_NATIVE_EVIDENCE_PROJECTED"
assert receipt["native_source_profile_digest"] == "c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607"
for row in receipt["sources"]:
    assert sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"], row["path"]
addition = """
## 2026-09-16 CAS-RPA typed records and real native episode views

Both supplied CAS-RPA PDFs were read in full and reviewed mathematically.
The relationship model now has a bounded implementation: composition,
refinement, recorded reachability, common-witness overlap and shared idea IDs
retain distinct meanings. Recursive inspection has explicit depth/node caps
and reports deferred work. Focus, hypotheses and the actual native state
remain separate. The original native source profile is unchanged.

A read-only adapter semantically replays native journals before constructing
the atlas. The offline prototype shows the actual suspended missing-procedure
caller, checked result7 and subsequent recovery/reuse/rollback/refusal.
Flower and ordinary graph layouts use exactly the same records and budgets.
Both preserve the current state; proposed next actions grant no permission.
Browser checks cover focus/layout/filter behavior, readable labels, inert
hostile strings, exact evidence inspection, no external requests and mobile
layout. Full homebase verification passed571 tests plus462 subtests.

Current evidence is records/rpa_001/STATUS.md, final_full_suite_tests.xml and
demo2/receipt.json in vision-next. The exact project fit and first prototype
are documented in docs/CAS_RPA_PROJECT_FIT.md; mathematical findings are in
docs/CAS_RPA_MATHEMATICAL_REVIEW.md. The source register preserves the hashes
of both original PDFs. Forty positive normalized components have39 independent
dimensions; the centered inverse must restore its reference; a common witness
is required for joint overlap. Pairwise overlap alone does not suffice.

This advances inspection/diagnosis portions of V08/V10/V13 and systems8/9/24/
27/31 without completing them. No measured40-coordinate native profile,
Foundation-to-Drive mapping, general live planner, full sheaf/nerve, learned
procedure synthesis, neural-flow closure or performance advantage is claimed.
A fair held-out benefit study remains open. No new paid model/provider work
was used. The full V01-V18,31-system and integrated20-step destination remains
open; prior negative results and budget reservations remain unchanged.
"""
paths = [base / "docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md" for base in (HOME, ROOT)]
originals = [path.read_bytes() for path in paths]
assert all(sha256(raw).hexdigest() == EXPECTED for raw in originals)
rows = []
for path, before in zip(paths, originals):
    path.write_bytes(before + addition.encode())
    rows.append({"path": str(path), "before_sha256": sha256(before).hexdigest(),
        "after_sha256": sha256(path.read_bytes()).hexdigest(),
        "original_bytes_preserved": path.read_bytes().startswith(before),
        "full_goal_complete": False})
record = {"ledgers": rows, "tests_xml_sha256": sha256(test_path.read_bytes()).hexdigest(),
    "demo_receipt_sha256": sha256(receipt_path.read_bytes()).hexdigest()}
with Path(__file__).with_name("ledger_update.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps(record))
