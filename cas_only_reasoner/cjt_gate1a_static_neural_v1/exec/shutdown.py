"""shutdown.py -- the registered shutdown/termination path (GATE 1A.2 section 9).

Every success, failure, timeout, cancellation, or exception path must: write the
final receipt, upload required evidence, invoke THIS registered path, and
request instance termination. The campaign driver calls finalize() from a
`finally` block; the separate watchdog (exec/watchdog.py) requests termination
even if the driver never reaches it. Real instances launch with
InstanceInitiatedShutdownBehavior=terminate (infra/instance_launch.json), so an
OS shutdown IS termination.
"""
from __future__ import annotations

import json
from pathlib import Path


class ShutdownPath:
    """Uploader + terminator are the two registered backends; synthetic mode
    records every action to files so conformance tests can verify the path ran."""

    def __init__(self, mode: str, evidence_dir: Path):
        self.mode = mode
        self.evidence_dir = Path(evidence_dir)
        self.actions = []

    def upload(self, path: Path, dest_label: str) -> None:
        if self.mode == "SYNTHETIC_CONFORMANCE":
            self.actions.append({"action": "UPLOAD", "path": str(path),
                                 "dest": dest_label})
            return
        if not dest_label.startswith("s3://"):
            raise RuntimeError(f"UPLOAD_DEST_INVALID: {dest_label} is not an s3 URI")
        import boto3                                  # real mode: S3 put
        rest = dest_label[len("s3://"):]
        if "/" not in rest:
            raise RuntimeError(f"UPLOAD_DEST_INVALID: {dest_label} has no key")
        bucket, key = rest.split("/", 1)
        boto3.client("s3").upload_file(str(path), bucket, key)
        self.actions.append({"action": "UPLOAD", "path": str(path),
                             "dest": dest_label})

    def request_termination(self, reason: str) -> None:
        self.actions.append({"action": "TERMINATION_REQUESTED", "reason": reason})
        marker = self.evidence_dir / "TERMINATION_REQUESTED.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        with marker.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"reason": reason, "mode": self.mode},
                                indent=2) + "\n")
        if self.mode == "SYNTHETIC_CONFORMANCE":
            return
        # real mode: EC2 terminate. SAFETY LAW (conformance near-miss, fixed):
        # if IMDS does not answer, this process is NOT on EC2 -- record the
        # fact and DO NOT touch the host OS. The OS-shutdown last resort is
        # reachable ONLY after a confirmed on-EC2 identity (where the launch
        # template's terminate-on-shutdown makes it a termination).
        try:
            from exec.identity import fetch_real_aws_identity
            ident = fetch_real_aws_identity()
        except Exception:
            not_ec2 = self.evidence_dir / "TERMINATION_UNAVAILABLE_NOT_ON_EC2.json"
            with not_ec2.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"reason": reason,
                                     "note": "REAL-mode termination requested "
                                             "off-EC2; host untouched"},
                                    indent=2) + "\n")
            return
        try:
            import boto3
            boto3.client("ec2", region_name=ident["region"]).terminate_instances(
                InstanceIds=[ident["instance_id"]])
        except Exception:
            import subprocess                         # confirmed on-EC2 only
            subprocess.run(["shutdown", "-h", "now"], check=False)

    def finalize(self, receipt: dict, receipt_path: Path, uploads,
                 dest_label: str, reason: str) -> None:
        """The ONE registered end path: receipt -> uploads -> termination.
        Uploads are BEST-EFFORT (each wrapped): an upload failure (e.g. an S3
        error, or boto3 absent on a dev box) must NEVER prevent termination.
        Every attempt and outcome is recorded so the evidence names what was
        uploaded and what was not."""
        receipt_path = Path(receipt_path)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        # preserve the file's path RELATIVE to the evidence root in the S3 key so
        # two files that share a basename in different subdirs do not collide
        # (audit fix); fall back to the basename if a file is outside the root
        for p in uploads:
            p = Path(p)
            try:
                rel = p.relative_to(self.evidence_dir).as_posix()
            except ValueError:
                rel = p.name
            try:
                self.upload(p, f"{dest_label}/{rel}")
            except Exception as exc:                   # noqa: BLE001 -- best effort
                self.actions.append({"action": "UPLOAD_FAILED", "path": str(p),
                                     "error": f"{type(exc).__name__}"})
        self.request_termination(reason)
