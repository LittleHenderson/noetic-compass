"""Run local CJT ungating checks and emit a readiness report.

This script can prove local engineering evidence. It cannot create legal
review, 30 trading days of paper proof, external red-team proof, or regulatory
approval.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.cjt_readiness import (  # noqa: E402
    build_cjt_production_readiness_report,
    collect_local_cjt_evidence,
)


TEST_GROUPS = {
    "cjt_compiler_syntax": ["tests/test_cjt_compiler_syntax.py"],
    "cjt_readiness": ["tests/test_cjt_readiness.py"],
    "execution_guards": [
        "tests/test_execution_guards.py",
        "tests/test_verifier.py::TestCASForexAuditor::test_full_accept_flow",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="Optional JSON output path.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    test_results: dict[str, bool] = {}
    command_results = {}

    for name, paths in TEST_GROUPS.items():
        cmd = [sys.executable, "-m", "pytest", *paths, "-q"]
        completed = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
        test_results[name] = completed.returncode == 0
        command_results[name] = {
            "command": " ".join(cmd),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        print(completed.stdout)
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)

    evidence = collect_local_cjt_evidence(root, test_results)
    report = build_cjt_production_readiness_report(evidence=evidence)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "local_evidence": evidence,
        "command_results": command_results,
        "readiness_report": report.model_dump(mode="json"),
        "summary": (
            "Local CJT syntax/no-ACCEPT evidence collected. External/time/legal/regulatory "
            "gates remain missing unless independently supplied."
        ),
    }
    text = json.dumps(payload, indent=2, default=str)
    print(text)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")

    return 0 if all(test_results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
