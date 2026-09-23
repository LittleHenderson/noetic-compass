"""Read-only output fingerprint verification; never loads torch or executes a model."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    manifest = json.loads((HERE / "OUTPUT_MANIFEST.json").read_text(encoding="utf-8"))
    checked = []
    for row in manifest["files"]:
        path = ROOT / row["path"]
        body = path.read_bytes()
        raw = hashlib.sha256(body).hexdigest()
        lf = hashlib.sha256(body.replace(b"\r\n", b"\n")).hexdigest()
        if lf != row["sha256_lf"]:
            raise ValueError("FINGERPRINT_MISMATCH: " + str(path))
        checked.append({"path": row["path"], "raw_equal": raw == row["sha256_raw"], "lf_equal": True})
    print(json.dumps({"status": "VERIFIED", "files": len(checked),
                      "raw_equal": sum(r["raw_equal"] for r in checked),
                      "lf_equal": len(checked), "model_execution": False}))


if __name__ == "__main__":
    main()
