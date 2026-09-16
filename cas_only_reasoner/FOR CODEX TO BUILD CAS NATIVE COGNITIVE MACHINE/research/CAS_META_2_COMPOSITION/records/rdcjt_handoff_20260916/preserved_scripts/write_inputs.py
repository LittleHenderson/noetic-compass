"""Write the request + authority JSON for one seed of CAS_RDCJT_001.

Request and authority are built from the frozen design in the launcher, so they
cannot drift from what the validator checks. Nothing is launched here.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

COMPOSITION = Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
    r"\research\CAS_META_2_COMPOSITION")
sys.path.insert(0, str(COMPOSITION))

PACKAGE_DIR = COMPOSITION / "records" / "recurrent_cjt_001" / "rdcjt_package_004"
OUT_DIR = COMPOSITION / "records" / "recurrent_cjt_001"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    seed = int(sys.argv[1])
    stamp = sys.argv[2] if len(sys.argv) > 2 else None
    if stamp is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    from aws import recurrent_cjt_launch as L

    receipt = json.loads((PACKAGE_DIR / "receipt.json").read_bytes())
    archive_sha = receipt["archive_sha256"]
    manifest_sha = receipt["manifest_sha256"]
    source_sha = receipt["source_sha"]

    job = "cas-meta2-rdcjt-%s-%s" % (stamp, archive_sha[:8])

    request = {
        "schema": L.REQUEST_SCHEMA,
        "job": job,
        "source_sha": source_sha,
        "archive_sha256": archive_sha,
        "manifest_sha256": manifest_sha,
        "launch_authorized": False,
    }
    authority = {
        "schema": L.AUTHORITY_SCHEMA,
        "job": job,
        "source_sha": source_sha,
        "archive_sha256": archive_sha,
        "manifest_sha256": manifest_sha,
        "owner_authorization_sha256": sha256_file(
            OUT_DIR / "OWNER_AUTHORIZATION_RDCJT_003.json"),
        "candidate": L.CANDIDATE,
        "arms": list(L.FROZEN_ARMS),
        "seed": seed,
        "learning_rate": L.FROZEN_LEARNING_RATE,
        "round_depths": list(L.FROZEN_ROUND_DEPTHS),
        "evaluation_depths": list(L.FROZEN_EVALUATION_DEPTHS),
        "updates_per_arm": L.FROZEN_UPDATES_PER_ARM,
        "decisions_per_arm": L.FROZEN_DECISIONS_PER_ARM,
        "max_wall_seconds": L.FROZEN_MAX_WALL_SECONDS,
        "reservation_usd": str(L.RESERVATION_USD),
        "training": True,
    }

    L.validate_request(request)
    L.validate_authority(authority)

    request_path = OUT_DIR / ("request_rdcjt_%d.json" % seed)
    authority_path = OUT_DIR / ("authority_rdcjt_%d.json" % seed)
    request_path.write_bytes((json.dumps(request, indent=2, sort_keys=True)
                              + "\n").encode("utf-8"))
    authority_path.write_bytes((json.dumps(authority, indent=2, sort_keys=True)
                                + "\n").encode("utf-8"))

    print(json.dumps({
        "validated": True,
        "seed": seed,
        "job": job,
        "request": str(request_path),
        "request_sha256": sha256_file(request_path),
        "authority": str(authority_path),
        "authority_sha256": sha256_file(authority_path),
        "receipt_dir": str(OUT_DIR / ("receipt_" + job)),
        "owner_authorization": str(OUT_DIR / "OWNER_AUTHORIZATION_RDCJT_002.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
