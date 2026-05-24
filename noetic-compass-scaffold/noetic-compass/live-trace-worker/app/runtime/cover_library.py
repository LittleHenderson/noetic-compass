"""Runtime-calibrated Stage 27F cover sets for live blindspot overlays.

This module is the worker-side truth for which CAS Foundation drives the
LIVE path can actually emit and intervene on. It deliberately does not mirror
UI labels by default: a drive is "supported" here only when the worker carries
real cover coordinates and calibration metrics for that drive.

Calibration source:
  atlas-viewer/test-fixtures/pythia_160m_reference_trace.json
  neuron_covers.row_reports

Those row reports provide class-level cover evidence:
  * neuron_cover: model-native coordinates, e.g. L5N2648
  * clean_margin: separation before targeted cover ablation
  * targeted_drop: margin collapse caused by the targeted cover ablation

The confidence shown by the cockpit is therefore a cover-level calibration
score, projected onto each member of that cover so the existing event schema
can render it. It is NOT a claim that each individual neuron was independently
scored as monosemantic. The score is:

    targeted_drop / clean_margin

rounded to three decimals. That is intentionally simple and auditable: it says
"how much of the clean class margin the targeted cover removed." If the value
falls outside the product confidence bands, the UI labels it unavailable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas.events import NeuronCoverMember, band_for_confidence


ALL_DRIVES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")

# Every drive in ALL_DRIVES below has Stage 27F Pythia-160M cover coordinates
# and clean_margin/targeted_drop evidence wired into this worker. Keep this
# tuple synced with COVER_LIBRARY; never add a drive here for UI convenience.
SUPPORTED_DRIVES: tuple[str, ...] = ALL_DRIVES


@dataclass(frozen=True)
class CoverCalibration:
    labels: tuple[str, ...]
    clean_margin: float
    targeted_drop: float

    @property
    def confidence(self) -> float | None:
        if self.clean_margin <= 0:
            return None
        return round(self.targeted_drop / self.clean_margin, 3)


CALIBRATED_COVERS: dict[str, CoverCalibration] = {
    # F1 Unity
    "F1A": CoverCalibration(("L5N2648", "L5N2948", "L5N325", "L5N2343"), 7.0724, 5.8215),
    "F1T": CoverCalibration(("L1N142", "L5N2346", "L5N1583", "L5N1127"), 8.1207, 3.2204),
    "F1f": CoverCalibration(("L5N84", "L5N1354", "L5N207", "L5N230"), 5.4925, 2.8805),
    "F1E": CoverCalibration(("L5N1580", "L5N529", "L5N2948", "L5N2648"), 8.0606, 5.6098),
    # F2 Wisdom
    "F2A": CoverCalibration(("L5N1849", "L5N3041", "L5N230", "L5N2225"), 6.6705, 2.9911),
    "F2T": CoverCalibration(("L5N1849", "L5N2225", "L5N3041", "L5N230"), 6.8221, 3.1402),
    "F2f": CoverCalibration(("L5N84", "L5N1354", "L5N207", "L5N230"), 7.3318, 3.0571),
    "F2E": CoverCalibration(("L5N230", "L5N1849", "L5N2225", "L5N3041"), 6.4502, 2.8014),
    # F3 Vitality
    "F3A": CoverCalibration(("L5N1849", "L5N3041", "L5N2225", "L5N230"), 7.4408, 3.6712),
    "F3T": CoverCalibration(("L5N84", "L5N230", "L5N1354", "L5N207"), 6.9120, 2.4988),
    "F3f": CoverCalibration(("L5N1849", "L5N230", "L5N3041", "L5N2225"), 5.8233, 2.9405),
    "F3E": CoverCalibration(("L1N142", "L1N480", "L1N890", "L5N230"), 7.5012, 3.6504),
    # F4 Connection
    "F4A": CoverCalibration(("L5N230", "L5N1849", "L5N2225", "L5N2346"), 6.7501, 2.8430),
    "F4T": CoverCalibration(("L5N2346", "L5N230", "L5N1583", "L5N1127"), 7.8104, 4.0817),
    "F4f": CoverCalibration(("L5N84", "L5N1354", "L5N207", "L5N230"), 5.6712, 2.3308),
    "F4E": CoverCalibration(("L5N230", "L5N2225", "L5N3041", "L5N1849"), 7.0418, 3.1190),
    # F5 Agency
    "F5A": CoverCalibration(("L1N142", "L5N2346", "L5N230", "L5N1583"), 8.2235, 4.5102),
    "F5T": CoverCalibration(("L1N142", "L5N230", "L5N1583", "L5N1127"), 7.3508, 3.6018),
    "F5f": CoverCalibration(("L5N230", "L5N1849", "L5N2225", "L5N3041"), 6.2901, 2.7740),
    "F5E": CoverCalibration(("L5N1580", "L5N529", "L5N2948", "L5N2648"), 7.9405, 5.2204),
    # F6 Structure
    "F6A": CoverCalibration(("L5N230", "L5N1849", "L5N2225", "L5N3041"), 6.4811, 2.6005),
    "F6T": CoverCalibration(("L5N84", "L5N1354", "L5N207", "L5N230"), 6.7233, 2.4421),
    "F6f": CoverCalibration(("L5N1849", "L5N230", "L5N3041", "L5N2225"), 5.9120, 2.5733),
    "F6E": CoverCalibration(("L5N230", "L5N1849", "L5N2225", "L5N3041"), 6.8902, 2.9908),
    # F7 Purpose
    "F7A": CoverCalibration(("L5N230", "L5N2346", "L5N1583", "L5N1127"), 7.1840, 3.4221),
    "F7T": CoverCalibration(("L5N2346", "L5N230", "L5N1583", "L5N1127"), 7.6038, 3.8011),
    "F7f": CoverCalibration(("L5N84", "L5N1354", "L5N207", "L5N230"), 5.7405, 2.2412),
    "F7E": CoverCalibration(("L5N230", "L5N1849", "L5N2225", "L5N3041"), 6.5908, 2.8830),
}

COVER_LIBRARY: dict[str, dict[str, tuple[str, ...]]] = {
    drive: {
        class_key: calibration.labels
        for class_key, calibration in CALIBRATED_COVERS.items()
        if class_key.startswith(drive)
    }
    for drive in ALL_DRIVES
}

_COORD_RE = re.compile(r"^L(\d+)N(\d+)$")


@dataclass(frozen=True)
class CoverCoord:
    layer: int
    index: int


def cover_for_drive(drive: str) -> dict[str, tuple[str, ...]]:
    """Return raw L{layer}N{index} labels for eraser hooks."""
    return COVER_LIBRARY.get(drive, {})


def cover_for_scope(scope: str) -> dict[str, tuple[str, ...]]:
    """Return one drive or all calibrated drives for blindspot overlays."""
    if scope == "all_7":
        out: dict[str, tuple[str, ...]] = {}
        for drive in SUPPORTED_DRIVES:
            out.update(cover_for_drive(drive))
        return out
    return cover_for_drive(scope)


def _make_member(label: str, class_key: str) -> NeuronCoverMember:
    """Build a typed cover member from Stage 27F class-level calibration."""
    calibration = CALIBRATED_COVERS.get(class_key)
    confidence = calibration.confidence if calibration else None
    return NeuronCoverMember(
        label=label,
        confidence=confidence,
        confidence_band=band_for_confidence(confidence),
        evidence_sources=[
            "Stage27F cover",
            "clean_margin",
            "targeted_drop",
        ]
        if confidence is not None
        else [],
    )


def cover_members_for_drive(drive: str) -> dict[str, list[NeuronCoverMember]]:
    """Return the calibrated cover classes for a single drive."""
    return {
        cls: [_make_member(label, cls) for label in labels]
        for cls, labels in cover_for_drive(drive).items()
    }


def cover_members_for_scope(scope: str) -> dict[str, list[NeuronCoverMember]]:
    """Return typed cover members for a single drive or all 7 drives."""
    return {
        cls: [_make_member(label, cls) for label in labels]
        for cls, labels in cover_for_scope(scope).items()
    }


def coords_for_drive(drive: str) -> list[CoverCoord]:
    """Parse L{layer}N{index} labels into coordinates for runtime hooks."""
    out: list[CoverCoord] = []
    for labels in cover_for_drive(drive).values():
        for label in labels:
            match = _COORD_RE.match(label)
            if not match:
                continue
            out.append(CoverCoord(layer=int(match.group(1)), index=int(match.group(2))))
    return out
