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
        import boto3                                  # real mode: S3 put
        bucket_key = dest_label[len("s3://"):].split("/", 1)
        boto3.client("s3").upload_file(str(path), bucket_key[0], bucket_key[1])
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
        """The ONE registered end path: receipt -> uploads -> termination."""
        receipt_path = Path(receipt_path)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        for p in uploads:
            self.upload(Path(p), f"{dest_label}/{Path(p).name}")
        self.request_termination(reason)
