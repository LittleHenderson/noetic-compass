from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[1] / "capture_stage6_role_bound_activations.py"
_SPEC = importlib.util.spec_from_file_location("capture_stage6_role_bound_activations", _MODULE_PATH)
assert _SPEC is not None
capture = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(capture)


def test_find_focus_char_index_uses_terminal_marker_not_earlier_letters() -> None:
    text = "A calls up B. A and B appear earlier. Focus: B."

    idx = capture._find_focus_char_index(text, "B")

    assert text[idx] == "B"
    assert idx == text.rfind("B")


def test_find_focus_char_index_accepts_marker_without_final_period() -> None:
    text = "A names the object; B compares it. Focus: A"

    idx = capture._find_focus_char_index(text, "A")

    assert text[idx] == "A"
    assert idx == text.rfind("A")


def test_find_focus_char_index_rejects_missing_terminal_marker() -> None:
    with pytest.raises(ValueError, match="Focus: A/B"):
        capture._find_focus_char_index("A names the object; B compares it.", "A")


def test_find_focus_char_index_rejects_mismatched_focus() -> None:
    with pytest.raises(ValueError, match="focus marker mismatch"):
        capture._find_focus_char_index("A names the object; B compares it. Focus: B.", "A")


def test_find_focus_char_index_rejects_invalid_expected_focus() -> None:
    with pytest.raises(ValueError, match="expected_focus"):
        capture._find_focus_char_index("A names the object; B compares it. Focus: A.", "C")


def test_find_token_for_char_maps_inside_span() -> None:
    offsets = [(0, 1), (1, 7), (7, 8), (8, 9)]

    assert capture._find_token_for_char(offsets, 8) == 3


def test_find_token_for_char_falls_back_to_nearest_whitespace_prefixed_token() -> None:
    offsets = [(0, 4), (4, 10), (12, 13), (13, 14)]

    assert capture._find_token_for_char(offsets, 11) == 2


def test_find_token_for_char_rejects_unmappable_offset() -> None:
    with pytest.raises(ValueError, match="could not map"):
        capture._find_token_for_char([(20, 21)], 1)
