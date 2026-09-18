import json
import pathlib

A = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
) / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts"

for name in sorted(row.name for row in A.glob("*predictions.json")):
    payload = json.loads((A / name).read_text(encoding="utf-8"))
    rows = payload["predictions"]
    phase = payload.get("phase")
    ids = {row["record_id"] for row in rows}
    print(f"{name:38s} rows={len(rows):5d} phase={phase}")
print()
base = {row["record_id"] for row in json.loads(
    (A / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]}
print(f"exposed course (final_predictions.json): {len(base)}")
for name in sorted(row.name for row in A.glob("*predictions.json")):
    if name == "final_predictions.json":
        continue
    ids = {row["record_id"] for row in json.loads((A / name).read_text(encoding="utf-8"))["predictions"]}
    print(f"{name:38s} rows={len(ids):5d} overlap_with_exposed={len(ids & base)}")
