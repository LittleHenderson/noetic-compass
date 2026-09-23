"""Read-only hashes and receipt checks; no model loading or new test run."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CN = ROOT.parents[1]


def verify():
    manifest = json.loads((ROOT / "ACCEPTANCE_MANIFEST.json").read_text(encoding="utf-8"))
    for row in manifest["artifacts"]:
        path = (CN / row["path"]).resolve()
        if not path.is_relative_to(CN.resolve()):
            raise ValueError("Artifact path escaped project")
        raw = path.read_bytes()
        matches = (len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256_raw"])
        if row["verification"] == "LF_NORMALIZED_SOURCE_WITH_RAW_FINGERPRINT_RETAINED":
            matches = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == row["sha256_lf"]
        if not matches:
            raise ValueError("Artifact fingerprint differs: " + row["path"])
    plan = json.loads((ROOT / "plan.json").read_text())
    for name, expected in plan["source_pins"].items():
        raw = (CN / "research/helm_cas_expression_lab" / name).read_bytes()
        if hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() != expected:
            raise ValueError("Runtime source differs: " + name)
    result = json.loads((ROOT / "run_001/result.json").read_text())
    replay = json.loads((ROOT / "saved_run_verification.json").read_text())
    if result["checkpoint_weights_sha256"] != replay["checkpoint_weights_sha256"]:
        raise ValueError("Checkpoint identities differ")
    if result["actual_updates"] != replay["actual_updates"] or result["dev_by_depth"] != replay["by_depth"]:
        raise ValueError("Result and checker replay differ")
    print(json.dumps({"integrity": "PASS", "artifact_hashes": len(manifest["artifacts"]),
                      "runtime_source_hashes": len(plan["source_pins"]),
                      "actual_updates": replay["actual_updates"], "canonical_exact": replay["exact_count"],
                      "development_predictions": replay["prediction_count"], "neural_execution": False}))


if __name__ == "__main__":
    verify()
