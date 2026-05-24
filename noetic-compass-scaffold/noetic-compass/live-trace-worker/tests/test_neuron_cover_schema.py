"""NeuronCoverMember schema + band classification + emit-shape checks.

The cockpit's interpretable-blindspots feature relies on:
  1. NeuronCoverMember accepting typed records with confidence + band.
  2. ``band_for_confidence`` matching the spec bands (80-95 high / 60-79
     medium / 40-59 low / unavailable otherwise).
  3. Placeholder records (confidence=None) being valid — that's the
     "real probe scores not in-tree yet" path.
  4. ``cover_members_for_drive`` wrapping legacy string covers into the
     new shape.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.events import (
    NeuronCoverMember,
    NeuronCoversEvent,
    band_for_confidence,
)
from app.runtime.cover_library import cover_members_for_drive


# --- band_for_confidence --------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.80, "high"),
        (0.85, "high"),
        (0.95, "high"),
        (0.79, "medium"),
        (0.60, "medium"),
        (0.799999, "medium"),
        (0.40, "low"),
        (0.59, "low"),
        (0.599999, "low"),
        (0.39, "unavailable"),
        (0.95001, "unavailable"),  # >0.95 must NOT silently re-bucket
        (0.96, "unavailable"),
        (1.0, "unavailable"),
        (0.0, "unavailable"),
        (None, "unavailable"),
    ],
)
def test_band_for_confidence_boundaries(value, expected):
    assert band_for_confidence(value) == expected


def test_band_for_confidence_handles_nan():
    nan = float("nan")
    assert band_for_confidence(nan) == "unavailable"


# --- NeuronCoverMember ----------------------------------------------------


def test_member_typed_record_with_real_confidence():
    m = NeuronCoverMember(
        label="L3N142",
        confidence=0.84,
        confidence_band="high",
        evidence_sources=["probe", "ablation"],
    )
    assert m.label == "L3N142"
    assert m.confidence == 0.84
    assert m.confidence_band == "high"
    assert m.evidence_sources == ["probe", "ablation"]


def test_member_placeholder_record_is_valid():
    """confidence=None / band=unavailable is the supported placeholder.

    This is the path we ship today because per-neuron probe scores are
    not yet in-tree. The "unavailable" band exists precisely so we don't
    have to invent fake numbers.
    """
    m = NeuronCoverMember(label="L3N518")
    assert m.confidence is None
    assert m.confidence_band == "unavailable"
    assert m.evidence_sources == []


def test_member_label_must_be_string():
    with pytest.raises(ValidationError):
        NeuronCoverMember(label=42)  # type: ignore[arg-type]


def test_member_band_must_be_known_literal():
    with pytest.raises(ValidationError):
        NeuronCoverMember(
            label="L3N142",
            confidence=0.84,
            confidence_band="excellent",  # type: ignore[arg-type]
        )


# --- NeuronCoversEvent ----------------------------------------------------


def test_neuron_covers_event_carries_typed_members():
    event = NeuronCoversEvent(
        per_class_neuron_covers={
            "F1A": [
                NeuronCoverMember(label="L3N142"),
                NeuronCoverMember(
                    label="L3N518",
                    confidence=0.72,
                    confidence_band="medium",
                    evidence_sources=["probe"],
                ),
            ],
        },
    )
    f1a = event.per_class_neuron_covers["F1A"]
    assert [m.label for m in f1a] == ["L3N142", "L3N518"]
    assert f1a[0].confidence_band == "unavailable"
    assert f1a[1].confidence_band == "medium"


def test_neuron_covers_event_round_trip_json():
    event = NeuronCoversEvent(
        per_class_neuron_covers={
            "F1A": [NeuronCoverMember(label="L3N142")],
        },
    )
    payload = event.model_dump_json()
    rehydrated = NeuronCoversEvent.model_validate_json(payload)
    assert rehydrated.per_class_neuron_covers["F1A"][0].label == "L3N142"
    assert rehydrated.per_class_neuron_covers["F1A"][0].confidence_band == "unavailable"


# --- cover_library emit shape --------------------------------------------


def test_cover_members_for_drive_wraps_legacy_strings():
    """The legacy F1_COVER dict still uses bare label strings.

    cover_members_for_drive must promote them into typed members. Until
    per-neuron probe scores land in-tree, every member ships with
    confidence=None and band='unavailable' — the placeholder path.
    """
    members_by_class = cover_members_for_drive("F1")
    assert set(members_by_class.keys()) == {"F1A", "F1T", "F1f", "F1E"}

    all_members = [m for ms in members_by_class.values() for m in ms]
    assert all(isinstance(m, NeuronCoverMember) for m in all_members)
    # No probe scores in-tree -> every member is the placeholder shape.
    assert all(m.confidence is None for m in all_members)
    assert all(m.confidence_band == "unavailable" for m in all_members)
    assert all(m.evidence_sources == [] for m in all_members)


def test_cover_members_for_drive_preserves_label_strings():
    """Sanity: labels survive the wrap. Eraser-hook code parses these."""
    members = cover_members_for_drive("F1")["F1A"]
    assert [m.label for m in members] == ["L3N142", "L3N518", "L5N91", "L7N2204"]


def test_cover_members_for_unknown_drive_is_empty():
    assert cover_members_for_drive("F999") == {}


def test_cover_members_for_known_but_uncalibrated_drives_is_empty():
    """F2-F7 translations exist, but live runtime covers are F1-only today."""
    for drive in ("F2", "F3", "F4", "F5", "F6", "F7"):
        assert cover_members_for_drive(drive) == {}
