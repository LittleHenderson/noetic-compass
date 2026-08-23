"""Capture one byte-attested local open-weight generation trajectory.

This command never downloads model files.  It requires an existing absolute
local snapshot, verifies the loaded parameter values against its safetensors
values, consumes the in-repository architecture adapter, and persists
create-once artifacts.  Success is an engineering-capture result only; the
receipt is always NOT_PACKET_ELIGIBLE and NOT_A_SCIENTIFIC_EXPERIMENT_RESULT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from app.runtime.open_weight.artifacts import persist_capture_create_new  # noqa: E402
from app.runtime.open_weight.engine import (  # noqa: E402
    InterventionSpec,
    RuntimeLoadConfig,
    capture_greedy_trajectory,
    load_open_weight_runtime,
)
from app.runtime.open_weight.identity import LocalModelSnapshot  # noqa: E402


DEFAULT_ADAPTER_SOURCE = (
    WORKER_ROOT.parent / "api" / "services" / "cas_harness_interpretability_adapter.py"
)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scenario, scenario_snapshot = _load_scenario(args.scenario_json)
    intervention = _load_intervention(args.intervention_json)
    runtime = load_open_weight_runtime(
        RuntimeLoadConfig(
            snapshot=LocalModelSnapshot(
                model_id=args.model_id,
                revision=args.revision,
                snapshot_root=args.snapshot_root,
                model_storage_root=args.model_storage_root,
            ),
            adapter_source_path=DEFAULT_ADAPTER_SOURCE,
            entrypoint_source_path=Path(__file__).resolve(),
            device=args.device,
            dtype=args.dtype,
        )
    )
    capture = capture_greedy_trajectory(
        runtime,
        scenario_id=scenario["scenario_id"],
        prompt=scenario["prompt"],
        max_new_tokens=args.max_new_tokens,
        intervention=intervention,
        seed=args.seed,
        scenario_source=scenario_snapshot,
    )
    receipt = persist_capture_create_new(
        runtime=runtime,
        capture=capture,
        output_directory=args.output_directory,
        artifact_stem=args.artifact_stem,
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "packet_eligibility": receipt["packet_eligibility"],
                "scientific_status": receipt["scientific_status"],
                "receipt_sha256": receipt["receipt_sha256"],
                "tensor_sha256": receipt["output"]["tensor_sha256"],
                "generated_text": receipt["output"]["generated_text"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--snapshot-root", required=True, type=Path)
    parser.add_argument("--model-storage-root", required=True, type=Path)
    parser.add_argument("--scenario-json", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--artifact-stem", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", choices=("auto",), default="auto")
    parser.add_argument("--intervention-json", type=Path)
    return parser


def _load_scenario(path: Path) -> tuple[dict[str, str], dict[str, object]]:
    if not path.is_absolute() or not path.is_file():
        raise ValueError("scenario-json must be an existing absolute file")
    raw = path.read_bytes()
    value = _strict_json(raw, "scenario")
    if set(value) != {"schema_version", "scenario_id", "prompt"}:
        raise ValueError("scenario keyset must be schema_version/scenario_id/prompt")
    if value["schema_version"] != "cas_open_weight_capture_scenario.v1":
        raise ValueError("scenario schema_version mismatch")
    for key in ("scenario_id", "prompt"):
        if not isinstance(value[key], str) or not value[key]:
            raise ValueError(f"scenario {key} must be non-empty text")
    return (
        {"scenario_id": value["scenario_id"], "prompt": value["prompt"]},
        {
            "path": str(path),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
            "snapshot_semantics": "one immutable byte snapshot strict-parsed and hashed",
        },
    )


def _load_intervention(path: Path | None) -> InterventionSpec:
    if path is None:
        return InterventionSpec()
    if not path.is_absolute() or not path.is_file():
        raise ValueError("intervention-json must be an existing absolute file")
    value = _strict_json(path.read_bytes(), "intervention")
    required = {
        "schema_version",
        "mode",
        "layer_index",
        "active_steps",
        "vector",
        "max_vector_norm",
    }
    if set(value) != required:
        raise ValueError("intervention keyset mismatch")
    if value["schema_version"] != "cas_open_weight_intervention.v1":
        raise ValueError("intervention schema_version mismatch")
    active_steps = value["active_steps"]
    vector = value["vector"]
    if not isinstance(active_steps, list):
        raise ValueError("intervention active_steps must be a list")
    if vector is not None and not isinstance(vector, list):
        raise ValueError("intervention vector must be a list or null")
    return InterventionSpec(
        mode=value["mode"],
        layer_index=value["layer_index"],
        active_steps=tuple(active_steps),
        vector=tuple(float(item) for item in vector) if vector is not None else None,
        max_vector_norm=value["max_vector_norm"],
    )


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key in {label}: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number in {label}: {value}")

    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=pairs_hook,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
