"""Read-only verification of the Attempt 6 PRE environment evidence."""

from __future__ import annotations

import json
from pathlib import Path
import sys


WORKER_ROOT = Path(
    "/workspace/cas-jlcv1-official-29551624-f3e3adad/"
    "repo/noetic-compass-scaffold/noetic-compass/live-trace-worker"
)
PRE_MAIN = Path(
    "/workspace/cas-jlcv1-official-29551624-f3e3adad/"
    "environment_pre/pre.environment.json"
)
sys.path.insert(0, str(WORKER_ROOT))

from research.jacobian_lens_environment_evidence import (  # noqa: E402
    load_environment_evidence,
    verify_current_runtime_files,
)


evidence = load_environment_evidence(PRE_MAIN)
result = verify_current_runtime_files(evidence)
print(
    json.dumps(
        {
            "main_path": str(evidence.main_path),
            "main_sha256": evidence.main_sha256,
            **result,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
