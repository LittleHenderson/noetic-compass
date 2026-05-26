from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts.derive_probe_dataset_axis import derive_axis


def _write_dataset(path: Path) -> None:
    np.savez_compressed(
        path,
        features=np.zeros((4, 2, 3), dtype=np.float16),
        layers=np.asarray([0, 1], dtype=np.int16),
        scenario_ids=np.asarray(["a", "b", "c", "d"], dtype="U8"),
        prompts=np.asarray(["pa", "pb", "pc", "pd"], dtype=object),
        token_counts=np.asarray([1, 1, 1, 1], dtype=np.int32),
        axis_names=np.asarray(["domain", "operator"], dtype="U32"),
        labels_domain=np.asarray(["P", "O", "P", ""], dtype="U64"),
        labels_operator=np.asarray(["^0", "^1", "^0", "^2"], dtype="U64"),
    )


def test_derive_axis_adds_composite_labels(tmp_path: Path):
    source = tmp_path / "source.npz"
    output = tmp_path / "derived.npz"
    _write_dataset(source)

    metadata = derive_axis(
        dataset=source,
        output=output,
        axis_name="element",
        left_axis="operator",
        right_axis="domain",
    )

    with np.load(output, allow_pickle=True) as data:
        assert set(np.asarray(data["axis_names"], dtype=str)) == {"domain", "element", "operator"}
        assert np.asarray(data["labels_element"], dtype=str).tolist() == ["^0|P", "^1|O", "^0|P", ""]
    assert metadata["class_count"] == 2
    assert metadata["class_distribution"] == {"^0|P": 2, "^1|O": 1}


def test_derive_axis_rejects_missing_source_axis(tmp_path: Path):
    source = tmp_path / "source.npz"
    output = tmp_path / "derived.npz"
    _write_dataset(source)

    with pytest.raises(ValueError, match="labels_noetic"):
        derive_axis(
            dataset=source,
            output=output,
            axis_name="element",
            left_axis="noetic",
            right_axis="domain",
        )
