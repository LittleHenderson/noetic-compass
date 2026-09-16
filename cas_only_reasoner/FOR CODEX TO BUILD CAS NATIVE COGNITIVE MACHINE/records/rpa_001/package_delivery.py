"""Copy verified standalone prototypes to a short, user-facing local path."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
SOURCE = ROOT / "records/rpa_001/demo2"
OUT = HOME / "output/rpa_001"
receipt = json.loads((SOURCE / "receipt.json").read_bytes())
for base, rows in ((ROOT, receipt["sources"]), (SOURCE, receipt["files"])):
    for row in rows:
        raw = (base / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"], row["path"]
OUT.mkdir(parents=True, exist_ok=False)
sources = [SOURCE / (name + ".html") for name in
    ("missing_procedure", "checked_solution", "recovery_and_rollback")]
sources += [ROOT / "docs" / name for name in
    ("CAS_RPA_PROJECT_FIT.md", "CAS_RPA_MATHEMATICAL_REVIEW.md")]
rows = []
for source in sources:
    target = OUT / source.name
    with target.open("xb") as stream:
        stream.write(source.read_bytes())
    assert target.read_bytes() == source.read_bytes()
    rows.append({"source": str(source), "delivered": str(target),
        "bytes": target.stat().st_size, "sha256": sha256(target.read_bytes()).hexdigest()})
record = {"schema_version": "cncm.rpa-delivery/0.1",
    "source_receipt_sha256": sha256((SOURCE / "receipt.json").read_bytes()).hexdigest(),
    "byte_equal_files": rows, "scope": "Offline read-only evidence prototype; no deployed service."}
for path in (OUT / "delivery_receipt.json", Path(__file__).with_name("delivery_receipt.json")):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
print(json.dumps({"output": str(OUT), "byte_equal_files": len(rows)}))
