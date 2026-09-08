"""Pinned composition of the unchanged bootstrap plus three support downloads."""
from hashlib import sha256
from pathlib import Path
import re

from aws import teaching_cycle_bootstrap as base

BASE_SHA256 = "e39245ef84983d08068ffca928893070e25f0b2fd8edbc710e5851b2be3c11dc"
SUPPORT_KEYS = {"base_remote.py": "base_guest_driver_sha256",
                "continuation_package.py": "prior_package_validator_sha256",
                "restore_probe.py": "restore_probe_sha256"}


def render_bootstrap(*, bucket, job, source_sha256, driver_sha256, config_sha256, deadline_unix, continuation):
    if sha256(Path(base.__file__).read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError("CONTINUATION_BOOTSTRAP_BASE_CHANGED")
    lines = []
    for name, key in SUPPORT_KEYS.items():
        pin = continuation.get(key)
        if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin):
            raise ValueError("CONTINUATION_BOOTSTRAP_SUPPORT_PIN")
        lines += ["get_object input/" + name + " " + name,
                  "echo '" + pin + "  " + name + "' | sha256sum -c -"]
    original = base.render_bootstrap(bucket=bucket, job=job, source_sha256=source_sha256,
        driver_sha256=driver_sha256, config_sha256=config_sha256, deadline_unix=deadline_unix)
    marker = "# The config pin is independent. This permit hash only identifies the received bytes."
    if original.count(marker) != 1:
        raise ValueError("CONTINUATION_BOOTSTRAP_INSERTION_POINT")
    result = original.replace(marker, "# Source-pinned support remains outside the frozen worker bundle.\n"
        + "\n".join(lines) + "\n" + marker)
    if len(result.encode()) > 16384:
        raise ValueError("CONTINUATION_BOOTSTRAP_TOO_LARGE")
    return result
