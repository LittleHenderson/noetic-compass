"""NeuronCoverMember schema + Stage 27F runtime-cover checks.

The cockpit's interpretable-blindspots feature relies on:
  1. NeuronCoverMember accepting typed records with confidence + band.
  2. band_for_confidence matching the spec bands.
  3. Placeholder confidence=None records staying valid for legacy traces.
  4. cover_members_for_drive emitting calibrated Pythia-160M F1-F7 covers.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.runtime.cover_library import (
    ALL_DRIVES,
    SUPPORTED_DRIVES,
    cover_members_for_drive,
    cover_members_for_scope,
    coords_for_drive,
)
from app.schemas.events import (
    NeuronCoverMember,
    NeuronCoversEvent,
    band_for_confidence,
)


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
        (0.95001, "unavailable"),
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


def test_member_typed_record_with_real_confidence():
    m = NeuronCoverMember(
        label="L5N2648",
        confidence=0.823,
        confidence_band="high",
        evidence_sources=["Stage27F cover", "clean_margin", "targeted_drop"],
    )
    assert m.label == "L5N2648"
    assert m.confidence == 0.823
    assert m.confidence_band == "high"
    assert m.evidence_sources == ["Stage27F cover", "clean_margin", "targeted_drop"]


def test_member_placeholder_record_is_valid_for_legacy_traces():
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


def test_cover_members_for_drive_emits_stage27f_calibrated_members():
    members_by_class = cover_members_for_drive("F1")
    assert set(members_by_class.keys()) == {"F1A", "F1T", "F1f", "F1E"}

    all_members = [m for ms in members_by_class.values() for m in ms]
    assert all(isinstance(m, NeuronCoverMember) for m in all_members)
    assert all(m.confidence is not None for m in all_members)
    assert all("targeted_drop" in m.evidence_sources for m in all_members)


def test_cover_members_for_drive_preserves_stage27f_labels_and_scores():
    members = cover_members_for_drive("F1")["F1A"]
    assert [m.label for m in members] == ["L5N2648", "L5N2948", "L5N325", "L5N2343"]
    assert members[0].confidence == 0.823
    assert members[0].confidence_band == "high"


def test_cover_members_for_unknown_drive_is_empty():
    assert cover_members_for_drive("F999") == {}


def test_supported_drives_are_runtime_calibrated():
    assert SUPPORTED_DRIVES == ALL_DRIVES
    for drive in ALL_DRIVES:
        covers = cover_members_for_drive(drive)
        assert set(covers.keys()) == {f"{drive}A", f"{drive}T", f"{drive}f", f"{drive}E"}
        assert all(member.confidence is not None for ms in covers.values() for member in ms)
        assert coords_for_drive(drive)


def test_all_7_scope_combines_every_calibrated_drive():
    covers = cover_members_for_scope("all_7")
    assert len(covers) == 28
    assert "F1A" in covers
    assert "F7E" in covers
