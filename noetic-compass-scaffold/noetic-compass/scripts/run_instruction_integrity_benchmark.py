"""Run a local Instruction Integrity fixture suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.cas_harness_instruction_integrity_benchmark import (  # noqa: E402
    load_instruction_integrity_benchmark_suite,
    run_instruction_integrity_benchmark_suite,
)


DEFAULT_FIXTURE = ROOT / "scenarios" / "instruction_integrity_benchmark_v0.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a shadow-only Instruction Integrity evaluation suite."
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--fail-on-gate", action="store_true")
    args = parser.parse_args()

    suite = load_instruction_integrity_benchmark_suite(args.fixture)
    result = run_instruction_integrity_benchmark_suite(suite)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.fail_on_gate and not result["gates"]["overall_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
