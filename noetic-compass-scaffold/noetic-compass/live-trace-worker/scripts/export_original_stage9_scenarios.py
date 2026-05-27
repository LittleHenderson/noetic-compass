#!/usr/bin/env python3
"""Regenerate the historical Stage 9 40-Element scenario fixture for diagnostics.

The original Stage 9 builder is not carried on master anymore. This script
loads that exact builder and its Stage 6 dependency from a historical commit,
runs `build_rows()`, and exports the rows in the modern scenario JSON shape so
text-baseline diagnostics can be reproduced without restoring the old research
tree.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any


DEFAULT_COMMIT = "be9b4a3"
RESEARCH_PREFIX = "noetic-compass-scaffold/noetic-compass/research/cas_probe"
DOMAIN_TO_CAS_DOMAIN = {
    "A": "P",
    "B": "C",
    "C": "E",
    "D": "O",
}


def _git_show(commit: str, relative_path: str) -> str:
    ref = f"{commit}:{RESEARCH_PREFIX}/{relative_path}"
    result = subprocess.run(
        ["git", "show", ref],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def _load_stage9_builder(commit: str, tmp_dir: Path) -> Any:
    for name in ("build_stage6_role_bound_full.py", "build_stage9_elements_fixture.py"):
        (tmp_dir / name).write_text(_git_show(commit, name), encoding="utf-8")

    sys.path.insert(0, str(tmp_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "historical_build_stage9_elements_fixture",
            tmp_dir / "build_stage9_elements_fixture.py",
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load historical Stage 9 builder.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        try:
            sys.path.remove(str(tmp_dir))
        except ValueError:
            pass


def _convert_row(row: dict[str, Any]) -> dict[str, Any]:
    legacy_domain = str(row["element_domain"])
    cas_domain = DOMAIN_TO_CAS_DOMAIN[legacy_domain]
    operator = str(row["element_cas_noetic"])
    element = f"{operator}|{cas_domain}"
    return {
        "id": str(row["sample_id"]),
        "prompt": str(row["english"]),
        "expected_cas_axes": {
            "domain": cas_domain,
            "operator": operator,
            "noetic": operator,
            "element": element,
        },
        "metadata": {
            "axis": "element",
            "legacy_element_code": str(row["element_label"]),
            "legacy_domain": legacy_domain,
            "legacy_domain_name": str(row["element_domain_name"]),
            "legacy_element_noetic": int(row["element_noetic_tks"]),
            "legacy_element_name": str(row["element_noetic_name"]),
            "counterfactual_pair_id": str(row["counterfactual_pair_id"]),
            "pair_kind": str(row["pair_kind"]),
            "paraphrase_family": str(row["paraphrase_family"]),
            "split": str(row["split"]),
            "source_profile": "exact_original_stage9_rolebound_fixture",
        },
    }


def export_scenarios(*, output: Path, commit: str, mode: str) -> dict[str, Any]:
    with TemporaryDirectory() as td:
        module = _load_stage9_builder(commit, Path(td))
        rows = module.build_rows(mode)

    scenarios = [_convert_row(row) for row in rows]
    payload = {
        "schema_version": "cas_harness_original_stage9_scenarios_export.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source_commit": commit,
        "source_builder": f"{RESEARCH_PREFIX}/build_stage9_elements_fixture.py",
        "mode": mode,
        "axis": "element",
        "scenario_count": len(scenarios),
        "important_limit": (
            "Scenario export only. This is not a probe result, ablation result, "
            "verifier verdict, or Evidence Packet."
        ),
        "scenarios": scenarios,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--commit", default=DEFAULT_COMMIT)
    parser.add_argument("--mode", choices=("pilot", "full"), default="pilot")
    args = parser.parse_args()

    payload = export_scenarios(output=args.output, commit=args.commit, mode=args.mode)
    print(f"wrote {args.output}")
    print(f"scenarios={payload['scenario_count']}")
    print(f"source_commit={payload['source_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
