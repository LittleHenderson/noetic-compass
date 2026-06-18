"""Export a frozen PCBA/CJT risk direction from a passing W0 layer."""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.evaluate_cjt_bias_vibration_diagnostic import (  # noqa: E402
    CONTROL_LABEL,
    RISK_LABEL,
    build_delta_rows,
    load_dataset,
)


SCHEMA_VERSION = "cas_harness_cjt_bias_vibration_direction.v0"


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--layer", required=True, type=int)
    parser.add_argument("--output-direction", required=True, type=Path)
    parser.add_argument("--metadata-output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = export_cjt_bias_vibration_direction(
        dataset_path=args.dataset,
        layer=args.layer,
        output_direction_path=args.output_direction,
        metadata_output_path=args.metadata_output,
    )
    print(json.dumps(public_summary(metadata), indent=2, sort_keys=True))
    print(f"[cjt-direction] wrote {args.output_direction}")
    print(f"[cjt-direction] wrote {args.metadata_output}")
    return 0


def export_cjt_bias_vibration_direction(
    *,
    dataset_path: Path,
    layer: int,
    output_direction_path: Path,
    metadata_output_path: Path,
) -> dict[str, Any]:
    data = load_dataset(dataset_path, layer=layer)
    delta_rows = build_delta_rows(data)
    if delta_rows["status"] != "ready":
        raise RuntimeError(f"Delta rows are not ready: {delta_rows['status']}")
    x = delta_rows["features"].astype(np.float64)
    y = delta_rows["label"].astype(str)
    risk = x[y == RISK_LABEL]
    control = x[y == CONTROL_LABEL]
    if len(risk) == 0 or len(control) == 0:
        raise RuntimeError("Need both risk and control deltas to export direction")
    raw = risk.mean(axis=0) - control.mean(axis=0)
    norm = float(np.linalg.norm(raw))
    if norm < 1e-12:
        raise RuntimeError("Risk and control means coincide; no direction")
    direction = (raw / norm).astype(np.float32)
    output_direction_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_direction_path, direction)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "layer": int(layer),
        "direction_file": str(output_direction_path),
        "direction_norm": float(np.linalg.norm(direction)),
        "hidden_size": int(direction.shape[0]),
        "risk_row_count": int(len(risk)),
        "control_row_count": int(len(control)),
        "delta_label_distribution": dict(sorted(Counter(y.tolist()).items())),
        "role_distribution": dict(sorted(Counter(delta_rows["role"].astype(str).tolist()).items())),
        "family_distribution": dict(sorted(Counter(delta_rows["family"].astype(str).tolist()).items())),
        "claim": (
            "Frozen PCBA/CJT risk direction for causal-intervention testing only. "
            "This artifact by itself does not license causal proof, removal, reversal, "
            "or universal hidden-state prompt-injection/hallucination detection."
        ),
    }
    metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_output_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata


def public_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "layer": metadata["layer"],
        "hidden_size": metadata["hidden_size"],
        "direction_norm": metadata["direction_norm"],
        "risk_row_count": metadata["risk_row_count"],
        "control_row_count": metadata["control_row_count"],
        "claim": metadata["claim"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
