"""Add a derived composite label axis to a captured probe dataset."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--axis-name", required=True)
    parser.add_argument("--left-axis", required=True)
    parser.add_argument("--right-axis", required=True)
    parser.add_argument("--separator", default="|")
    parser.add_argument("--metadata-output", type=Path)
    parser.add_argument("--allow-overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = derive_axis(
        dataset=args.dataset,
        output=args.output,
        axis_name=args.axis_name,
        left_axis=args.left_axis,
        right_axis=args.right_axis,
        separator=args.separator,
        allow_overwrite=args.allow_overwrite,
    )
    metadata_path = args.metadata_output or args.output.with_suffix(".derived_axis_metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[derive-axis] wrote {args.output}")
    print(f"[derive-axis] wrote {metadata_path}")
    return 0


def derive_axis(
    *,
    dataset: Path,
    output: Path,
    axis_name: str,
    left_axis: str,
    right_axis: str,
    separator: str = "|",
    allow_overwrite: bool = False,
) -> dict[str, Any]:
    if not axis_name.strip():
        raise ValueError("axis_name is required")
    axis_name = axis_name.strip()
    with np.load(dataset, allow_pickle=True) as data:
        payload = {key: data[key] for key in data.files}
        axis_names = [str(axis) for axis in np.asarray(data["axis_names"], dtype=str)]
        if axis_name in axis_names and not allow_overwrite:
            raise ValueError(f"axis {axis_name!r} already exists; pass --allow-overwrite to replace it")
        left_key = f"labels_{left_axis}"
        right_key = f"labels_{right_axis}"
        if left_key not in data.files:
            raise ValueError(f"missing source label array: {left_key}")
        if right_key not in data.files:
            raise ValueError(f"missing source label array: {right_key}")
        left = np.asarray(data[left_key], dtype=str)
        right = np.asarray(data[right_key], dtype=str)
        if left.shape != right.shape:
            raise ValueError(f"source label arrays have different shapes: {left.shape} vs {right.shape}")
        labels = np.asarray(
            [
                f"{l}{separator}{r}" if str(l).strip() and str(r).strip() else ""
                for l, r in zip(left.tolist(), right.tolist(), strict=True)
            ],
            dtype="U64",
        )
    if axis_name not in axis_names:
        axis_names.append(axis_name)
    payload["axis_names"] = np.asarray(sorted(axis_names), dtype="U32")
    payload[f"labels_{axis_name}"] = labels
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **payload)
    nonempty = labels[labels != ""]
    class_counts = {
        str(label): int((nonempty == label).sum())
        for label in sorted(set(nonempty.tolist()))
    }
    return {
        "schema_version": "cas_harness_probe_dataset_derived_axis.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source_dataset": str(dataset),
        "output_dataset": str(output),
        "axis_name": axis_name,
        "left_axis": left_axis,
        "right_axis": right_axis,
        "separator": separator,
        "row_count": int(labels.shape[0]),
        "nonempty_row_count": int(nonempty.shape[0]),
        "class_count": len(class_counts),
        "class_distribution": class_counts,
        "important_limit": "Derived labels only. This is not a probe result, ablation result, verifier verdict, or Evidence Packet.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
