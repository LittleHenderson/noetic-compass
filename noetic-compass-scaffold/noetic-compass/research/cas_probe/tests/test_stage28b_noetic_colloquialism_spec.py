from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage28b_noetic_colloquialism_realization_spec.py"


def _load_module(name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, SPEC)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_stage28b_payload_validates() -> None:
    stage28b = _load_module("stage28b_spec_valid")

    payload = stage28b.stage28b_payload()

    assert payload["status"] == "PREREGISTERED_LOCAL_FORWARD_PASS"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["locked_probe_readout"]["layer"] == 5
    assert payload["claim_boundary"]["pass_status"] == "PASS_BOUNDED_NOETIC_COLLOQUIALISM_REALIZATION"


def test_stage28b_fixture_is_balanced_and_natural_language() -> None:
    stage28b = _load_module("stage28b_spec_fixture")
    payload = stage28b.stage28b_payload()

    counts: dict[str, int] = {}
    for row in payload["colloquialism_fixture"]:
        counts[row["noetic"]] = counts.get(row["noetic"], 0) + 1
        assert "^" not in row["phrase"]
        assert "|" not in row["phrase"]

    assert set(counts) == {"^0", "^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9"}
    assert set(counts.values()) == {4}
    assert len(payload["colloquialism_fixture"]) == 40


def test_stage28b_locks_involution_pairs_and_forbidden_claims() -> None:
    stage28b = _load_module("stage28b_spec_pairs")
    payload = stage28b.stage28b_payload()

    assert tuple(tuple(x) for x in payload["required_inputs"]["involution_pairs"]) == (
        ("^2", "^3"),
        ("^5", "^6"),
        ("^8", "^9"),
    )
    forbidden = payload["claim_boundary"]["forbidden_claims"]
    assert "Noetic clusters" in forbidden
    assert "free-form generation control" in forbidden


def test_stage28b_validation_rejects_wrong_runtime_readout() -> None:
    stage28b = _load_module("stage28b_spec_invalid")
    payload = stage28b.stage28b_payload()
    payload["required_inputs"]["runtime_readout"]["name"] = "final_token"

    errors = stage28b.validate_stage28b_payload(payload)

    assert "required_inputs" in errors
