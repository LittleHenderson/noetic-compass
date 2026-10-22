"""helm_cold_cloud.py -- the cloud tier of HELM's cold memory (A-TEACH2-5 L3-L6): where the oldest verbatim originals
go when the device's own cold folder is full, and where HELM fetches them back when it is online.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
Three tiers: WORKING (lines and capsules, in RAM) -> LOCAL COLD (verbatim originals in the device's folder) -> CLOUD
COLD (a private S3 bucket). This module is only the last step: put bytes, get bytes, say whether the cloud can be
reached. It never deletes anything (only the owner deletes). The caller checks every fingerprint.

  FakeCloud  an in-memory stand-in for tests and exams (no network); `online` and `corrupt` are set by the test.
  S3Cloud    the real bucket through the AWS command line tool (standard library only: one subprocess per call).
             Uploads are encrypted at rest by AWS (SSE-S3) and never carry an ACL; the bucket blocks public access.

Design: docs/working/helm_cube_oscillation_v1/AMENDMENT_A_TEACH2_5.md; spec 7.125.
CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional

DEFAULT_BUCKET = "helm-cold-memory-807562639912-usw2"
DEFAULT_REGION = "us-west-2"
CLI_TIMEOUT_S = 60


class CloudUnavailable(RuntimeError):
    """The cloud cannot be reached right now (no Wi-Fi, no credentials, or the call failed)."""


class FakeCloud:
    """A stand-in for the bucket. `corrupt=True` stores damaged bytes, so the read-back check fails."""

    def __init__(self, online: bool = True, corrupt: bool = False) -> None:
        self.online = online
        self.corrupt = corrupt
        self.objects: Dict[str, bytes] = {}
        self.deletes = 0

    def available(self) -> bool:
        return self.online

    def put(self, key: str, data: bytes) -> None:
        if not self.online:
            raise CloudUnavailable("offline")
        self.objects[key] = (data[:-1] + b"#") if (self.corrupt and data) else bytes(data)

    def get(self, key: str) -> Optional[bytes]:
        if not self.online:
            raise CloudUnavailable("offline")
        return self.objects.get(key)


class S3Cloud:
    """The private bucket, through `aws s3api`. `runner` is subprocess.run (a test passes a fake one)."""

    def __init__(self, bucket: str = DEFAULT_BUCKET, prefix: str = "", region: str = DEFAULT_REGION,
                 aws: str = "aws", runner: Optional[Callable[..., Any]] = None) -> None:
        self.bucket, self.prefix, self.region, self.aws = bucket, prefix, region, aws
        self.runner = runner or subprocess.run

    def _run(self, args: List[str]) -> Any:
        try:
            res = self.runner([self.aws, "s3api"] + args + ["--region", self.region], capture_output=True,
                              timeout=CLI_TIMEOUT_S)
        except (OSError, subprocess.SubprocessError) as exc:
            raise CloudUnavailable(str(exc)) from exc
        if res.returncode != 0:
            raise CloudUnavailable((res.stderr or b"").decode("utf-8", "replace")[:200])
        return res

    def available(self) -> bool:
        try:
            self._run(["head-bucket", "--bucket", self.bucket])
            return True
        except CloudUnavailable:
            return False

    def put(self, key: str, data: bytes) -> None:
        fd, path = tempfile.mkstemp(prefix="helm_cold_")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            self._run(["put-object", "--bucket", self.bucket, "--key", key, "--body", path,
                       "--server-side-encryption", "AES256"])
        finally:
            os.remove(path)

    def get(self, key: str) -> Optional[bytes]:
        fd, path = tempfile.mkstemp(prefix="helm_cold_")
        os.close(fd)
        try:
            self._run(["get-object", "--bucket", self.bucket, "--key", key, path])
            with open(path, "rb") as fh:
                return fh.read()
        finally:
            os.remove(path)
