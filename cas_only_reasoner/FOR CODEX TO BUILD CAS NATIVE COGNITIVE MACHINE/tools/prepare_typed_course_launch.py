"""Bind one reviewed source package to standing project authorization; no launch."""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import subprocess
import sys
import io
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT.parents[3]
COMP = ROOT / "research/CAS_META_2_COMPOSITION"
CANONICAL_LEDGER = HOME / "_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/budget/campaign_ledger.json"
sys.path[:0] = [str(ROOT), str(COMP)]
from aws import typed_course_launch as launch


def require_clean_source(root, source):
    launch.require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip() == source,
                   "PREPARE_SOURCE_HEAD")
    launch.require(not subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root).strip(),
                   "PREPARE_TRACKED_MODIFICATIONS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-receipt", required=True)
    parser.add_argument("--package-receipt-sha256", required=True)
    parser.add_argument("--rehearsal-receipt", required=True)
    parser.add_argument("--rehearsal-receipt-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raw = Path(args.package_receipt).read_bytes()
    launch.require(sha256(raw).hexdigest() == args.package_receipt_sha256, "PREPARE_PACKAGE_RECEIPT_PIN")
    package = json.loads(raw)
    source = package["source_sha"]
    require_clean_source(ROOT, source)
    archive = Path(package["archive"]).read_bytes()
    launch.require(len(archive) == package["archive_bytes"] and launch.digest(archive) == package["archive_sha256"],
                   "PREPARE_ARCHIVE_PIN")
    rehearsal_raw = Path(args.rehearsal_receipt).read_bytes()
    launch.require(launch.digest(rehearsal_raw) == args.rehearsal_receipt_sha256, "PREPARE_REHEARSAL_PIN")
    rehearsal = json.loads(rehearsal_raw)
    launch.require(rehearsal["status"] == "PASSED" and rehearsal["source_sha"] == source
                   and rehearsal["archive_sha256"] == package["archive_sha256"]
                   and rehearsal["manifest_sha256"] == package["manifest_sha256"], "PREPARE_REHEARSAL_BINDING")
    ledger_path = launch.validate_ledger_path(CANONICAL_LEDGER)
    ledger_raw = ledger_path.read_bytes()
    ledger = launch.shared.read_ledger(ledger_path)
    launch.require(ledger_path.read_bytes() == ledger_raw, "PREPARE_LEDGER_CHANGED")
    now = datetime.now(timezone.utc)
    job = "cas-meta2-typedcourse-" + now.strftime("%Y%m%d%H%M%S") + "-" + source[:8]
    identity = {"job": job, "source_sha": source, "archive_sha256": package["archive_sha256"],
                "manifest_sha256": package["manifest_sha256"]}
    config = launch.worker_config(job, source_sha=source)
    with ZipFile(io.BytesIO(archive)) as archive_stream:
        manifest_raw = archive_stream.read(launch.shared.MANIFEST_NAME)
    launch.require(launch.digest(manifest_raw) == package["manifest_sha256"], "PREPARE_MANIFEST_PIN")
    manifest = json.loads(manifest_raw)
    launch.require(manifest["source_sha"] == source
        and launch.canonical(manifest["inputs"]) == launch.canonical(config["inputs"])
        and manifest["inputs_sha256"] == config["inputs_sha256"]
        and launch.canonical(manifest["typed_design"]) == launch.canonical(config["design"]),
        "PREPARE_COMMITTED_MANIFEST_CONFIG_BINDING")
    owner = {"schema": launch.OWNER_SCHEMA, "candidate": launch.CANDIDATE, **identity,
        "recorded_utc": now.isoformat(), "evidence_kind": "owner_instruction_in_session",
        "owner_instruction_raw": "I give you approval for it all ....GO!",
        "continuation_objective_raw": "&#x20;       CONTINUE ON WITH AI AGENTS RESEARCH AND DEVELOPMENT UNTIL THE VISION OF THIS PROJECT IS FULLY FULFILLED",
        "interpretation": "Standing project research authorization applied to one complete typed-course engineering training run, under the existing $5000 campaign cap. This records the in-session instruction, not a new human attestation or provider receipt.",
        "bounds": launch.BOUNDS, "design": launch.DESIGN,
        "inputs_sha256": launch.frozen_inputs_hash(),
        "evidence_contract_sha256": launch.run_evidence.contract_digest(launch.evidence_contract())}
    owner_raw = launch.canonical(owner)
    request = {"schema": launch.REQUEST_SCHEMA, **identity, "launch_authorized": False}
    authority = {"schema": launch.AUTHORITY_SCHEMA, "candidate": launch.CANDIDATE, **identity,
        **launch.BOUNDS, "owner_authorization_sha256": launch.digest(owner_raw),
        "inputs_sha256": owner["inputs_sha256"], "design_sha256": launch.digest(launch.canonical(launch.DESIGN)),
        "evidence_contract_sha256": owner["evidence_contract_sha256"], "worker_config": config}
    launch.validate_request(request)
    launch.validate_authority(authority)
    output = Path(args.output).resolve()
    launch.require(output.is_relative_to(ROOT / "records/typed_numeric_001") and not output.exists(), "PREPARE_NEW_OUTPUT")
    output.mkdir()
    for name, value in (("OWNER_AUTHORIZATION.json", owner), ("request.json", request), ("authority.json", authority),
                        ("canonical_ledger_before.json", ledger)):
        with (output / name).open("xb") as stream: stream.write(launch.canonical(value))
    launch.validate_owner(output / "OWNER_AUTHORIZATION.json", authority)
    result = {"status": "BOUND_FOR_ONE_REVIEWED_RUN_NO_RESERVATION", **identity,
        "package_receipt_sha256": args.package_receipt_sha256,
        "rehearsal_receipt_sha256": args.rehearsal_receipt_sha256,
        "canonical_ledger_path": str(ledger_path), "canonical_ledger_sha256_before": launch.digest(ledger_raw),
        "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": launch.digest(path.read_bytes())}
                  for path in sorted(output.iterdir())], "provider_calls": 0, "reservation_created": False}
    with (output / "receipt.json").open("xb") as stream: stream.write(launch.canonical(result))
    print(json.dumps({"output": str(output), "job": job, "request_sha256": launch.digest(launch.canonical(request)),
                      "authority_sha256": launch.digest(launch.canonical(authority))}))


if __name__ == "__main__":
    main()
