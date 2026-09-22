"""Verify existing acceptance bytes and case reconciliation without reruns."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / ".git").exists())
manifest = json.loads((HERE / "ACCEPTANCE_MANIFEST.json").read_text(encoding="utf-8"))
for entry in manifest["artifacts"]:
    data = (ROOT / entry["path"]).read_bytes()
    assert len(data) == entry["bytes"], entry["path"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]
receipts = json.loads((HERE / "RECEIPTS.json").read_text(encoding="utf-8"))
for run in receipts["runs"]:
    xml = ROOT / next(r["path"] for r in run["receipts"] if r["path"].endswith(".xml"))
    cases = list(ET.parse(xml).getroot().iter("testcase"))
    assert len(cases) == run["cases"]
    names = {c.attrib["name"] for c in cases}
    assert len(names) == len(cases)
    assert names == {c["id"].split("::", 1)[1] for c in run["case_results"]}
    for status in ("failure", "error", "skipped"):
        assert sum(c.find(status) is not None for c in cases) == run["counts"][status]
    for reconciliation in run.get("failed_case_reconciliation", []):
        assert reconciliation["final_status"] == "passed"
final = receipts["runs"][-1]
assert final["exit_code"] == 0 and final["counts"]["passed"] == final["cases"]
assert hashlib.sha256((ROOT / final["source_path"]).read_bytes()).hexdigest() == final["source_sha256"]
assert receipts["test_accounting"]["new_cases"] == sum(c["group"] == "new" for c in final["case_results"])
print(f"PASS: {len(manifest['artifacts'])} artifact hashes, {final['cases']} final cases, all retained failed cases reconciled")
