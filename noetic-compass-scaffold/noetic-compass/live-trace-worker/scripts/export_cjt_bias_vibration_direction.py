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
from scripts.build_cjt_bias_vibration_bank import (  # noqa: E402
    BENIGN_ROLE,
    INJECTION_ROLE,
    SUPPORTED_ROLE,
    TRUSTED_CORRECTION_ROLE,
    UNSUPPORTED_ROLE,
)


SCHEMA_VERSION = "cas_harness_cjt_bias_vibration_direction.v0"


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--layer", required=True, type=int)
    parser.add_argument("--output-direction", required=True, type=Path)
    parser.add_argument("--metadata-output", required=True, type=Path)
    parser.add_argument("--risk-roles", nargs="*", default=None)
    parser.add_argument("--control-roles", nargs="*", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = export_cjt_bias_vibration_direction(
        dataset_path=args.dataset,
        layer=args.layer,
        output_direction_path=args.output_direction,
        metadata_output_path=args.metadata_output,
        risk_roles=args.risk_roles,
        control_roles=args.control_roles,
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
    risk_roles: list[str] | None = None,
    control_roles: list[str] | None = None,
) -> dict[str, Any]:
    data = load_dataset(dataset_path, layer=layer)
    delta_rows = build_delta_rows(data)
    if delta_rows["status"] != "ready":
        raise RuntimeError(f"Delta rows are not ready: {delta_rows['status']}")
    x = delta_rows["features"].astype(np.float64)
    y = delta_rows["label"].astype(str)
    roles = delta_rows["role"].astype(str)
    resolved_risk_roles = tuple(risk_roles or [INJECTION_ROLE, UNSUPPORTED_ROLE])
    resolved_control_roles = tuple(control_roles or [BENIGN_ROLE, TRUSTED_CORRECTION_ROLE, SUPPORTED_ROLE])
    risk_mask = (y == RISK_LABEL) & np.isin(roles, resolved_risk_roles)
    control_mask = (y == CONTROL_LABEL) & np.isin(roles, resolved_control_roles)
    risk = x[risk_mask]
    control = x[control_mask]
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
        "risk_roles": list(resolved_risk_roles),
        "control_roles": list(resolved_control_roles),
        "selected_risk_role_distribution": dict(sorted(Counter(roles[risk_mask].tolist()).items())),
        "selected_control_role_distribution": dict(sorted(Counter(roles[control_mask].tolist()).items())),
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
        "risk_roles": metadata["risk_roles"],
        "control_roles": metadata["control_roles"],
        "claim": metadata["claim"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
